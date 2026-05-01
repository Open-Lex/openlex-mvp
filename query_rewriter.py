"""
LLM-basiertes Query-Rewriting: Alltagssprache → juristische Fachsprache.
Nutzt Mistral Medium mit persistentem SQLite-Cache.
"""
import os
import re as _re
import sqlite3
import hashlib
import time
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# === Konfiguration ===
_CACHE_PATH = os.getenv(
    "OPENLEX_REWRITE_CACHE_PATH",
    "/opt/openlex-mvp/cache/rewrite_cache.sqlite",
)
_MODEL = os.getenv("OPENLEX_REWRITE_MODEL", "mistral-medium-latest")
_TIMEOUT_MS = int(float(os.getenv("OPENLEX_REWRITE_TIMEOUT_S", "10")) * 1000)
_MISTRAL_KEY = os.getenv("MISTRAL_KEY")  # Bestehendes Env-Var aus app.py


# === System-Prompt für den Rewriter ===
_SYSTEM_PROMPT = """Du bist ein juristischer Assistent für deutsches Datenschutzrecht. Deine Aufgabe:
Wandle eine laienhaft formulierte Nutzerfrage in eine kurze, sachlich-präzise juristische Suchanfrage um, damit sie passende DSGVO-, BDSG- oder Rechtsprechungs-Chunks trifft.

Regeln:
1. Ersetze Alltagsbegriffe durch juristische Fachterminologie.
   Beispiele: "Chef liest Mails" → "Beschäftigtendatenschutz E-Mail-Kontrolle Arbeitgeber"
   "darf Firma Daten weitergeben" → "Datenübermittlung an Dritte Rechtsgrundlage Einwilligung"
   "Kamera im Büro" → "Videoüberwachung Arbeitsplatz Beschäftigte"
2. Erhalte den juristischen Kern. Keine neuen Fakten dazudichten. Keine Rechtsberatung.
3. Ausgabe nur die umgeschriebene Query, KEINE Erklärung, KEINE Begrüßung, KEIN Präambel.
4. Maximal 20 Wörter.
5. Wenn die Frage bereits juristisch präzise ist (z.B. "Art. 82 DSGVO Schadensersatz"), gib sie unverändert zurück.
6. Bei unklaren oder themenfremden Queries: gib die Original-Query unverändert zurück.
7. Eigennamen (Kläger, Beklagte, Urteilsnamen wie "Rottler", "Schrems", "Breyer") EXAKT aus der Nutzerfrage übernehmen — niemals verändern, korrigieren oder ersetzen.
8. Gerichtsbezeichnungen (EuGH, EuG, BGH, BAG, BSG, BVerwG, BFH) aus der Nutzerfrage unverändert übernehmen. Niemals eine Gerichtsbezeichnung hinzufügen, die nicht in der Frage stand.

Eingabe-Format: Nutzerfrage auf Deutsch.
Ausgabe-Format: Nur die umgeschriebene Query, eine Zeile, keine Anführungszeichen."""


@dataclass
class RewriteResult:
    original: str
    rewritten: str
    from_cache: bool
    duration_ms: float
    error: Optional[str] = None


# === Cache-Schicht ===
def _init_cache():
    Path(_CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_CACHE_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rewrites (
            query_hash TEXT PRIMARY KEY,
            original TEXT NOT NULL,
            rewritten TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_created ON rewrites(created_at)
    """)
    conn.commit()
    return conn


def _query_hash(query: str, model: str) -> str:
    """Hash über normalisierte Query + Model für Cache-Key."""
    normalized = query.strip().lower()
    return hashlib.sha256(f"{model}::{normalized}".encode()).hexdigest()


def _cache_get(query: str, model: str) -> Optional[str]:
    h = _query_hash(query, model)
    conn = _init_cache()
    try:
        row = conn.execute(
            "SELECT rewritten FROM rewrites WHERE query_hash = ?", (h,)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _cache_put(query: str, rewritten: str, model: str):
    h = _query_hash(query, model)
    conn = _init_cache()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO rewrites "
            "(query_hash, original, rewritten, model, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (h, query, rewritten, model, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


# === Compiled patterns für Guards (einmal kompilieren) ===
# Guard A: EuGH/EuG-Aktenzeichen z.B. C-526/24, T-123/21
_AZ_PAT = _re.compile(r'\b[CT][-‑‐–—]\d+/\d+\b', _re.UNICODE)

# Guard B: Gerichtsbezeichnungen
_COURT_PAT = _re.compile(
    r'\b(EuGH|EuG|BGH|BAG|BSG|BVerwG|BFH|OLG|LG|VG|AG)\b', _re.IGNORECASE
)

# Guard C: Eigennamen direkt neben "Urteil/Entscheidung/Fall/Klage/Rechtssache"
# Matcht z.B. "Rottler Urteil", "Urteil Rottler", "brillen rottler urteil" (case-insensitive)
_URTEIL_NEIGHBOR = _re.compile(
    r'\b([A-ZÄÖÜa-zäöüß][a-zäöüß]{2,})\s+(?:Urteil|Entscheidung|Fall|Klage|Rechtssache)\b'
    r'|(?:Urteil|Entscheidung|Fall|Klage|Rechtssache)\s+([A-ZÄÖÜa-zäöüß][a-zäöüß]{2,})\b',
    _re.UNICODE | _re.IGNORECASE
)

# Wörter, die trotz Großschreibung kein Eigenname sind (juristische Schlüsselwörter)
_NOT_PROPER_NOUNS = frozenset({
    "das", "die", "der", "ein", "eine", "ist", "hat", "muss", "darf",
    "dsgvo", "bdsg", "tdddg", "recht", "gesetz", "urteil", "entscheidung",
    "fall", "klage", "rechtssache", "datenschutz", "gericht", "instanz",
    "artikel", "absatz", "paragraph", "satz",
})


# === Sanity-Checks am LLM-Output ===
def _is_valid_rewrite(original: str, candidate: str) -> bool:
    """Halluzinations-Kontrolle: Format + Proper-Noun-Erhaltung."""
    if not candidate or not candidate.strip():
        return False
    c = candidate.strip()

    # Extrem lang → Halluzination wahrscheinlich
    if len(c.split()) > 30:
        return False

    # LLM liefert Erklärung statt Rewrite zurück
    lower = c.lower()
    bad_prefixes = (
        "hier ist", "die umgeschriebene", "ich würde", "als juristischer",
        "the rewritten", "here is", "sorry", "leider",
    )
    if any(lower.startswith(p) for p in bad_prefixes):
        return False

    # Enthält mehrere Newlines → LLM hat Erklärung dazugehängt
    if c.count("\n") > 1:
        return False

    # ── Guard A: Aktenzeichen (C-526/24 etc.) müssen erhalten bleiben ──
    orig_az = {m.lower() for m in _AZ_PAT.findall(original)}
    if orig_az:
        cand_az = {m.lower() for m in _AZ_PAT.findall(c)}
        if not orig_az.issubset(cand_az):
            logger.warning(
                f"Rewrite dropped/changed Aktenzeichen: {orig_az} not in '{c[:60]}'"
            )
            return False

    # ── Guard B: Wenn Original ein Gericht nennt, muss es im Rewrite erhalten bleiben ──
    # (EuGH→BGH oder EuGH weggelassen = Fallback)
    # Wenn Original kein Gericht nennt, darf der Rewrite eines ergänzen (ok).
    orig_courts = {m.lower() for m in _COURT_PAT.findall(original)}
    if orig_courts:
        cand_courts = {m.lower() for m in _COURT_PAT.findall(c)}
        if not orig_courts.issubset(cand_courts):
            logger.warning(
                f"Rewrite dropped/changed court: {orig_courts} not in '{c[:60]}'"
            )
            return False

    # ── Guard C: Eigennamen neben "Urteil/Fall/…" müssen erhalten bleiben ──
    # Extrahiert Wörter direkt neben Urteil-Schlüsselwörtern im Original,
    # die nicht zu juristischen Schlüsselwörtern gehören.
    orig_names: set[str] = set()
    for m in _URTEIL_NEIGHBOR.finditer(original):
        for grp in [m.group(1), m.group(2)]:
            if grp and grp.lower() not in _NOT_PROPER_NOUNS:
                orig_names.add(grp.lower())
    if orig_names:
        cand_lower = c.lower()
        missing = [name for name in orig_names if name not in cand_lower]
        if missing:
            logger.warning(
                f"Rewrite changed proper noun(s) {missing}: '{original[:60]}' → '{c[:60]}'"
            )
            return False

    return True


# === Mistral-Aufruf (mistralai v2) ===
def _call_mistral(query: str) -> str:
    from mistralai.client import Mistral

    key = _MISTRAL_KEY or os.getenv("MISTRAL_KEY")
    if not key:
        raise RuntimeError("MISTRAL_KEY not set in environment")

    client = Mistral(api_key=key, timeout_ms=_TIMEOUT_MS)

    response = client.chat.complete(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        temperature=0.0,
        max_tokens=80,
    )

    content = response.choices[0].message.content
    return (content or "").strip()


# === Public API ===
def rewrite(query: str, use_cache: bool = True) -> RewriteResult:
    """
    Schreibt Query auf Legalese um. Fallback auf Original bei Fehler.

    Args:
        query: Original-User-Query
        use_cache: Cache nutzen? Default true.

    Returns:
        RewriteResult mit rewritten (= original bei Fehler) und Meta.
    """
    start = time.time()

    # Cache-Check
    if use_cache:
        cached = _cache_get(query, _MODEL)
        if cached is not None:
            return RewriteResult(
                original=query,
                rewritten=cached,
                from_cache=True,
                duration_ms=(time.time() - start) * 1000,
            )

    # Mistral-Call
    try:
        raw = _call_mistral(query)
    except Exception as e:
        logger.warning(f"Mistral rewrite failed for query: {query[:50]}... — {e}")
        return RewriteResult(
            original=query,
            rewritten=query,  # Fallback
            from_cache=False,
            duration_ms=(time.time() - start) * 1000,
            error=str(e),
        )

    # Sanity-Check (inkl. Proper-Noun-Guards)
    if not _is_valid_rewrite(query, raw):
        logger.warning(
            f"Invalid rewrite, falling back. Original: {query[:50]}... "
            f"Candidate: {raw[:80]}..."
        )
        return RewriteResult(
            original=query,
            rewritten=query,
            from_cache=False,
            duration_ms=(time.time() - start) * 1000,
            error="invalid_rewrite",
        )

    # Cache speichern
    if use_cache:
        _cache_put(query, raw, _MODEL)

    return RewriteResult(
        original=query,
        rewritten=raw,
        from_cache=False,
        duration_ms=(time.time() - start) * 1000,
    )


def cache_stats() -> dict:
    """Liefert Cache-Statistik."""
    conn = _init_cache()
    try:
        total = conn.execute("SELECT COUNT(*) FROM rewrites").fetchone()[0]
        oldest = conn.execute(
            "SELECT MIN(created_at) FROM rewrites"
        ).fetchone()[0]
        newest = conn.execute(
            "SELECT MAX(created_at) FROM rewrites"
        ).fetchone()[0]
        return {
            "total_entries": total,
            "oldest_ts": oldest,
            "newest_ts": newest,
            "path": _CACHE_PATH,
        }
    finally:
        conn.close()
