"""
Intent-Analyzer für OpenLex-Queries.
Klassifiziert Intent-Typ, bewertet Completeness, generiert ggf. Rückfrage.
Mistral Medium mit SQLite-Cache.
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


_VALID_INTENT_TYPES = {
    "definition",
    "subsumtion",
    "handlungsanweisung",
    "rechtsprechung",
    "prozedural",
    "unbekannt",
}

_CACHE_PATH = os.getenv(
    "OPENLEX_INTENT_CACHE_PATH",
    "/opt/openlex-mvp/cache/intent_cache.sqlite",
)
_MODEL = os.getenv("OPENLEX_INTENT_MODEL", "mistral-medium-latest")
_THRESHOLD = float(os.getenv("OPENLEX_INTENT_COMPLETENESS_THRESHOLD", "0.5"))


_SYSTEM_PROMPT = """Du analysierst Nutzerfragen an ein juristisches Datenschutz-Assistenz-System (Fokus: DSGVO, BDSG, deutsche Rechtsprechung).

Gib ein JSON mit genau diesen Feldern zurück:
- "intent_type": einer von [definition, subsumtion, handlungsanweisung, rechtsprechung, prozedural, unbekannt]
- "completeness_score": float 0.0–1.0
- "clarification_question": string oder null — NUR bei completeness_score < 0.5, sonst null
- "detected_roles": Liste erkannter Rollen (z.B. ["Arbeitnehmer", "Arbeitgeber"]) oder leere Liste
- "key_aspects": 1–3 zentrale juristische Aspekte (z.B. ["Widerspruchsrecht", "Direktwerbung"]) oder leere Liste

Intent-Typ-Definitionen:
- definition: reine Begriffsfrage, "Was ist X?"
- subsumtion: "Ist X erlaubt? Unter welchen Bedingungen?" — erfordert Rechtsprüfung
- handlungsanweisung: "Wie muss/kann ich vorgehen?" — erwartet konkrete Schritte
- rechtsprechung: explizit nach Urteilen oder Rechtsprechungs-Tendenz gefragt
- prozedural: Verfahrensfrage, z.B. "Wie stelle ich einen Auskunftsantrag?"
- unbekannt: passt in keine Kategorie oder ist juristisch nicht greifbar

Completeness-Kalibrierung:
- 1.0: vollständig, alle nötigen Angaben vorhanden
- 0.7–0.9: beantwortbar mit generischen Annahmen, Details fehlen
- 0.5–0.7: substantiell beantwortbar, wichtiger Kontext offen
- 0.3–0.5: Kontext zu dünn, Antwort wäre zu generisch
- 0.0–0.3: ohne Rückfrage nicht sinnvoll beantwortbar

Clarification-Regeln:
- Maximal 30 Wörter
- EIN konkreter Aspekt pro Rückfrage, nicht mehrere
- Konkret formulieren ("Welches Bundesland?" statt "Wo?")
- Nur bei completeness_score < 0.5, sonst null

WICHTIG: Die meisten Fragen mit Kontext (Arbeitgeber, Kunde, konkrete Situation) haben completeness >= 0.7.
Rückfragen sind die Ausnahme, nicht die Regel. Frage nur bei wirklich dünnen Queries wie "Hilfe" oder "DSGVO?".

Antworte ausschließlich mit JSON, keine Erklärung, kein Markdown."""


@dataclass
class IntentAnalysis:
    intent_type: str
    completeness_score: float
    clarification_question: Optional[str]
    detected_roles: list
    key_aspects: list
    from_cache: bool = False
    duration_ms: float = 0.0
    error: Optional[str] = None
    raw_response: Optional[str] = None


# === Cache ===
def _init_cache():
    Path(_CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_CACHE_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS intents (
            query_hash TEXT PRIMARY KEY,
            original TEXT NOT NULL,
            analysis_json TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


def _hash(query: str, model: str) -> str:
    return hashlib.sha256(f"{model}::{query.strip().lower()}".encode()).hexdigest()


def _cache_get(query: str) -> Optional[dict]:
    try:
        conn = _init_cache()
        row = conn.execute(
            "SELECT analysis_json FROM intents WHERE query_hash = ?",
            (_hash(query, _MODEL),),
        ).fetchone()
        conn.close()
        return json.loads(row[0]) if row else None
    except Exception as e:
        logger.warning(f"Intent cache get error: {e}")
        return None


def _cache_put(query: str, analysis: dict):
    try:
        conn = _init_cache()
        conn.execute(
            "INSERT OR REPLACE INTO intents "
            "(query_hash, original, analysis_json, model, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (_hash(query, _MODEL), query, json.dumps(analysis), _MODEL, time.time()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Intent cache put error: {e}")


# === Default bei Fehler ===
def _default_analysis(error: str = "", raw: str = "") -> IntentAnalysis:
    return IntentAnalysis(
        intent_type="unbekannt",
        completeness_score=0.7,  # Default erlaubt Retrieval
        clarification_question=None,
        detected_roles=[],
        key_aspects=[],
        from_cache=False,
        duration_ms=0.0,
        error=error,
        raw_response=raw,
    )


# === Validierung ===
def _validate_and_normalize(raw: dict) -> Optional[dict]:
    required = {"intent_type", "completeness_score", "clarification_question",
                "detected_roles", "key_aspects"}
    if not all(k in raw for k in required):
        return None

    if raw["intent_type"] not in _VALID_INTENT_TYPES:
        raw["intent_type"] = "unbekannt"

    try:
        raw["completeness_score"] = max(0.0, min(1.0, float(raw["completeness_score"])))
    except (TypeError, ValueError):
        raw["completeness_score"] = 0.7

    cq = raw.get("clarification_question")
    if cq is not None:
        if not isinstance(cq, str) or len(cq.split()) > 40:
            raw["clarification_question"] = None
        elif raw["completeness_score"] >= 0.7:
            # LLM liefert Clarification trotz hohem Score → verwerfen
            raw["clarification_question"] = None

    if not isinstance(raw.get("detected_roles"), list):
        raw["detected_roles"] = []
    if not isinstance(raw.get("key_aspects"), list):
        raw["key_aspects"] = []
    raw["detected_roles"] = [str(x)[:100] for x in raw["detected_roles"][:5]]
    raw["key_aspects"] = [str(x)[:100] for x in raw["key_aspects"][:5]]

    return raw


# === Mistral-Call (via requests, OpenAI-kompatibel wie in app.py) ===
_MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"


def _call_mistral(query: str, max_retries: int = 4) -> str:
    import requests as _requests
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
        "max_tokens": 500,
        "response_format": {"type": "json_object"},
    }
    last_exc = None
    for attempt in range(max_retries):
        try:
            r = _requests.post(_MISTRAL_URL, headers=headers, json=payload, timeout=30)
            if r.status_code == 429:
                wait = min(2 ** attempt * 2, 30)  # 2, 4, 8, 16s
                logger.warning(f"Rate limit, retry {attempt+1}/{max_retries} in {wait}s")
                time.sleep(wait)
                last_exc = ConnectionError(f"429 Rate Limit (attempt {attempt+1})")
                continue
            r.raise_for_status()
            return (r.json()["choices"][0]["message"]["content"] or "").strip()
        except Exception as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(1)
    raise last_exc or RuntimeError("Mistral call failed")


# === Public API ===
def analyze(query: str, use_cache: bool = True) -> IntentAnalysis:
    start = time.time()

    if use_cache:
        cached = _cache_get(query)
        if cached is not None:
            allowed = {"intent_type", "completeness_score", "clarification_question",
                       "detected_roles", "key_aspects"}
            filtered = {k: v for k, v in cached.items() if k in allowed}
            return IntentAnalysis(
                **filtered,
                from_cache=True,
                duration_ms=(time.time() - start) * 1000,
            )

    try:
        raw_response = _call_mistral(query)
    except Exception as e:
        logger.warning(f"Intent LLM failed for query: {query[:50]}... — {e}")
        return _default_analysis(error=str(e))

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        return _default_analysis(raw=raw_response, error="invalid_json")

    validated = _validate_and_normalize(parsed)
    if validated is None:
        return _default_analysis(raw=raw_response, error="schema_mismatch")

    result = IntentAnalysis(
        **validated,
        from_cache=False,
        duration_ms=(time.time() - start) * 1000,
        raw_response=raw_response,
    )

    if use_cache:
        _cache_put(query, {
            "intent_type": result.intent_type,
            "completeness_score": result.completeness_score,
            "clarification_question": result.clarification_question,
            "detected_roles": result.detected_roles,
            "key_aspects": result.key_aspects,
        })

    return result


def cache_stats() -> dict:
    try:
        conn = _init_cache()
        total = conn.execute("SELECT COUNT(*) FROM intents").fetchone()[0]
        conn.close()
        return {"total_entries": total, "path": _CACHE_PATH}
    except Exception as e:
        return {"error": str(e), "path": _CACHE_PATH}
