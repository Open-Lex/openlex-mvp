#!/usr/bin/env python3
"""
merge_chromadb.py – Merged die Passauer ChromaDB-Collection in die
bestehende lokale 'openlex_datenschutz' Collection.

Verwendung:
  1. scp root@SERVER_IP:~/chromadb_passau.tar.gz ~/openlex-mvp/
  2. cd ~/openlex-mvp && tar xzf chromadb_passau.tar.gz
  3. python3 merge_chromadb.py
"""

from __future__ import annotations

import os
import time

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
LOCAL_CHROMADB = os.path.join(BASE_DIR, "chromadb")
PASSAU_CHROMADB = os.path.join(BASE_DIR, "chromadb_passau")

LOCAL_COLLECTION = "openlex_datenschutz"
PASSAU_COLLECTION = "passau_urteile"
BATCH_SIZE = 500


def main():
    print("=" * 60)
    print("OpenLex MVP – ChromaDB Merge")
    print("=" * 60)

    import chromadb

    # Passauer DB öffnen
    print(f"\n  Öffne Passauer ChromaDB: {PASSAU_CHROMADB}")
    if not os.path.isdir(PASSAU_CHROMADB):
        print(f"  FEHLER: {PASSAU_CHROMADB} nicht gefunden!")
        print("  Hast du chromadb_passau.tar.gz entpackt?")
        return

    passau_client = chromadb.PersistentClient(path=PASSAU_CHROMADB)
    try:
        passau_col = passau_client.get_collection(PASSAU_COLLECTION)
    except Exception:
        print(f"  FEHLER: Collection '{PASSAU_COLLECTION}' nicht gefunden!")
        return

    passau_count = passau_col.count()
    print(f"  Passauer Collection: {passau_count} Chunks")

    # Lokale DB öffnen
    print(f"\n  Öffne lokale ChromaDB: {LOCAL_CHROMADB}")
    local_client = chromadb.PersistentClient(path=LOCAL_CHROMADB)
    local_col = local_client.get_or_create_collection(
        name=LOCAL_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    local_before = local_col.count()
    print(f"  Lokale Collection: {local_before} Chunks")

    # Bereits vorhandene IDs
    print("\n  Ermittle vorhandene IDs für Deduplizierung ...")
    existing_ids = set()
    if local_before > 0:
        stored = local_col.get(include=[])
        existing_ids = set(stored["ids"])
    print(f"  {len(existing_ids)} vorhandene IDs.")

    # Passauer Chunks batched lesen und in lokale DB einfügen
    print(f"\n  Merge {passau_count} Passauer Chunks ...")
    t_start = time.time()

    inserted = 0
    skipped = 0

    # ChromaDB get() mit offset/limit
    for offset in range(0, passau_count, BATCH_SIZE):
        limit = min(BATCH_SIZE, passau_count - offset)

        batch = passau_col.get(
            include=["embeddings", "documents", "metadatas"],
            limit=limit,
            offset=offset,
        )

        # Filtern: nur neue IDs
        new_ids = []
        new_embeddings = []
        new_documents = []
        new_metadatas = []

        for i, chunk_id in enumerate(batch["ids"]):
            if chunk_id in existing_ids:
                skipped += 1
                continue
            new_ids.append(chunk_id)
            new_embeddings.append(batch["embeddings"][i])
            new_documents.append(batch["documents"][i])
            new_metadatas.append(batch["metadatas"][i])

        if new_ids:
            local_col.add(
                ids=new_ids,
                embeddings=new_embeddings,
                documents=new_documents,
                metadatas=new_metadatas,
            )
            inserted += len(new_ids)

        done = offset + limit
        pct = done / passau_count * 100
        if done % 5000 < BATCH_SIZE or done >= passau_count:
            print(f"    {done:>7}/{passau_count} ({pct:5.1f}%)  "
                  f"+{inserted} eingefügt, {skipped} übersprungen")

    t_elapsed = time.time() - t_start
    local_after = local_col.count()

    print(f"\n  FERTIG!")
    print(f"  Eingefügt: {inserted}")
    print(f"  Übersprungen (Duplikat): {skipped}")
    print(f"  Lokale Collection vorher: {local_before}")
    print(f"  Lokale Collection nachher: {local_after}")
    print(f"  Dauer: {t_elapsed:.0f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
