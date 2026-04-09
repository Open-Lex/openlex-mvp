#!/usr/bin/env python3
"""
load_eugh_landmark_cases.py – Lädt die drei Landmark-Urteile zum Recht auf
Vergessenwerden als segmentierte Chunks in ChromaDB:

  - C-131/12  (Google Spain, 13.05.2014)
  - C-136/17  (GC u.a., 24.09.2019)
  - C-507/17  (Google/CNIL, 24.09.2019)

Verwendet die bereits vorhandenen Raw-JSONs in data/urteile/.
"""

from __future__ import annotations

import json
import os
import re
import sys

import chromadb
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
URTEILE_DIR = os.path.join(BASE_DIR, "data", "urteile")
SEG_DIR = os.path.join(BASE_DIR, "data", "urteile_segmentiert")
NAMES_FILE = os.path.join(BASE_DIR, "data", "urteilsnamen.json")

CHUNK_TARGET = 2400
CHUNK_MIN = 2000
CHUNK_MAX = 3200
OVERLAP = 400

EMBED_MODEL = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"

CASES = {
    "C-131/12": {
        "json_file": "EuGH_C-131_12.json",
        "kurzname": "Google Spain",
        "datum": "2014-05-13",
    },
    "C-136/17": {
        "json_file": "EuGH_Rechtssache_C-136_17.json",
        "kurzname": "GC u.a.",
        "datum": "2019-09-24",
    },
    "C-507/17": {
        "json_file": "EuGH_Rechtssache_C-507_17.json",
        "kurzname": "CNIL/Google",
        "datum": "2019-09-24",
    },
}

# Segment-Prefix für Embedding-Text (wie update_index.py)
SEGMENT_PREFIX = {
    "sachverhalt": "Sachverhalt: ",
    "wuerdigung": "Würdigung des Gerichtshofs: ",
    "tenor": "Tenor: ",
    "vorlagefragen": "Vorlagefragen: ",
    "leitsatz": "Leitsatz: ",
    "tatbestand": "Tatbestand: ",
    "entscheidungsgruende": "Entscheidungsgründe: ",
}


# ---------------------------------------------------------------------------
# Chunking (aus segment_urteile.py übernommen)
# ---------------------------------------------------------------------------

_ABK = {
    "abs", "art", "nr", "lit", "buchst", "bzw", "gem", "vgl", "usw",
    "etc", "sog", "ggf", "bsp", "var", "ziff", "rn", "kap", "anh",
    "bgh", "bsg", "bfh", "bag", "bverwg", "bverfg", "eugh", "dr", "prof",
}
_SATZ_KANDIDAT = re.compile(r"(\S+)\.\s+([A-ZÄÖÜ(])", re.UNICODE)


def chunk_text(text: str) -> list[str]:
    """Teilt Text in überlappende Chunks an Satzgrenzen."""
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


def normalize_az(az: str) -> str:
    """Normalisiert Aktenzeichen (Non-Breaking Hyphen → Normal Hyphen)."""
    return az.replace("\u2011", "-").replace("\u2013", "-").replace("‑", "-").replace("–", "-")


# ---------------------------------------------------------------------------
# Custom Segmentierung für C-131/12
# ---------------------------------------------------------------------------

def segment_c131(volltext: str) -> dict[str, str]:
    """
    C-131/12 hat keine klaren Abschnittsüberschriften im EuGH-Stil.
    Manuelle Segmentierung:
      - sachverhalt: Header + Rechtlicher Rahmen + Fakten + Vorlagefragen (bis ~26500)
      - wuerdigung: Gerichtshof-Analyse (ab ~26500 bis Tenor)
      - tenor: Ab 'Aus diesen Gründen hat der Gerichtshof'
    """
    # Tenor finden
    tenor_marker = "Aus diesen Gründen hat der Gerichtshof"
    tenor_pos = volltext.find(tenor_marker)
    if tenor_pos < 0:
        tenor_pos = len(volltext)

    # Würdigung-Beginn: Die Stellungnahmen der Beteiligten beginnen ca. nach den
    # Vorlagefragen. Die eigentliche Analyse beginnt nach den Stellungnahmen.
    # Pragmatisch: Suche nach der Stelle wo der Gerichtshof anfängt, die Fragen
    # inhaltlich zu beantworten. Das ist ca. bei Position 26500 (nach den Parteistell.)
    # Genauer: Finde "Zur Beantwortung" oder den Bereich nach den Fragen

    # Suche die letzte Frage der Audiencia Nacional (markiert Ende Sachverhalt)
    # "Zur Tragweite des Rechts auf Löschung" ist die letzte Fragengruppe (~24827)
    # Danach kommen Stellungnahmen der Parteien.
    # Die eigentliche Analyse des Gerichtshofs beginnt bei "Bei der Tätigkeit, um die
    # es im Ausgangsverfahren geht" (~29000) oder ähnlich.
    # Pragmatisch: Split bei ~26500 (nach Fragen + vor Stellungnahmen/Analyse)

    wuerdigung_pos = 26500

    # Versuche, eine bessere Position zu finden
    # Der Gerichtshof beginnt mit der Analyse ab dem Abschnitt über Art. 2 Buchst. b
    # Suche "Bei der Tätigkeit" als Marker für den Analysebeginn
    analysis_start = volltext.find("Bei der Tätigkeit, um die es im Ausgangsverfahren")
    if analysis_start > 0 and analysis_start < tenor_pos:
        # Gehe etwas zurück um den Kontext zu fangen
        # Suche den vorherigen Absatz
        prev_para = volltext.rfind("\n", 0, analysis_start - 10)
        if prev_para > 0:
            wuerdigung_pos = prev_para
        else:
            wuerdigung_pos = analysis_start

    segments = {
        "sachverhalt": volltext[:wuerdigung_pos].strip(),
        "wuerdigung": volltext[wuerdigung_pos:tenor_pos].strip(),
        "tenor": volltext[tenor_pos:].strip(),
    }

    return segments


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("OpenLex MVP – Landmark-Urteile laden")
    print("=" * 60)

    # ChromaDB öffnen
    client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chromadb"))
    col = client.get_collection("openlex_datenschutz")
    print(f"\nChromaDB: {col.count()} Chunks")

    # Existing IDs für Deduplizierung
    existing = set(col.get(include=[])["ids"])

    # Embedding-Model laden
    print(f"\nLade Embedding-Model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)
    print("  ✓ Model geladen")

    total_new = 0

    for rechtssache, cfg in CASES.items():
        print(f"\n{'─' * 60}")
        print(f"  {rechtssache} ({cfg['kurzname']})")
        print(f"{'─' * 60}")

        # 1. Raw-JSON laden
        json_path = os.path.join(URTEILE_DIR, cfg["json_file"])
        if not os.path.exists(json_path):
            print(f"  ✗ JSON nicht gefunden: {json_path}")
            continue

        with open(json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        volltext = doc.get("volltext", "")
        print(f"  Volltext: {len(volltext)} Zeichen")

        # AZ normalisieren
        az_raw = doc.get("aktenzeichen", "")
        az_norm = normalize_az(az_raw)
        print(f"  AZ: {az_raw} → {az_norm}")

        datum = cfg["datum"] or doc.get("datum", "")
        quelle = doc.get("quelle", "eugh_cellar")

        # 2. Check ob bereits als urteil_segmentiert in ChromaDB
        existing_seg = col.get(
            where={"source_type": "urteil_segmentiert"},
            include=["metadatas"],
            limit=25000,
        )
        case_pattern = rechtssache.replace("C-", "").replace("/", "_")
        already_in_db = sum(
            1 for m in existing_seg["metadatas"]
            if case_pattern.replace("_", "/") in normalize_az(m.get("aktenzeichen", ""))
            or rechtssache in normalize_az(m.get("aktenzeichen", ""))
        )

        if already_in_db > 0:
            print(f"  → Bereits {already_in_db} urteil_segmentiert Chunks in ChromaDB")
            if rechtssache != "C-131/12":
                print(f"  → Überspringe (bereits vorhanden)")
                continue
            else:
                print(f"  → C-131/12 trotzdem verarbeiten (war 0)")

        # 3. Segmentieren
        if rechtssache == "C-131/12":
            print("  Custom-Segmentierung für C-131/12...")
            segments = segment_c131(volltext)
        else:
            # Standard-Segmentierung aus JSON-Feldern
            segments = {}
            for seg_name in ["sachverhalt", "wuerdigung", "vorlagefragen", "tenor",
                             "tatbestand", "entscheidungsgruende", "leitsatz"]:
                text = doc.get(seg_name, "")
                if text and len(text.strip()) > 50:
                    segments[seg_name] = text.strip()

        for seg_name, seg_text in segments.items():
            print(f"  Segment '{seg_name}': {len(seg_text)} Zeichen")

        # 4. Chunks erzeugen
        all_chunks = []
        short_segments = {"leitsatz", "tenor"}

        for seg_name, seg_text in segments.items():
            if seg_name in short_segments and len(seg_text) < CHUNK_MAX:
                chunk_id = sanitize(f"EuGH_{az_norm}_{seg_name}")
                all_chunks.append({
                    "chunk_id": chunk_id,
                    "segment": seg_name,
                    "text": seg_text,
                })
            else:
                text_chunks = chunk_text(seg_text)
                for idx, ct in enumerate(text_chunks):
                    chunk_id = sanitize(f"EuGH_{az_norm}_{seg_name}_{idx}")
                    all_chunks.append({
                        "chunk_id": chunk_id,
                        "chunk_index": idx,
                        "total_chunks": len(text_chunks),
                        "segment": seg_name,
                        "text": ct,
                    })

        print(f"  → {len(all_chunks)} Chunks erzeugt")

        # 5. Chunk-Dateien schreiben (für Konsistenz mit Pipeline)
        for chunk in all_chunks:
            chunk_file = {
                "chunk_id": chunk["chunk_id"],
                "segment": chunk["segment"],
                "text": chunk["text"],
                "gericht": "EuGH",
                "aktenzeichen": az_norm,
                "datum": datum,
                "quelle": quelle,
            }
            if "chunk_index" in chunk:
                chunk_file["chunk_index"] = chunk["chunk_index"]
                chunk_file["total_chunks"] = chunk["total_chunks"]

            fpath = os.path.join(SEG_DIR, f"{chunk['chunk_id']}.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(chunk_file, f, ensure_ascii=False, indent=2)

        print(f"  → {len(all_chunks)} Chunk-Dateien geschrieben")

        # 6. In ChromaDB embedden
        ids_to_add = []
        docs_to_add = []
        metas_to_add = []
        embed_texts = []

        for chunk in all_chunks:
            chroma_id = f"seg_{chunk['chunk_id']}"

            if chroma_id in existing:
                continue

            prefix = SEGMENT_PREFIX.get(chunk["segment"], "")
            embed_text = f"{prefix}{chunk['text']}"

            meta = {
                "source_type": "urteil_segmentiert",
                "gericht": "EuGH",
                "aktenzeichen": az_norm,
                "kurzname": cfg["kurzname"],
                "datum": datum,
                "quelle": quelle,
                "segment": chunk["segment"],
                "chunk_id": chunk["chunk_id"],
            }
            if "chunk_index" in chunk:
                meta["chunk_index"] = chunk["chunk_index"]
                meta["total_chunks"] = chunk["total_chunks"]

            ids_to_add.append(chroma_id)
            docs_to_add.append(chunk["text"])
            metas_to_add.append(meta)
            embed_texts.append(embed_text)
            existing.add(chroma_id)

        if not ids_to_add:
            print("  → Alle Chunks bereits in ChromaDB")
            continue

        print(f"  Embedde {len(ids_to_add)} neue Chunks...")
        embeddings = model.encode(embed_texts, normalize_embeddings=True,
                                   show_progress_bar=False).tolist()

        # Batch-Add (max 5000 pro Batch)
        batch_size = 500
        for i in range(0, len(ids_to_add), batch_size):
            end = min(i + batch_size, len(ids_to_add))
            col.add(
                ids=ids_to_add[i:end],
                documents=docs_to_add[i:end],
                metadatas=metas_to_add[i:end],
                embeddings=embeddings[i:end],
            )

        total_new += len(ids_to_add)
        print(f"  ✓ {len(ids_to_add)} Chunks in ChromaDB eingebettet")

    # ──────────────────────────────────────────────────────────────────────
    # urteilsnamen.json aktualisieren
    # ──────────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print("urteilsnamen.json aktualisieren")
    print(f"{'═' * 60}")

    with open(NAMES_FILE, "r", encoding="utf-8") as f:
        names = json.load(f)

    updates = {
        "C-131/12": "Google Spain",
        "C-136/17": "GC u.a.",
        "C-507/17": "CNIL/Google",
    }

    changed = False
    for az, name in updates.items():
        old = names.get(az)
        if old != name:
            names[az] = name
            print(f"  {az}: {old!r} → {name!r}")
            changed = True
        else:
            print(f"  {az}: {name!r} (bereits korrekt)")

    if changed:
        with open(NAMES_FILE, "w", encoding="utf-8") as f:
            json.dump(names, f, ensure_ascii=False, indent=2)
        print("  ✓ Gespeichert")

    # ──────────────────────────────────────────────────────────────────────
    # Zusammenfassung
    # ──────────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print("Zusammenfassung")
    print(f"{'═' * 60}")
    print(f"  Neue Chunks: {total_new}")
    print(f"  ChromaDB gesamt: {col.count()}")

    # Verifizierung
    seg_all = col.get(where={"source_type": "urteil_segmentiert"}, include=["metadatas"], limit=25000)
    for az in ["131/12", "136/17", "507/17"]:
        count = sum(1 for m in seg_all["metadatas"] if az in normalize_az(m.get("aktenzeichen", "")))
        print(f"  C-{az}: {count} urteil_segmentiert Chunks")


if __name__ == "__main__":
    main()
