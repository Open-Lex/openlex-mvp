"""Zentrale Konfiguration des Intent-Skills.

Werte sind über eine lokale intent/.env überschreibbar (dependency-freier
Loader unten). Die .env ist gitignored und enthält die kopierten Mistral-/
Ollama-Zugangsdaten — die Live-.env wird NICHT referenziert (Isolation).
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Gültige Skill-Slugs (Single Source: skills_master.yaml). Für Validierung der
# LLM-Rechtsgebiet-Vorschläge (verhindert halluzinierte Slugs).
SKILLS = [
    "datenschutz", "kaufrecht", "mietrecht", "arbeitsrecht", "verkehrsrecht",
    "verbraucherrecht", "familienrecht", "erbrecht", "sozialrecht", "baurecht",
    "verwaltungsrecht", "nachbarrecht", "bildungsrecht", "versicherungsrecht",
    "reiserecht", "medizinrecht", "migrationsrecht", "strafrecht", "steuerrecht",
    "handelsrecht", "gesellschaftsrecht", "insolvenzrecht", "urheberrecht",
    "it_recht", "gewerblicher_rechtsschutz", "jugendrecht", "umweltrecht",
    "waffenrecht", "kartellrecht", "energierecht", "ki_recht",
    "bank_kapitalmarktrecht", "vergaberecht", "transportrecht",
    "wirtschaftsstrafrecht", "voelkerstrafrecht", "voelkerrecht", "sportrecht",
    "weltraumrecht", "sanktionsrecht", "kirchenrecht", "agrarrecht", "sachenrecht",
    "staatsorganisationsrecht", "grundrechte", "ipr", "zivilverfahrensrecht",
    "strafverfahrensrecht", "verfassungsprozessrecht", "europarecht",
    "polizei_ordnungsrecht", "kommunalrecht", "verwaltungsprozessrecht",
]


def _load_dotenv(path: Path) -> None:
    """Minimaler KEY=VALUE-Loader (kein python-dotenv-Zwang)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR / ".env")

# ── Pfade ───────────────────────────────────────────────────────────────
SCHEMA_DIR = BASE_DIR / "schema"
STATE_DIR = BASE_DIR / "state"
STATIC_DIR = BASE_DIR / "static"

# ── Server ──────────────────────────────────────────────────────────────
HOST = os.environ.get("INTENT_HOST", "127.0.0.1")
PORT = int(os.environ.get("INTENT_PORT", "7870"))

# ── Dialog-Steuerung ────────────────────────────────────────────────────
MAX_TURNS = int(os.environ.get("INTENT_MAX_TURNS", "12"))
SESSION_TTL_H = int(os.environ.get("INTENT_SESSION_TTL_H", "24"))
# Wie oft ein einzelner Slot maximal erfragt wird, bevor er übersprungen wird
# (verhindert Endlosschleifen, wenn der Nutzer nicht antworten kann/will).
MAX_SLOT_ATTEMPTS = int(os.environ.get("INTENT_MAX_SLOT_ATTEMPTS", "2"))
# Nach so vielen Turns ohne Fortschritt (kein Pflicht-Slot neu gefüllt) wird zum
# Handoff gezwungen — verhindert Endlosschleifen auch bei LLM-geführten Fragen.
MAX_NO_PROGRESS = int(os.environ.get("INTENT_MAX_NO_PROGRESS", "2"))
ENABLE_WEICHEN: bool = os.environ.get("INTENT_ENABLE_WEICHEN", "1") != "0"

# ── Confidence / Signal-Matching (kalibrierbar) ─────────────────────────
# Sättigungskonstante: signal_score = score / (score + SATURATION_K).
# Nach erster Test-Runde voraussichtlich 1.5–3.0 je nach Signal-Verteilung.
SATURATION_K = float(os.environ.get("INTENT_SATURATION_K", "2.5"))
CONFIDENCE_THRESHOLD = float(os.environ.get("INTENT_CONFIDENCE_THRESHOLD", "0.25"))
# Gewicht für Querverstrebungs-Treffer (methodisch zentraler).
QUER_WEIGHT = float(os.environ.get("INTENT_QUER_WEIGHT", "1.5"))
# Gewicht für KONTEXT-Rechtsgebiete einer Konstellation (vs. Kern). Niedrig, damit
# Kontext-Gebiete (z.B. verkehrsrecht bei Körperverletzung) nur mit eigener
# Korroboration über den Threshold kommen.
KONTEXT_WEIGHT = float(os.environ.get("INTENT_KONTEXT_WEIGHT", "0.5"))
# Max. Anzahl Rechtsgebiete im Handoff (gegen Über-Breite).
MAX_RECHTSGEBIETE = int(os.environ.get("INTENT_MAX_RECHTSGEBIETE", "5"))
# Sekundär-Rauschen-Filter: ein Sekundär-Skill wird nur behalten, wenn seine
# confidence mindestens primary × SECONDARY_MIN_RATIO erreicht, oder es eine
# starke Einzelevidenz (Signal oder LLM ≥ 0.5) gibt. Filtert 0.33-Tails.
SECONDARY_MIN_RATIO = float(os.environ.get("INTENT_SECONDARY_MIN_RATIO", "0.55"))
# Obergrenze AG-Hypothesen im Handoff + max. pro Gesetz (Kategorie-Spread).
MAX_ANSPRUCHSGRUNDLAGEN = int(os.environ.get("INTENT_MAX_AG", "6"))
AG_MAX_PER_GESETZ = int(os.environ.get("INTENT_AG_MAX_PER_GESETZ", "3"))

# ── LLM-Provider (Kaskade: Mistral primär → Ollama Fallback) ────────────
# Dev-App (alle 53 Skills) für den Orchestrator-Aufruf via Gradio-API.
DEV_APP_URL = os.environ.get("INTENT_DEV_APP_URL", "http://127.0.0.1:7864")
DEV_APP_TIMEOUT_S = int(os.environ.get("INTENT_DEV_APP_TIMEOUT_S", "120"))
# Multi-Skill bei Multi-Facetten: max. Anzahl gleichzeitig angefragter Skills
# und Mindest-Confidence, damit ein Skill automatisch aufgerufen wird.
MAX_AUTO_SKILLS = int(os.environ.get("INTENT_MAX_AUTO_SKILLS", "2"))
MULTI_SKILL_MIN_CONF = float(os.environ.get("INTENT_MULTI_SKILL_MIN_CONF", "0.4"))

# DSGVO/Privacy
# Wenn false, werden debug-Felder in HTTP-Responses unterdrückt (PII-arm).
INCLUDE_DEBUG_IN_RESPONSE = os.environ.get("INTENT_INCLUDE_DEBUG", "true").lower() == "true"
DISCLAIMER = ("Hinweis: Dies ist eine erste rechtliche Orientierung, KEINE "
              "Rechtsberatung im Sinne des RDG. Für eine verbindliche "
              "Beratung wenden Sie sich an eine Rechtsanwältin oder einen "
              "Rechtsanwalt.")

# ── Rechtssystem-Klassifikation je Skill-Slug ────────────────────────────
_STR_SKILLS: frozenset = frozenset({
    "strafrecht", "wirtschaftsstrafrecht", "voelkerstrafrecht",
    "jugendrecht", "strafverfahrensrecht", "waffenrecht",
})
_OER_SKILLS: frozenset = frozenset({
    "sozialrecht", "baurecht", "verwaltungsrecht", "migrationsrecht",
    "steuerrecht", "grundrechte", "staatsorganisationsrecht",
    "verwaltungsprozessrecht", "umweltrecht", "polizei_ordnungsrecht",
    "kommunalrecht", "vergaberecht", "energierecht",
    "verfassungsprozessrecht", "voelkerrecht",
    "bildungsrecht",
})


def rechtssystem_fuer_skill(skill: str) -> str:
    """Gibt 'StR', 'ÖR' oder 'ZR' zurück für einen Skill-Slug."""
    if skill in _STR_SKILLS:
        return "StR"
    if skill in _OER_SKILLS:
        return "ÖR"
    return "ZR"


MISTRAL_KEY = os.environ.get("MISTRAL_KEY", "")
MISTRAL_URL = os.environ.get("INTENT_MISTRAL_URL", "https://api.mistral.ai/v1/chat/completions")
MISTRAL_MODEL = os.environ.get("INTENT_MISTRAL_MODEL", "mistral-medium-latest")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODELS = [m.strip() for m in os.environ.get("INTENT_OLLAMA_MODELS", "gemma").split(",") if m.strip()]
LLM_TIMEOUT_S = int(os.environ.get("INTENT_LLM_TIMEOUT_S", "30"))
LLM_CONNECT_TIMEOUT_S = int(os.environ.get("INTENT_LLM_CONNECT_TIMEOUT_S", "5"))
LLM_MAX_ATTEMPTS = int(os.environ.get("INTENT_LLM_MAX_ATTEMPTS", "3"))
LLM_BACKOFF_BASE_S = float(os.environ.get("INTENT_LLM_BACKOFF_BASE_S", "1.0"))
