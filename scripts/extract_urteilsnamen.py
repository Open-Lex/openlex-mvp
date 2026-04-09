#!/usr/bin/env python3
"""
extract_urteilsnamen.py – Extrahiert Kurznamen für Urteile aus den JSON-Daten.

Drei Strategien:
  1. Vorhandene Metadaten (kurzname, titel)
  2. Regex-Extraktion aus Volltext (Rechtssache-Muster, Parteinamen)
  3. Fallback-Heuristik (Leitsatz, Orientierungssatz)

Ergebnis: data/urteilsnamen.json  →  {aktenzeichen: kurzname | null}
"""

from __future__ import annotations

import glob
import json
import os
import re

BASE_DIR = os.path.expanduser("~/openlex-mvp")
URTEILE_DIR = os.path.join(BASE_DIR, "data", "urteile")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "urteilsnamen.json")


# ---------------------------------------------------------------------------
# Regex-Patterns
# ---------------------------------------------------------------------------

# EuGH: "In der Rechtssache C-131/12 ... Google Spain SL, Google Inc. gegen ..."
_RS_PARTY_RE = re.compile(
    r"(?:In der|in der)\s+Rechtssache\s+"
    r"(?:C[\-‑–]\d+/\d+\s*)"
    r"(?:,?\s*(?:C[\-‑–]\d+/\d+)\s*)*"  # verbundene Rechtssachen
    r"(?:betreffend.*?in dem Verfahren\s+)?"
    r"([\w\s,.()äöüÄÖÜß]+?)\s+gegen\s+([\w\s,.()äöüÄÖÜß]+?)"
    r"\s*(?:erlässt|erläss|,\s*$|\n)",
    re.DOTALL | re.UNICODE,
)

# Einfacheres Pattern: "Rechtssache C-XXX/XX – Name"
_RS_DASH_RE = re.compile(
    r"Rechtssache\s+(?:C[\-‑–]\d+/\d+)\s*[\-‑–]\s*([A-ZÄÖÜ][\w\s/,.äöüÄÖÜß]+?)(?:\s*\(|\s*,?\s*$|\n)",
    re.UNICODE | re.MULTILINE,
)

# "URTEIL DES GERICHTSHOFS" gefolgt von Datum, dann Parteiname
_URTEIL_HEADER_RE = re.compile(
    r"URTEIL DES GERICHTSHOFS.*?\n.*?\n\s*(?:in der Rechtssache.*?\n)?"
    r"([\w\s,.()äöüÄÖÜß]+?)\s+gegen\s+([\w\s,.()äöüÄÖÜß]+?)\s*(?:erlässt|\n)",
    re.DOTALL | re.UNICODE,
)

# BGH/BVerfG: "Leitsatz:" oder "Orientierungssatz:" – erster Satz als Beschreibung
_LEITSATZ_RE = re.compile(
    r"(?:Leitsatz|Orientierungssatz)\s*:?\s*\n?\s*(.+?)(?:\.|$)",
    re.UNICODE,
)


# Phrasen die kein Parteiname sind
_PARTY_BLACKLIST = [
    "betreffend", "vorabentscheidungsersuchen", "eingereicht",
    "ersuchen", "vorgelegt", "erlässt", "unter mitwirkung",
    "im verfahren", "in dem verfahren",
]


def _clean_party_name(name: str) -> str:
    """Bereinigt einen Parteinamen auf eine kurze Form."""
    name = name.strip().strip(",").strip()
    # Zeilenumbrüche → Leerzeichen
    name = re.sub(r"\s+", " ", name)
    # Rechtsform-Suffixe kürzen
    for suffix in [" Limited", " Ltd.", " Ltd", " GmbH", " AG", " SE",
                   " S.L.", " SL", " Inc.", " Inc", " B.V.", " BV",
                   " S.A.", " SA", " NV", " u. a."]:
        name = name.replace(suffix, "")
    # "vormals XY" kürzen
    name = re.sub(r"\s*,?\s*vormals\s+.*", "", name)
    # Blacklist-Wörter → ungültig
    if any(bl in name.lower() for bl in _PARTY_BLACKLIST):
        return ""
    # Zu lange Namen: nur erste 2 Wörter
    words = name.split()
    if len(words) > 3:
        name = " ".join(words[:2])
    return name.strip().strip(",").strip()


def _shorten_parties(party1: str, party2: str) -> str:
    """Erzeugt einen Kurznamen aus zwei Parteinamen."""
    p1 = _clean_party_name(party1)
    p2 = _clean_party_name(party2)
    if not p1 and not p2:
        return ""
    if not p1:
        return p2
    if not p2:
        return p1
    # Beide kurz genug → kombinieren
    combined = f"{p1}/{p2}"
    if len(combined) > 40:
        # Nur den kürzeren nehmen
        return p1 if len(p1) <= len(p2) else p2
    return combined


def extract_from_metadata(doc: dict) -> str | None:
    """Strategie 1: Vorhandene Metadaten-Felder."""
    # kurzname (EuGH aus Cellar)
    kurzname = doc.get("kurzname", "")
    if kurzname and len(kurzname) > 2:
        # Bereinigen: Zeilenumbrüche, mehrere Namen (Komma-getrennt → erster)
        kurzname = re.sub(r"\s+", " ", kurzname).strip()
        kurzname = kurzname.split(",")[0].strip()
        if kurzname and len(kurzname) > 2:
            return kurzname
    # titel
    titel = doc.get("titel", "")
    if titel and len(titel) > 3 and len(titel) < 80:
        # Nur wenn es nicht nur das Aktenzeichen wiederholt
        az = doc.get("aktenzeichen", "")
        if titel.strip() != az.strip():
            return titel.strip()
    return None


def extract_from_volltext_eugh(doc: dict) -> str | None:
    """Strategie 2: Regex-Extraktion aus EuGH-Volltext."""
    text = doc.get("volltext", "") or doc.get("sachverhalt", "") or ""
    if not text:
        return None

    # Nur die ersten 3000 Zeichen durchsuchen (Parteien stehen am Anfang)
    head = text[:3000]

    # Pattern 1: "Rechtssache C-XXX/XX – Name"
    m = _RS_DASH_RE.search(head)
    if m:
        name = _clean_party_name(m.group(1))
        if name and len(name) > 2:
            return name

    # Pattern 2: "... Party1 gegen Party2 ..."
    m = _RS_PARTY_RE.search(head)
    if m:
        result = _shorten_parties(m.group(1), m.group(2))
        if result and len(result) > 2:
            return result

    # Pattern 3: URTEIL-Header
    m = _URTEIL_HEADER_RE.search(head)
    if m:
        result = _shorten_parties(m.group(1), m.group(2))
        if result and len(result) > 2:
            return result

    return None


# Wörter die auf einen Leitsatz-Vollsatz hindeuten (kein echter Kurzname)
_LEITSATZ_STOPWORDS = {"leitsatz", "nv:", "die", "der", "das", "ein", "eine",
                        "zum", "zur", "wenn", "soweit", "nach", "im", "es",
                        "bei", "mit", "auf", "für", "von", "dem", "den"}


def _is_valid_short_name(text: str) -> bool:
    """Prüft ob ein Text ein echter Kurzname ist (max 5 Wörter, keine Leitsatz-Sprache)."""
    words = text.split()
    if not words or len(words) > 5:
        return False
    # Erstes Wort darf kein Leitsatz-Stopword sein
    if words[0].lower().rstrip(":") in _LEITSATZ_STOPWORDS:
        return False
    # Reine Zahlen/Zeichen (z.B. "1", "1a", "2.") sind keine Namen
    if re.match(r"^[\d\s.a-c]+$", text):
        return False
    # Mindestens 3 Zeichen
    if len(text) < 3:
        return False
    # "NV:" am Anfang = Nicht-Veröffentlicht-Leitsatz
    if text.upper().startswith("NV"):
        return False
    return True


def extract_from_volltext_de(doc: dict) -> str | None:
    """Strategie 3: Fallback für deutsche Gerichte – nur echte Kurznamen."""
    # Leitsatz-Feld direkt
    leitsatz = doc.get("leitsatz", "")
    if leitsatz:
        first_sentence = leitsatz.strip().split(".")[0].strip()
        if first_sentence and _is_valid_short_name(first_sentence):
            return first_sentence

    # Im Volltext nach Leitsatz/Orientierungssatz suchen
    text = doc.get("volltext", "")
    if not text:
        return None

    m = _LEITSATZ_RE.search(text[:2000])
    if m:
        sentence = m.group(1).strip()
        if sentence and _is_valid_short_name(sentence):
            return sentence

    return None


def normalize_az(az: str) -> str:
    """Normalisiert ein Aktenzeichen für den Dict-Key."""
    # Unicode-Bindestriche vereinheitlichen
    az = az.replace("\u2011", "-").replace("\u2013", "-").replace("\u2010", "-")
    # "Rechtssache" entfernen
    az = re.sub(r"Rechtssache\s*", "", az)
    return az.strip()


def main():
    print("=" * 60)
    print("Urteilsnamen-Extraktion")
    print("=" * 60)

    files = sorted(glob.glob(os.path.join(URTEILE_DIR, "*.json")))
    print(f"\n{len(files)} Urteils-Dateien gefunden.\n")

    results: dict[str, str | None] = {}
    stats = {"total": 0, "metadata": 0, "regex_eugh": 0, "regex_de": 0, "none": 0}

    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        az = doc.get("aktenzeichen", "")
        if not az:
            continue

        az_key = normalize_az(az)
        gericht = doc.get("gericht", "").lower()
        stats["total"] += 1

        # Bereits einen guten Namen? → nicht überschreiben
        if results.get(az_key):
            continue

        # Strategie 1: Metadaten
        name = extract_from_metadata(doc)
        if name:
            results[az_key] = name
            stats["metadata"] += 1
            continue

        # Strategie 2: EuGH-Volltext
        if "eugh" in gericht or "gerichtshof" in gericht or az_key.startswith("C-"):
            name = extract_from_volltext_eugh(doc)
            if name:
                results[az_key] = name
                stats["regex_eugh"] += 1
                continue

        # Strategie 3: Deutsche Gerichte
        name = extract_from_volltext_de(doc)
        if name:
            results[az_key] = name
            stats["regex_de"] += 1
            continue

        # Kein Name gefunden
        if az_key not in results:
            results[az_key] = None
        stats["none"] += 1

    # Speichern
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Statistik
    found = stats["metadata"] + stats["regex_eugh"] + stats["regex_de"]
    print(f"\nErgebnis:")
    print(f"  Urteile gesamt:     {stats['total']:,}")
    print(f"  Mit Name:           {found:,} ({found / max(stats['total'], 1) * 100:.0f}%)")
    print(f"    - aus Metadaten:  {stats['metadata']:,}")
    print(f"    - EuGH-Regex:    {stats['regex_eugh']:,}")
    print(f"    - DE-Heuristik:  {stats['regex_de']:,}")
    print(f"  Ohne Name:          {stats['none']:,}")
    print(f"\nGespeichert: {OUTPUT_FILE}")

    # Beispiele
    examples = [(k, v) for k, v in results.items() if v is not None][:15]
    if examples:
        print(f"\nBeispiele:")
        for az, name in examples:
            print(f"  {az:30s} → {name}")


if __name__ == "__main__":
    main()
