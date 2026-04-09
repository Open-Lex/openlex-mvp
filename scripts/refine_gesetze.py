#!/usr/bin/env python3
"""
refine_gesetze.py – Reichert die Gesetzes-JSONs in data/gesetze/ an:

  1. Granulares Parsing (Absätze → Nummern/Buchstaben → Sätze)
  2. Erweiterte JSON-Struktur (überschreibt bestehende Dateien)
  3. Granulare Chunks in data/gesetze_granular/
  4. Erwägungsgrund-Artikel-Mapping (von privacy-regulation.eu)
"""

from __future__ import annotations

import glob
import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
GESETZE_DIR = os.path.join(BASE_DIR, "data", "gesetze")
GRANULAR_DIR = os.path.join(BASE_DIR, "data", "gesetze_granular")
os.makedirs(GRANULAR_DIR, exist_ok=True)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0")

RATE_LIMIT = 2.0

# Abkürzungen vor Punkt, die KEIN Satzende markieren
_ABKUERZUNGEN = {
    "abs", "art", "nr", "lit", "buchst", "bzw", "gem", "vgl", "usw",
    "etc", "sog", "ggf", "bsp", "var", "ziff", "rn", "kap", "anh",
    "verf", "aufl", "abschn", "unterabs", "satz", "bgh", "bsg", "bfh",
    "bag", "bverwg", "bverfg", "eugh", "dr", "prof", "bgbl", "gg",
    "stgb", "zpo", "bgb", "stpo", "vwgo", "vo", "rl",
}

# Einfacher Regex zum Finden von Satzende-Kandidaten
_SATZ_KANDIDAT_RE = re.compile(r"(\S+)\.\s+([A-ZÄÖÜ(])", re.UNICODE)

# Granularer Verweis-Regex
VERWEIS_RE = re.compile(
    # Art. X Abs. Y lit. z Satz N DSGVO
    r"Art\.?\s*\d+\s*"
    r"(?:Abs\.?\s*\d+\s*)?"
    r"(?:(?:lit\.?\s*[a-z]|Buchst\.?\s*[a-z]|Nr\.?\s*\d+)\s*)?"
    r"(?:(?:UAbs\.?\s*\d+|S(?:atz)?\.?\s*\d+)\s*)?"
    r"(?:DSGVO|GDPR|DS-GVO|EUV\s*2016/679)"
    # Art. X Abs. Y lit. z Gesetzname
    r"|Art\.?\s*\d+\s*"
    r"(?:Abs\.?\s*\d+\s*)?"
    r"(?:(?:lit\.?\s*[a-z]|Nr\.?\s*\d+)\s*)?"
    r"(?:(?:UAbs\.?\s*\d+|S(?:atz)?\.?\s*\d+)\s*)?"
    r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*"
    # § X Abs. Y S. Z Gesetzname
    r"|§§?\s*\d+[a-z]?\s*"
    r"(?:Abs\.?\s*\d+\s*)?"
    r"(?:(?:S(?:atz)?\.?\s*\d+|Nr\.?\s*\d+)\s*)?"
    r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*",
    re.UNICODE,
)


def find_verweise(text: str) -> list[str]:
    return list(set(VERWEIS_RE.findall(text)))


def sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\s]+', "_", name).strip("_")[:150]


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 1 + 2 – Granulares Parsing + Erweiterte JSON-Struktur
# ═══════════════════════════════════════════════════════════════════════════


def split_saetze(text: str) -> list[str]:
    """Teilt Text in einzelne Sätze, respektiert juristische Abkürzungen."""
    text = text.strip()
    if not text:
        return []

    # Finde alle Satzende-Positionen (Punkt + Leerzeichen + Großbuchstabe)
    # ABER nicht nach Abkürzungen
    split_positions = []
    for m in _SATZ_KANDIDAT_RE.finditer(text):
        word_before = m.group(1).lower().rstrip(".")
        # Prüfe ob das Wort vor dem Punkt eine Abkürzung ist
        if word_before not in _ABKUERZUNGEN and not re.match(r"^[ivxlcdm]+$", word_before):
            # Position: nach dem Punkt + Leerzeichen
            split_positions.append(m.start() + len(m.group(1)) + 1)

    if not split_positions:
        return [text]

    # Text an den Positionen aufteilen
    saetze = []
    prev = 0
    for pos in split_positions:
        satz = text[prev:pos].strip()
        if satz:
            saetze.append(satz)
        prev = pos + 1  # nach dem Leerzeichen

    # Rest
    rest = text[prev:].strip()
    if rest:
        saetze.append(rest)

    return saetze if saetze else [text]


def parse_buchstaben_nummern(text: str) -> list[dict]:
    """Erkennt lit. a) / a) / 1. / Nr. 1 Unterstruktur innerhalb eines Absatzes."""
    # Patterns für Buchstaben/Nummern
    # Typisch: \na)\n, \nlit. a\n, \n1.\n, \nNr. 1\n
    patterns = [
        # DSGVO-Stil: a)\n oder a) am Anfang
        (r"(?:^|\n)\s*([a-z])\)\s*\n?", "lit"),
        # lit. a
        (r"(?:^|\n)\s*lit\.\s*([a-z])\s*", "lit"),
        # 1.\n Nummern
        (r"(?:^|\n)\s*(\d+)\.\s+", "nr"),
    ]

    # Versuche verschiedene Patterns
    for pattern, typ in patterns:
        splits = re.split(pattern, text)
        if len(splits) >= 3:
            # Erfolgreicher Split
            items = []
            # splits: [vor-text, kennung1, text1, kennung2, text2, ...]
            preamble = splits[0].strip()
            for i in range(1, len(splits) - 1, 2):
                kennung_raw = splits[i]
                item_text = splits[i + 1].strip() if i + 1 < len(splits) else ""
                if not item_text:
                    continue
                if typ == "lit":
                    kennung = f"lit. {kennung_raw}"
                else:
                    kennung = f"Nr. {kennung_raw}"
                saetze = split_saetze(item_text)
                items.append({
                    "kennung": kennung,
                    "text": item_text,
                    "saetze": saetze,
                })
            if items:
                return items

    return []


def parse_absaetze(text: str) -> list[dict]:
    """Erkennt Absätze (1), (2), (3) etc. im Gesetzestext."""
    # Split an (N) am Zeilenanfang oder nach Zeilenumbruch
    # Pattern: Absatznummer in Klammern, möglicherweise mit Leerzeichen davor
    splits = re.split(r"(?:^|\n)\s*\((\d+)\)\s+", text)

    if len(splits) < 3:
        # Kein Absatz-Split möglich → ganzer Text = Absatz 1
        sub = parse_buchstaben_nummern(text)
        saetze = split_saetze(text) if not sub else []
        return [{
            "nummer": 1,
            "text": text.strip(),
            "nummern_oder_buchstaben": sub,
            "saetze": saetze,
        }]

    absaetze = []
    # splits: [vortext, "1", text1, "2", text2, ...]
    for i in range(1, len(splits) - 1, 2):
        nummer = int(splits[i])
        abs_text = splits[i + 1].strip()
        if not abs_text:
            continue

        sub = parse_buchstaben_nummern(abs_text)
        # Sätze nur auf Absatz-Ebene, wenn keine Untergliederung
        saetze = split_saetze(abs_text) if not sub else []

        absaetze.append({
            "nummer": nummer,
            "text": abs_text,
            "nummern_oder_buchstaben": sub,
            "saetze": saetze,
        })

    return absaetze


def refine_gesetz(doc: dict) -> dict:
    """Erweitert ein Gesetzes-JSON um granulare Struktur."""
    text = doc.get("text", "")
    absaetze = parse_absaetze(text)

    return {
        "gesetz": doc.get("gesetz", ""),
        "paragraph": doc.get("paragraph", ""),
        "ueberschrift": doc.get("ueberschrift", ""),
        "volltext": text,
        "absaetze": absaetze,
        "verweise": doc.get("verweise", []),
    }


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 3 – Granulare Chunks
# ═══════════════════════════════════════════════════════════════════════════


def make_volladresse(gesetz: str, para: str, abs_nr: int | None = None,
                     kennung: str | None = None, satz_nr: int | None = None) -> str:
    """Erzeugt eine vollständige Normadresse, z.B. 'Art. 6 Abs. 1 lit. f DSGVO'."""
    parts = [para]
    if abs_nr is not None:
        parts.append(f"Abs. {abs_nr}")
    if kennung is not None:
        parts.append(kennung)
    if satz_nr is not None:
        parts.append(f"S. {satz_nr}")
    parts.append(gesetz)
    return " ".join(parts)


def generate_granular_chunks(doc: dict) -> list[dict]:
    """Erzeugt granulare Chunks aus einem erweiterten Gesetzes-JSON."""
    gesetz = doc.get("gesetz", "")
    para = doc.get("paragraph", "")
    volltext = doc.get("volltext", "")
    chunks = []

    for absatz in doc.get("absaetze", []):
        abs_nr = absatz["nummer"]

        if absatz.get("nummern_oder_buchstaben"):
            # Untergliederung vorhanden → Chunk pro Buchstabe/Nummer
            for sub in absatz["nummern_oder_buchstaben"]:
                kennung = sub["kennung"]
                addr = make_volladresse(gesetz, para, abs_nr, kennung)
                chunk_id = sanitize(f"{gesetz}_{para}_Abs.{abs_nr}_{kennung}")

                chunks.append({
                    "chunk_id": chunk_id,
                    "gesetz": gesetz,
                    "volladresse": addr,
                    "text": sub["text"],
                    "kontext_paragraph": volltext[:5000],
                    "verweise": find_verweise(sub["text"]),
                })

                # Optional: einzelne Sätze als noch feinere Chunks
                if len(sub.get("saetze", [])) > 1:
                    for s_idx, satz in enumerate(sub["saetze"], 1):
                        s_addr = make_volladresse(gesetz, para, abs_nr, kennung, s_idx)
                        s_id = sanitize(f"{gesetz}_{para}_Abs.{abs_nr}_{kennung}_S.{s_idx}")
                        chunks.append({
                            "chunk_id": s_id,
                            "gesetz": gesetz,
                            "volladresse": s_addr,
                            "text": satz,
                            "kontext_paragraph": volltext[:5000],
                            "verweise": find_verweise(satz),
                        })

        elif len(absatz.get("saetze", [])) > 1:
            # Keine Untergliederung, aber mehrere Sätze → Chunk pro Absatz + pro Satz
            addr = make_volladresse(gesetz, para, abs_nr)
            chunk_id = sanitize(f"{gesetz}_{para}_Abs.{abs_nr}")
            chunks.append({
                "chunk_id": chunk_id,
                "gesetz": gesetz,
                "volladresse": addr,
                "text": absatz["text"],
                "kontext_paragraph": volltext[:5000],
                "verweise": find_verweise(absatz["text"]),
            })

            for s_idx, satz in enumerate(absatz["saetze"], 1):
                s_addr = make_volladresse(gesetz, para, abs_nr, satz_nr=s_idx)
                s_id = sanitize(f"{gesetz}_{para}_Abs.{abs_nr}_S.{s_idx}")
                chunks.append({
                    "chunk_id": s_id,
                    "gesetz": gesetz,
                    "volladresse": s_addr,
                    "text": satz,
                    "kontext_paragraph": volltext[:5000],
                    "verweise": find_verweise(satz),
                })

        else:
            # Einfacher Absatz ohne weitere Gliederung
            addr = make_volladresse(gesetz, para, abs_nr)
            chunk_id = sanitize(f"{gesetz}_{para}_Abs.{abs_nr}")
            chunks.append({
                "chunk_id": chunk_id,
                "gesetz": gesetz,
                "volladresse": addr,
                "text": absatz["text"],
                "kontext_paragraph": volltext[:5000],
                "verweise": find_verweise(absatz["text"]),
            })

    return chunks


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 4 – Erwägungsgrund-Artikel-Mapping
# ═══════════════════════════════════════════════════════════════════════════


def fetch_eg_artikel_mapping() -> dict[int, list[int]]:
    """
    Scrapet privacy-regulation.eu um das Mapping Artikel → Erwägungsgründe
    zu bauen, und invertiert es zu Erwägungsgrund → Artikel.
    """
    print("\n  Lade Erwägungsgrund-Artikel-Mapping von privacy-regulation.eu ...")

    # Schritt 1: Für jeden DSGVO-Artikel die verlinkten Erwägungsgründe holen
    artikel_zu_eg: dict[int, list[int]] = {}

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    for art_nr in range(1, 100):
        url = f"https://www.privacy-regulation.eu/de/{art_nr}.htm"
        try:
            r = session.get(url, timeout=15)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "lxml")
            egs = set()
            for a in soup.find_all("a", href=re.compile(r"^r\d+\.htm")):
                m = re.match(r"r(\d+)\.htm", a.get("href", ""))
                if m:
                    egs.add(int(m.group(1)))

            if egs:
                artikel_zu_eg[art_nr] = sorted(egs)

            if art_nr % 20 == 0:
                print(f"    Artikel {art_nr}/99 verarbeitet ...")
            time.sleep(0.5)  # Schneller, da kleine Seiten

        except Exception as e:
            print(f"    FEHLER bei Art. {art_nr}: {e}")

    # Schritt 2: Invertieren → EG → Artikel
    eg_zu_artikel: dict[int, list[int]] = {}
    for art_nr, egs in artikel_zu_eg.items():
        for eg in egs:
            if eg not in eg_zu_artikel:
                eg_zu_artikel[eg] = []
            if art_nr not in eg_zu_artikel[eg]:
                eg_zu_artikel[eg].append(art_nr)

    # Sortieren
    for eg in eg_zu_artikel:
        eg_zu_artikel[eg].sort()

    print(f"    {len(artikel_zu_eg)} Artikel mit EG-Verknüpfungen")
    print(f"    {len(eg_zu_artikel)} Erwägungsgründe mit Artikel-Verknüpfungen")

    return eg_zu_artikel, artikel_zu_eg


# ═══════════════════════════════════════════════════════════════════════════
# Hauptprogramm
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 60)
    print("OpenLex MVP – Gesetzes-Verfeinerung")
    print("=" * 60)

    # ── Alle JSON-Dateien laden ──
    json_files = sorted(glob.glob(os.path.join(GESETZE_DIR, "*.json")))
    print(f"\n  {len(json_files)} Dateien in {GESETZE_DIR}")

    docs = []
    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                docs.append((fpath, json.load(f)))
        except Exception:
            pass

    print(f"  {len(docs)} erfolgreich geladen.")

    # ── SCHRITT 4 zuerst: EG-Mapping holen (braucht Netzwerk) ──
    print("\n" + "=" * 60)
    print("SCHRITT 4 – Erwägungsgrund-Artikel-Mapping")
    print("=" * 60)

    eg_zu_artikel = {}
    artikel_zu_eg = {}
    eg_mapping_count = 0

    try:
        eg_zu_artikel, artikel_zu_eg = fetch_eg_artikel_mapping()
        eg_mapping_count = sum(len(v) for v in eg_zu_artikel.values())
    except Exception as e:
        print(f"  FEHLER beim Mapping: {e}")

    # ── SCHRITT 1+2: Granulares Parsing + Erweiterte Struktur ──
    print("\n" + "=" * 60)
    print("SCHRITT 1+2 – Granulares Parsing + Erweiterte Struktur")
    print("=" * 60)

    refined_count = 0
    for fpath, doc in docs:
        refined = refine_gesetz(doc)
        gesetz = doc.get("gesetz", "")
        para = doc.get("paragraph", "")

        # EG-Mapping eintragen (nur für DSGVO)
        if gesetz == "DSGVO":
            # Erwägungsgrund → erlaeutert_artikel
            eg_match = re.match(r"Erwägungsgrund\s+(\d+)", para)
            if eg_match:
                eg_nr = int(eg_match.group(1))
                if eg_nr in eg_zu_artikel:
                    refined["erlaeutert_artikel"] = [
                        f"Art. {a}" for a in eg_zu_artikel[eg_nr]
                    ]

            # Artikel → relevante_erwägungsgruende
            art_match = re.match(r"Art\.\s*(\d+)", para)
            if art_match:
                art_nr = int(art_match.group(1))
                if art_nr in artikel_zu_eg:
                    refined["relevante_erwägungsgruende"] = artikel_zu_eg[art_nr]

        # Überschreibe bestehende Datei
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(refined, f, ensure_ascii=False, indent=2)
        refined_count += 1

    print(f"  {refined_count} Dateien verfeinert und überschrieben.")

    # ── SCHRITT 3: Granulare Chunks ──
    print("\n" + "=" * 60)
    print("SCHRITT 3 – Granulare Chunks")
    print("=" * 60)

    # Alle Dateien nochmal laden (jetzt mit erweiterter Struktur)
    chunk_total = 0
    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception:
            continue

        chunks = generate_granular_chunks(doc)
        for chunk in chunks:
            chunk_fname = sanitize(chunk["chunk_id"]) + ".json"
            chunk_path = os.path.join(GRANULAR_DIR, chunk_fname)
            with open(chunk_path, "w", encoding="utf-8") as f:
                json.dump(chunk, f, ensure_ascii=False, indent=2)
            chunk_total += 1

    print(f"  {chunk_total} granulare Chunks in {GRANULAR_DIR}")

    # ── Zusammenfassung ──
    # Zähle EG-Verknüpfungen
    eg_linked = 0
    art_linked = 0
    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception:
            continue
        if doc.get("erlaeutert_artikel"):
            eg_linked += 1
        if doc.get("relevante_erwägungsgruende"):
            art_linked += 1

    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"  Dateien eingelesen:                {len(docs)}")
    print(f"  Dateien verfeinert:                {refined_count}")
    print(f"  Granulare Chunks erzeugt:          {chunk_total}")
    print(f"  EG mit Artikel-Verknüpfung:        {eg_linked}")
    print(f"  Artikel mit EG-Verknüpfung:        {art_linked}")
    print(f"  EG-Artikel-Zuordnungen gesamt:     {eg_mapping_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
