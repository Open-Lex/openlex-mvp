"""
Resolved eine Norm-Hypothese (z.B. 'Art. 6 DSGVO') zu konkreten ChromaDB-Chunk-IDs.

Metadaten-Struktur in openlex_datenschutz:
  DSGVO:  gesetz="DSGVO",  artikel="Art. 6"   (kein paragraph, kein absatz)
  BDSG:   gesetz="BDSG",   paragraph="26",      absatz="1"  (granular-Ebene)
  TDDDG:  gesetz="TDDDG",  kein paragraph-Feld, chunk_id="gran_TDDDG_§_25"
  AEUV/GRCh: gesetz="AEUV"/"GRCh", artikel="Art. X"

Strategie:
  1. Direkter Metadata-Match auf gesetz + artikel/paragraph
  2. Fallback für TDDDG: chunk_id-Pattern
  3. lru_cache, weil dieselben Normen häufig vorkommen
"""
import re
import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

CHROMADB_PATH = "/opt/openlex-mvp/chromadb"
COLLECTION_NAME = "openlex_datenschutz"

# Gesetz-Normalisierung: Aliase auf kanonischen Namen
_GESETZ_ALIASES = {
    "DSGVO": "DSGVO",
    "DS-GVO": "DSGVO",
    "GDPR": "DSGVO",
    "BDSG": "BDSG",
    "TDDDG": "TDDDG",
    "TTDSG": "TDDDG",   # umbenannt 2024
    "AEUV": "AEUV",
    "GRCH": "GRCh",
    "GRCh": "GRCh",
    "UWG": "UWG",
    "DDG": "DDG",
}


def parse_norm(norm_str: str) -> Optional[dict]:
    """Parst einen Norm-String zu strukturierten Komponenten.

    Beispiele:
        'Art. 6 DSGVO'           -> {type:'art', num:6, absatz:None, gesetz:'DSGVO'}
        'Art. 6 Abs. 1 DSGVO'    -> {type:'art', num:6, absatz:1,    gesetz:'DSGVO'}
        'Art. 6 Abs. 1 lit. f DSGVO' -> {type:'art', num:6, absatz:1, lit:'f', gesetz:'DSGVO'}
        '§ 26 BDSG'              -> {type:'para', num:26, absatz:None, gesetz:'BDSG'}
        '§ 26 Abs. 1 BDSG'       -> {type:'para', num:26, absatz:1,   gesetz:'BDSG'}
        '§ 25 TDDDG'             -> {type:'para', num:25, absatz:None, gesetz:'TDDDG'}
    """
    s = norm_str.strip()

    # Art. X [Abs. Y] [lit. z] [Nr. N] GESETZ
    m = re.match(
        r"Art(?:ikel)?\.?\s*(\d+)"
        r"(?:\s+Abs(?:atz)?\.?\s*(\d+))?"
        r"(?:\s+lit\.?\s*([a-z]))?"
        r"(?:\s+Nr\.?\s*(\d+))?"
        r"\s+([A-Za-z\-]+)",
        s, re.IGNORECASE,
    )
    if m:
        raw_gesetz = m.group(5).upper().replace("-", "")
        gesetz = _GESETZ_ALIASES.get(raw_gesetz) or _GESETZ_ALIASES.get(m.group(5).upper())
        if not gesetz:
            gesetz = m.group(5).upper()
        return {
            "type": "art",
            "num": int(m.group(1)),
            "absatz": int(m.group(2)) if m.group(2) else None,
            "lit": m.group(3),
            "nummer": int(m.group(4)) if m.group(4) else None,
            "gesetz": gesetz,
        }

    # § X [Abs. Y] GESETZ
    m = re.match(
        r"§\s*(\d+[a-z]?)"
        r"(?:\s+Abs(?:atz)?\.?\s*(\d+))?"
        r"\s+([A-Za-zÄÖÜ\-]+)",
        s, re.IGNORECASE,
    )
    if m:
        raw_gesetz = m.group(3).upper().replace("-", "")
        gesetz = _GESETZ_ALIASES.get(raw_gesetz) or _GESETZ_ALIASES.get(m.group(3).upper())
        if not gesetz:
            gesetz = m.group(3).upper()
        # Extract numeric part of paragraph
        para_raw = m.group(1)
        para_num = re.sub(r'[^0-9]', '', para_raw)
        return {
            "type": "para",
            "num": int(para_num) if para_num else None,
            "para_raw": para_raw,  # preserve "26a" etc.
            "absatz": int(m.group(2)) if m.group(2) else None,
            "gesetz": gesetz,
        }

    return None


# Lazy ChromaDB connection
_col = None


def _get_col():
    global _col
    if _col is None:
        import chromadb
        _col = chromadb.PersistentClient(CHROMADB_PATH).get_collection(COLLECTION_NAME)
    return _col


@lru_cache(maxsize=512)
def resolve_norm_to_chunks(norm_str: str, max_chunks: int = 3) -> tuple:
    """Findet ChromaDB-Chunk-IDs für eine Norm-Hypothese.

    Returns: tuple of chunk_ids (für lru_cache, listen sind nicht hashbar)
    """
    parsed = parse_norm(norm_str)
    if not parsed:
        logger.debug(f"Could not parse norm: {norm_str!r}")
        return ()

    col = _get_col()
    ids = []

    try:
        if parsed["type"] == "art":
            # DSGVO/AEUV/GRCh: artikel-Feld = "Art. X"
            artikel_val = f"Art. {parsed['num']}"
            where = {
                "$and": [
                    {"source_type": {"$in": ["gesetz_granular", "gesetz"]}},
                    {"gesetz": {"$eq": parsed["gesetz"]}},
                    {"artikel": {"$eq": artikel_val}},
                ]
            }
            result = col.get(
                where=where,
                limit=max_chunks * 3,
                include=["metadatas"],
            )
            ids = result.get("ids", [])

        elif parsed["type"] == "para":
            gesetz = parsed["gesetz"]

            if gesetz == "TDDDG":
                # TDDDG hat kein paragraph-Feld; chunk_id = "gran_TDDDG_§_X"
                target_id = f"gran_TDDDG_§_{parsed['para_raw']}"
                result = col.get(
                    ids=[target_id],
                    include=["metadatas"],
                )
                ids = result.get("ids", [])
                if not ids:
                    # Fallback: where_document
                    result = col.get(
                        where={"gesetz": {"$eq": "TDDDG"}},
                        limit=max_chunks * 5,
                        include=["metadatas"],
                    )
                    for cid, m in zip(result.get("ids", []), result.get("metadatas", [])):
                        if parsed["para_raw"] in cid:
                            ids.append(cid)
                            if len(ids) >= max_chunks:
                                break
            else:
                # BDSG und andere: paragraph-Feld = "26"
                where = {
                    "$and": [
                        {"source_type": {"$eq": "gesetz_granular"}},
                        {"gesetz": {"$eq": gesetz}},
                        {"paragraph": {"$eq": parsed["para_raw"]}},
                    ]
                }
                result = col.get(
                    where=where,
                    limit=max_chunks * 5,
                    include=["metadatas"],
                )
                raw_ids = result.get("ids", [])
                metas = result.get("metadatas", [])

                # Absatz-Priorisierung: wenn angegeben, passende zuerst
                target_absatz = str(parsed["absatz"]) if parsed.get("absatz") else None
                if target_absatz:
                    prio, rest = [], []
                    for cid, m in zip(raw_ids, metas):
                        if (m or {}).get("absatz") == target_absatz:
                            prio.append(cid)
                        else:
                            rest.append(cid)
                    ids = prio + rest
                else:
                    ids = raw_ids

    except Exception as e:
        logger.warning(f"ChromaDB query failed for {norm_str!r}: {e}")
        return ()

    if not ids:
        logger.debug(f"No chunks found for {norm_str!r} (parsed={parsed})")

    return tuple(ids[:max_chunks])


def resolve_hypotheses_to_chunks(
    hypotheses: list[dict],
    min_confidence: float = 0.5,
    max_chunks_per_norm: int = 2,
) -> list[dict]:
    """Resolved Liste von Hypothesen zu Chunk-Vorschlägen mit Score.

    Args:
        hypotheses: Liste mit dicts {norm, confidence, reason}
        min_confidence: Schwellwert für Injection
        max_chunks_per_norm: Wie viele Chunks pro Norm maximal

    Returns:
        Liste mit dicts {chunk_id, score, source_norm, confidence}
    """
    resolved = []
    seen_chunk_ids: set = set()

    for h in hypotheses:
        confidence = h.get("confidence", 0.0)
        if confidence < min_confidence:
            continue

        norm = h.get("norm", "")
        chunk_ids = resolve_norm_to_chunks(norm, max_chunks=max_chunks_per_norm)
        if not chunk_ids:
            logger.debug(f"No chunks resolved for hypothesis norm: {norm!r}")
            continue

        # Score-Logik gemäß Design-Entscheidung
        if confidence >= 0.8:
            score = 8.0 + confidence * 1.5   # 9.20 – 9.50
        else:
            score = 6.0 + confidence * 2.0   # 7.00 – 7.60

        for cid in chunk_ids:
            if cid in seen_chunk_ids:
                continue
            seen_chunk_ids.add(cid)
            resolved.append({
                "chunk_id": cid,
                "score": score,
                "source_norm": norm,
                "confidence": confidence,
            })

    return resolved


def cache_stats() -> dict:
    info = resolve_norm_to_chunks.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "currsize": info.currsize,
        "maxsize": info.maxsize,
    }
