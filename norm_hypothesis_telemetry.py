"""
Telemetrie für Norm-Hypothesizer im Shadow-Mode und Injection-Mode.
Loggt jede Hypothesen-Generierung in JSONL für spätere Auswertung.
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
    "OPENLEX_NORM_HYPOTHESIS_LOG_PATH",
    "/opt/openlex-mvp/logs/norm_hypothesis.jsonl",
)
_lock = Lock()


def log_hypothesis(
    query: str,
    hypotheses: list,
    duration_ms: float,
    from_cache: bool,
    error: Optional[str] = None,
    qu_norms: Optional[list] = None,
    injected_chunks: Optional[int] = None,      # Schritt 1.3: wie viele Chunks injiziert
    resolved_chunks: Optional[int] = None,      # Schritt 1.3: wie viele Chunks aufgelöst
    injection_strategy: Optional[str] = None,   # Schritt 1.4: additive/primary_hypothesis/fallback_qu/disabled
):
    """Schreibt einen JSONL-Eintrag für eine Hypothesen-Generierung."""
    Path(_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts": time.time(),
        "query": query[:500],  # truncate für Log-Hygiene
        "hypotheses": hypotheses,
        "n_hypotheses": len(hypotheses),
        "duration_ms": round(duration_ms, 1),
        "from_cache": from_cache,
        "error": error,
        "qu_norms": qu_norms or [],  # Aus Vergleichszweck: was QU-Regex liefert
        "injected_chunks": injected_chunks,      # None wenn Injection nicht aktiv
        "resolved_chunks": resolved_chunks,      # None wenn Injection nicht aktiv
        "injection_strategy": injection_strategy, # None wenn Injection nicht aktiv
    }

    try:
        with _lock:
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Hypothesis telemetry write failed: {e}")


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
