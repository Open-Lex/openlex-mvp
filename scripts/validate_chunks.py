#!/usr/bin/env python3
"""
validate_chunks.py – Qualitätsprüfung der granularen Gesetzes-Chunks.
"""

from __future__ import annotations

import glob
import json
import os
import random
import re
from collections import defaultdict

BASE_DIR = os.path.expanduser("~/openlex-mvp")
GRANULAR_DIR = os.path.join(BASE_DIR, "data", "gesetze_granular")

# Plausible Volladresse-Patterns
VALID_ADDR_RE = re.compile(
    r"^(?:Art\.?\s*\d+|§\s*\d+[a-z]?|Erwägungsgrund\s+\d+)"
    r"(?:\s+Abs\.\s*\d+)?"
    r"(?:\s+(?:lit\.\s*[a-z]|Nr\.\s*\d+|Buchst\.\s*[a-z]))?"
    r"(?:\s+S\.\s*\d+)?"
    r"\s+\S+",  # Gesetzesname am Ende
)

# Satz-Nummer extrahieren
SATZ_NR_RE = re.compile(r"S\.\s*(\d+)")

# Einfacher Satzzähler (Punkt gefolgt von Großbuchstabe oder Absatzende)
_ABK = {"abs", "art", "nr", "lit", "buchst", "bzw", "gem", "vgl", "usw",
        "etc", "sog", "ggf", "bsp", "rn", "kap", "bgh", "bsg", "bfh",
        "bag", "dr", "prof"}
_SATZ_KANDID = re.compile(r"(\S+)\.\s+([A-ZÄÖÜ(])", re.UNICODE)


def count_sentences(text: str) -> int:
    if not text:
        return 0
    count = 1
    for m in _SATZ_KANDID.finditer(text):
        word = m.group(1).lower().rstrip(".")
        if word not in _ABK:
            count += 1
    return count


def main():
    print("=" * 60)
    print("OpenLex MVP – Chunk-Validierung")
    print("=" * 60)

    files = sorted(glob.glob(os.path.join(GRANULAR_DIR, "*.json")))
    print(f"\n  {len(files)} Dateien in {GRANULAR_DIR}\n")

    # Datenstrukturen
    errors: list[dict] = []
    warnings: list[dict] = []
    text_to_addrs: dict[str, list[str]] = defaultdict(list)
    per_gesetz: dict[str, dict] = defaultdict(lambda: {
        "total": 0, "high_satz": 0, "short": 0, "chunks": [],
    })

    total = 0

    for fpath in files:
        fname = os.path.basename(fpath)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            errors.append({"file": fname, "error": f"JSON parse error: {e}"})
            continue

        total += 1
        addr = doc.get("volladresse", "")
        text = doc.get("text", "")
        gesetz = doc.get("gesetz", "Unbekannt")
        kontext = doc.get("kontext_paragraph", "")

        per_gesetz[gesetz]["total"] += 1
        per_gesetz[gesetz]["chunks"].append(doc)

        # ── PRÜFUNG 1a: Volladresse-Format ──
        if not addr:
            errors.append({"file": fname, "error": "volladresse leer"})
        elif not VALID_ADDR_RE.match(addr):
            errors.append({"file": fname, "error": f"volladresse ungültig: '{addr}'"})

        # ── PRÜFUNG 1c+d: Text nicht leer, mindestens 10 Zeichen ──
        if not text or not text.strip():
            errors.append({"file": fname, "error": "text leer"})
        elif len(text.strip()) < 10:
            errors.append({"file": fname, "error": f"text zu kurz ({len(text.strip())} Z): '{text.strip()}'"})
            per_gesetz[gesetz]["short"] += 1
        elif len(text.strip()) < 20:
            warnings.append({"file": fname, "warning": f"text verdächtig kurz ({len(text.strip())} Z)"})
            per_gesetz[gesetz]["short"] += 1

        # ── PRÜFUNG 1b: Satz-Index plausibel ──
        satz_match = SATZ_NR_RE.search(addr)
        if satz_match:
            satz_nr = int(satz_match.group(1))
            if satz_nr > 5:
                per_gesetz[gesetz]["high_satz"] += 1

            # Kontext-Paragraph auf tatsächliche Satzanzahl prüfen
            if kontext:
                # Finde den relevanten Absatz im Kontext
                abs_match = re.search(r"Abs\.\s*(\d+)", addr)
                abs_nr = int(abs_match.group(1)) if abs_match else 1

                # Absatz aus Kontext extrahieren
                abs_splits = re.split(r"(?:^|\n)\s*\(\d+\)\s+", kontext)
                abs_text = abs_splits[abs_nr] if abs_nr < len(abs_splits) else kontext

                actual_sentences = count_sentences(abs_text)
                if satz_nr > actual_sentences + 2:  # Toleranz von 2
                    warnings.append({
                        "file": fname,
                        "warning": f"S. {satz_nr} aber Absatz hat ~{actual_sentences} Sätze: {addr}",
                    })

        # ── PRÜFUNG 2: Duplikate sammeln ──
        text_key = text.strip()[:200] if text else ""
        if text_key:
            text_to_addrs[text_key].append(addr)

    # ── PRÜFUNG 2: Duplikate auswerten ──
    print("=" * 60)
    print("PRÜFUNG 2 – Duplikate")
    print("=" * 60)
    dup_count = 0
    for text_key, addrs in text_to_addrs.items():
        if len(addrs) > 1:
            unique_addrs = set(addrs)
            if len(unique_addrs) > 1:
                dup_count += 1
                if dup_count <= 10:
                    print(f"  Duplikat-Text: '{text_key[:60]}...'")
                    for a in sorted(unique_addrs):
                        print(f"    -> {a}")
    print(f"\n  {dup_count} Text-Duplikate mit unterschiedlicher Adresse gefunden.")

    # ── PRÜFUNG 3: Statistik pro Gesetz ──
    print("\n" + "=" * 60)
    print("PRÜFUNG 3 – Statistik pro Gesetz")
    print("=" * 60)
    print(f"\n  {'Gesetz':<15} {'Total':>7} {'S.>5':>7} {'<20 Z':>7}")
    print("  " + "-" * 38)
    for gesetz in sorted(per_gesetz.keys()):
        s = per_gesetz[gesetz]
        flag = " ⚠️" if s["high_satz"] > s["total"] * 0.1 else ""
        print(f"  {gesetz:<15} {s['total']:>7} {s['high_satz']:>7} {s['short']:>7}{flag}")

    # ── PRÜFUNG 4: Stichprobe ──
    print("\n" + "=" * 60)
    print("PRÜFUNG 4 – Stichprobe (5 pro Gesetz)")
    print("=" * 60)
    for gesetz in sorted(per_gesetz.keys()):
        chunks = per_gesetz[gesetz]["chunks"]
        sample = random.sample(chunks, min(5, len(chunks)))
        print(f"\n  --- {gesetz} ---")
        for c in sample:
            addr = c.get("volladresse", "?")
            text = c.get("text", "")[:100].replace("\n", " ")
            print(f"    {addr}")
            print(f"      {text}...")

    # ── ZUSAMMENFASSUNG ──
    error_count = len(errors)
    warning_count = len(warnings)
    error_pct = error_count / total * 100 if total else 0

    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"  Chunks total:       {total}")
    print(f"  Fehler:             {error_count} ({error_pct:.1f}%)")
    print(f"  Warnungen:          {warning_count}")
    print(f"  Text-Duplikate:     {dup_count}")

    if error_count > 0:
        print(f"\n  Erste 20 Fehler:")
        for e in errors[:20]:
            print(f"    {e['file']}: {e['error']}")

    if warning_count > 0:
        print(f"\n  Erste 10 Warnungen:")
        for w in warnings[:10]:
            print(f"    {w['file']}: {w['warning']}")

    if error_pct > 5:
        print(f"\n  ⚠️ MEHR ALS 5% FEHLERHAFT ({error_pct:.1f}%)")
        print("  Empfohlener Fix: refine_gesetze.py erneut ausführen mit angepasstem Parsing.")
        # Häufigste Fehlertypen
        from collections import Counter
        error_types = Counter()
        for e in errors:
            reason = e["error"].split(":")[0]
            error_types[reason] += 1
        print(f"\n  Häufigste Fehlertypen:")
        for reason, count in error_types.most_common(5):
            print(f"    {reason}: {count}")
    else:
        print(f"\n  ✅ Fehlerquote unter 5% – Datenqualität akzeptabel.")

    print("=" * 60)


if __name__ == "__main__":
    main()
