"""
BM25-Index für OpenLex. Nutzt bm25s mit Snowball-Stemmer für Deutsch.
Index wird persistiert nach /opt/openlex-mvp/bm25_index/.
"""
import os
import time
import logging
from pathlib import Path
from typing import Optional

import bm25s
import Stemmer
import chromadb

logger = logging.getLogger(__name__)

_STEMMER = Stemmer.Stemmer("german")
_DEFAULT_INDEX_PATH = os.getenv(
    "OPENLEX_BM25_INDEX_PATH",
    "/opt/openlex-mvp/bm25_index"
)

# Globaler Lazy-Cache für den geladenen Index
_retriever_cache: Optional["bm25s.BM25"] = None
_id_cache: Optional[list] = None


def _tokenize(texts: list) -> list:
    """Deutscher Tokenizer mit Stemmer und Stopwords."""
    return bm25s.tokenize(
        texts,
        stopwords="de",
        stemmer=_STEMMER,
        show_progress=False,
    )


def build_index(
    chromadb_path: str = "/opt/openlex-mvp/chromadb",
    collection_name: str = "openlex_datenschutz",
    index_path: str = _DEFAULT_INDEX_PATH,
) -> dict:
    """
    Liest alle Chunks aus ChromaDB, baut BM25-Index, persistiert.

    Returns: dict mit Build-Statistiken (n_chunks, index_size_mb, duration_s)
    """
    start = time.time()

    client = chromadb.PersistentClient(path=chromadb_path)
    collection = client.get_collection(collection_name)

    # ChromaDB: .get() mit offset für alle Chunks
    batch_size = 5000
    all_ids = []
    all_docs = []
    offset = 0

    while True:
        result = collection.get(
            limit=batch_size,
            offset=offset,
            include=["documents"],
        )
        batch_ids = result.get("ids", [])
        batch_docs = result.get("documents", [])
        if not batch_ids:
            break
        all_ids.extend(batch_ids)
        all_docs.extend(batch_docs)
        if len(batch_ids) < batch_size:
            break
        offset += batch_size

    if not all_ids:
        raise RuntimeError(f"Collection {collection_name} ist leer oder fehlt")

    logger.info(f"Loaded {len(all_ids)} chunks from ChromaDB")
    print(f"  Geladene Chunks: {len(all_ids)}")

    # Tokenize
    print("  Tokenisiere...")
    tokenized = _tokenize(all_docs)

    # Build index
    print("  Baue BM25-Index...")
    retriever = bm25s.BM25(corpus=all_ids)
    retriever.index(tokenized, show_progress=False)

    # Persist
    Path(index_path).mkdir(parents=True, exist_ok=True)
    retriever.save(index_path)
    print(f"  Index gespeichert: {index_path}")

    # Stats
    duration = time.time() - start
    index_size_bytes = sum(
        f.stat().st_size for f in Path(index_path).rglob("*") if f.is_file()
    )
    index_size_mb = index_size_bytes / (1024 * 1024)

    stats = {
        "n_chunks": len(all_ids),
        "index_size_mb": round(index_size_mb, 2),
        "duration_s": round(duration, 1),
        "index_path": str(index_path),
    }
    logger.info(f"BM25 index built: {stats}")
    return stats


def load_index(index_path: str = _DEFAULT_INDEX_PATH) -> tuple:
    """
    Lädt persistierten Index (Lazy-Singleton).

    Returns: (retriever, id_list)
    """
    global _retriever_cache, _id_cache

    if _retriever_cache is not None and _id_cache is not None:
        return _retriever_cache, _id_cache

    if not Path(index_path).exists():
        raise FileNotFoundError(
            f"BM25 index not found at {index_path}. "
            f"Run scripts/build_bm25_index.py first."
        )

    retriever = bm25s.BM25.load(index_path, load_corpus=True)
    # corpus ist die Liste der chunk_ids
    ids = retriever.corpus

    _retriever_cache = retriever
    _id_cache = list(ids)
    return retriever, _id_cache


def retrieve(query: str, k: int = 40) -> list:
    """
    Führt BM25-Retrieval aus.

    Args:
        query: Natürlichsprachige Query
        k: Top-K Chunks

    Returns:
        Liste von {"id": chunk_id, "bm25_score": float, "rank": int (1-basiert)}
    """
    retriever, ids = load_index()

    query_tokens = _tokenize([query])

    results, scores = retriever.retrieve(query_tokens, k=k, show_progress=False)

    # results[0] = Array von k corpus-entries (strings)
    # scores[0] = Array von k float scores
    output = []
    for rank, (chunk_id, score) in enumerate(zip(results[0], scores[0]), start=1):
        output.append({
            "id": str(chunk_id),
            "bm25_score": float(score),
            "rank": rank,
        })
    return output


def invalidate_cache():
    """Für Tests: Cache leeren."""
    global _retriever_cache, _id_cache
    _retriever_cache = None
    _id_cache = None
