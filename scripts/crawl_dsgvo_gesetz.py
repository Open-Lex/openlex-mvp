#!/usr/bin/env python3
"""
crawl_dsgvo_gesetz.py – Crawlt alle DSGVO-Artikel (1-99) und
Erwägungsgründe (1-173) von dsgvo-gesetz.de.

Speichert als JSON in data/dsgvo_komplett/artikel/ und
data/dsgvo_komplett/erwaegungsgruende/.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup, Tag

BASE_DIR = os.path.expanduser("~/openlex-mvp")
OUT_DIR = os.path.join(BASE_DIR, "data", "dsgvo_komplett")
ART_DIR = os.path.join(OUT_DIR, "artikel")
EG_DIR = os.path.join(OUT_DIR, "erwaegungsgruende")
PROGRESS_FILE = os.path.join(BASE_DIR, "dsgvo_reload_progress.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (OpenLex-MVP Academic Research Bot)"}
DELAY = 1.0  # Sekunden zwischen Requests

# Kapitelzuordnung Art. → Kapitel
KAPITEL = {
    range(1, 5): "Kapitel 1 – Allgemeine Bestimmungen",
    range(5, 12): "Kapitel 2 – Grundsätze",
    range(12, 24): "Kapitel 3 – Rechte der betroffenen Person",
    range(24, 44): "Kapitel 4 – Verantwortlicher und Auftragsverarbeiter",
    range(44, 50): "Kapitel 5 – Übermittlungen personenbezogener Daten an Drittländer oder an internationale Organisationen",
    range(50, 60): "Kapitel 6 – Unabhängige Aufsichtsbehörden",
    range(60, 77): "Kapitel 7 – Zusammenarbeit und Kohärenz",
    range(77, 85): "Kapitel 8 – Rechtsbehelfe, Haftung und Sanktionen",
    range(85, 92): "Kapitel 9 – Vorschriften für besondere Verarbeitungssituationen",
    range(92, 94): "Kapitel 10 – Delegierte Rechtsakte und Durchführungsrechtsakte",
    range(94, 100): "Kapitel 11 – Schlussbestimmungen",
}


def get_kapitel(art_nr: int) -> str:
    for rng, name in KAPITEL.items():
        if art_nr in rng:
            return name
    return ""


def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_progress(data: dict):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_url(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, timeout=30, headers=HEADERS)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        print(f"    FEHLER: {e}")
        return None


def clean_text(text: str) -> str:
    """Bereinigt extrahierten Text."""
    # Doppelte Leerzeilen reduzieren
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Führende/nachfolgende Whitespace pro Zeile
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def extract_article(soup: BeautifulSoup, art_nr: int) -> dict | None:
    """Extrahiert einen DSGVO-Artikel aus der gecrawlten Seite."""

    # 1. Titel extrahieren
    h1 = soup.find("h1")
    raw_title = h1.get_text(strip=True) if h1 else ""

    # Titel bereinigen: "Art. 17 DSGVORecht auf Löschung..." → "Recht auf Löschung..."
    titel = ""
    m = re.search(r"DSGVO\s*[–—-]?\s*(.+)", raw_title)
    if m:
        titel = m.group(1).strip()
    elif raw_title:
        # Fallback: Alles nach "Art. N "
        m2 = re.search(r"Art\.?\s*\d+\s*(?:DSGVO)?\s*(.+)", raw_title)
        if m2:
            titel = m2.group(1).strip()

    # 2. Artikeltext extrahieren
    content = soup.find("div", class_="entry-content")
    if not content:
        content = soup.find("article")
    if not content:
        content = soup.find("main")
    if not content:
        return None

    # Finde den Gesetzestext: Alles vor "Passende Erwägungsgründe" oder ähnlichen Abschnitten
    article_text_parts = []
    eg_section_found = False

    for child in content.children:
        if not isinstance(child, Tag):
            text = str(child).strip()
            if text:
                article_text_parts.append(text)
            continue

        tag_text = child.get_text(strip=True)

        # Stoppe vor den Querverweis-Sektionen
        if child.name in ("h2", "h3", "h4", "strong", "b"):
            if any(kw in tag_text.lower() for kw in
                   ["passende erwägungsgründe", "passende erwaegungsgruende",
                    "passende paragraphen", "suitable recitals",
                    "passende artikel", "kommentare"]):
                eg_section_found = True
                break

        # Auch im Text einer div/p nach dem Marker suchen
        if child.name in ("div", "p", "section"):
            inner = child.get_text(strip=True)
            if any(kw in inner.lower() for kw in
                   ["passende erwägungsgründe", "passende erwaegungsgruende",
                    "passende paragraphen"]) and len(inner) < 200:
                eg_section_found = True
                break

        # Skip Navigation
        if child.name == "nav" or (child.get("class") and any("nav" in c for c in child.get("class", []))):
            continue
        if child.name in ("script", "style", "aside"):
            continue

        text = child.get_text("\n", strip=True)
        if text and len(text) > 3:
            # Skip offensichtliche Navigation/Breadcrumbs
            if text.startswith("←") or text.startswith("→"):
                continue
            if "Nächster Artikel" in text or "Vorheriger Artikel" in text:
                continue
            if "dsgvo-gesetz.de" in text.lower() and len(text) < 100:
                continue
            article_text_parts.append(text)

    article_text = "\n".join(article_text_parts)
    article_text = clean_text(article_text)

    # Entferne den Titel am Anfang (falls im Text wiederholt)
    if article_text.startswith(f"Art. {art_nr}"):
        first_newline = article_text.find("\n")
        if first_newline > 0 and first_newline < 200:
            article_text = article_text[first_newline:].strip()

    # 3. Passende Erwägungsgründe extrahieren
    eg_list = []
    eg_section = None

    for heading in content.find_all(["h2", "h3", "h4", "p", "div", "strong"]):
        ht = heading.get_text(strip=True).lower()
        if "passende erwägungsgründe" in ht or "passende erwaegungsgruende" in ht or "suitable recitals" in ht:
            eg_section = heading
            break

    if eg_section:
        # Sammle alle Links nach der Überschrift bis zur nächsten Sektion
        sibling = eg_section.find_next_sibling()
        while sibling:
            if sibling.name in ("h2", "h3", "h4"):
                break
            for link in (sibling.find_all("a") if isinstance(sibling, Tag) else []):
                text = link.get_text(strip=True)
                href = link.get("href", "")
                # Pattern: "(26) Keine Anwendung auf anonymisierte Daten" oder "Nr. 26"
                m = re.search(r"\((\d+)\)\s*(.*)", text)
                if m:
                    eg_list.append({"nr": int(m.group(1)), "titel": m.group(2).strip()})
                else:
                    m2 = re.search(r"(?:Nr\.?\s*)?(\d+)", text)
                    if m2 and "erwaegungsgruende" in href:
                        eg_list.append({"nr": int(m2.group(1)), "titel": text.strip()})
            sibling = sibling.find_next_sibling()

    # 4. Passende BDSG-Paragraphen extrahieren
    bdsg_list = []
    bdsg_section = None

    for heading in content.find_all(["h2", "h3", "h4", "p", "div", "strong"]):
        ht = heading.get_text(strip=True).lower()
        if "passende paragraphen" in ht or "passende §" in ht or "bdsg" in ht:
            if "passend" in ht:
                bdsg_section = heading
                break

    if bdsg_section:
        sibling = bdsg_section.find_next_sibling()
        while sibling:
            if sibling.name in ("h2", "h3", "h4"):
                break
            for link in (sibling.find_all("a") if isinstance(sibling, Tag) else []):
                text = link.get_text(strip=True)
                href = link.get("href", "")
                m = re.search(r"(§\s*\d+[a-z]?)\s*BDSG\s*(.*)", text)
                if m:
                    bdsg_list.append({"paragraph": m.group(1).strip(), "titel": m.group(2).strip()})
                elif "bdsg" in href:
                    bdsg_list.append({"paragraph": text.strip(), "titel": ""})
            sibling = sibling.find_next_sibling()

    if not article_text or len(article_text) < 20:
        return None

    return {
        "artikel": f"Art. {art_nr}",
        "titel": titel,
        "kapitel": get_kapitel(art_nr),
        "text": article_text,
        "passende_erwaegungsgruende": eg_list,
        "passende_bdsg": bdsg_list,
    }


def extract_eg(soup: BeautifulSoup, eg_nr: int) -> dict | None:
    """Extrahiert einen Erwägungsgrund aus der gecrawlten Seite."""

    # 1. Titel
    h1 = soup.find("h1")
    raw_title = h1.get_text(strip=True) if h1 else ""

    titel = ""
    # Pattern: "Erwägungsgrund 26Keine Anwendung auf anonymisierte Daten"
    m = re.search(r"Erwägungsgrund\s*\d+\s*[–—-]?\s*(.+)", raw_title)
    if m:
        titel = m.group(1).strip()
    elif raw_title:
        # Fallback: Alles nach der Nummer
        m2 = re.search(r"\d+\s*[–—-]?\s*(.+)", raw_title)
        if m2:
            titel = m2.group(1).strip()

    # 2. Text extrahieren
    content = soup.find("div", class_="entry-content")
    if not content:
        content = soup.find("article")
    if not content:
        content = soup.find("main")
    if not content:
        return None

    text_parts = []
    for child in content.children:
        if not isinstance(child, Tag):
            text = str(child).strip()
            if text:
                text_parts.append(text)
            continue

        tag_text = child.get_text(strip=True)

        # Stoppe vor Querverweisen
        if child.name in ("h2", "h3", "h4", "strong"):
            lower = tag_text.lower()
            if any(kw in lower for kw in ["passende artikel", "passende art", "suitable"]):
                break

        if child.name in ("script", "style", "nav", "aside"):
            continue

        text = child.get_text("\n", strip=True)
        if text and len(text) > 3:
            if text.startswith("←") or text.startswith("→"):
                continue
            if "Nächster" in text or "Vorheriger" in text:
                continue
            if "dsgvo-gesetz.de" in text.lower() and len(text) < 100:
                continue
            text_parts.append(text)

    eg_text = "\n".join(text_parts)
    eg_text = clean_text(eg_text)

    # Entferne Titel-Wiederholung am Anfang
    if eg_text.startswith(("Erwägungsgrund", "Nr.")):
        first_newline = eg_text.find("\n")
        if first_newline > 0 and first_newline < 200:
            eg_text = eg_text[first_newline:].strip()

    # 3. Passende Artikel
    passende_artikel = []
    art_section = None
    for heading in content.find_all(["h2", "h3", "h4", "p", "div", "strong"]):
        ht = heading.get_text(strip=True).lower()
        if "passende artikel" in ht or "passende art" in ht:
            art_section = heading
            break

    if art_section:
        sibling = art_section.find_next_sibling()
        while sibling:
            if sibling.name in ("h2", "h3", "h4"):
                break
            for link in (sibling.find_all("a") if isinstance(sibling, Tag) else []):
                text = link.get_text(strip=True)
                m = re.search(r"Art\.?\s*(\d+)", text)
                if m:
                    passende_artikel.append(f"Art. {m.group(1)}")
            sibling = sibling.find_next_sibling()

    if not eg_text or len(eg_text) < 20:
        return None

    return {
        "nr": eg_nr,
        "titel": titel,
        "text": eg_text,
        "passende_artikel": passende_artikel,
    }


def crawl_articles(progress: dict) -> tuple[int, int, list[int]]:
    """Crawlt alle DSGVO-Artikel. Returns (total, success, failed_list)."""
    done = set(progress.get("artikel_done", []))
    failed = list(progress.get("artikel_failed", []))
    success = len(done)

    print("\n" + "=" * 60)
    print("DSGVO-Artikel crawlen (Art. 1-99)")
    print("=" * 60)

    for art_nr in range(1, 100):
        if art_nr in done:
            continue

        url = f"https://dsgvo-gesetz.de/art-{art_nr}-dsgvo/"
        print(f"  Art. {art_nr:>2}: ", end="", flush=True)

        soup = fetch_url(url)
        if soup is None:
            print("NICHT GEFUNDEN / FEHLER")
            if art_nr not in failed:
                failed.append(art_nr)
            progress["artikel_failed"] = failed
            save_progress(progress)
            time.sleep(DELAY)
            continue

        data = extract_article(soup, art_nr)
        if data is None:
            print("KEIN TEXT EXTRAHIERT")
            if art_nr not in failed:
                failed.append(art_nr)
            progress["artikel_failed"] = failed
            save_progress(progress)
            time.sleep(DELAY)
            continue

        # Speichern
        out_path = os.path.join(ART_DIR, f"art_{art_nr}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        eg_count = len(data["passende_erwaegungsgruende"])
        bdsg_count = len(data["passende_bdsg"])
        print(f"{data['titel'][:40]:<40} ({len(data['text']):>5} Z, {eg_count} EG, {bdsg_count} BDSG)")

        done.add(art_nr)
        success += 1
        progress["artikel_done"] = sorted(done)
        progress["artikel_failed"] = [x for x in failed if x not in done]
        save_progress(progress)

        if art_nr < 99:
            time.sleep(DELAY)

    return 99, success, [x for x in failed if x not in done]


def crawl_egs(progress: dict) -> tuple[int, int, list[int]]:
    """Crawlt alle 173 Erwägungsgründe. Returns (total, success, failed_list)."""
    done = set(progress.get("eg_done", []))
    failed = list(progress.get("eg_failed", []))
    success = len(done)

    print("\n" + "=" * 60)
    print("Erwägungsgründe crawlen (1-173)")
    print("=" * 60)

    for eg_nr in range(1, 174):
        if eg_nr in done:
            continue

        url = f"https://dsgvo-gesetz.de/erwaegungsgruende/nr-{eg_nr}/"
        print(f"  EG {eg_nr:>3}: ", end="", flush=True)

        soup = fetch_url(url)
        if soup is None:
            print("NICHT GEFUNDEN / FEHLER")
            if eg_nr not in failed:
                failed.append(eg_nr)
            progress["eg_failed"] = failed
            save_progress(progress)
            time.sleep(DELAY)
            continue

        data = extract_eg(soup, eg_nr)
        if data is None:
            print("KEIN TEXT EXTRAHIERT")
            if eg_nr not in failed:
                failed.append(eg_nr)
            progress["eg_failed"] = failed
            save_progress(progress)
            time.sleep(DELAY)
            continue

        # Speichern
        out_path = os.path.join(EG_DIR, f"eg_{eg_nr}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        art_count = len(data["passende_artikel"])
        print(f"{data['titel'][:40]:<40} ({len(data['text']):>5} Z, {art_count} Art.)")

        done.add(eg_nr)
        success += 1
        progress["eg_done"] = sorted(done)
        progress["eg_failed"] = [x for x in failed if x not in done]
        save_progress(progress)

        if eg_nr < 173:
            time.sleep(DELAY)

    return 173, success, [x for x in failed if x not in done]


def main():
    os.makedirs(ART_DIR, exist_ok=True)
    os.makedirs(EG_DIR, exist_ok=True)

    progress = load_progress()

    # Artikel crawlen
    art_total, art_success, art_failed = crawl_articles(progress)
    print(f"\n  Artikel: {art_success}/{art_total} erfolgreich")
    if art_failed:
        print(f"  Fehlgeschlagen: {art_failed}")

    # Erwägungsgründe crawlen
    eg_total, eg_success, eg_failed = crawl_egs(progress)
    print(f"\n  Erwägungsgründe: {eg_success}/{eg_total} erfolgreich")
    if eg_failed:
        print(f"  Fehlgeschlagen: {eg_failed}")

    # Gesamtstatistik
    progress["schritt_1"] = {
        "status": "done",
        "artikel_gecrawlt": art_success,
        "artikel_fehlgeschlagen": art_failed,
        "eg_gecrawlt": eg_success,
        "eg_fehlgeschlagen": eg_failed,
    }
    save_progress(progress)

    print("\n" + "=" * 60)
    print("CRAWLER ABGESCHLOSSEN")
    print(f"  Artikel: {art_success}/{art_total}")
    print(f"  Erwägungsgründe: {eg_success}/{eg_total}")
    print("=" * 60)


if __name__ == "__main__":
    main()
