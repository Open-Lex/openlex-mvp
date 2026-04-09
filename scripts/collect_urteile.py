#!/usr/bin/env python3
"""
collect_urteile.py – Lädt Urteile von Open Legal Data und EuGH-Schlüssel-
entscheidungen (via EU Cellar API), parst den Volltext und speichert sie
als JSON in data/urteile/.
"""

from __future__ import annotations

import json
import os
import re
import time
import warnings

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "urteile")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0",
}

# Open Legal Data API – Suchbegriffe
OLD_API_BASE = "https://de.openlegaldata.io/api/cases/"
OLD_SEARCH_TERMS = ["DSGVO", "Datenschutz-Grundverordnung", "BDSG", "Datenschutz"]
OLD_PAGE_SIZE = 20
RATE_LIMIT_SECONDS = 1.0

# EuGH-Schlüsselentscheidungen zum Datenschutz
# Format: (Kurzname, Rechtssache, CELEX-Nummer)
EUGH_ENTSCHEIDUNGEN = [
    ("Schrems I",      "C-362/14", "62014CJ0362"),
    ("Schrems II",     "C-311/18", "62018CJ0311"),
    ("Google Spain",   "C-131/12", "62012CJ0131"),
    ("Meta/Facebook",  "C-252/21", "62021CJ0252"),
    ("Deutsche Post",  "C-34/21",  "62021CJ0034"),
    ("CNIL/Google",    "C-507/17", "62017CJ0507"),
]

CELLAR_URL = "https://publications.europa.eu/resource/celex/{celex}.DEU"

# Verweis-Regex (gleich wie in collect_gesetze.py)
VERWEIS_RE = re.compile(
    r"(?:§§?\s*\d+[a-z]?(?:\s*(?:Abs\.|Absatz|S\.|Satz|Nr\.|Nummer)\s*\d+)*"
    r"\s+[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*)"
    r"|(?:Art\.?\s*\d+\s+[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*)"
)

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def find_verweise(text: str) -> list[str]:
    """Findet Normverweise im Text."""
    return list(set(VERWEIS_RE.findall(text)))


def sanitize_filename(name: str) -> str:
    """Entfernt Zeichen, die in Dateinamen problematisch sind."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def save_json(data: dict, filename: str) -> None:
    """Speichert ein Dict als JSON-Datei."""
    path = os.path.join(OUTPUT_DIR, sanitize_filename(filename))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 1. Open Legal Data API
# ---------------------------------------------------------------------------


def fetch_openlegaldata() -> list[dict]:
    """
    Durchsucht die Open Legal Data API nach Datenschutz-Urteilen.
    Paginiert durch alle Ergebnisse mit Rate Limiting.
    """
    print("\n--- Open Legal Data API ---")

    alle_urteile = []
    gesehene_ids = set()

    for suchbegriff in OLD_SEARCH_TERMS:
        print(f"\n  Suche nach: '{suchbegriff}' ...")
        url = OLD_API_BASE
        params = {
            "search": suchbegriff,
            "format": "json",
            "page_size": OLD_PAGE_SIZE,
        }

        seite = 0
        while url:
            seite += 1
            try:
                resp = requests.get(
                    url, params=params if seite == 1 else None,
                    headers=HEADERS, timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
            except requests.exceptions.ConnectionError:
                print("    WARNUNG: API nicht erreichbar (ConnectionError). Überspringe.")
                break
            except requests.exceptions.Timeout:
                print("    WARNUNG: API-Timeout. Überspringe.")
                break
            except requests.exceptions.HTTPError as e:
                print(f"    WARNUNG: HTTP-Fehler {e}. Überspringe.")
                break
            except Exception as e:
                print(f"    FEHLER: {e}")
                break

            results = data.get("results", [])
            if not results:
                break

            for case in results:
                case_id = case.get("id")
                if case_id in gesehene_ids:
                    continue
                gesehene_ids.add(case_id)

                # Felder extrahieren
                gericht = case.get("court", {})
                if isinstance(gericht, dict):
                    gericht_name = gericht.get("name", "Unbekannt")
                else:
                    gericht_name = str(gericht)

                datum = case.get("date", "")
                aktenzeichen = case.get("file_number", "")
                volltext = case.get("content", "") or ""

                # HTML-Tags aus Volltext entfernen
                if "<" in volltext:
                    volltext = BeautifulSoup(volltext, "lxml").get_text(
                        separator="\n", strip=True
                    )

                verweise = find_verweise(volltext)

                eintrag = {
                    "quelle": "openlegaldata",
                    "gericht": gericht_name,
                    "datum": datum,
                    "aktenzeichen": aktenzeichen,
                    "volltext": volltext[:50000],  # Begrenze auf 50k Zeichen
                    "normbezuege": verweise,
                }
                alle_urteile.append(eintrag)

                # Dateiname: Gericht_Aktenzeichen.json
                az_clean = re.sub(r'[\s/\\]', '_', aktenzeichen) if aktenzeichen else str(case_id)
                fname = f"OLD_{gericht_name[:20]}_{az_clean}.json"
                save_json(eintrag, fname)

            print(f"    Seite {seite}: {len(results)} Ergebnisse "
                  f"(gesamt bisher: {len(alle_urteile)})")

            # Nächste Seite
            url = data.get("next")
            if url:
                params = None  # next-URL enthält bereits alle Parameter
                time.sleep(RATE_LIMIT_SECONDS)

    print(f"\n  => {len(alle_urteile)} Urteile von Open Legal Data geladen.")
    return alle_urteile


# ---------------------------------------------------------------------------
# 2. EuGH-Entscheidungen (EU Cellar API)
# ---------------------------------------------------------------------------


def fetch_eugh_entscheidung(name: str, rechtssache: str, celex: str) -> dict | None:
    """Lädt eine einzelne EuGH-Entscheidung über die EU Cellar API."""
    url = CELLAR_URL.format(celex=celex)
    print(f"  Lade {name} ({rechtssache}) ...")

    try:
        resp = requests.get(
            url,
            headers={
                "Accept": "application/xhtml+xml, text/html",
                "User-Agent": HEADERS["User-Agent"],
            },
            timeout=60,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"    FEHLER: {e}")
        return None

    if len(resp.text) < 1000:
        print(f"    WARNUNG: Antwort zu kurz ({len(resp.text)} Bytes). Überspringe.")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # Volltext aus allen relevanten <p>-Elementen extrahieren
    # EUR-Lex verwendet verschiedene CSS-Klassen je nach Dokumentformat:
    #   Formex-Legacy: normal, pnormal, sum-title-1, index
    #   Formex-COJ:    coj-normal, coj-pnormal, coj-sum-title-1, coj-index, coj-count
    RELEVANT_CLASSES = {
        "normal", "pnormal", "sum-title-1", "index",
        "coj-normal", "coj-pnormal", "coj-sum-title-1", "coj-index", "coj-count",
        "oj-normal",
    }
    text_parts = []
    for p in soup.find_all("p"):
        cls = set(p.get("class", []))
        if cls & RELEVANT_CLASSES:
            txt = p.get_text(strip=True)
            if txt:
                text_parts.append(txt)

    volltext = "\n".join(text_parts)
    if not volltext:
        print(f"    WARNUNG: Kein Text extrahiert.")
        return None

    # Gericht und Datum aus dem Text extrahieren
    gericht = "EuGH"
    datum_match = re.search(r"(\d{1,2})\.\s*(\w+)\s+(\d{4})", volltext[:500])
    datum = ""
    if datum_match:
        datum = datum_match.group(0)

    # Aktenzeichen aus dem Text oder Parameter
    az_match = re.search(r"Rechtssache\s+C[‑\-]\d+/\d+", volltext[:2000])
    aktenzeichen = az_match.group() if az_match else f"Rechtssache {rechtssache}"

    verweise = find_verweise(volltext)

    eintrag = {
        "quelle": "eugh_cellar",
        "gericht": gericht,
        "datum": datum,
        "aktenzeichen": aktenzeichen,
        "kurzname": name,
        "rechtssache": rechtssache,
        "volltext": volltext,
        "normbezuege": verweise,
    }

    fname = f"EuGH_{rechtssache.replace('/', '_')}.json"
    save_json(eintrag, fname)

    print(f"    -> {len(volltext)} Zeichen, {len(verweise)} Normbezüge.")
    return eintrag


def fetch_all_eugh() -> list[dict]:
    """Lädt alle vordefinierten EuGH-Schlüsselentscheidungen."""
    print("\n--- EuGH-Schlüsselentscheidungen (EU Cellar API) ---\n")

    urteile = []
    for name, rechtssache, celex in EUGH_ENTSCHEIDUNGEN:
        eintrag = fetch_eugh_entscheidung(name, rechtssache, celex)
        if eintrag:
            urteile.append(eintrag)
        time.sleep(RATE_LIMIT_SECONDS)

    print(f"\n  => {len(urteile)} EuGH-Entscheidungen geladen.")
    return urteile


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------


def main():
    print("=" * 60)
    print("OpenLex MVP – Urteilssammler")
    print("=" * 60)

    # 1. Open Legal Data
    old_urteile = fetch_openlegaldata()

    # 2. EuGH
    eugh_urteile = fetch_all_eugh()

    # Zusammenfassung
    alle = old_urteile + eugh_urteile
    total_verweise = sum(len(u.get("normbezuege", [])) for u in alle)

    print()
    print("=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"  Urteile Open Legal Data:      {len(old_urteile)}")
    print(f"  Urteile EuGH:                 {len(eugh_urteile)}")
    print(f"  Urteile gesamt:               {len(alle)}")
    print(f"  Normbezüge gesamt:            {total_verweise}")
    print(f"  Ausgabeverzeichnis:           {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
