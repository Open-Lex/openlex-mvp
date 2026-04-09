#!/usr/bin/env python3
"""
load_uwg_newsletter.py – Lädt § 7 UWG (+ granulare Chunks) und den
Newsletter-Methodenwissen-Chunk in ChromaDB.

Verwendung:
    python3 ~/openlex-mvp/load_uwg_newsletter.py
"""

from __future__ import annotations

import glob
import json
import os

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.expanduser("~/openlex-mvp")
CHROMADB_DIR = os.path.join(BASE_DIR, "chromadb")
COLLECTION_NAME = "openlex_datenschutz"
MODEL_NAME = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"
BATCH_SIZE = 50


def main():
    print("=== UWG § 7 + Newsletter-MW in ChromaDB laden ===\n")

    # ChromaDB + Modell
    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    col = client.get_or_create_collection(COLLECTION_NAME)
    model = SentenceTransformer(MODEL_NAME)

    existing_ids = set(col.get(include=[])["ids"])
    print(f"ChromaDB: {len(existing_ids)} bestehende Chunks")

    to_add = []  # (id, text, metadata)

    # 1) § 7 UWG aus data/gesetze/
    gesetze_file = os.path.join(BASE_DIR, "data", "gesetze", "UWG_§_7.json")
    if os.path.exists(gesetze_file):
        with open(gesetze_file, "r", encoding="utf-8") as f:
            doc = json.load(f)
        chunk_id = "UWG_§_7"
        text = doc.get("volltext", "")
        meta = {
            "source_type": "gesetz",
            "chunk_id": chunk_id,
            "gesetz": "UWG",
            "paragraph": "§ 7",
            "ueberschrift": doc.get("ueberschrift", ""),
            "verweise": ", ".join(doc.get("verweise", [])),
        }
        if chunk_id not in existing_ids:
            to_add.append((chunk_id, text, meta))
            print(f"  + {chunk_id}")
        else:
            print(f"  ~ {chunk_id} (existiert bereits)")

    # 2) Granulare § 7 UWG Chunks
    granular_pattern = os.path.join(BASE_DIR, "data", "gesetze_granular", "UWG_§_7_*.json")
    for fp in sorted(glob.glob(granular_pattern)):
        with open(fp, "r", encoding="utf-8") as f:
            doc = json.load(f)
        chunk_id = doc.get("chunk_id", os.path.basename(fp).replace(".json", ""))
        text = doc.get("text", "")
        if not text:
            continue
        meta = {
            "source_type": "gesetz_granular",
            "chunk_id": chunk_id,
            "gesetz": "UWG",
            "volladresse": doc.get("volladresse", ""),
            "verweise": ", ".join(doc.get("verweise", [])) if isinstance(doc.get("verweise"), list) else "",
        }
        if chunk_id not in existing_ids:
            to_add.append((chunk_id, text, meta))
            print(f"  + {chunk_id}")
        else:
            print(f"  ~ {chunk_id} (existiert bereits)")

    # 3) Newsletter-Methodenwissen-Chunk
    mw_file = os.path.join(BASE_DIR, "data", "methodenwissen", "Newsletter_Einwilligung_Dreistufig.json")
    if os.path.exists(mw_file):
        with open(mw_file, "r", encoding="utf-8") as f:
            doc = json.load(f)
        chunk_id = doc.get("chunk_id", "mw_newsletter_einwilligung_dreistufig")
        text = doc.get("text", "")
        meta = {
            "source_type": "methodenwissen",
            "chunk_id": chunk_id,
            "thema": doc.get("thema", ""),
            "normbezuege": ", ".join(doc.get("normbezuege", [])),
        }
        if chunk_id not in existing_ids:
            to_add.append((chunk_id, text, meta))
            print(f"  + {chunk_id}")
        else:
            print(f"  ~ {chunk_id} (existiert bereits)")

    # 4) Embedden und einfügen
    if not to_add:
        print("\nKeine neuen Chunks zum Laden.")
        return

    print(f"\nEmbedde {len(to_add)} Chunks...")
    ids = [t[0] for t in to_add]
    texts = [t[1] for t in to_add]
    metas = [t[2] for t in to_add]

    for i in range(0, len(ids), BATCH_SIZE):
        batch_ids = ids[i:i + BATCH_SIZE]
        batch_texts = texts[i:i + BATCH_SIZE]
        batch_metas = metas[i:i + BATCH_SIZE]
        embeddings = model.encode(batch_texts).tolist()
        col.add(
            ids=batch_ids,
            documents=batch_texts,
            metadatas=batch_metas,
            embeddings=embeddings,
        )
        print(f"  Batch {i // BATCH_SIZE + 1}: {len(batch_ids)} Chunks eingefügt")

    print(f"\n✅ Fertig! {len(to_add)} neue Chunks in ChromaDB geladen.")
    print(f"   ChromaDB gesamt: {col.count()} Chunks")


if __name__ == "__main__":
    main()
