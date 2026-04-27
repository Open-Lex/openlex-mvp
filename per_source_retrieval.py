"""
Per-Source-Retrieval für OpenLex.

Statt eines einzigen ChromaDB-Calls über alle 18k Chunks: separate Calls
pro Source-Type mit konfigurierbarem Typ-Budget.

Standalone-Modul. Pipeline-Integration kommt in Schritt 2.2.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

CHROMADB_PATH = "/opt/openlex-mvp/chromadb"
COLLECTION_NAME = "openlex_datenschutz"

SOURCE_TYPES = [
    "gesetz_granular",
    "urteil_segmentiert",
    "leitlinie",
    "erwaegungsgrund",
    "methodenwissen",
]

# Default top-k pro Source-Type für per_source_query()
DEFAULT_TOP_K: dict[str, int] = {
    "gesetz_granular": 6,
    "urteil_segmentiert": 6,
    "leitlinie": 6,
    "erwaegungsgrund": 4,
    "methodenwissen": 4,
}

# Default Typ-Budget für merge_with_type_budget()
# (min, max) pro Source-Type
DEFAULT_BUDGET: dict[str, tuple[int, int]] = {
    "gesetz_granular":    (2, 4),
    "urteil_segmentiert": (0, 3),
    "leitlinie":          (0, 3),
    "erwaegungsgrund":    (0, 2),
    "methodenwissen":     (0, 2),
}


@dataclass
class SourceResult:
    """Ergebnis einer per-Source-Suche."""
    source_type: str
    chunk_ids: list
    distances: list
    metadatas: list
    documents: list
    duration_ms: float
    error: Optional[str] = None


@dataclass
class PerSourceResults:
    """Aggregierte Ergebnisse aller Source-Types."""
    query: str
    query_embedding_duration_ms: float
    per_source: dict  # source_type -> SourceResult
    total_duration_ms: float
    total_chunks: int


# Lazy collection
_col = None


def _get_col():
    global _col
    if _col is None:
        import chromadb
        _col = chromadb.PersistentClient(CHROMADB_PATH).get_collection(COLLECTION_NAME)
    return _col


def per_source_query(
    query_text: str,
    embed_fn,
    top_k_per_source: Optional[dict] = None,
    source_types: Optional[list] = None,
) -> PerSourceResults:
    """
    Führt pro Source-Type einen separaten ChromaDB-Call aus.

    Args:
        query_text:        User-Frage (oder rewritten Query)
        embed_fn:          Funktion str → embedding (numpy-array oder list)
        top_k_per_source:  dict {source_type: n}; DEFAULT_TOP_K wenn None
        source_types:      Welche Types abfragen; SOURCE_TYPES wenn None

    Returns:
        PerSourceResults mit allen Pro-Source-Ergebnissen
    """
    if top_k_per_source is None:
        top_k_per_source = DEFAULT_TOP_K
    if source_types is None:
        source_types = SOURCE_TYPES

    col = _get_col()

    # 1. Embedding einmal generieren
    t_emb = time.time()
    raw_emb = embed_fn(query_text)
    if hasattr(raw_emb, "tolist"):
        query_embedding = raw_emb.tolist()
    else:
        query_embedding = list(raw_emb)
    embedding_ms = (time.time() - t_emb) * 1000

    # 2. Pro Source-Type ChromaDB-Query
    t_total = time.time()
    per_source_results: dict = {}
    total_chunks = 0

    for source_type in source_types:
        n = top_k_per_source.get(source_type, 5)
        t_src = time.time()
        try:
            r = col.query(
                query_embeddings=[query_embedding],
                n_results=n,
                where={"source_type": source_type},
                include=["metadatas", "documents", "distances"],
            )
            ids       = (r.get("ids")       or [[]])[0]
            distances = (r.get("distances") or [[]])[0]
            metadatas = (r.get("metadatas") or [[]])[0]
            documents = (r.get("documents") or [[]])[0]

            per_source_results[source_type] = SourceResult(
                source_type=source_type,
                chunk_ids=ids,
                distances=distances,
                metadatas=[m or {} for m in metadatas],
                documents=[d or "" for d in documents],
                duration_ms=(time.time() - t_src) * 1000,
            )
            total_chunks += len(ids)
        except Exception as e:
            logger.warning(f"Per-source query failed for {source_type!r}: {e}")
            per_source_results[source_type] = SourceResult(
                source_type=source_type,
                chunk_ids=[], distances=[], metadatas=[], documents=[],
                duration_ms=(time.time() - t_src) * 1000,
                error=str(e),
            )

    return PerSourceResults(
        query=query_text,
        query_embedding_duration_ms=embedding_ms,
        per_source=per_source_results,
        total_duration_ms=(time.time() - t_total) * 1000,
        total_chunks=total_chunks,
    )


def merge_with_type_budget(
    per_source: PerSourceResults,
    budget: Optional[dict] = None,
) -> list:
    """
    Wendet Typ-Budget auf PerSourceResults an.

    Algorithmus:
      1. Alle Chunks zusammenführen, nach Distance sortieren
      2. Über sortierte Liste iterieren; jeden Chunk nehmen falls
         sein Source-Type noch unter max liegt
      (Min-Constraints werden geprüft aber nicht hart erzwungen —
       Schritt 2.2 kann das verfeinern)

    Args:
        per_source: Output von per_source_query()
        budget:     dict {source_type: (min, max)}; DEFAULT_BUDGET wenn None

    Returns:
        Liste von dicts, sortiert nach Distance, Typ-Budget angewendet
    """
    if budget is None:
        budget = DEFAULT_BUDGET

    # Alle Chunks flach
    all_chunks = []
    for source_type, src in per_source.per_source.items():
        for cid, dist, meta, doc in zip(
            src.chunk_ids, src.distances, src.metadatas, src.documents
        ):
            all_chunks.append({
                "chunk_id": cid,
                "id": cid,
                "distance": dist,
                "source_type": source_type,
                "metadata": meta,
                "meta": meta,
                "document": doc,
                "text": doc,
            })

    all_chunks.sort(key=lambda c: c["distance"])

    counts: dict = {st: 0 for st in budget}
    selected = []

    for chunk in all_chunks:
        st = chunk["source_type"]
        if st not in budget:
            selected.append(chunk)   # unbekannter Type: immer nehmen
            continue
        _, max_n = budget[st]
        if counts[st] < max_n:
            selected.append(chunk)
            counts[st] += 1

    return selected


def per_source_stats() -> dict:
    """Statistik: Chunk-Anzahl pro Source-Type im Korpus."""
    col = _get_col()
    stats = {}
    for st in SOURCE_TYPES:
        ids_set: set = set()
        offset = 0
        try:
            while True:
                page = col.get(
                    where={"source_type": st},
                    include=[],
                    limit=5000,
                    offset=offset,
                )
                page_ids = page.get("ids") or []
                if not page_ids:
                    break
                ids_set.update(page_ids)
                if len(page_ids) < 5000:
                    break
                offset += 5000
            stats[st] = len(ids_set)
        except Exception as e:
            stats[st] = f"error: {e}"
    return stats
