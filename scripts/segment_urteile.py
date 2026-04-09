#!/usr/bin/env python3
"""
segment_urteile.py – Segmentiert Urteile in strukturierte Abschnitte:

  1. Passauer Datensatz (HuggingFace: harshildarji/openlegaldata)
  2. Heuristischer Segmentierer für deutsche Gerichte
  3. EuGH/EuG-Segmentierer
  4. JSON-Dateien aktualisieren
  5. Segmentierte Chunks erzeugen
"""

from __future__ import annotations

import glob
import json
import os
import re
import time

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
URTEILE_DIR = os.path.join(BASE_DIR, "data", "urteile")
SEG_CHUNKS_DIR = os.path.join(BASE_DIR, "data", "urteile_segmentiert")
os.makedirs(SEG_CHUNKS_DIR, exist_ok=True)

# Chunking-Parameter (Zeichen; ~1 Token ≈ 4 Zeichen)
CHUNK_TARGET = 2400
CHUNK_MIN = 2000
CHUNK_MAX = 3200
OVERLAP = 400

# Abkürzungen für Satz-Split (keine variable-length lookbehinds)
_ABK = {
    "abs", "art", "nr", "lit", "buchst", "bzw", "gem", "vgl", "usw",
    "etc", "sog", "ggf", "bsp", "var", "ziff", "rn", "kap", "anh",
    "bgh", "bsg", "bfh", "bag", "bverwg", "bverfg", "eugh", "dr", "prof",
}
_SATZ_KANDIDAT = re.compile(r"(\S+)\.\s+([A-ZÄÖÜ(])", re.UNICODE)

# ─── Statistiken ──────────────────────────────────────────────────────────

stats = {
    "passau": 0,
    "heuristisch_de": 0,
    "heuristisch_eu": 0,
    "unsegmentiert": 0,
    "chunk_counts": {},
}

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def normalize_az(az: str) -> str:
    if not az:
        return ""
    az = az.strip().lower()
    az = az.replace("\u2011", "-").replace("\u2013", "-").replace("‑", "-").replace("–", "-")
    az = re.sub(r"\s+", " ", az)
    return az


def split_saetze(text: str) -> list[str]:
    """Teilt Text in Sätze, respektiert Abkürzungen."""
    text = text.strip()
    if not text:
        return []
    positions = []
    for m in _SATZ_KANDIDAT.finditer(text):
        word = m.group(1).lower().rstrip(".")
        if word not in _ABK:
            positions.append(m.start() + len(m.group(1)) + 1)
    if not positions:
        return [text]
    saetze = []
    prev = 0
    for pos in positions:
        s = text[prev:pos].strip()
        if s:
            saetze.append(s)
        prev = pos + 1
    rest = text[prev:].strip()
    if rest:
        saetze.append(rest)
    return saetze or [text]


def chunk_text(text: str) -> list[str]:
    """Teilt Text in überlappende Chunks, an Satzgrenzen."""
    if not text or len(text) < CHUNK_MIN:
        return [text] if text else []
    chunks = []
    pos = 0
    tlen = len(text)
    while pos < tlen:
        if tlen - pos <= CHUNK_MAX:
            c = text[pos:].strip()
            if c:
                chunks.append(c)
            break
        # Finde Satzende nahe target
        target = pos + CHUNK_TARGET
        best = target
        for m in _SATZ_KANDIDAT.finditer(text, max(pos, target - 200)):
            end = m.start() + len(m.group(1)) + 1
            if end >= target:
                best = end
                break
            if end > target + 300:
                break
        best = max(best, pos + CHUNK_MIN)
        best = min(best, pos + CHUNK_MAX)
        c = text[pos:best].strip()
        if c:
            chunks.append(c)
        pos = best - OVERLAP
        if pos <= best - CHUNK_MIN:
            pos = best
    return chunks


def sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\s]+', "_", name).strip("_")[:120]


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 1 – Passauer Datensatz
# ═══════════════════════════════════════════════════════════════════════════


def build_passau_index() -> dict[str, dict]:
    """Lädt den Passauer Datensatz und baut einen AZ-Index."""
    print("\n" + "=" * 60)
    print("SCHRITT 1 – Passauer Datensatz (HuggingFace)")
    print("=" * 60)

    try:
        from datasets import load_dataset
    except ImportError:
        print("  WARNUNG: 'datasets'-Paket nicht installiert. Überspringe Passauer DS.")
        return {}

    print("  Lade harshildarji/openlegaldata (streaming) ...")
    try:
        ds = load_dataset("harshildarji/openlegaldata", split="main", streaming=True)
    except Exception as e:
        print(f"  FEHLER: {e}")
        return {}

    # Index über normalisierte Aktenzeichen
    index: dict[str, dict] = {}
    count = 0
    for row in ds:
        fn = row.get("file_number", "")
        if not fn:
            continue
        az_norm = normalize_az(fn)

        tenor = row.get("tenor") or []
        tatbestand = row.get("tatbestand") or []
        eg = row.get("entscheidungsgründe") or row.get("entscheidungsgruende") or []

        # Nur brauchbare Einträge
        if not (tenor or tatbestand or eg):
            continue

        index[az_norm] = {
            "tenor": "\n".join(tenor) if isinstance(tenor, list) else str(tenor),
            "tatbestand": "\n".join(tatbestand) if isinstance(tatbestand, list) else str(tatbestand),
            "entscheidungsgruende": "\n".join(eg) if isinstance(eg, list) else str(eg),
        }
        count += 1
        if count % 50000 == 0:
            print(f"    {count} Einträge indexiert ...")

    print(f"  {count} Einträge im Passauer Index.")
    return index


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 2 – Heuristischer Segmentierer (deutsche Gerichte)
# ═══════════════════════════════════════════════════════════════════════════

# Überschriften-Patterns (case-insensitive)
DE_PATTERNS = {
    "leitsatz": [
        r"(?:^|\n)\s*(?:Leitsatz|Leitsätze|Orientierungssatz|Orientierungssätze)\s*\n",
    ],
    "tenor": [
        r"(?:^|\n)\s*(?:Tenor|T\s*e\s*n\s*o\s*r)\s*\n",
        r"(?:^|\n)\s*(?:hat\s+(?:erkannt|für\s+Recht\s+erkannt|beschlossen))\s*[:.]",
        r"(?:^|\n)\s*Im\s+Namen\s+des\s+Volkes\s*\n",
    ],
    "tatbestand": [
        r"(?:^|\n)\s*(?:Tatbestand|Sachverhalt|T\s*a\s*t\s*b\s*e\s*s\s*t\s*a\s*n\s*d)\s*\n",
    ],
    "entscheidungsgruende": [
        r"(?:^|\n)\s*(?:Entscheidungsgründe|Gründe|Aus\s+den\s+Gründen)\s*\n",
        r"(?:^|\n)\s*(?:E\s*n\s*t\s*s\s*c\s*h\s*e\s*i\s*d\s*u\s*n\s*g\s*s\s*g\s*r\s*ü\s*n\s*d\s*e)\s*\n",
        r"(?:^|\n)\s*(?:Die\s+Revision|Die\s+Berufung|Die\s+Klage|Die\s+Beschwerde)\s+(?:ist|hat|wird|war)",
    ],
}


def segment_deutsch(volltext: str) -> dict[str, str] | None:
    """Heuristische Segmentierung für deutsche Gerichtsentscheidungen."""
    if not volltext or len(volltext) < 200:
        return None

    # Finde alle Positionen der Überschriften
    found: list[tuple[int, str]] = []
    for segment_name, patterns in DE_PATTERNS.items():
        for pat in patterns:
            for m in re.finditer(pat, volltext, re.IGNORECASE | re.MULTILINE):
                found.append((m.start(), segment_name))
                break  # Nur erste Treffer pro Pattern-Gruppe
            if any(name == segment_name for _, name in found):
                break

    if len(found) < 2:
        return None  # Nicht genug Struktur erkannt

    # Sortiere nach Position
    found.sort(key=lambda x: x[0])

    # Schneide Abschnitte zu
    segments: dict[str, str] = {}
    for i, (pos, name) in enumerate(found):
        # Text bis zum nächsten Abschnitt (oder Ende)
        end = found[i + 1][0] if i + 1 < len(found) else len(volltext)
        # Überschrift selbst überspringen (bis zum Zeilenumbruch)
        text_start = volltext.find("\n", pos)
        if text_start == -1 or text_start > pos + 100:
            text_start = pos + 20
        text = volltext[text_start:end].strip()
        if text and len(text) > 30:
            segments[name] = text

    return segments if segments else None


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 3 – EuGH/EuG-Segmentierer
# ═══════════════════════════════════════════════════════════════════════════

EU_SECTIONS = {
    "sachverhalt": [
        r"(?:^|\n)\s*(?:Rechtlicher\s+Rahmen|Vorgeschichte|"
        r"Sachverhalt|Ausgangsverfahren(?:\s+und\s+Vorlagefragen)?|"
        r"Vorverfahren|Zum\s+Sachverhalt|In\s+der\s+Rechtssache)\s*\n?",
    ],
    "vorlagefragen": [
        r"(?:^|\n)\s*(?:Zu\s+den\s+Vorlagefragen|Vorlagefragen|"
        r"Zur\s+(?:ersten|zweiten|dritten|vierten)\s+(?:Frage|Vorlagefrage))\s*\n?",
    ],
    "wuerdigung": [
        r"(?:^|\n)\s*(?:Würdigung|Zur\s+Begründetheit|"
        r"Rechtliche\s+Würdigung|Beurteilung|"
        r"Zu\s+den\s+Vorlagefragen)\s*\n?",
    ],
    "tenor": [
        r"(?:^|\n)\s*(?:Aus\s+diesen\s+Gründen\s+hat\s+(?:der\s+Gerichtshof|das\s+Gericht)|"
        r"Tenor|erklärt\s+und\s+entscheidet)\s*",
    ],
}


def segment_eugh(volltext: str) -> dict[str, str] | None:
    """Segmentiert EuGH/EuG-Entscheidungen."""
    if not volltext or len(volltext) < 500:
        return None

    found: list[tuple[int, str]] = []
    for segment_name, patterns in EU_SECTIONS.items():
        for pat in patterns:
            for m in re.finditer(pat, volltext, re.IGNORECASE | re.MULTILINE):
                found.append((m.start(), segment_name))
                break
            if any(name == segment_name for _, name in found):
                break

    if not found:
        return None

    found.sort(key=lambda x: x[0])

    segments: dict[str, str] = {}
    for i, (pos, name) in enumerate(found):
        end = found[i + 1][0] if i + 1 < len(found) else len(volltext)
        text_start = volltext.find("\n", pos)
        if text_start == -1 or text_start > pos + 150:
            text_start = pos + 30
        text = volltext[text_start:end].strip()
        if text and len(text) > 30:
            # Falls gleichnamiger Abschnitt schon da, anhängen
            if name in segments:
                segments[name] += "\n\n" + text
            else:
                segments[name] = text

    # Wenn keine wuerdigung, aber vorlagefragen vorhanden,
    # dann ist vorlagefragen = wuerdigung
    if "vorlagefragen" in segments and "wuerdigung" not in segments:
        segments["wuerdigung"] = segments["vorlagefragen"]

    return segments if segments else None


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 5 – Segmentierte Chunks
# ═══════════════════════════════════════════════════════════════════════════


def create_segment_chunks(doc: dict) -> list[dict]:
    """Erzeugt segmentierte Chunks für ein Urteil."""
    chunks = []
    gericht = doc.get("gericht", "Unbekannt")
    az = doc.get("aktenzeichen", "")
    datum = doc.get("datum", "")
    quelle = doc.get("quelle", "")

    base_meta = {
        "gericht": gericht,
        "aktenzeichen": az,
        "datum": datum,
        "quelle": quelle,
    }

    # Segmente die als einzelne Chunks gespeichert werden (kurz)
    short_segments = ["leitsatz", "tenor"]
    # Segmente die gechunked werden (lang)
    long_segments = ["tatbestand", "entscheidungsgruende", "wuerdigung",
                     "vorlagefragen", "sachverhalt"]

    for seg_name in short_segments + long_segments:
        text = doc.get(seg_name, "")
        if not text or len(text.strip()) < 20:
            continue

        seg_type = seg_name
        if seg_name in short_segments:
            # Ein Chunk pro kurzes Segment
            chunk_id = sanitize(f"{gericht}_{az}_{seg_name}")
            chunk = {
                "chunk_id": chunk_id,
                "segment": seg_type,
                "text": text.strip(),
                **base_meta,
            }
            chunks.append(chunk)
            stats["chunk_counts"][seg_type] = stats["chunk_counts"].get(seg_type, 0) + 1

        else:
            # Lange Segmente chunken
            text_chunks = chunk_text(text.strip())
            for idx, ct in enumerate(text_chunks):
                chunk_id = sanitize(f"{gericht}_{az}_{seg_name}_{idx}")
                chunk = {
                    "chunk_id": chunk_id,
                    "chunk_index": idx,
                    "total_chunks": len(text_chunks),
                    "segment": seg_type,
                    "text": ct,
                    **base_meta,
                }
                chunks.append(chunk)
                stats["chunk_counts"][seg_type] = stats["chunk_counts"].get(seg_type, 0) + 1

    return chunks


# ═══════════════════════════════════════════════════════════════════════════
# Hauptprogramm
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 60)
    print("OpenLex MVP – Urteils-Segmentierer")
    print("=" * 60)

    # ── Alle Urteile laden ──
    json_files = sorted(glob.glob(os.path.join(URTEILE_DIR, "*.json")))
    print(f"\n  {len(json_files)} Urteile in {URTEILE_DIR}")

    urteile: list[tuple[str, dict]] = []
    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                urteile.append((fpath, json.load(f)))
        except Exception:
            pass

    print(f"  {len(urteile)} erfolgreich geladen.")

    # ── SCHRITT 1: Passauer Datensatz ──
    passau_index = build_passau_index()

    passau_matched = 0
    passau_az_set = set()

    if passau_index:
        print(f"\n  Matche gegen {len(urteile)} Urteile ...")
        for fpath, doc in urteile:
            az = doc.get("aktenzeichen", "")
            az_norm = normalize_az(az)
            if not az_norm:
                continue

            if az_norm in passau_index:
                p = passau_index[az_norm]
                if p.get("tenor"):
                    doc["tenor"] = p["tenor"]
                if p.get("tatbestand"):
                    doc["tatbestand"] = p["tatbestand"]
                if p.get("entscheidungsgruende"):
                    doc["entscheidungsgruende"] = p["entscheidungsgruende"]
                doc["segmentiert"] = True
                doc["segmentierung_quelle"] = "passau"
                passau_matched += 1
                passau_az_set.add(az_norm)

        print(f"  {passau_matched} Urteile über Passauer Datensatz segmentiert.")
        stats["passau"] = passau_matched

    # ── SCHRITT 2+3: Heuristische Segmentierung ──
    print("\n" + "=" * 60)
    print("SCHRITT 2+3 – Heuristische Segmentierung")
    print("=" * 60)

    eu_gerichte = {"eugh", "eug", "gerichtshof"}

    for fpath, doc in urteile:
        if doc.get("segmentiert"):
            continue

        volltext = doc.get("volltext", "")
        if not volltext or len(volltext) < 200:
            doc["segmentiert"] = False
            stats["unsegmentiert"] += 1
            continue

        gericht = doc.get("gericht", "").lower()
        is_eu = any(g in gericht for g in eu_gerichte) or doc.get("quelle", "") in (
            "eugh_cellar", "cellar_eurlex", "gdprhub"
        )

        if is_eu:
            # SCHRITT 3: EuGH/EuG
            segments = segment_eugh(volltext)
            if segments:
                for seg_name, seg_text in segments.items():
                    doc[seg_name] = seg_text
                doc["segmentiert"] = True
                doc["segmentierung_quelle"] = "heuristisch_eugh"
                stats["heuristisch_eu"] += 1
            else:
                doc["segmentiert"] = False
                stats["unsegmentiert"] += 1
        else:
            # SCHRITT 2: Deutsche Gerichte
            segments = segment_deutsch(volltext)
            if segments:
                for seg_name, seg_text in segments.items():
                    doc[seg_name] = seg_text
                doc["segmentiert"] = True
                doc["segmentierung_quelle"] = "heuristisch_de"
                stats["heuristisch_de"] += 1
            else:
                doc["segmentiert"] = False
                stats["unsegmentiert"] += 1

    seg_total = stats["passau"] + stats["heuristisch_de"] + stats["heuristisch_eu"]
    print(f"\n  Passauer DS:     {stats['passau']}")
    print(f"  Heuristisch DE:  {stats['heuristisch_de']}")
    print(f"  Heuristisch EU:  {stats['heuristisch_eu']}")
    print(f"  Unsegmentiert:   {stats['unsegmentiert']}")
    print(f"  Gesamt seg.:     {seg_total}")

    # ── SCHRITT 4: JSON-Dateien aktualisieren ──
    print("\n" + "=" * 60)
    print("SCHRITT 4 – JSON-Dateien aktualisieren")
    print("=" * 60)

    updated = 0
    for fpath, doc in urteile:
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            updated += 1
        except Exception:
            pass
    print(f"  {updated} Dateien aktualisiert.")

    # ── SCHRITT 5: Segmentierte Chunks ──
    print("\n" + "=" * 60)
    print("SCHRITT 5 – Segmentierte Chunks erzeugen")
    print("=" * 60)

    total_chunks = 0
    for fpath, doc in urteile:
        if not doc.get("segmentiert"):
            continue

        chunks = create_segment_chunks(doc)
        for chunk in chunks:
            chunk_fname = sanitize(chunk["chunk_id"]) + ".json"
            chunk_path = os.path.join(SEG_CHUNKS_DIR, chunk_fname)
            with open(chunk_path, "w", encoding="utf-8") as f:
                json.dump(chunk, f, ensure_ascii=False, indent=2)
            total_chunks += 1

    print(f"  {total_chunks} Chunks in {SEG_CHUNKS_DIR}")

    # ── Zusammenfassung ──
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"  Passauer Datensatz:          {stats['passau']}")
    print(f"  Heuristisch (deutsch):       {stats['heuristisch_de']}")
    print(f"  Heuristisch (EuGH/EuG):      {stats['heuristisch_eu']}")
    print(f"  Unsegmentiert:               {stats['unsegmentiert']}")
    print(f"  Segmentiert gesamt:          {seg_total}")
    print(f"\n  Chunks pro Segment-Typ:")
    for seg_type, count in sorted(stats["chunk_counts"].items()):
        print(f"    {seg_type:<25} {count:>6}")
    print(f"    {'GESAMT':<25} {total_chunks:>6}")
    print("=" * 60)


if __name__ == "__main__":
    main()
