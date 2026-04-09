#!/usr/bin/env python3
"""
rechunk_eugh.py – Re-Chunking aller EuGH/EuG-Urteile mit semantischem Parser.

Schritte:
  1. Volltext aus data/urteile/ laden (bevorzugt) oder aus ChromaDB rekonstruieren
  2. Alle bestehenden EuGH/EuG-Chunks löschen
  3. Mit parse_eugh.py semantisch parsen und neu chunken
  4. In ChromaDB embedden
  5. Statistiken berichten

Fortschritt wird in rechunk_progress.json gespeichert.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import traceback
from collections import Counter

import chromadb
from sentence_transformers import SentenceTransformer

from parse_eugh import parse_and_chunk, normalize_az, Segment

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
URTEILE_DIR = os.path.join(BASE_DIR, "data", "urteile")
RAW_DIR = os.path.join(BASE_DIR, "data", "urteile_eugh_raw")
NAMES_FILE = os.path.join(BASE_DIR, "data", "urteilsnamen.json")
PROGRESS_FILE = os.path.join(BASE_DIR, "rechunk_progress.json")
EMBED_MODEL = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"
BATCH_SIZE = 100

# Segment-Prefix für Embedding-Text
SEGMENT_PREFIX = {
    "header": "",
    "rechtsrahmen": "Rechtsrahmen: ",
    "sachverhalt": "Sachverhalt: ",
    "vorlagefragen": "Vorlagefragen: ",
    "wuerdigung": "Würdigung des Gerichtshofs: ",
    "tenor": "Tenor: ",
}

os.makedirs(RAW_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Fortschritts-Management
# ---------------------------------------------------------------------------

def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(progress: dict):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def sanitize_filename(az: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]', '_', az).strip('_')


def detect_language(text: str) -> str:
    """Erkennt ob Text deutsch oder englisch ist."""
    sample = text[:1000].lower()
    de_words = ["der", "die", "das", "und", "ist", "für", "des", "den", "dem",
                "verarbeitung", "personenbezogene", "daten", "richtlinie", "verordnung"]
    en_words = ["the", "and", "for", "with", "that", "this", "processing",
                "personal", "data", "directive", "regulation", "court"]
    de_score = sum(1 for w in de_words if f" {w} " in f" {sample} ")
    en_score = sum(1 for w in en_words if f" {w} " in f" {sample} ")
    return "de" if de_score > en_score else "en"


def get_segment_prefix(seg_name: str) -> str:
    """Ermittelt den Embedding-Prefix basierend auf dem Segment-Basisnamen."""
    base = seg_name.split("_")[0] if "_" in seg_name else seg_name
    # vf_1, vf_2b etc. → "Vorlagefrage"
    if seg_name.startswith("vf_"):
        return "Vorlagefrage: "
    return SEGMENT_PREFIX.get(base, "")


# ---------------------------------------------------------------------------
# SCHRITT 1: Volltexte sammeln
# ---------------------------------------------------------------------------

def collect_volltexte(col) -> dict[str, dict]:
    """
    Sammelt Volltexte für alle EuGH/EuG-Urteile.
    Bevorzugt: data/urteile/ JSON-Dateien (vollständig).
    Fallback: Chunks aus ChromaDB rekonstruieren.
    """
    print("\n" + "=" * 60)
    print("SCHRITT 1 – Volltexte sammeln")
    print("=" * 60)

    # 1a. Alle EuGH/EuG AZ aus ChromaDB ermitteln
    all_u = col.get(where={"source_type": "urteil"}, include=["metadatas"], limit=25000)
    all_s = col.get(where={"source_type": "urteil_segmentiert"}, include=["metadatas"], limit=25000)

    az_set = set()
    az_meta: dict[str, dict] = {}  # norm_az → best metadata

    for meta_list in [all_u["metadatas"], all_s["metadatas"]]:
        for m in meta_list:
            gericht = m.get("gericht", "")
            if "EuGH" not in gericht and gericht != "EuG":
                continue
            raw_az = m.get("aktenzeichen", "") or m.get("rechtssache", "")
            norm = normalize_az(raw_az).replace("Rechtssache ", "").strip()
            if norm:
                az_set.add(norm)
                if norm not in az_meta:
                    az_meta[norm] = {
                        "gericht": gericht,
                        "datum": m.get("datum", ""),
                        "kurzname": m.get("kurzname", ""),
                        "quelle": m.get("quelle", ""),
                    }

    print(f"  {len(az_set)} unique EuGH/EuG-Aktenzeichen in ChromaDB")

    # 1b. Lade urteilsnamen
    names = {}
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, "r", encoding="utf-8") as f:
            names = json.load(f)

    # 1c. Finde Volltexte in data/urteile/
    json_files = os.listdir(URTEILE_DIR)
    urteile: dict[str, dict] = {}  # norm_az → {volltext, gericht, datum, ...}

    for az in sorted(az_set):
        # Suche passende JSON-Datei
        num_match = re.match(r'C-?(\d+)/(\d+)', az)
        if not num_match:
            continue
        num1, num2 = num_match.group(1), num_match.group(2)

        # Mögliche Dateinamen
        candidates = [
            f"EuGH_C-{num1}_{num2}.json",
            f"EuGH_Rechtssache_C-{num1}_{num2}.json",
            f"EuGH_Rechtssache_C_{num1}_{num2}.json",
        ]

        json_file = None
        for c in candidates:
            if c in json_files:
                json_file = c
                break
        if not json_file:
            # Fuzzy match
            for f in json_files:
                if f"_{num1}_{num2}" in f and f.startswith("EuGH"):
                    json_file = f
                    break

        if json_file:
            fpath = os.path.join(URTEILE_DIR, json_file)
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    doc = json.load(fh)
                volltext = doc.get("volltext", "")
                if volltext and len(volltext) > 500:
                    lang = detect_language(volltext)
                    meta = az_meta.get(az, {})
                    kurzname = doc.get("kurzname") or names.get(az) or meta.get("kurzname", "")
                    urteile[az] = {
                        "volltext": volltext,
                        "gericht": doc.get("gericht") or meta.get("gericht", "EuGH"),
                        "datum": doc.get("datum") or meta.get("datum", ""),
                        "kurzname": kurzname,
                        "quelle": doc.get("quelle") or meta.get("quelle", "eugh_cellar"),
                        "json_file": json_file,
                        "sprache": lang,
                    }
            except Exception:
                pass

    # 1d. Für fehlende AZ: aus ChromaDB-Chunks rekonstruieren
    missing = az_set - set(urteile.keys())
    if missing:
        print(f"  {len(missing)} Urteile ohne Raw-JSON, rekonstruiere aus Chunks...")
        # Get all chunks with documents
        for src_type in ["urteil", "urteil_segmentiert"]:
            chunks_data = col.get(
                where={"source_type": src_type},
                include=["metadatas", "documents"],
                limit=25000,
            )
            for cid, meta, doc in zip(chunks_data["ids"], chunks_data["metadatas"], chunks_data["documents"]):
                gericht = meta.get("gericht", "")
                if "EuGH" not in gericht and gericht != "EuG":
                    continue
                raw_az = meta.get("aktenzeichen", "") or meta.get("rechtssache", "")
                norm = normalize_az(raw_az).replace("Rechtssache ", "").strip()
                if norm in missing and doc:
                    if norm not in urteile:
                        urteile[norm] = {
                            "volltext": "",
                            "gericht": gericht,
                            "datum": meta.get("datum", ""),
                            "kurzname": meta.get("kurzname") or names.get(norm, ""),
                            "quelle": meta.get("quelle", ""),
                            "json_file": None,
                            "sprache": "unknown",
                            "chunks": [],
                        }
                    urteile[norm].setdefault("chunks", []).append(
                        (meta.get("chunk_index", 0) or 0, doc)
                    )

        # Rekonstruiere Volltext aus sortierten Chunks
        for az in list(missing):
            if az in urteile and urteile[az].get("chunks"):
                chunks = sorted(urteile[az]["chunks"], key=lambda x: x[0])
                volltext = "\n\n".join(text for _, text in chunks)
                urteile[az]["volltext"] = volltext
                urteile[az]["sprache"] = detect_language(volltext)
                del urteile[az]["chunks"]

    # 1e. Speichere Raw-Texte
    for az, data in urteile.items():
        vt = data.get("volltext", "")
        if vt:
            fname = sanitize_filename(az) + ".txt"
            with open(os.path.join(RAW_DIR, fname), "w", encoding="utf-8") as f:
                f.write(vt)

    de_count = sum(1 for d in urteile.values() if d.get("sprache") == "de")
    en_count = sum(1 for d in urteile.values() if d.get("sprache") == "en")
    print(f"  Gesammelt: {len(urteile)} Urteile (DE: {de_count}, EN: {en_count})")

    return urteile


# ---------------------------------------------------------------------------
# SCHRITT 2: Alte Chunks löschen
# ---------------------------------------------------------------------------

def delete_old_chunks(col) -> int:
    print("\n" + "=" * 60)
    print("SCHRITT 2 – Alte EuGH/EuG-Chunks löschen")
    print("=" * 60)

    total_deleted = 0
    for src_type in ["urteil", "urteil_segmentiert"]:
        data = col.get(where={"source_type": src_type}, include=["metadatas"], limit=25000)
        ids_to_delete = []
        for cid, meta in zip(data["ids"], data["metadatas"]):
            gericht = meta.get("gericht", "")
            if "EuGH" in gericht or gericht == "EuG":
                ids_to_delete.append(cid)

        if ids_to_delete:
            for i in range(0, len(ids_to_delete), 500):
                col.delete(ids=ids_to_delete[i:i + 500])
            print(f"  {src_type}: {len(ids_to_delete)} Chunks gelöscht")
            total_deleted += len(ids_to_delete)

    print(f"  Gesamt gelöscht: {total_deleted}")
    print(f"  ChromaDB nach Löschung: {col.count()}")
    return total_deleted


# ---------------------------------------------------------------------------
# SCHRITT 3+4: Parse und Embedde
# ---------------------------------------------------------------------------

def parse_and_embed(col, urteile: dict[str, dict], model: SentenceTransformer) -> dict:
    print("\n" + "=" * 60)
    print("SCHRITT 3+4 – Parse und Embedde")
    print("=" * 60)

    progress = load_progress()
    done_az = set(progress.get("rechunked_az", []))

    stats = {
        "total": 0,
        "semantic": 0,  # VF erkannt
        "fallback": 0,  # Nur wuerdigung-Blöcke
        "skipped_en": 0,
        "skipped_short": 0,
        "errors": 0,
        "total_chunks": 0,
    }

    log_entries: list[dict] = []

    # Batch-Puffer
    batch_ids: list[str] = []
    batch_docs: list[str] = []
    batch_metas: list[dict] = []
    batch_embeds: list[str] = []

    def flush_batch():
        if not batch_ids:
            return
        embeddings = model.encode(batch_embeds, normalize_embeddings=True,
                                   show_progress_bar=False).tolist()
        col.add(ids=batch_ids[:], documents=batch_docs[:],
                metadatas=batch_metas[:], embeddings=embeddings)
        batch_ids.clear()
        batch_docs.clear()
        batch_metas.clear()
        batch_embeds.clear()

    existing_ids = set(col.get(include=[])["ids"])

    for i, (az, data) in enumerate(sorted(urteile.items())):
        if az in done_az:
            continue

        volltext = data.get("volltext", "")
        sprache = data.get("sprache", "unknown")
        gericht = data.get("gericht", "EuGH")
        datum = data.get("datum", "")
        kurzname = data.get("kurzname", "")
        quelle = data.get("quelle", "eugh_cellar")

        # Skip englische Texte
        if sprache == "en":
            stats["skipped_en"] += 1
            log_entries.append({
                "az": az, "status": "skipped_en",
                "reason": "Englischer Text",
            })
            done_az.add(az)
            continue

        # Skip zu kurze Texte
        if len(volltext) < 1000:
            stats["skipped_short"] += 1
            done_az.add(az)
            continue

        try:
            # Parse
            segments = parse_and_chunk(volltext, az)

            if not segments:
                stats["errors"] += 1
                log_entries.append({"az": az, "status": "error", "reason": "Keine Segmente"})
                done_az.add(az)
                continue

            # Prüfe ob VF erkannt
            has_vf = any(s.name.startswith("vf_") for s in segments)
            has_tenor = any("tenor" in s.name for s in segments)

            if has_vf:
                stats["semantic"] += 1
            else:
                stats["fallback"] += 1

            stats["total"] += 1

            # Chunks erzeugen
            used_chunk_ids = set()
            for seg in segments:
                chunk_id = sanitize_filename(f"eugh_{az}_{seg.name}")

                # Eindeutigkeit sicherstellen
                if chunk_id in used_chunk_ids:
                    suffix = 1
                    while f"{chunk_id}_{suffix}" in used_chunk_ids:
                        suffix += 1
                    chunk_id = f"{chunk_id}_{suffix}"
                used_chunk_ids.add(chunk_id)

                chroma_id = f"seg_{chunk_id}"
                if chroma_id in existing_ids:
                    continue

                prefix = get_segment_prefix(seg.name)
                embed_text = f"{prefix}{seg.text}"

                meta = {
                    "source_type": "urteil_segmentiert",
                    "gericht": gericht or "EuGH",
                    "aktenzeichen": az or "",
                    "kurzname": kurzname or "",
                    "datum": datum or "",
                    "quelle": quelle or "",
                    "segment": seg.name or "",
                    "chunk_id": chunk_id or "",
                }

                batch_ids.append(chroma_id)
                batch_docs.append(seg.text)
                batch_metas.append(meta)
                batch_embeds.append(embed_text)
                existing_ids.add(chroma_id)
                stats["total_chunks"] += 1

                if len(batch_ids) >= BATCH_SIZE:
                    flush_batch()

            # Logging
            vf_count = len(set(
                s.name.rsplit("_", 1)[0] if re.match(r'vf_\d+[a-z]?_\d+', s.name) else s.name
                for s in segments if s.name.startswith("vf_")
            ))
            log_entries.append({
                "az": az,
                "kurzname": kurzname,
                "status": "ok",
                "segments": len(segments),
                "vf_count": vf_count,
                "has_tenor": has_tenor,
                "mode": "semantic" if has_vf else "fallback",
            })

            done_az.add(az)

            # Fortschritt speichern alle 10 Urteile
            if len(done_az) % 10 == 0:
                progress["rechunked_az"] = sorted(done_az)
                progress["stats"] = stats
                save_progress(progress)

            # Status ausgeben
            if (i + 1) % 5 == 0 or has_vf:
                mode = "SEM" if has_vf else "FB"
                print(f"  [{i+1:>3}/{len(urteile)}] {az:<16} {(kurzname or ''):<20} "
                      f"{len(segments):>3} seg  VF={vf_count}  T={'✓' if has_tenor else '✗'}  [{mode}]")

        except Exception as e:
            stats["errors"] += 1
            log_entries.append({"az": az, "status": "error", "reason": str(e)})
            done_az.add(az)
            print(f"  FEHLER {az}: {e}")

    # Letzte Batch flushen
    flush_batch()

    # Finaler Fortschritt
    progress["rechunked_az"] = sorted(done_az)
    progress["stats"] = stats
    progress["log"] = log_entries
    save_progress(progress)

    return stats


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("OpenLex MVP – EuGH Re-Chunking mit semantischem Parser")
    print("=" * 60)

    # ChromaDB
    client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chromadb"))
    col = client.get_collection("openlex_datenschutz")
    pre_count = col.count()
    print(f"\nChromaDB vorher: {pre_count} Chunks")

    # SCHRITT 1: Volltexte sammeln
    urteile = collect_volltexte(col)

    # SCHRITT 2: Alte Chunks löschen
    old_chunk_count = delete_old_chunks(col)

    # Embedding-Model laden
    print(f"\nLade Embedding-Model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)
    print("  ✓ Model geladen")

    # SCHRITT 3+4: Parse und Embedde
    stats = parse_and_embed(col, urteile, model)

    # SCHRITT 5: Statistik
    post_count = col.count()

    print(f"\n\n{'═' * 60}")
    print("  SCHRITT 5 – Gesamtstatistik")
    print(f"{'═' * 60}")
    print(f"  Urteile gesamt:              {stats['total']}")
    print(f"  Semantisch (VF erkannt):     {stats['semantic']}")
    print(f"  Fallback (wuerdigung):       {stats['fallback']}")
    print(f"  Übersprungen (Englisch):     {stats['skipped_en']}")
    print(f"  Übersprungen (zu kurz):      {stats['skipped_short']}")
    print(f"  Fehler:                      {stats['errors']}")
    print(f"  ─────────────────────────────────")
    print(f"  Alte Chunk-Anzahl:           {old_chunk_count}")
    print(f"  Neue Chunk-Anzahl:           {stats['total_chunks']}")
    print(f"  ChromaDB vorher:             {pre_count}")
    print(f"  ChromaDB nachher:            {post_count}")

    # Zeige englische Urteile
    progress = load_progress()
    en_cases = [e for e in progress.get("log", []) if e.get("status") == "skipped_en"]
    if en_cases:
        print(f"\n  Englische Urteile (übersprungen):")
        for e in en_cases:
            print(f"    {e['az']}")

    save_progress(progress)
    print(f"\n  Progress gespeichert: {PROGRESS_FILE}")


if __name__ == "__main__":
    main()
