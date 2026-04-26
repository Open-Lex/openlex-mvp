"""
Norm-Hypothesizer für OpenLex-Queries.

Aus User-Frage → priorisierte Liste von Norm-Hypothesen.
Output-Format: [{"norm": "Art. 6 DSGVO", "confidence": 0.9, "reason": "Rechtsgrundlage"}, ...]

Mistral Medium mit SQLite-Cache. KEINE Integration in retrieve().
"""
import os
import json
import sqlite3
import hashlib
import time
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


_CACHE_PATH = os.getenv(
    "OPENLEX_NORM_HYPOTHESIS_CACHE_PATH",
    "/opt/openlex-mvp/cache/norm_hypothesis_cache.sqlite",
)
_MODEL = os.getenv("OPENLEX_NORM_HYPOTHESIS_MODEL", "mistral-medium-latest")


_SYSTEM_PROMPT = """Du bist ein juristischer Norm-Analyst für deutsches Datenschutzrecht.

Aufgabe: Aus einer User-Frage eine priorisierte Liste der wahrscheinlich einschlägigen Normen ableiten.

Regeln:
1. Maximal 5 Normen, nach Relevanz absteigend
2. Norm-Format: "Art. X DSGVO", "§ Y BDSG", "§ Z TDDDG", "Art. W AEUV" etc.
3. Confidence 0.0-1.0: 1.0 = ganz sicher einschlägig, 0.5 = möglicherweise relevant
4. Reason: 1-3 Wörter — was regelt diese Norm hier?
5. Bevorzuge Spezialregelungen vor Generalklauseln (Art. 9 vor Art. 6 bei besonderen Kategorien)
6. Bei Fragen zur Rechtsprechung: zusätzlich relevante Normen, KEINE Aktenzeichen
7. Bei unklaren Fragen: weniger Hypothesen mit niedriger Confidence

Beispiele:

Query: "Darf mein Arbeitgeber meine E-Mails lesen?"
Output:
[
  {"norm": "§ 26 BDSG", "confidence": 0.95, "reason": "Beschäftigtendatenschutz"},
  {"norm": "Art. 6 DSGVO", "confidence": 0.85, "reason": "Rechtsgrundlage"},
  {"norm": "Art. 88 DSGVO", "confidence": 0.7, "reason": "Öffnungsklausel"}
]

Query: "Was ist eine Auftragsverarbeitung?"
Output:
[
  {"norm": "Art. 4 DSGVO", "confidence": 0.95, "reason": "Definition Nr. 8"},
  {"norm": "Art. 28 DSGVO", "confidence": 0.95, "reason": "AVV-Pflichten"}
]

Query: "Kann ich Schadensersatz nach SCHUFA-Urteil verlangen?"
Output:
[
  {"norm": "Art. 82 DSGVO", "confidence": 0.95, "reason": "Schadensersatzanspruch"},
  {"norm": "Art. 22 DSGVO", "confidence": 0.85, "reason": "Automatisierte Entscheidung"},
  {"norm": "Art. 15 DSGVO", "confidence": 0.6, "reason": "Auskunftsanspruch"}
]

Antworte ausschließlich mit JSON-Array, kein Markdown, keine Erklärung."""


@dataclass
class NormHypothesis:
    norm: str
    confidence: float
    reason: str


@dataclass
class HypothesisResult:
    query: str
    hypotheses: list
    from_cache: bool = False
    duration_ms: float = 0.0
    error: Optional[str] = None
    raw_response: Optional[str] = None


# === Cache ===
def _init_cache():
    Path(_CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_CACHE_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hypotheses (
            query_hash TEXT PRIMARY KEY,
            original TEXT NOT NULL,
            hypotheses_json TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


def _hash(query: str, model: str) -> str:
    return hashlib.sha256(f"{model}::{query.strip().lower()}".encode()).hexdigest()


def _cache_get(query: str) -> Optional[list]:
    conn = _init_cache()
    try:
        row = conn.execute(
            "SELECT hypotheses_json FROM hypotheses WHERE query_hash = ?",
            (_hash(query, _MODEL),),
        ).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        conn.close()


def _cache_put(query: str, hypotheses: list):
    conn = _init_cache()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO hypotheses "
            "(query_hash, original, hypotheses_json, model, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (_hash(query, _MODEL), query, json.dumps(hypotheses), _MODEL, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


# === Validierung ===
def _validate_hypothesis(item: dict) -> Optional[dict]:
    """Validiert ein einzelnes Hypothesen-Item."""
    if not isinstance(item, dict):
        return None
    norm = item.get("norm")
    confidence = item.get("confidence")
    reason = item.get("reason", "")

    if not isinstance(norm, str) or len(norm) > 50:
        return None
    if not isinstance(confidence, (int, float)):
        return None

    confidence = max(0.0, min(1.0, float(confidence)))
    reason = str(reason)[:100] if reason else ""

    # Norm-Format: muss mit Art./§ beginnen
    norm_lower = norm.lower().strip()
    if not (norm_lower.startswith("art") or norm_lower.startswith("§")
            or norm_lower.startswith("paragraph")):
        return None

    return {"norm": norm.strip(), "confidence": confidence, "reason": reason}


def _parse_response(raw: str) -> Optional[list]:
    """Parst LLM-Output zu validierter Hypothesen-Liste."""
    if not raw:
        return None

    # Markdown-Fences entfernen falls LLM trotzdem welche setzt
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(ln for ln in lines if not ln.startswith("```"))

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, list):
        return None

    validated = []
    for item in parsed[:5]:  # max 5
        v = _validate_hypothesis(item)
        if v:
            validated.append(v)

    return validated if validated else None


# === Mistral-Call ===
def _call_mistral(query: str) -> str:
    import requests

    api_key = os.getenv("MISTRAL_KEY") or os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_KEY not set")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        "temperature": 0.0,
        "max_tokens": 600,
    }

    backoff = 1.0
    for attempt in range(5):
        try:
            r = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                json=payload, headers=headers, timeout=15,
            )
            if r.status_code == 429:
                time.sleep(backoff)
                backoff *= 2
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt == 4:
                raise
            logger.warning(f"Mistral error (attempt {attempt+1}): {e}")
            time.sleep(backoff)
            backoff *= 2
    raise RuntimeError("Mistral call failed after retries")


# === Public API ===
def hypothesize(query: str, use_cache: bool = True) -> HypothesisResult:
    """Generiert Norm-Hypothesen für eine Query. Fallback auf leere Liste bei Fehler."""
    start = time.time()

    if use_cache:
        cached = _cache_get(query)
        if cached is not None:
            hypotheses = [NormHypothesis(**h) for h in cached]
            return HypothesisResult(
                query=query,
                hypotheses=hypotheses,
                from_cache=True,
                duration_ms=(time.time() - start) * 1000,
            )

    try:
        raw = _call_mistral(query)
    except Exception as e:
        logger.warning(f"Mistral failed for query: {query[:50]}... — {e}")
        return HypothesisResult(
            query=query, hypotheses=[],
            from_cache=False,
            duration_ms=(time.time() - start) * 1000,
            error=str(e),
        )

    parsed = _parse_response(raw)
    if not parsed:
        logger.warning(f"Invalid response for {query[:50]}: {raw[:200]}")
        return HypothesisResult(
            query=query, hypotheses=[],
            from_cache=False,
            duration_ms=(time.time() - start) * 1000,
            error="parse_failed",
            raw_response=raw,
        )

    if use_cache:
        _cache_put(query, parsed)

    return HypothesisResult(
        query=query,
        hypotheses=[NormHypothesis(**h) for h in parsed],
        from_cache=False,
        duration_ms=(time.time() - start) * 1000,
        raw_response=raw,
    )


def cache_stats() -> dict:
    conn = _init_cache()
    try:
        total = conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0]
        return {"total_entries": total, "path": _CACHE_PATH}
    finally:
        conn.close()
