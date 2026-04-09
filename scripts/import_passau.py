#!/usr/bin/env python3
"""
import_passau.py – Importiert datenschutzrelevante Instanzgerichts-Urteile
aus dem Passauer Datensatz (harshildarji/openlegaldata) mit professioneller
Segmentierung. Dedupliziert gegen bestehende data/urteile/.
"""

from __future__ import annotations

import glob
import json
import os
import re

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
URTEILE_DIR = os.path.join(BASE_DIR, "data", "urteile")
SEG_CHUNKS_DIR = os.path.join(BASE_DIR, "data", "urteile_segmentiert")
os.makedirs(URTEILE_DIR, exist_ok=True)
os.makedirs(SEG_CHUNKS_DIR, exist_ok=True)

# Datenschutz-Keywords für die Filterung
DS_KEYWORDS = re.compile(
    r"DSGVO|DS-GVO|Datenschutz-Grundverordnung|Datenschutzgrundverordnung|"
    r"BDSG|Bundesdatenschutzgesetz|"
    r"(?:Art(?:ikel)?\.?\s*(?:5|6|7|9|12|13|14|15|16|17|21|22|25|28|32|33|34|44|45|46|49|77|79|82|83|85)\s+(?:DSGVO|DS-GVO))|"
    r"Datenschutzbeauftragter|personenbezogene\s+Daten|"
    r"Auskunftsanspruch|Löschungsanspruch|Einwilligung.*Daten|"
    r"(?:Schadensersatz|Schmerzensgeld).*(?:Daten|DSGVO)|"
    r"Datenverarbeitung|Auftragsverarbeitung",
    re.IGNORECASE,
)

VERWEIS_RE = re.compile(
    r"Art\.?\s*\d+\s*"
    r"(?:Abs\.?\s*\d+\s*)?"
    r"(?:(?:lit\.?\s*[a-z]|Nr\.?\s*\d+)\s*)?"
    r"(?:DSGVO|DS-GVO|GDPR)"
    r"|§§?\s*\d+[a-z]?\s*"
    r"(?:Abs\.?\s*\d+\s*)?"
    r"(?:(?:S(?:atz)?\.?\s*\d+|Nr\.?\s*\d+)\s*)?"
    r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*"
    r"|Art\.?\s*\d+\s+[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*",
    re.UNICODE,
)

# Chunk-Parameter
CHUNK_TARGET = 2400
CHUNK_MIN = 2000
CHUNK_MAX = 3200
OVERLAP = 400
_SATZ_RE = re.compile(r"(\S+)\.\s+([A-ZÄÖÜ(])", re.UNICODE)


def sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\s]+', "_", name).strip("_")[:120]


def normalize_az(az: str) -> str:
    return re.sub(r"[^a-z0-9]", "", az.lower().strip()) if az else ""


def find_verweise(text: str) -> list[str]:
    return list(set(VERWEIS_RE.findall(text)))


def chunk_text(text: str) -> list[str]:
    if not text or len(text) < CHUNK_MIN:
        return [text] if text else []
    chunks, pos, tlen = [], 0, len(text)
    while pos < tlen:
        if tlen - pos <= CHUNK_MAX:
            c = text[pos:].strip()
            if c:
                chunks.append(c)
            break
        target = pos + CHUNK_TARGET
        best = target
        for m in _SATZ_RE.finditer(text, max(pos, target - 200)):
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


def main():
    print("=" * 60)
    print("OpenLex MVP – Passauer Datensatz Import")
    print("=" * 60)

    # Vorhandene AZ laden für Deduplizierung
    existing_az = set()
    for fpath in glob.glob(os.path.join(URTEILE_DIR, "*.json")):
        try:
            with open(fpath) as f:
                doc = json.load(f)
            az = doc.get("aktenzeichen", "")
            if az:
                existing_az.add(normalize_az(az))
        except Exception:
            pass
    print(f"\n  {len(existing_az)} vorhandene Aktenzeichen.")

    # Passauer Datensatz streamen und filtern
    print("  Lade Passauer Datensatz (streaming) ...")
    from datasets import load_dataset
    ds = load_dataset("harshildarji/openlegaldata", split="main", streaming=True)

    imported = 0
    skipped_dup = 0
    skipped_irrelevant = 0
    total_chunks = 0
    chunk_counts = {}

    for row_idx, row in enumerate(ds):
        if row_idx % 50000 == 0 and row_idx > 0:
            print(f"    {row_idx} geprüft, {imported} importiert ...")

        fn = row.get("file_number", "")
        if not fn:
            continue

        # Deduplizierung
        az_norm = normalize_az(fn)
        if az_norm in existing_az:
            skipped_dup += 1
            continue

        # Segmente extrahieren
        tenor_parts = row.get("tenor") or []
        tatbestand_parts = row.get("tatbestand") or []
        eg_parts = row.get("entscheidungsgründe") or []

        tenor = "\n".join(tenor_parts) if isinstance(tenor_parts, list) else ""
        tatbestand = "\n".join(tatbestand_parts) if isinstance(tatbestand_parts, list) else ""
        eg = "\n".join(eg_parts) if isinstance(eg_parts, list) else ""

        volltext = f"{tenor}\n{tatbestand}\n{eg}".strip()

        # Datenschutz-Relevanz prüfen
        if not DS_KEYWORDS.search(volltext):
            skipped_irrelevant += 1
            continue

        # Brauchbare Segmentierung vorhanden?
        if not (tenor or eg):
            skipped_irrelevant += 1
            continue

        # Metadaten
        court = row.get("court", {})
        court_name = court.get("name", "") if isinstance(court, dict) else str(court)
        date = str(row.get("date", ""))[:10]
        ecli = row.get("ecli", "")
        refs = row.get("references", {})
        law_refs = refs.get("law", []) if isinstance(refs, dict) else []

        verweise = find_verweise(volltext)

        # JSON-Dokument erstellen
        doc = {
            "quelle": "passau_openlegaldata",
            "gericht": court_name,
            "datum": date,
            "aktenzeichen": fn,
            "ecli": ecli,
            "leitsatz": "",
            "tenor": tenor,
            "tatbestand": tatbestand,
            "entscheidungsgruende": eg,
            "volltext": volltext[:100000],
            "normbezuege": verweise,
            "referenzen_gesetz": law_refs[:50] if isinstance(law_refs, list) else [],
            "segmentiert": True,
            "segmentierung_quelle": "passau",
        }

        # Speichern
        gericht_s = sanitize(court_name[:25])
        az_s = sanitize(fn[:60])
        fpath = os.path.join(URTEILE_DIR, f"{gericht_s}_{az_s}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        existing_az.add(az_norm)
        imported += 1

        # Segmentierte Chunks erzeugen
        base_meta = {"gericht": court_name, "aktenzeichen": fn,
                     "datum": date, "quelle": "passau_openlegaldata"}

        for seg_name, seg_text in [("tenor", tenor), ("tatbestand", tatbestand),
                                    ("entscheidungsgruende", eg)]:
            if not seg_text or len(seg_text.strip()) < 20:
                continue

            if seg_name == "tenor":
                # Kurz → 1 Chunk
                cid = sanitize(f"{court_name}_{fn}_{seg_name}")
                chunk = {"chunk_id": cid, "segment": seg_name,
                         "text": seg_text.strip(), **base_meta}
                cp = os.path.join(SEG_CHUNKS_DIR, sanitize(cid) + ".json")
                with open(cp, "w", encoding="utf-8") as f:
                    json.dump(chunk, f, ensure_ascii=False, indent=2)
                total_chunks += 1
                chunk_counts[seg_name] = chunk_counts.get(seg_name, 0) + 1
            else:
                # Lang → chunken
                text_chunks = chunk_text(seg_text.strip())
                for idx, ct in enumerate(text_chunks):
                    cid = sanitize(f"{court_name}_{fn}_{seg_name}_{idx}")
                    chunk = {"chunk_id": cid, "chunk_index": idx,
                             "total_chunks": len(text_chunks),
                             "segment": seg_name, "text": ct, **base_meta}
                    cp = os.path.join(SEG_CHUNKS_DIR, sanitize(cid) + ".json")
                    with open(cp, "w", encoding="utf-8") as f:
                        json.dump(chunk, f, ensure_ascii=False, indent=2)
                    total_chunks += 1
                    chunk_counts[seg_name] = chunk_counts.get(seg_name, 0) + 1

    print(f"\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"  Geprüft:                     {row_idx + 1}")
    print(f"  Importiert (Datenschutz):    {imported}")
    print(f"  Übersprungen (Duplikat):     {skipped_dup}")
    print(f"  Übersprungen (irrelevant):   {skipped_irrelevant}")
    print(f"  Segmentierte Chunks:         {total_chunks}")
    print(f"\n  Chunks pro Segment:")
    for seg, cnt in sorted(chunk_counts.items()):
        print(f"    {seg:<25} {cnt:>6}")
    print(f"    {'GESAMT':<25} {total_chunks:>6}")
    print(f"\n  Gespeichert in: {URTEILE_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
