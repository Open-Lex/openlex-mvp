"""
telemetry.py – Best-effort JSONL-Telemetrie für OpenLex.
Logt nur Hashes (kein Klartext), Intent, Retrieval-Metriken, Validator-Status.
"""
import os
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)

_LOG_PATH = os.getenv(
    "OPENLEX_TELEMETRY_PATH",
    "/opt/openlex-mvp/logs/telemetry.jsonl",
)
_ENABLED = None  # lazily resolved


def _is_enabled() -> bool:
    global _ENABLED
    if _ENABLED is None:
        _ENABLED = os.getenv("OPENLEX_TELEMETRY_ENABLED", "false").lower() == "true"
    return _ENABLED


def _query_hash(query: str) -> str:
    """SHA-256[:16] — nicht umkehrbar, kein PII."""
    return hashlib.sha256(query.strip().encode()).hexdigest()[:16]


def log_query(
    query: str,
    *,
    intent: Optional[dict] = None,
    rewrite: Optional[dict] = None,
    retrieval: Optional[dict] = None,
    validator: Optional[dict] = None,
    duration_ms: float = 0.0,
    model: str = "",
    error: Optional[str] = None,
) -> None:
    """
    Schreibt einen JSONL-Eintrag. Alle Felder optional; bricht bei Fehler still ab.

    Erwartete Strukturen (alle optional):
      intent:     {"type": str, "completeness": float, "clarification": bool, "from_cache": bool}
      rewrite:    {"used": bool, "query_hash": str}
      retrieval:  {"chunks_returned": int, "top_score": float, "source_types": list[str]}
      validator:  {"unknown_norms": int, "ungrounded_norms": int, "warning_shown": bool}
    """
    if not _is_enabled():
        return

    try:
        event: dict[str, Any] = {
            "ts": time.time(),
            "query_hash": _query_hash(query),
            "duration_ms": round(duration_ms, 1),
            "model": model,
        }
        if intent is not None:
            event["intent"] = intent
        if rewrite is not None:
            event["rewrite"] = rewrite
        if retrieval is not None:
            event["retrieval"] = retrieval
        if validator is not None:
            event["validator"] = validator
        if error:
            event["error"] = str(error)[:200]

        log_path = Path(_LOG_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    except Exception as exc:
        logger.debug(f"Telemetry write failed (non-fatal): {exc}")
