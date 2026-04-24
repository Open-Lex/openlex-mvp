#!/usr/bin/env python3
"""
Läuft für jede Query das aktuelle Retrieval, speichert Top-10-Kandidaten.
"""
import os
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, "/opt/openlex-mvp")
os.environ["OPENLEX_REWRITE_ENABLED"] = "true"
os.environ["OPENLEX_INTENT_ANALYSIS_ENABLED"] = "false"
os.environ["OPENLEX_TRACE_MODE"] = "false"
os.environ["OPENLEX_BM25_ENABLED"] = "false"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

INPUT = Path("/opt/openlex-mvp/eval_sets/v4/queries_raw.json")
OUTPUT = Path("/opt/openlex-mvp/eval_sets/v4/queries_with_candidates.json")

FORBIDDEN_PATTERNS = [
    "§ 28 BDSG-alt", "§ 29 BDSG-alt", "§ 32 BDSG-alt", "§ 34 BDSG-alt",
    "§ 35 BDSG-alt", "BDSG 2003", "TMG § 13", "TMG § 15", "TTDSG",
]


def find_forbidden_candidates(col) -> list:
    """Chunks mit veralteten Normen — einmalig laden."""
    candidates = []
    for pat in FORBIDDEN_PATTERNS:
        try:
            r = col.get(where_document={"$contains": pat}, limit=3, include=["metadatas"])
            for cid in r.get("ids", []):
                if cid not in candidates:
                    candidates.append(cid)
        except Exception:
            pass
    return candidates[:10]


def main():
    import importlib
    import app as _app
    importlib.reload(_app)
    from app import retrieve

    import chromadb
    col = chromadb.PersistentClient("/opt/openlex-mvp/chromadb").get_collection("openlex_datenschutz")

    with open(INPUT) as f:
        queries = json.load(f)

    # Forbidden-Kandidaten einmalig laden
    forbidden_global = find_forbidden_candidates(col)
    logger.info(f"Forbidden-Kandidaten (global): {len(forbidden_global)}")

    for i, q in enumerate(queries, 1):
        # Templates ohne echten Query-Text überspringen
        if q["query"].startswith("[TO BE FILLED"):
            q["retrieval_candidates"] = []
            q["forbidden_candidates"] = forbidden_global[:5]
            continue

        logger.info(f"[{i}/{len(queries)}] {q['query_id']}: {q['query'][:60]}")

        try:
            results = retrieve(q["query"])
            if isinstance(results, dict) and results.get("type") == "clarification_needed":
                q["retrieval_candidates"] = []
                q["forbidden_candidates"] = forbidden_global[:5]
                q["notes"] = (q.get("notes", "") + " [clarification triggered]").strip()
                continue

            candidates = []
            for r in (results or [])[:10]:
                meta = r.get("meta") or r.get("metadata") or {}
                doc = r.get("document") or r.get("text") or r.get("doc") or ""
                cid = r.get("id") or meta.get("chunk_id", "")
                candidates.append({
                    "chunk_id": cid,
                    "score": float(r.get("ce_score") or r.get("score") or 0.0),
                    "source_type": meta.get("source_type", ""),
                    "gesetz": meta.get("gesetz", ""),
                    "snippet": str(doc)[:300],
                    "volladresse": meta.get("volladresse", ""),
                })
            q["retrieval_candidates"] = candidates
            q["forbidden_candidates"] = forbidden_global[:5]

        except Exception as e:
            logger.error(f"Failed: {e}")
            q["retrieval_candidates"] = []
            q["forbidden_candidates"] = forbidden_global[:5]
            q["notes"] = (q.get("notes", "") + f" [preselect error: {str(e)[:80]}]").strip()

        # Save every 20
        if i % 20 == 0:
            with open(OUTPUT, "w") as f:
                json.dump(queries, f, indent=2, ensure_ascii=False)
            logger.info(f"  Zwischenstand gespeichert ({i}/{len(queries)})")

    with open(OUTPUT, "w") as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)

    with_candidates = sum(1 for q in queries if q.get("retrieval_candidates"))
    logger.info(f"Fertig. {with_candidates}/{len(queries)} Queries mit Kandidaten.")


if __name__ == "__main__":
    main()
