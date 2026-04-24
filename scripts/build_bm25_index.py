#!/usr/bin/env python3
"""Baut den BM25-Index idempotent. Rebuild nur wenn ChromaDB jünger."""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, "/opt/openlex-mvp")

from bm25_index import build_index

CHROMADB_PATH = "/opt/openlex-mvp/chromadb"
INDEX_PATH = os.getenv("OPENLEX_BM25_INDEX_PATH", "/opt/openlex-mvp/bm25_index")


def should_rebuild() -> bool:
    index_dir = Path(INDEX_PATH)
    if not index_dir.exists():
        return True

    chroma_dir = Path(CHROMADB_PATH)
    if not chroma_dir.exists():
        print(f"ERROR: ChromaDB nicht gefunden: {CHROMADB_PATH}", file=sys.stderr)
        sys.exit(1)

    def latest_mtime(path: Path) -> float:
        return max(
            (f.stat().st_mtime for f in path.rglob("*") if f.is_file()),
            default=0.0,
        )

    index_mtime = latest_mtime(index_dir)
    chroma_mtime = latest_mtime(chroma_dir)

    if index_mtime > chroma_mtime:
        print(f"BM25 index is newer than ChromaDB, skipping rebuild.")
        print(f"  Index mtime:  {index_mtime:.0f}")
        print(f"  Chroma mtime: {chroma_mtime:.0f}")
        return False
    return True


def main():
    if not should_rebuild():
        print("No rebuild needed.")
        return 0

    print(f"Building BM25 index from {CHROMADB_PATH} -> {INDEX_PATH}")
    stats = build_index(
        chromadb_path=CHROMADB_PATH,
        collection_name="openlex_datenschutz",
        index_path=INDEX_PATH,
    )
    print(f"Done: {json.dumps(stats, indent=2)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
