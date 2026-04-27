"""
Telemetrie für Per-Source-Retrieval im Shadow-Mode.
Loggt pro Query: Single-Call-Result vs. Per-Source-Result, Performance, Differenzen.
"""
import os
import json
import time
import logging
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

_LOG_PATH = os.getenv(
    "OPENLEX_PER_SOURCE_TELEMETRY_PATH",
    "/opt/openlex-mvp/logs/per_source_retrieval.jsonl",
)
_lock = Lock()


def log_per_source(
    query: str,
    single_call_top10: list,
    per_source_top_per_type: dict,
    per_source_after_budget: list,
    single_call_duration_ms: float,
    per_source_duration_ms: float,
    overlap_top10: list,
    error: Optional[str] = None,
):
    """Schreibt JSONL-Eintrag für eine Per-Source-Vergleichs-Aufzeichnung."""
    Path(_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts": time.time(),
        "query": query[:500],
        "single_call_top10": single_call_top10[:10],
        "per_source_top_per_type": {
            st: ids[:5] for st, ids in per_source_top_per_type.items()
        },
        "per_source_after_budget": per_source_after_budget[:10],
        "single_call_duration_ms": round(single_call_duration_ms, 1),
        "per_source_duration_ms": round(per_source_duration_ms, 1),
        "overhead_ms": round(per_source_duration_ms - single_call_duration_ms, 1),
        "overlap_top10": overlap_top10,
        "n_overlap": len(overlap_top10),
        "error": error,
    }

    try:
        with _lock:
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Per-source telemetry write failed: {e}")


def read_recent(n: int = 50) -> list:
    """Liest die letzten n Telemetrie-Einträge."""
    path = Path(_LOG_PATH)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [json.loads(line) for line in lines[-n:] if line.strip()]
    except Exception as e:
        logger.warning(f"Telemetry read failed: {e}")
        return []
