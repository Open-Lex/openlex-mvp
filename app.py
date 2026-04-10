#!/usr/bin/env python3
"""
app.py – OpenLex Datenschutzrecht MVP
Open-Source Rechts-KI für deutsches und europäisches Datenschutzrecht.

Gradio-Interface mit RAG-Pipeline:
  1. Retrieval (ChromaDB + Norm-Lookup)
  2. LLM-Anbindung (Ollama)
  3. Validator (Normen + Aktenzeichen verifizieren)
  4. Gradio-UI mit Quellenleiste
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import chromadb
import gradio as gr
import requests
from sentence_transformers import SentenceTransformer, CrossEncoder

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

CHROMADB_DIR = os.environ.get("CHROMADB_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromadb"))
COLLECTION_NAME = "openlex_datenschutz"
MODEL_NAME = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODELS = ["gemma4:12b", "qwen2.5:14b-instruct"]
TOP_K_RETRIEVAL = 20
TOP_K_CONTEXT = 10  # Legacy, jetzt dynamischer Cutoff
MIN_DOCS = 3
MAX_DOCS = 15
CE_CUTOFF = 3.0
DIST_CUTOFF = 0.25

# Provider-Konfiguration (Cascading Fallback)
HF_TOKEN = os.environ.get("HF_TOKEN")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")
MISTRAL_KEY = os.environ.get("MISTRAL_KEY")

# Urteilsnamen (generiert von extract_urteilsnamen.py)
_URTEILSNAMEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "urteilsnamen.json")
_urteilsnamen: dict[str, str | None] = {}


def _load_urteilsnamen():
    """Lädt die Urteilsnamen-Datei (lazy, einmalig)."""
    global _urteilsnamen
    if _urteilsnamen:
        return
    if os.path.exists(_URTEILSNAMEN_FILE):
        try:
            with open(_URTEILSNAMEN_FILE, "r", encoding="utf-8") as f:
                _urteilsnamen = json.load(f)
            print(f"  Urteilsnamen: {sum(1 for v in _urteilsnamen.values() if v)} von {len(_urteilsnamen)} geladen")
        except Exception:
            pass


def _normalize_az(az: str) -> str:
    """Normalisiert Aktenzeichen für Lookup (Unicode-Bindestriche etc.)."""
    az = az.replace("\u2011", "-").replace("\u2013", "-").replace("\u2010", "-")
    az = re.sub(r"Rechtssache\s*", "", az)
    return az.strip()


def get_urteilsname(az: str) -> str | None:
    """Gibt den Kurznamen eines Urteils zurück (oder None)."""
    _load_urteilsnamen()
    key = _normalize_az(az)
    name = _urteilsnamen.get(key)
    if name:
        return name
    # Fallback: ohne Leerzeichen-Varianten
    for k, v in _urteilsnamen.items():
        if v and _normalize_az(k) == key:
            return v
    return None

# ---------------------------------------------------------------------------
# System-Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Du bist ein juristischer Assistent der AUSSCHLIESSLICH auf Basis der bereitgestellten Quellen antwortet. Du hast KEIN eigenes Wissen über Datenschutzrecht.

STRIKTE QUELLENBINDUNG: Du darfst AUSSCHLIESSLICH Informationen verwenden, die in den bereitgestellten Quellen enthalten sind. Nenne KEINE Normen, Urteile, Aktenzeichen oder Rechtsgrundsätze, die nicht in den Quellen vorkommen. Wenn die Quellen eine Frage nicht beantworten können, sage ehrlich: Die bereitgestellten Quellen enthalten keine ausreichenden Informationen zu dieser Frage. Ergänze NIEMALS aus eigenem Wissen.

ABSOLUTE REGELN:
1. Jede Aussage muss sich auf eine der nummerierten Quellen stützen. Kennzeichne jede Aussage mit [Quelle X].
2. Wenn eine Information in KEINER Quelle steht, sage: "Diese Information ist in den vorliegenden Quellen nicht enthalten."
3. Erfinde NIEMALS Paragraphen, Aktenzeichen oder Rechtsnormen. Wenn du eine Norm zitierst, muss sie wörtlich in einer Quelle stehen.
4. Nenne KEINE Paragraphen aus deinem eigenen Wissen. Nur was in den Quellen steht.
5. Wenn die Quellen widersprüchliche Informationen enthalten, stelle beide Positionen dar und kennzeichne die jeweilige Quelle.
6. Strukturiere die Antwort so: Erst die Kernaussage, dann die Begründung mit Quellenverweisen. Falls die Quellen eine Frage wirklich nicht beantworten können, nenne dies kurz – aber nur dann.
7. Bei Folgefragen: Beziehe dich auf den bisherigen Kontext und die bereits genannten Quellen.

SACHVERHALTSAUFNAHME: Wenn die Frage zu unspezifisch ist für eine fundierte Antwort, stelle maximal 3 gezielte Rückfragen. Erkläre warum die Information nötig ist.

PRÜFUNGSREIHENFOLGE bei Zulässigkeitsfragen: Anwendbarkeit (Art. 2, 3 DSGVO) → Personenbezug → Verantwortlicher → Rechtsgrundlage → Grundsätze Art. 5 → Betroffenenrechte → Pflichten. Aber nur soweit die Quellen dies abdecken.

URTEILSZITATE: Wenn du ein Urteil zitierst und der Urteilsname in den Quellen angegeben ist, nenne ihn in Klammern nach dem Aktenzeichen, z.B. 'EuGH C-311/18 (Schrems II)'.

EDPB-QUELLEN: Wenn du EDPB-Leitlinien zitierst, verwende den offiziellen deutschen Titel und die Randnummer, z.B. 'EDPB Leitlinien 05/2020 zur Einwilligung, Rn. 13'.

DEFINITIONSREGEL: Wenn der Nutzer nach der Bedeutung eines Begriffs fragt oder ein zentraler Begriff der DSGVO in der Frage vorkommt, beginne deine Antwort IMMER mit der Legaldefinition aus Art. 4 DSGVO und nenne die konkrete Nummer. Art. 4 DSGVO enthält 26 Legaldefinitionen in vier Gruppen: Daten/Identität (Nr. 1,5,13-15), Rollen/Verarbeitung (Nr. 2-4,6-10), Einwilligung/Datenpanne (Nr. 11-12), Institutionell (Nr. 16-26). Nenne bei Definitionen immer die konkrete Nummer.

VERALTETE NORMEN: § 29 BDSG-alt (geschäftsmäßige Datenspeicherung zum Zweck der Übermittlung / Scoring) existiert NICHT mehr. Er wurde mit Inkrafttreten der DSGVO am 25.05.2018 aufgehoben. Die Nachfolgenorm für Scoring ist § 31 BDSG-neu. Der aktuelle § 29 BDSG regelt Auskunftssperren im Melderegister. Zitiere § 29 BDSG nur im Kontext von Auskunftssperren, NIEMALS im Kontext von Scoring oder Datenübermittlung.

GESETZESUMBENENNUNG: Das TTDSG wurde 2024 in TDDDG umbenannt (Telekommunikation-Digitale-Dienste-Datenschutz-Gesetz). Zitiere IMMER § 25 TDDDG, NIEMALS § 25 TTDSG. Falls in Quellen noch TTDSG steht, ersetze es in deiner Antwort durch TDDDG.

Formuliere auf Deutsch, präzise und fachlich. Verwende den Gutachtenstil wo angemessen."""

# ---------------------------------------------------------------------------
# Regex-Patterns
# ---------------------------------------------------------------------------

# Granulare Normreferenzen
NORM_RE = re.compile(
    r"Art\.?\s*\d+\s*"
    r"(?:Abs\.?\s*\d+\s*)?"
    r"(?:(?:lit\.?\s*[a-z]|Buchst\.?\s*[a-z]|Nr\.?\s*\d+)\s*)?"
    r"(?:(?:UAbs\.?\s*\d+|S(?:atz)?\.?\s*\d+)\s*)?"
    r"(?:DSGVO|DS-GVO|GDPR|GRCh|AEUV|BDSG|TDDDG|TTDSG|TKG|SGB|AO|BetrVG|KUG|GG)"
    r"|§§?\s*\d+[a-z]?\s*"
    r"(?:Abs\.?\s*\d+\s*)?"
    r"(?:(?:S(?:atz)?\.?\s*\d+|Nr\.?\s*\d+)\s*)?"
    r"(?:DSGVO|BDSG|TDDDG|TTDSG|TKG|SGB|AO|BetrVG|KUG|GG|StGB|ZPO|BGB)",
    re.UNICODE,
)

# Aktenzeichen
AZ_RE = re.compile(
    r"(?:Rechtssache\s+)?"
    r"(?:C|T)[-‑]\d+/\d+"
    r"|\d+\s+(?:AZR|BvR|BvL|ZR|ZB|StR|AR)\s+\d+/\d+"
    r"|(?:IX|VIII|VII|VI|V|IV|III|II|I)\s+(?:ZR|ZB|ZA|AR|StR)\s+\d+/\d+",
    re.UNICODE,
)

# Emoji-Mapping für Quelltypen
SOURCE_EMOJI = {
    "gesetz": "📘",
    "gesetz_granular": "📘",
    "urteil": "📗",
    "urteil_segmentiert": "📗",
    "leitlinie": "📙",
    "behoerde": "📙",
    "methodenwissen": "🟣",
    "community": "💜",
}

# Segment-Boost: Gewichtungsfaktoren
SEGMENT_BOOST = {
    "methodenwissen": 0.70,
    "leitsatz": 0.85,
    "gesetz_granular": 0.92,
    "entscheidungsgruende": 0.92,
    "wuerdigung": 0.92,
    "tenor": 0.95,
    "tatbestand": 1.05,
    "sachverhalt": 1.05,
}

# ---------------------------------------------------------------------------
# Globale Objekte (lazy init)
# ---------------------------------------------------------------------------

_model: SentenceTransformer | None = None
_collection: Any = None
_db_stats: dict[str, int] | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMADB_DIR)
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


_reranker: CrossEncoder | None = None
RERANKER_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANKER_MODEL)
    return _reranker


def get_db_stats() -> dict[str, int]:
    global _db_stats
    if _db_stats is None:
        col = get_collection()
        total = col.count()
        # Sample to estimate type distribution
        sample = col.get(include=["metadatas"], limit=total)
        counts: dict[str, int] = {}
        for meta in sample["metadatas"]:
            st = meta.get("source_type", "unbekannt")
            counts[st] = counts.get(st, 0) + 1
        # Scale up if sampled
        if len(sample["metadatas"]) < total:
            scale = total / len(sample["metadatas"])
            counts = {k: int(v * scale) for k, v in counts.items()}
        counts["GESAMT"] = total
        _db_stats = counts
    return _db_stats


# ═══════════════════════════════════════════════════════════════════════════
# TEIL 1 – Retrieval
# ═══════════════════════════════════════════════════════════════════════════


def extract_norms(text: str) -> list[str]:
    """Extrahiert granulare Normreferenzen aus Text."""
    return list(set(NORM_RE.findall(text)))


def extract_aktenzeichen(text: str) -> list[str]:
    """Extrahiert Aktenzeichen aus Text."""
    return list(set(AZ_RE.findall(text)))


# Jahr aus Metadaten extrahieren
_YEAR_RE = re.compile(r"(?:20[12]\d|199\d)")


def _extract_year(chunk: dict) -> int | None:
    """Extrahiert die Jahreszahl aus Chunk-Metadaten."""
    for field in ("datum", "titel", "chunk_id", "thema"):
        val = chunk.get("meta", {}).get(field, "")
        if val:
            m = _YEAR_RE.search(str(val))
            if m:
                return int(m.group())
    return None


def _recency_factor(year: int | None) -> float:
    """Aktualitäts-Multiplikator für CE-Scores."""
    if year is None:
        return 1.0
    if year >= 2023:
        return 0.7
    if year >= 2020:
        return 0.85
    if year >= 2018:
        return 0.95
    return 1.1


# Veraltete Normen (vor DSGVO / aufgehobene Gesetze)
_VERALTET_NORMEN = re.compile(
    r"§\s*(?:4a|4b|4c|4f|4g|6b|11|28|28a|29|33|34|35)\s+BDSG"
    r"|§\s*(?:12|13|14|15|16)\s+TMG"
    r"|§\s*(?:88|91|92|93|94|95|96|97|98|99|100)\s+TKG"
)

# DSGVO-Stichtag: 25.05.2018
_DSGVO_YEAR = 2018


def _is_outdated_chunk(chunk: dict) -> bool:
    """Prüft ob ein Chunk veraltet ist (Pre-DSGVO-Datum ODER aufgehobene Normen).

    Nur Leitlinien werden datumbasiert gefiltert. Gesetze, Methodenwissen
    und Urteile sind ausgenommen.
    """
    meta = chunk.get("meta", {})
    source_type = meta.get("source_type", "")

    # Zeitlose Quellen: nie veraltet
    if source_type in ("gesetz", "gesetz_granular", "methodenwissen"):
        return False
    # Urteile: auch alte können relevant sein (BGH etc.)
    if source_type in ("urteil", "urteil_segmentiert"):
        return False

    # 1) Datum-basierte Prüfung für Leitlinien
    if source_type == "leitlinie":
        year = _extract_year(chunk)
        if year is not None and year < _DSGVO_YEAR:
            return True

    # 2) Aufgehobene Normen im Text (alle source_types außer den obigen)
    text = chunk.get("text", "")
    if _VERALTET_NORMEN.search(text):
        return True

    return False


# Themen → Pflicht-Chunk-IDs
# Pflicht-Chunk-Suchen pro Thema: Liste von (suchtext, source_type_filter)
# source_type: None = beliebig, str = exakter Typ, list = $in-Filter
THEMEN_PFLICHT_SEARCHES: dict[str, list[tuple[str, str | None]]] = {
    "drittland": [
        ("Art. 44", "gesetz_granular"),
        ("Art. 45", "gesetz_granular"),
        ("Art. 46", "gesetz_granular"),
        ("id:seg_eugh_C-311_18_tenor", None),
        ("Drittlandtransfer nach Kapitel V DSGVO", "methodenwissen"),
        ("Data Privacy Framework", "methodenwissen"),
    ],
    "video": [
        ("Art. 88", "gesetz_granular"),
        ("§ 4 BDSG", "gesetz_granular"),
        ("Art. 6 Abs. 1 lit. f", "gesetz_granular"),
        ("Videoüberwachung", "methodenwissen"),
        ("Prüfungsschema Videoüberwachung", "methodenwissen"),
    ],
    "cookie": [
        ("Speicherung von Informationen in der Endeinrichtung", "gesetz_granular"),
        ("Cookie", "methodenwissen"),
    ],
    "einwilligung": [
        ("Art. 7", "gesetz_granular"),
        ("Speicherung von Informationen in der Endeinrichtung", "gesetz_granular"),
        ("§ 7 UWG", "gesetz_granular"),
        ("Newsletter", "methodenwissen"),
        ("Einwilligung gemäß Verordnung", "leitlinie"),
    ],
    "beschaeftigt": [
        ("Art. 88", "gesetz_granular"),
        ("§ 26 BDSG", "gesetz_granular"),
        ("C-34/21", "urteil"),
        ("E-Mail- und IT-Privatnutzung", "methodenwissen"),
    ],
    "schaden": [
        ("Art. 82", "gesetz_granular"),
        ("Schadensersatz", "methodenwissen"),
    ],
    "dsfa": [
        ("Art. 35", "gesetz_granular"),
        ("DSFA", "methodenwissen"),
        ("Blacklist", "methodenwissen"),
    ],
    "definition": [
        ("Begriffsbestimmungen (Übersicht)", "methodenwissen"),
        ("C-582/14", "urteil"),
    ],
    "informationspflicht": [
        ("Art. 13", "gesetz_granular"),
        ("Art. 14", "gesetz_granular"),
        ("Informationspflichten und Datenschutzerklärung", "methodenwissen"),
    ],
    "loeschung": [
        ("Art. 17", "gesetz_granular"),
        ("Recht auf Vergessenwerden", "methodenwissen"),
    ],
    "vergessen": [
        ("Art. 17", "gesetz_granular"),
        ("C-131/12", "leitlinie"),
        ("Google Spain", "leitlinie"),
        ("Recht auf Vergessenwerden", "methodenwissen"),
    ],
    "dsb": [
        ("Art. 37", "gesetz_granular"),
        ("§ 38 BDSG", "gesetz_granular"),
    ],
    "foto": [
        ("Art. 6 Abs. 1", "gesetz_granular"),
        ("Fotografieren und Datenschutz", "leitlinie"),
        ("Bildnisrecht", "methodenwissen"),
    ],
    "scoring": [
        ("Art. 6 Abs. 1 lit. f", "gesetz_granular"),
        ("berechtigtes Interesse", "methodenwissen"),
        ("SCHUFA", None),
        ("Profiling und automatisierte Einzelentscheidung", "methodenwissen"),
    ],
    "berechtigt": [
        ("Art. 6 Abs. 1 lit. f", "gesetz_granular"),
        ("Erwägungsgrund 47", None),
        ("C-621/22", "urteil"),
        ("Berechtigtes Interesse", "methodenwissen"),
    ],
    "gesundheit": [
        ("Art. 9", "gesetz_granular"),
    ],
    "kundenkonto": [
        ("Datenminimierung", "gesetz_granular"),
        ("Verarbeitung ist nur rechtmäßig", "gesetz_granular"),
        ("Datenminimierung", "methodenwissen"),
        ("Verhältnismäßigkeit", "methodenwissen"),
    ],
    "auftragsverarbeitung": [
        ("Art. 28", "gesetz_granular"),
        ("Art. 29", "gesetz_granular"),
        ("Auftragsverarbeitung", "methodenwissen"),
    ],
    "gemeinsam": [
        ("Art. 26", "gesetz_granular"),
        ("Art. 4 Nr. 7", "gesetz_granular"),
        ("Gemeinsame Verantwortlichkeit", "methodenwissen"),
        ("C-210/16", "urteil"),
    ],
    "ki": [
        ("KI und Datenschutz", "methodenwissen"),
        ("Art. 28", "gesetz_granular"),
        ("Art. 35", "gesetz_granular"),
        ("AI Act", "methodenwissen"),
        ("Zweckbindungsprüfung", "methodenwissen"),
    ],
    "ki_training": [
        ("Zweckbindungsprüfung", "methodenwissen"),
        ("KI-Modellen", "leitlinie"),
    ],
    "chatgpt": [
        ("KI und Datenschutz", "methodenwissen"),
        ("ChatGPT", "leitlinie"),
    ],
    "ki_vo": [
        ("Zuständigkeiten für die KI-Verordnung", "leitlinie"),
        ("AI Act", "methodenwissen"),
    ],
    "auskunft": [
        ("Art. 15", "gesetz_granular"),
        ("Rechte der betroffenen Person", "leitlinie"),
    ],
    "video_edpb": [
        ("Verarbeitung personenbezogener Daten durch Videogeräte", "leitlinie"),
    ],
    "dpbd": [
        ("Art. 25", "gesetz_granular"),
        ("Artikel 25 Datenschutz durch Technikgestaltung", "leitlinie"),
    ],
    "verein": [
        ("Vereinsmitglieder", "leitlinie"),
    ],
    "social_media": [
        ("gezielte Ansprache von Nutzern sozialer Medien", "leitlinie"),
    ],
    "datenpanne": [
        ("Art. 33", "gesetz_granular"),
        ("Art. 34", "gesetz_granular"),
        ("Meldung von Verletzungen des Schutzes", "leitlinie"),
    ],
    "vertrag": [
        ("Art. 6 Abs. 1 lit. b", "gesetz_granular"),
        ("Verarbeitung personenbezogener Daten im Zusammenhang mit Verträgen", "leitlinie"),
    ],
    "rechenschaft": [
        ("Art. 5 Abs. 2", "gesetz_granular"),
        ("Art. 24", "gesetz_granular"),
        ("Rechenschaftspflicht", "methodenwissen"),
    ],
}

# Keyword → Themen-Schlüssel
THEMEN_KEYWORDS_MAP: list[tuple[list[str], str]] = [
    (["usa", "amerika", "drittland", "transfer", "cloud", "dpf", "schrems", "privacy shield", "safe harbor", "angemessenheitsbeschluss"], "drittland"),
    (["videoüberwachung", "videoueberwachung", "kamera", "überwachungskamera", "cctv"], "video"),
    (["videoüberwachung", "videoueberwachung", "kamera", "überwachungskamera", "cctv"], "video_edpb"),
    (["cookie", "banner", "tracking"], "cookie"),
    (["einwilligung", "consent", "opt-in", "opt in", "newsletter", "e-mail-werbung", "double opt"], "einwilligung"),
    (["arbeitgeber", "beschäftigte", "beschaeftigte", "arbeitsplatz", "betriebsvereinbarung",
      "mitarbeiter", "e-mail lesen", "e-mails lesen"], "beschaeftigt"),
    (["schadensersatz", "schaden", "art. 82"], "schaden"),
    (["dsfa", "folgenabschätzung", "folgenabschaetzung", "datenschutz-folgenabschätzung"], "dsfa"),
    (["personenbezogene daten", "definition", "definiert", "was ist", "was sind",
      "was bedeutet", "begriff", "begriffsbestimmung"], "definition"),
    (["datenschutzerklärung", "datenschutzerklaerung", "informationspflicht", "information"], "informationspflicht"),
    (["recht auf vergessenwerden", "löschung", "loeschung", "löschen", "loeschen"], "loeschung"),
    (["vergessenwerden", "vergessen", "recht auf löschung", "recht auf loeschung",
      "delisting", "recht auf vergessenwerden", "suchergebnis", "suchmaschine"], "vergessen"),
    (["datenschutzbeauftragter", "datenschutzbeauftragte", "dsb", "benennung"], "dsb"),
    (["foto", "fotos", "bild", "abbildung", "veröffentlichen", "veroeffentlichen",
      "fotografieren", "kita", "schulfoto"], "foto"),
    (["schufa", "auskunftei", "bonitaet", "bonität", "kreditwürdigkeit", "vermieter",
      "mietvertrag", "scoring", "kreditauskunft"], "scoring"),
    (["berechtigtes interesse", "interessenabwägung", "interessenabwaegung"], "berechtigt"),
    (["gesundheitsdaten", "gesundheit", "krankheit", "patient", "arzt", "medizinisch", "ärztlich"], "gesundheit"),
    (["kundenkonto", "registrierung", "gastbestellung", "onlineshop", "webshop",
      "kontopflicht", "kontenzwang", "registrierungspflicht", "gastzugang"], "kundenkonto"),
    (["auftragsverarbeiter", "auftragsverarbeitung", "dienstleister", "av-vertrag"], "auftragsverarbeitung"),
    (["gemeinsame verantwortlichkeit", "gemeinsam verantwortlich", "fanpage", "joint controller"], "gemeinsam"),
    (["künstliche intelligenz", "kuenstliche intelligenz", "ki-tool",
      "machine learning"], "ki"),
    (["ki-training", "trainingsdaten", "fine-tuning", "web scraping", "modelltraining"], "ki_training"),
    (["chatgpt", "openai", "llm", "chatbot", "copilot", "midjourney"], "chatgpt"),
    (["ki-verordnung", "ai act", "hochrisiko", "hochrisiko-ki"], "ki_vo"),
    (["auskunft", "auskunftsrecht", "kopie", "art. 15"], "auskunft"),
    (["privacy by design", "technikgestaltung", "art. 25", "datenschutz durch technik"], "dpbd"),
    (["verein", "mitglieder", "mitgliederliste", "vereinsarbeit"], "verein"),
    (["social media", "targeting", "werbung soziale"], "social_media"),
    (["facebook", "instagram"], "social_media"),
    (["datenpanne", "breach", "sicherheitsvorfall", "meldepflicht"], "datenpanne"),
    (["vertrag", "vertragserfüllung", "vertragserfuellung", "art. 6 abs. 1 lit. b"], "vertrag"),
    (["rechenschaftspflicht", "accountability", "nachweispflicht", "dokumentationspflicht"], "rechenschaft"),
]


# Query Expansion: Alltagsbegriffe → juristische Fachbegriffe (FIX 2)
_SYNONYM_MAP: dict[str, list[str]] = {
    "löschen": ["Löschung", "Recht auf Vergessenwerden", "Art. 17"],
    "loeschen": ["Löschung", "Recht auf Vergessenwerden", "Art. 17"],
    "überwachung": ["Videoüberwachung", "Überwachungsmaßnahme", "Art. 6"],
    "ueberwachung": ["Videoüberwachung", "Überwachungsmaßnahme"],
    "kamera": ["Videoüberwachung", "Videoanlage", "Kameraüberwachung"],
    "mitlesen": ["Fernmeldegeheimnis", "Beschäftigtendatenschutz", "§ 26 BDSG"],
    "chef": ["Arbeitgeber", "Beschäftigtendatenschutz"],
    "arbeitgeber": ["Beschäftigtendatenschutz", "§ 26 BDSG", "Betriebsvereinbarung"],
    "cookies": ["Cookie", "Einwilligung", "TDDDG", "§ 25 TDDDG"],
    "tracking": ["Cookie", "Einwilligung", "Profiling", "TDDDG"],
    "newsletter": ["Einwilligung", "E-Mail-Werbung", "Double Opt-In", "UWG"],
    "abmahnung": ["Schadensersatz", "Art. 82 DSGVO", "Unterlassungsanspruch"],
    "strafe": ["Bußgeld", "Art. 83 DSGVO", "Sanktion"],
    "bussgeld": ["Bußgeld", "Art. 83 DSGVO", "Aufsichtsbehörde"],
    "schufa": ["Scoring", "Profiling", "Bonitätsprüfung", "Art. 22 DSGVO"],
    "vermieter": ["Mietvertrag", "Bonitätsprüfung", "Selbstauskunft", "Datenerhebung"],
    "arzt": ["Gesundheitsdaten", "Art. 9 DSGVO", "besondere Kategorien", "Schweigepflicht"],
    "patient": ["Gesundheitsdaten", "Art. 9 DSGVO", "Patientenakte", "besondere Kategorien"],
    "schule": ["Schüler", "Bildungseinrichtung", "Einwilligung", "Minderjährige"],
    "kinder": ["Minderjährige", "Art. 8 DSGVO", "Einwilligung", "Kindeswohl"],
    "whatsapp": ["Messenger", "Drittlandtransfer", "Auftragsverarbeitung", "US-Transfer"],
    "instagram": ["Social Media", "Drittlandtransfer", "gemeinsame Verantwortlichkeit"],
    "facebook": ["Social Media", "Fanpage", "gemeinsame Verantwortlichkeit", "Drittlandtransfer"],
    "google": ["Drittlandtransfer", "Auftragsverarbeitung", "Analytics", "DPF"],
    "cloud": ["Auftragsverarbeitung", "Drittlandtransfer", "Art. 28 DSGVO"],
    "fotos": ["Foto", "Bildnisrecht", "KUG", "Einwilligung"],
    "foto": ["Bildnisrecht", "KUG", "Einwilligung", "Art. 6"],
    "handy": ["Mobilgerät", "Standortdaten", "Telekommunikation"],
    "app": ["Anwendung", "Einwilligung", "Datenschutzerklärung", "TDDDG"],
    # Cross-Language Expansion: Deutsche Begriffe → englische EDPB-Begriffe
    "einwilligung": ["consent", "Einwilligung", "Art. 7 DSGVO"],
    "verantwortlicher": ["controller", "Verantwortlicher", "Art. 4 Nr. 7"],
    "auftragsverarbeiter": ["processor", "Auftragsverarbeiter", "Art. 28"],
    "betroffenenrechte": ["data subject rights", "Betroffenenrechte", "right of access"],
    "datenpanne": ["data breach notification", "Datenpanne", "Art. 33", "Art. 34"],
    "videoüberwachung": ["video surveillance", "video devices", "Videoüberwachung"],
    "videoueberwachung": ["video surveillance", "video devices", "Videoüberwachung"],
    "drittland": ["international transfer", "third country", "Drittlandtransfer"],
    "bußgeld": ["administrative fines", "Bußgeld", "Art. 83"],
    "löschung": ["erasure", "right to be forgotten", "Löschung", "Art. 17"],
    "loeschung": ["erasure", "right to be forgotten", "Löschung", "Art. 17"],
    "auskunft": ["right of access", "Auskunftsrecht", "Art. 15"],
    "auskunftsrecht": ["right of access", "data subject rights", "Art. 15"],
    "profiling": ["profiling", "targeting", "automated decision", "Art. 22"],
    "zertifizierung": ["certification", "Zertifizierung", "Art. 42"],
    "datenschutz": ["data protection by design", "by default", "Art. 25"],
    "sprachassistent": ["virtual voice assistant", "Sprachassistent", "smart speaker"],
}


def _find_pflicht_chunks(question: str, col) -> list[dict]:
    """Findet themenbasierte Pflicht-Chunks per where_document-Suche."""
    q_lower = question.lower()
    needed_searches: list[tuple[str, str | None]] = []
    for keywords, thema_key in THEMEN_KEYWORDS_MAP:
        if any(kw in q_lower for kw in keywords):
            needed_searches.extend(THEMEN_PFLICHT_SEARCHES.get(thema_key, []))

    if not needed_searches:
        return []

    pflicht = []
    seen_ids = set()

    for query_text, source_type in needed_searches:
        try:
            # Direkte ID-Suche: query_text beginnt mit "id:"
            if query_text.startswith("id:"):
                chunk_id = query_text[3:]
                result = col.get(ids=[chunk_id], include=["documents", "metadatas"])
            else:
                kwargs: dict = {
                    "where_document": {"$contains": query_text},
                    "include": ["documents", "metadatas"],
                    "limit": 2,
                }
                if source_type:
                    kwargs["where"] = {"source_type": source_type}
                result = col.get(**kwargs)
            for doc, meta, cid in zip(
                result["documents"], result["metadatas"], result["ids"]
            ):
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)
                pflicht.append({
                    "text": doc,
                    "meta": meta,
                    "distance": 0.05,
                    "adjusted_distance": 0.05,
                    "source": "pflicht",
                    "ce_score": 10.0,
                })
        except Exception:
            pass

    return pflicht[:5]  # Max 5 Pflicht-Plätze


def _find_urteil_by_name(question: str, col) -> list[dict]:
    """Findet Urteils-Chunks wenn ein Kurzname aus urteilsnamen.json in der Frage vorkommt."""
    _load_urteilsnamen()
    q_lower = question.lower()
    found_chunks: list[dict] = []

    for az, kurzname in _urteilsnamen.items():
        if not kurzname or len(kurzname) < 4:
            continue
        if kurzname.lower() not in q_lower:
            continue
        norm_az = _normalize_az(az)
        r = col.get(
            where={"aktenzeichen": norm_az},
            include=["documents", "metadatas"],
            limit=30,
        )
        if not r["ids"]:
            r = col.get(
                where={"aktenzeichen": f"Rechtssache {norm_az}"},
                include=["documents", "metadatas"],
                limit=30,
            )
        if not r["ids"]:
            continue
        chunks = []
        for i in range(len(r["ids"])):
            chunks.append({
                "id": r["ids"][i],
                "text": r["documents"][i],
                "meta": r["metadatas"][i],
                "distance": 0.05,
                "adjusted_distance": 0.05,
                "source": "urteil_name",
                "ce_score": 10.0,
            })
        def _segment_priority(cid: str) -> int:
            if "tenor" in cid: return 0
            if "wuerdigung" in cid: return 1
            if "vorlagefragen" in cid or "vf_" in cid: return 2
            if "sachverhalt" in cid: return 3
            if "header" in cid: return 4
            return 5
        chunks.sort(key=lambda c: _segment_priority(c["id"]))
        found_chunks.extend(chunks[:3])
        print(f"  [Urteilsname] '{kurzname}' → {norm_az}: {len(chunks)} Chunks, {min(3, len(chunks))} geladen")

    return found_chunks


def retrieve(question: str, history: list[tuple[str, str]] | None = None) -> list[dict]:
    """Führt semantische + Norm-basierte + Keyword-Suche + Reranking durch."""
    model = get_model()
    col = get_collection()

    # FIX 1: Bei kurzen Folgefragen Kontext aus History ergänzen
    search_query = question
    if history and len(question.split()) < 30:
        last_user = history[-1][0] if history else ""
        if last_user and last_user != question:
            search_query = f"{last_user} – {question}"

    # a) Semantische Suche: Top-40 (breiterer Trichter für Merge)
    q_embedding = model.encode([search_query]).tolist()
    results = col.query(
        query_embeddings=q_embedding,
        n_results=40,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    seen_ids = set()
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        chunk_id = _normalize_az(meta.get("chunk_id", "") or meta.get("volladresse", "") or doc[:50])
        if chunk_id in seen_ids:
            continue
        seen_ids.add(chunk_id)

        # Gewichtung anpassen
        source_type = meta.get("source_type", "")
        segment = meta.get("segment", "")
        boost_key = segment or source_type
        boost = SEGMENT_BOOST.get(boost_key, 1.0)
        adjusted_dist = dist * boost

        chunks.append({
            "text": doc,
            "meta": meta,
            "distance": dist,
            "adjusted_distance": adjusted_dist,
            "source": "semantic",
        })

    # b) Norm-basierte Suche
    norms = extract_norms(question)
    for norm in norms[:5]:
        try:
            norm_results = col.query(
                query_embeddings=model.encode([norm]).tolist(),
                n_results=5,
                include=["documents", "metadatas", "distances"],
                where={"source_type": {"$in": ["gesetz_granular", "gesetz"]}},
            )
            for doc, meta, dist in zip(
                norm_results["documents"][0],
                norm_results["metadatas"][0],
                norm_results["distances"][0],
            ):
                cid = _normalize_az(meta.get("volladresse", "") or doc[:50])
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    chunks.append({
                        "text": doc,
                        "meta": meta,
                        "distance": dist,
                        "adjusted_distance": dist * 0.85,
                        "source": "norm_lookup",
                    })
        except Exception:
            pass

    # c) Keyword-Suche (hybride Suche): Für jedes wichtige Wort zusätzlich
    #    per where_document={'$contains': ...} suchen
    words = set()
    for w in re.findall(r"[A-Za-zÄÖÜäöüß§]{5,}", question):
        words.add(w)
    # Auch Varianten mit Umlauten: ü→ue etc.
    extra = set()
    for w in words:
        w2 = w.replace("ü", "ue").replace("ö", "oe").replace("ä", "ae")
        if w2 != w:
            extra.add(w2)
    words.update(extra)
    # FIX 2: Query Expansion – Alltagsbegriffe → juristische Fachbegriffe
    expansion = set()
    for w in list(words):
        for term in _SYNONYM_MAP.get(w.lower(), []):
            expansion.add(term)
    words.update(expansion)
    # Auch Aktenzeichen als Keywords
    for az in extract_aktenzeichen(question):
        words.add(az.strip())

    keyword_hits: dict[str, dict] = {}  # chunk_id → chunk_data
    for word in list(words)[:10]:
        try:
            kw_results = col.query(
                query_embeddings=q_embedding,
                n_results=5,
                include=["documents", "metadatas", "distances"],
                where_document={"$contains": word},
            )
            for doc, meta, dist in zip(
                kw_results["documents"][0],
                kw_results["metadatas"][0],
                kw_results["distances"][0],
            ):
                cid = _normalize_az(meta.get("chunk_id", "") or meta.get("volladresse", "") or doc[:50])
                if cid in keyword_hits:
                    # Bereits gefunden → niedrigste Distanz behalten
                    if dist < keyword_hits[cid]["distance"]:
                        keyword_hits[cid]["distance"] = dist
                else:
                    keyword_hits[cid] = {
                        "text": doc, "meta": meta,
                        "distance": dist, "source": "keyword",
                    }
        except Exception:
            pass

    # Merge: Keyword-Treffer in die Chunk-Liste einpflegen
    for cid, kw_chunk in keyword_hits.items():
        if cid in seen_ids:
            # Chunk existiert bereits aus Embedding → Distanz halbieren (starker Boost)
            for chunk in chunks:
                existing_cid = (chunk["meta"].get("chunk_id", "")
                                or chunk["meta"].get("volladresse", "")
                                or chunk["text"][:50])
                if existing_cid == cid:
                    chunk["adjusted_distance"] *= 0.5
                    chunk["source"] = "hybrid"
                    break
        else:
            # Nur Keyword-Treffer → mit synthetischer Distanz 0.15 einfügen
            seen_ids.add(cid)
            source_type = kw_chunk["meta"].get("source_type", "")
            segment = kw_chunk["meta"].get("segment", "")
            boost = SEGMENT_BOOST.get(segment or source_type, 1.0)
            chunks.append({
                "text": kw_chunk["text"],
                "meta": kw_chunk["meta"],
                "distance": kw_chunk["distance"],
                "adjusted_distance": 0.15 * boost,
                "source": "keyword",
            })

    # ── Cross-Encoder Reranking ──
    # Pre-filter: Sortiere nach adjusted_distance, nimm Top-40 Kandidaten
    chunks.sort(key=lambda x: x["adjusted_distance"])
    candidates = chunks[:40]

    if not candidates:
        return []

    reranker = get_reranker()
    pairs = [(question, c["text"][:500]) for c in candidates]
    ce_scores = reranker.predict(pairs).tolist()

    for chunk, ce_score in zip(candidates, ce_scores):
        # Keyword-Treffer behalten Mindest-Score von 3.0
        if chunk.get("source") in ("keyword", "hybrid") and ce_score < 3.0:
            ce_score = 3.0
        chunk["ce_score"] = ce_score

    # FIX 1: Aktualitäts-Boost auf CE-Score anwenden
    for c in candidates:
        year = _extract_year(c)
        recency = _recency_factor(year)
        # Höherer CE-Score = besser → teile durch Recency (< 1 = Boost, > 1 = Penalty)
        c["ce_score"] = c["ce_score"] / recency

    # FIX: Schlüsselurteile boosten – Urteile mit Kurznamen aus urteilsnamen.json
    _load_urteilsnamen()
    if _urteilsnamen:
        for c in candidates:
            az = c["meta"].get("aktenzeichen", "")
            if az and get_urteilsname(az):
                c["ce_score"] = c["ce_score"] * 1.5

    # FIX 3: Instanzgerichts-Penalty – niedrigrangige Gerichte abwerten,
    # es sei denn die Frage nennt explizit ein Gericht oder Aktenzeichen
    _LOWER_COURTS = {"bsg", "bfh", "bag", "bverwg", "olg", "lg", "vg", "ag"}
    _q_lower = question.lower()
    _has_court_ref = (
        any(g in _q_lower for g in _LOWER_COURTS)
        or bool(extract_aktenzeichen(question))
    )
    if not _has_court_ref:
        for c in candidates:
            gericht = (c["meta"].get("gericht") or "").lower()
            if any(g == gericht or gericht.startswith(g + " ") for g in _LOWER_COURTS):
                c["ce_score"] = c.get("ce_score", 0) / 1.3

    # Pre-DSGVO-Filter: Veraltete Leitlinien abwerten oder entfernen
    post_dsgvo = [c for c in candidates if not _is_outdated_chunk(c)]
    if len(post_dsgvo) >= 3:
        # Genug aktuelle Quellen → veraltete komplett entfernen
        outdated_count = len(candidates) - len(post_dsgvo)
        if outdated_count:
            print(f"  Pre-DSGVO-Filter: {outdated_count} veraltete Chunks entfernt")
        candidates = post_dsgvo
    else:
        # Zu wenig aktuelle → veraltete nur massiv abwerten + markieren
        for c in candidates:
            if _is_outdated_chunk(c):
                c["ce_score"] = c.get("ce_score", 0) / 3.0
                c["_pre_dsgvo"] = True

    # Sortiere nach Cross-Encoder-Score (höher = besser)
    # Tie-breaker: Segment-Boost
    def sort_key(c):
        ce = c["ce_score"]
        boost = SEGMENT_BOOST.get(
            c["meta"].get("segment", "") or c["meta"].get("source_type", ""), 1.0
        )
        return -(ce + (1.0 - boost) * 0.3)

    candidates.sort(key=sort_key)

    # FIX: Methodenwissen-Chunks priorisieren – MW mit CE > 4.0 nach vorne
    mw_top = []
    mw_rest = []
    non_mw = []
    for c in candidates:
        if c["meta"].get("source_type") == "methodenwissen" and c.get("ce_score", 0) > 4.0:
            if len(mw_top) < 3:
                mw_top.append(c)
            else:
                mw_rest.append(c)
        else:
            non_mw.append(c)
    if mw_top:
        candidates = mw_top + non_mw + mw_rest
        print(f"  MW-Priorisierung: {len(mw_top)} Chunks an Position 1-{len(mw_top)} gesetzt")

    # FIX 4: Pflicht-Chunks für erkannte Themen voranstellen
    pflicht = _find_pflicht_chunks(question, col)
    urteil_name_chunks = _find_urteil_by_name(question, col)
    # Dedupliziere: keine IDs doppelt laden
    pflicht_ids = {c["id"] for c in pflicht}
    for c in urteil_name_chunks:
        if c["id"] not in pflicht_ids:
            pflicht.append(c)
            pflicht_ids.add(c["id"])

    # Document-Level Deduplication: max 3 Chunks pro Dokument
    MAX_PER_DOC = 3
    doc_counts: dict[str, int] = {}
    deduped: list[dict] = []
    for chunk in candidates:
        dk = _doc_key(chunk.get("meta", {}))
        if doc_counts.get(dk, 0) >= MAX_PER_DOC:
            continue
        doc_counts[dk] = doc_counts.get(dk, 0) + 1
        deduped.append(chunk)
    n_removed = len(candidates) - len(deduped)
    if n_removed:
        print(f"  Doc-Dedup: {n_removed} Duplikate entfernt (max {MAX_PER_DOC}/Dokument)")
    candidates = deduped

    # Dynamischer Cutoff: CE-Score > CE_CUTOFF ODER adjusted_distance < DIST_CUTOFF
    selected = list(pflicht)  # Pflicht-Chunks zuerst (max 3)
    selected_ids = {c["meta"].get("chunk_id", "") or c["meta"].get("thema", "")
                    for c in selected}

    for chunk in candidates:
        meta = chunk["meta"]
        cid = meta.get("chunk_id", "") or meta.get("thema", "") or chunk["text"][:30]
        if cid in selected_ids:
            continue

        ce = chunk.get("ce_score", 0)
        dist = chunk.get("adjusted_distance", 1.0)
        if ce >= CE_CUTOFF or dist < DIST_CUTOFF:
            selected.append(chunk)
            selected_ids.add(cid)

    # Gruppiere nach Dokument und prüfe Min/Max
    docs = group_chunks_to_docs(selected)

    # Falls unter Minimum: Auffüllen mit nächstbesten Candidates
    if len(docs) < MIN_DOCS:
        for chunk in candidates:
            cid = chunk["meta"].get("chunk_id", "") or chunk["text"][:30]
            if cid not in selected_ids:
                selected.append(chunk)
                selected_ids.add(cid)
                docs = group_chunks_to_docs(selected)
                if len(docs) >= MIN_DOCS:
                    break

    # Falls über Maximum: Dokumente mit niedrigstem Score entfernen
    if len(docs) > MAX_DOCS:
        docs = docs[:MAX_DOCS]
        # Selected auf die Chunks der behaltenen Docs reduzieren
        kept_keys = {d["key"] for d in docs}
        selected = [c for c in selected if _doc_key(c.get("meta", {})) in kept_keys]
        # Pflicht-Chunks immer behalten
        for c in pflicht:
            if c not in selected:
                selected.append(c)

    # Source-Type-Diversifizierung: mindestens 1 Gesetz, 1 Urteil, 1 Leitlinie/MW
    _st_groups = {
        "gesetz": {"gesetz_granular"},
        "urteil": {"urteil", "urteil_segmentiert"},
        "leitlinie": {"leitlinie", "methodenwissen"},
    }
    for group_name, group_types in _st_groups.items():
        has = any(c.get("meta", {}).get("source_type") in group_types for c in selected)
        if not has:
            for chunk in candidates:
                if chunk.get("meta", {}).get("source_type") in group_types:
                    cid = chunk["meta"].get("chunk_id", "") or chunk["text"][:30]
                    if cid not in selected_ids:
                        selected.append(chunk)
                        selected_ids.add(cid)
                        print(f"  Diversifizierung: {group_name}-Chunk nachgeschoben")
                        break

    # EG-Anreicherung: Passende Erwägungsgründe automatisch nachladen
    selected = _enrich_with_erwaegungsgruende(selected, col)

    return selected


def _enrich_with_erwaegungsgruende(results: list[dict], col) -> list[dict]:
    """Lädt passende Erwägungsgründe nach, wenn DSGVO-Artikel in den Ergebnissen sind.

    Für jeden DSGVO-Artikel in den Top-Ergebnissen prüfe die Metadaten auf
    'erwaegungsgruende'. Lade den wichtigsten passenden EG (niedrigste Nummer)
    als zusätzlichen Kontextchunk. Max. 2 EGs pro Anfrage.
    """
    existing_ids = {c.get("meta", {}).get("chunk_id", "") or c.get("meta", {}).get("eg_nr", "")
                    for c in results}
    # Collect EG numbers from DSGVO articles in results
    eg_candidates: list[int] = []
    for chunk in results:
        meta = chunk.get("meta", {})
        if meta.get("gesetz") == "DSGVO" and meta.get("source_type") == "gesetz_granular":
            eg_str = meta.get("erwaegungsgruende", "")
            if eg_str:
                for nr_str in eg_str.split(","):
                    nr_str = nr_str.strip()
                    if nr_str.isdigit():
                        nr = int(nr_str)
                        if nr not in eg_candidates:
                            eg_candidates.append(nr)

    if not eg_candidates:
        return results

    # Sort by number (lowest = most fundamental) and take max 2
    eg_candidates.sort()
    added = 0
    for eg_nr in eg_candidates:
        if added >= 2:
            break
        chroma_id = f"dsgvo_eg_{eg_nr}"
        if chroma_id in existing_ids:
            continue
        try:
            r = col.get(ids=[chroma_id], include=["documents", "metadatas"])
            if r["ids"]:
                results.append({
                    "text": r["documents"][0],
                    "meta": r["metadatas"][0],
                    "distance": 0.10,
                    "adjusted_distance": 0.10,
                    "source": "eg_enrichment",
                    "ce_score": 5.0,
                })
                existing_ids.add(chroma_id)
                added += 1
        except Exception:
            pass

    if added:
        print(f"  EG-Anreicherung: {added} Erwägungsgründe nachgeladen")

    return results


def _normalize_az(text: str) -> str:
    """Normalisiert Aktenzeichen: Unicode-Bindestriche → ASCII-Bindestrich."""
    return text.replace("\u2011", "-").replace("\u2010", "-").replace("\u2013", "-").replace("\u2014", "-")


def _doc_key(meta: dict) -> str:
    """Erzeugt einen Gruppierungsschlüssel pro Dokument aus Chunk-Metadaten."""
    # Aktenzeichen + Gericht = ein Urteil
    az = _normalize_az(meta.get("aktenzeichen", ""))
    if az:
        gericht = meta.get("gericht", "")
        return f"{gericht}|{az}".strip("|")
    # Gesetz + Gesetzname = ein Gesetzesdokument
    gesetz = meta.get("gesetz", "")
    if gesetz:
        return gesetz
    # Titel als Fallback (z.B. Leitlinien, Methodenwissen)
    titel = meta.get("titel", "")
    if titel:
        return titel
    # Thema (Methodenwissen)
    thema = meta.get("thema", "")
    if thema:
        return thema
    return meta.get("chunk_id", "unknown")


def _doc_label(doc_chunks: list[dict]) -> str:
    """Erzeugt einen Anzeige-Titel für ein gruppiertes Dokument."""
    meta = doc_chunks[0]["meta"]
    # Aktenzeichen-Dokument (mit Urteilsname wenn verfügbar)
    az = meta.get("aktenzeichen", "")
    if az:
        gericht = meta.get("gericht", "")
        datum = meta.get("datum", "")
        name = get_urteilsname(az)
        parts = [gericht, az]
        if name:
            parts.append(f"({name})")
        if datum:
            parts.append(f"({datum})" if not name else f"– {datum}")
        return " ".join(p for p in parts if p)
    # Gesetz
    gesetz = meta.get("gesetz", "")
    if gesetz:
        return gesetz
    # Titel (Leitlinien etc.)
    titel = meta.get("titel", "")
    if titel:
        return titel
    # Thema (Methodenwissen)
    thema = meta.get("thema", "")
    if thema:
        return thema
    return "Unbekannte Quelle"


def _normalize_title(title: str) -> str:
    """Normalisiert einen Titel für Duplikat-Vergleich (Datum, Version, Whitespace entfernen)."""
    t = title.lower()
    # Jahreszahlen und Versionsnummern entfernen
    t = re.sub(r"\b(19|20)\d{2}\b", "", t)
    t = re.sub(r"v\s*\d+(\.\d+)*", "", t)
    t = re.sub(r"version\s*\d+(\.\d+)*", "", t)
    # Klammern mit Datum/Version entfernen
    t = re.sub(r"\([^)]*\)", "", t)
    # Whitespace normalisieren
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _jaccard_similarity(a: str, b: str) -> float:
    """Jaccard-Ähnlichkeit auf Wort-Ebene."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _dedup_leitlinien(docs: list[dict]) -> list[dict]:
    """Entfernt ältere Duplikate bei Leitlinien mit ähnlichem Titel."""
    if not docs:
        return docs

    # Nur Leitlinien deduplizieren
    leitlinien = [d for d in docs if d["source_type"] == "leitlinie"]
    other = [d for d in docs if d["source_type"] != "leitlinie"]

    if len(leitlinien) <= 1:
        return docs

    # Für jede Leitlinie: normalisierter Titel + Jahreszahl
    for d in leitlinien:
        d["_norm_title"] = _normalize_title(d["label"])
        year = _extract_year(d["chunks"][0]) if d["chunks"] else None
        d["_year"] = year or 0

    # Paarweise Duplikate finden: behalte das neuere
    to_remove = set()
    for i in range(len(leitlinien)):
        if i in to_remove:
            continue
        for j in range(i + 1, len(leitlinien)):
            if j in to_remove:
                continue
            sim = _jaccard_similarity(
                leitlinien[i]["_norm_title"],
                leitlinien[j]["_norm_title"],
            )
            if sim >= 0.8:
                # Behalte das neuere Dokument
                if leitlinien[i]["_year"] >= leitlinien[j]["_year"]:
                    to_remove.add(j)
                    print(f"  Duplikat entfernt: '{leitlinien[j]['label']}' "
                          f"(älter als '{leitlinien[i]['label']}')")
                else:
                    to_remove.add(i)
                    print(f"  Duplikat entfernt: '{leitlinien[i]['label']}' "
                          f"(älter als '{leitlinien[j]['label']}')")

    deduped = [d for idx, d in enumerate(leitlinien) if idx not in to_remove]

    # Temporäre Felder entfernen
    for d in deduped:
        d.pop("_norm_title", None)
        d.pop("_year", None)

    return other + deduped


def group_chunks_to_docs(chunks: list[dict]) -> list[dict]:
    """Gruppiert Chunks nach Dokument. Gibt Liste von Doc-Dicts zurück.

    Jedes Doc-Dict: {
        'key': str, 'label': str, 'source_type': str,
        'best_score': float, 'chunks': list[dict]
    }
    """
    from collections import OrderedDict
    groups: dict[str, list[dict]] = OrderedDict()
    for chunk in chunks:
        key = _doc_key(chunk.get("meta", {}))
        groups.setdefault(key, []).append(chunk)

    docs = []
    for key, doc_chunks in groups.items():
        # Sortiere Chunks innerhalb des Dokuments nach CE-Score (höchster zuerst)
        doc_chunks.sort(key=lambda c: -c.get("ce_score", 0))
        best_score = max(c.get("ce_score", 0) for c in doc_chunks)
        source_type = doc_chunks[0].get("meta", {}).get("source_type", "")
        docs.append({
            "key": key,
            "label": _doc_label(doc_chunks),
            "source_type": source_type,
            "best_score": best_score,
            "chunks": doc_chunks,
        })

    # Duplikat-Erkennung bei Leitlinien
    docs = _dedup_leitlinien(docs)

    # Sortiere Dokumente: Primärquellen zuerst (nach Score), dann MW (nach Score)
    primary = [d for d in docs if d["source_type"] != "methodenwissen"]
    mw = [d for d in docs if d["source_type"] == "methodenwissen"]
    primary.sort(key=lambda d: -d["best_score"])
    mw.sort(key=lambda d: -d["best_score"])
    return primary + mw


def format_context(chunks: list[dict]) -> str:
    """Formatiert die Chunks als nummerierte Quellen (pro Dokument) für das LLM."""
    docs = group_chunks_to_docs(chunks)
    parts = []
    for i, doc in enumerate(docs, 1):
        source_type = doc["source_type"]
        label = _fix_mojibake(doc["label"])

        header = f"[Quelle {i} – Typ: {source_type} – {label}]"

        # Alle Chunks des Dokuments als Abschnitte
        sections = []
        for j, chunk in enumerate(doc["chunks"]):
            segment = chunk["meta"].get("segment", "")
            volladresse = chunk["meta"].get("volladresse", "")
            paragraph = chunk["meta"].get("paragraph", "")
            section_label = segment or volladresse or paragraph or ""
            if section_label:
                sections.append(f"--- {section_label} ---\n{chunk['text'][:3000]}")
            else:
                sections.append(chunk["text"][:3000])

        parts.append(header + "\n" + "\n\n".join(sections))

    return "\n\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# TEIL 2 – LLM-Anbindung (Cascading Provider Fallback)
# ═══════════════════════════════════════════════════════════════════════════


def _build_llm_messages(question: str, context: str, history: list[dict]) -> list[dict]:
    """Baut die Message-Liste für LLM-Aufrufe."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-6:]:
        messages.append(msg)
    messages.append({"role": "user", "content": (
        f"FRAGE: {question}\n\n"
        f"BEREITGESTELLTE QUELLEN:\n\n{context}\n\n"
        f"Beantworte die Frage auf Grundlage der bereitgestellten Quellen. "
        f"Zitiere dabei exakt mit Fundstelle."
    )})
    return messages


# ---------------------------------------------------------------------------
# Provider 1: HuggingFace Inference API
# ---------------------------------------------------------------------------

_hf_client = None
_hf_model_name = None


def _hf_available() -> bool:
    return bool(HF_TOKEN)


def _hf_init():
    """Lazy-Init des HF InferenceClient."""
    global _hf_client, _hf_model_name
    if _hf_client is not None:
        return _hf_client, _hf_model_name
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        return None, None
    for model_id in ["Qwen/Qwen3-235B-A22B", "mistralai/Mixtral-8x7B-Instruct-v0.1"]:
        try:
            client = InferenceClient(model=model_id, token=HF_TOKEN)
            client.chat_completion(
                messages=[{"role": "user", "content": "test"}], max_tokens=5,
            )
            _hf_client = client
            _hf_model_name = model_id
            return client, model_id
        except Exception:
            continue
    return None, None


def _stream_hf(messages: list[dict]):
    """Streamt von HuggingFace. Yields Strings. Raises bei Fehler."""
    client, _ = _hf_init()
    if client is None:
        raise ConnectionError("HF InferenceClient nicht verfügbar")
    stream = client.chat_completion(
        messages=messages, max_tokens=2048, temperature=0.3, stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        token = delta.content if delta else None
        if token:
            yield token


# ---------------------------------------------------------------------------
# Provider 2: OpenRouter (OpenAI-kompatibel)
# ---------------------------------------------------------------------------

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_OPENROUTER_MODELS = [
    "qwen/qwen3-235b-a22b",
    "meta-llama/llama-3.3-70b-instruct",
    "google/gemma-3-27b-it",
    "mistralai/mistral-small-3.1-24b-instruct",
]
_OPENROUTER_EXTRA_HEADERS = {
    "HTTP-Referer": "https://openlex.de",
    "X-Title": "OpenLex Datenschutzrecht",
}


def _openrouter_available() -> bool:
    return bool(OPENROUTER_KEY)


def _stream_openai_compat(url: str, key: str, model: str, messages: list[dict],
                          extra_headers: dict | None = None):
    """Generische OpenAI-kompatible Streaming-Funktion. Yields Strings. Raises bei Fehler."""
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    r = requests.post(
        url,
        headers=headers,
        json={
            "model": model,
            "messages": messages,
            "stream": True,
            "max_tokens": 2048,
            "temperature": 0.3,
        },
        timeout=120,
        stream=True,
    )
    if r.status_code in (429, 503):
        raise ConnectionError(f"HTTP {r.status_code}: {r.text[:200]}")
    r.raise_for_status()

    for line in r.iter_lines():
        if not line:
            continue
        text = line.decode("utf-8", errors="replace")
        if not text.startswith("data: "):
            continue
        data = text[6:]
        if data.strip() == "[DONE]":
            break
        try:
            chunk = json.loads(data)
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    yield token
                # finish_reason "length" = Antwort wurde abgeschnitten
                if choices[0].get("finish_reason") == "length":
                    yield "\n\n---\n*Die Antwort wurde aus Platzgründen gekürzt. Für eine vollständige Analyse stellen Sie bitte eine spezifischere Frage.*"
        except json.JSONDecodeError:
            continue


def _stream_openrouter(messages: list[dict]):
    """Streamt von OpenRouter. Yields Strings. Raises bei Fehler."""
    last_error = None
    for model in _OPENROUTER_MODELS:
        try:
            yield from _stream_openai_compat(
                _OPENROUTER_URL, OPENROUTER_KEY, model, messages,
                extra_headers=_OPENROUTER_EXTRA_HEADERS,
            )
            return
        except Exception as e:
            last_error = e
            continue
    raise last_error or ConnectionError("OpenRouter nicht erreichbar")


# ---------------------------------------------------------------------------
# Provider 3: Mistral API (OpenAI-kompatibel)
# ---------------------------------------------------------------------------

_MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
_MISTRAL_MODEL = "mistral-large-latest"


def _mistral_available() -> bool:
    return bool(MISTRAL_KEY)


def _stream_mistral(messages: list[dict]):
    """Streamt von Mistral. Yields Strings. Raises bei Fehler."""
    yield from _stream_openai_compat(
        _MISTRAL_URL, MISTRAL_KEY, _MISTRAL_MODEL, messages,
    )


# ---------------------------------------------------------------------------
# Provider 4: Lokales Ollama (Fallback)
# ---------------------------------------------------------------------------

def _ollama_available() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200 and bool(r.json().get("models"))
    except Exception:
        return False


def _get_ollama_model() -> str | None:
    """Findet ein verfügbares Ollama-Modell."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code != 200:
            return None
        models = [m["name"] for m in r.json().get("models", [])]
        for preferred in OLLAMA_MODELS:
            for available in models:
                if preferred in available:
                    return available
        return models[0] if models else None
    except Exception:
        return None


def _stream_ollama(messages: list[dict]):
    """Streamt von Ollama. Yields Strings. Raises bei Fehler."""
    model_name = _get_ollama_model()
    if not model_name:
        raise ConnectionError("Ollama nicht erreichbar oder kein Modell installiert")
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": model_name, "messages": messages, "stream": True,
              "options": {"num_ctx": 8192}, "think": False},
        timeout=600, stream=True,
    )
    r.raise_for_status()
    for line in r.iter_lines():
        if not line:
            continue
        try:
            chunk = json.loads(line)
            token = chunk.get("message", {}).get("content", "")
            if token:
                yield token
            if chunk.get("done"):
                break
        except json.JSONDecodeError:
            continue


# ---------------------------------------------------------------------------
# Provider-Registry + Cascading Stream
# ---------------------------------------------------------------------------

PROVIDERS = [
    {
        "name": "HuggingFace",
        "display": "Qwen3-235B via HuggingFace",
        "is_available": _hf_available,
        "stream": _stream_hf,
    },
    {
        "name": "OpenRouter",
        "display": "Qwen3-235B via OpenRouter",
        "is_available": _openrouter_available,
        "stream": _stream_openrouter,
    },
    {
        "name": "Mistral",
        "display": "Mistral Large via Mistral",
        "is_available": _mistral_available,
        "stream": _stream_mistral,
    },
    {
        "name": "Ollama",
        "display": None,  # wird dynamisch gesetzt
        "is_available": _ollama_available,
        "stream": _stream_ollama,
    },
]


def get_provider_status() -> str:
    """Gibt eine Übersicht der verfügbaren Provider zurück."""
    parts = []
    for p in PROVIDERS:
        try:
            ok = p["is_available"]()
        except Exception:
            ok = False
        status = "✅" if ok else "❌"
        parts.append(f"{p['name']} {status}")
    return "Verfügbare Provider: " + ", ".join(parts)


def stream_with_fallback(messages: list[dict]):
    """Versucht Provider der Reihe nach. Yields (token, provider_display).

    Beim ersten erfolgreichen Token wird der Provider festgelegt.
    Bei Fehler wird automatisch zum nächsten Provider gewechselt.
    """
    for provider in PROVIDERS:
        if not provider["is_available"]():
            continue

        display = provider["display"]
        # Ollama: dynamischer Modellname
        if provider["name"] == "Ollama":
            model = _get_ollama_model()
            display = f"{model} via Ollama (lokal)" if model else "Ollama (lokal)"

        try:
            print(f"  LLM: Versuche {provider['name']}...")
            tokens_yielded = False
            for token in provider["stream"](messages):
                tokens_yielded = True
                yield token, display
            if tokens_yielded:
                return  # Erfolgreich gestreamt
            # Kein einziger Token → weiter
            print(f"  LLM: {provider['name']} lieferte keine Antwort, wechsle...")
        except Exception as e:
            print(f"  LLM: {provider['name']} Fehler: {e}, wechsle zum nächsten Provider...")
            continue

    # Kein Provider hat funktioniert
    yield ("⚠️ **Kein LLM-Provider erreichbar.**\n\n"
           "Verfügbare Optionen:\n"
           "- HF_TOKEN setzen für HuggingFace\n"
           "- OPENROUTER_KEY setzen für OpenRouter\n"
           "- MISTRAL_KEY setzen für Mistral\n"
           "- `ollama serve` starten für lokalen Betrieb\n"), "Kein Provider"


# ═══════════════════════════════════════════════════════════════════════════
# TEIL 3 – Validator
# ═══════════════════════════════════════════════════════════════════════════


def validate_response(response: str, chunks: list[dict]) -> list[dict]:
    """Validiert Normreferenzen und Aktenzeichen in der Antwort.

    Drei Stufen:
      'verified'   – in übergebenen Quellen UND in ChromaDB
      'in_db_only' – in ChromaDB aber NICHT im übergebenen Kontext
      'missing'    – nicht in ChromaDB (Halluzinationsverdacht)
    """
    col = get_collection()
    model = get_model()
    validations = []

    def _normalize_norm(text: str) -> str:
        """Normalisiert Normreferenzen für Vergleich: Leerzeichen, DS-GVO etc."""
        t = text.lower()
        t = t.replace("ds-gvo", "dsgvo").replace("ds gvo", "dsgvo")
        # "Abs " ohne Punkt → "Abs. "
        t = re.sub(r"\babs\s+", "abs. ", t)
        # Leerzeichen nach Art./§ normalisieren: "Art.17" → "Art. 17", "Art.  17" → "Art. 17"
        t = re.sub(r"(art\.?)\s*(\d)", r"art. \2", t)
        t = re.sub(r"(§§?)\s*(\d)", r"§ \2", t)
        # Mehrfach-Leerzeichen
        t = re.sub(r"\s+", " ", t)
        return t

    # Kontext-Texte für Stufe-1-Prüfung (war es in den übergebenen Quellen?)
    # a) Label/Metadaten-Suche (schnell, exakt)
    ctx_meta = _normalize_norm(" ".join(
        str(c["meta"].get("volladresse", "")) + " " +
        str(c["meta"].get("aktenzeichen", "")) + " " +
        str(c["meta"].get("thema", "")) + " " +
        str(c["meta"].get("chunk_id", ""))
        for c in chunks
    ))
    # b) Volltext-Suche (fängt granulare Referenzen in übergeordneten Artikeln ab)
    ctx_fulltext = _normalize_norm(" ".join(c["text"] for c in chunks))

    def _check(ref: str, ref_type: str, db_threshold: float) -> dict:
        ref_normalized = _normalize_norm(ref)
        # Stufe 1a: Label/Metadaten-Match
        in_context = ref_normalized in ctx_meta
        # Stufe 1b: Volltext-Match (z.B. "Art. 7 Abs. 3" im Text von Quelle "Art. 7 DSGVO")
        if not in_context:
            in_context = ref_normalized in ctx_fulltext

        in_db = False
        if not in_context:
            # 1) Embedding-Suche
            try:
                search = col.query(
                    query_embeddings=model.encode([ref]).tolist(),
                    n_results=1,
                    include=["metadatas", "distances"],
                )
                if search["distances"][0] and search["distances"][0][0] < db_threshold:
                    in_db = True
            except Exception:
                pass
            # 2) Keyword-Suche als Fallback (fängt existierende Normen ab)
            if not in_db:
                try:
                    kw_search = col.get(
                        where_document={"$contains": ref},
                        limit=1,
                        include=[],
                    )
                    if kw_search["ids"]:
                        in_db = True
                except Exception:
                    pass
        else:
            in_db = True  # Wenn in Kontext, dann sicher auch in DB

        if in_context:
            level = "verified"
        elif in_db:
            level = "in_db_only"
        else:
            level = "missing"

        # Urteilsname anhängen bei Aktenzeichen
        display_ref = ref
        if ref_type == "aktenzeichen":
            name = get_urteilsname(ref)
            if name:
                display_ref = f"{ref} ({name})"

        return {"type": ref_type, "reference": display_ref, "level": level}

    # a) Normreferenzen
    for norm in extract_norms(response)[:20]:
        validations.append(_check(norm.strip(), "norm", 0.15))

    # b) Aktenzeichen
    for az in extract_aktenzeichen(response)[:15]:
        validations.append(_check(az.strip(), "aktenzeichen", 0.12))

    return validations


# ═══════════════════════════════════════════════════════════════════════════
# TEIL 4 – Gradio Interface
# ═══════════════════════════════════════════════════════════════════════════


_HIGHLIGHT_NORM_RE = re.compile(
    r"(Art\.?\s*\d+\s*(?:Abs\.?\s*\d+\s*)?(?:(?:lit\.?\s*[a-z]|Nr\.?\s*\d+)\s*)?(?:DSGVO|BDSG|TTDSG|TDDDG|GRCh|AEUV|GG))"
    r"|(§§?\s*\d+[a-z]?\s*(?:Abs\.?\s*\d+\s*)?(?:DSGVO|BDSG|TTDSG|TDDDG|GG))"
    r"|((?:C|T)[-‑]\d+/\d+)",
    re.UNICODE,
)


def _highlight_text(text: str, query: str = "") -> str:
    """Highlightet Normen (gelb) und Query-Wörter (blau) in HTML-escaped Text."""
    import html as html_mod
    text = html_mod.escape(text)

    # Normen + AZ gelb highlighten
    def _mark_norm(m):
        return f'<mark>{m.group(0)}</mark>'
    text = _HIGHLIGHT_NORM_RE.sub(_mark_norm, text)

    # Query-Wörter blau highlighten
    if query:
        words = set(w for w in re.findall(r"[A-Za-zÄÖÜäöüß]{4,}", query)
                    if w.lower() not in {"dsgvo", "bdsg", "dass", "oder", "eine", "nach", "wird",
                                          "sind", "sein", "über", "auch", "sich", "wenn", "mein",
                                          "meine", "einem", "eines", "dieser", "diese"})
        for word in words:
            text = re.sub(
                rf"(?i)({re.escape(word)})",
                r'<span class="highlight-query">\1</span>',
                text,
            )
    return text


def _fix_mojibake(text: str) -> str:
    """Repariert kaputte UTF-8/Latin-1 Umlaute (Mojibake)."""
    replacements = [
        ("Ã¤", "ä"), ("Ã¶", "ö"), ("Ã¼", "ü"), ("ÃŸ", "ß"),
        ("Ã–", "Ö"), ("Ãœ", "Ü"),
        ("\u00e2\u0080\u0093", "–"), ("\u00e2\u0080\u0099", "'"),
    ]
    for bad, good in replacements:
        text = text.replace(bad, good)
    # Ã gefolgt von Kleinbuchstabe → Ä + Kleinbuchstabe (z.B. Ãn → Än)
    text = re.sub(r"Ã(?=[a-z])", "Ä", text)
    return text


def format_sources(chunks: list[dict], validations: list[dict],
                   question: str = "") -> str:
    """Formatiert die Quellenleiste als HTML mit aufklappbaren Dokumenten."""
    css = """<style>
.src-panel details{margin:4px 0;padding:4px 8px;border-radius:4px;background:rgba(128,128,128,0.08)}
.src-panel summary{cursor:pointer;font-weight:normal;font-size:14px;padding:2px 0}
.src-panel summary::-webkit-details-marker{color:#888}
.src-panel mark{background:#ffd700;color:#000;padding:0 2px;border-radius:2px}
.src-panel .highlight-query{background:#87ceeb;color:#000;padding:0 2px;border-radius:2px}
.src-panel .meta-line{color:#888;font-size:14px;margin-top:4px;border-top:1px solid rgba(128,128,128,0.2);padding-top:4px}
.src-panel .chunk-text{font-size:14px;line-height:1.4;padding:6px 0;white-space:pre-wrap;word-break:break-word}
.src-panel .val-box{padding:6px 10px;border-radius:6px;background:rgba(128,128,128,0.06);margin:6px 0}
.src-panel .sub-chunk{margin:4px 0 4px 12px;padding:4px 6px;border-left:2px solid rgba(128,128,128,0.2)}
</style>"""

    html = f'{css}<div class="src-panel"><h3>📚 Quellen</h3>'

    docs = group_chunks_to_docs(chunks)
    primary_docs = [d for d in docs if d["source_type"] != "methodenwissen"]
    mw_docs = [d for d in docs if d["source_type"] == "methodenwissen"]

    def _render_doc(doc, doc_nr, question):
        emoji = SOURCE_EMOJI.get(doc["source_type"], "📄")
        label = _fix_mojibake(doc["label"])
        n_chunks = len(doc["chunks"])
        count_tag = f' <small>({n_chunks} Abschnitte)</small>' if n_chunks > 1 else ""

        # Pre-DSGVO-Warnung wenn mindestens ein Chunk als veraltet markiert
        pre_dsgvo = any(c.get("_pre_dsgvo") for c in doc["chunks"])
        warn_tag = ' <span style="color:#e65100;font-size:14px">⚠️ Pre-DSGVO</span>' if pre_dsgvo else ""

        summary = f'[{doc_nr}] {emoji} {label}{count_tag}{warn_tag}'

        inner = ""
        for chunk in doc["chunks"]:
            meta = chunk["meta"]
            # Abschnitts-Label
            section = (
                _fix_mojibake(meta.get("segment", ""))
                or _fix_mojibake(meta.get("volladresse", ""))
                or _fix_mojibake(meta.get("paragraph", ""))
                or ""
            )
            section_tag = f'<b>{section}</b><br>' if section else ""

            text_excerpt = chunk.get("text", "")[:800]
            highlighted = _highlight_text(_fix_mojibake(text_excerpt), question)

            inner += (
                f'<div class="sub-chunk">'
                f'{section_tag}'
                f'<div class="chunk-text">{highlighted}</div>'
                f'</div>'
            )

        # Metadaten aus erstem Chunk
        meta = doc["chunks"][0]["meta"]
        meta_parts = []
        for key in ("gericht", "datum", "aktenzeichen", "gesetz"):
            val = meta.get(key, "")
            if val:
                meta_parts.append(f"{key}: {_fix_mojibake(val)}")
        meta_parts.append(f"typ: {doc['source_type']}")
        meta_line = " | ".join(meta_parts)

        return (
            f'<details>'
            f'<summary>{summary}</summary>'
            f'{inner}'
            f'<div class="meta-line">{meta_line}</div>'
            f'</details>'
        )

    # Primärquellen
    nr = 1
    for doc in primary_docs:
        html += _render_doc(doc, nr, question)
        nr += 1

    # Hintergrundwissen
    if mw_docs:
        html += '<hr style="border:none;border-top:1px solid rgba(128,128,128,0.3);margin:10px 0">'
        html += '<h4 style="margin:6px 0">🟣 Hintergrundwissen</h4>'
        for doc in mw_docs:
            html += _render_doc(doc, nr, question)
            nr += 1

    # Validierung NACH den Quellen
    if validations:
        html += '<hr style="border:none;border-top:1px solid rgba(128,128,128,0.3);margin:10px 0">'
        nv = sum(1 for v in validations if v["level"] == "verified")
        nd = sum(1 for v in validations if v["level"] == "in_db_only")
        nm = sum(1 for v in validations if v["level"] == "missing")
        total = len(validations)

        html += f'<div class="val-box"><b>Normen-Check ({total} Zitate geprüft):</b><br>'
        if nv:
            html += f'✅ {nv} in Quellen gefunden &nbsp;'
        if nd:
            html += f'⚠️ {nd} nicht in Quellen &nbsp;'
        if nm:
            html += f'⚠️ {nm} nicht in DB'
        html += '<br><small style="color:#888">Prüft, ob vom Modell genannte Gesetze und Urteile in den abgerufenen Quellen vorkommen.</small>'
        html += '</div>'

        db_only = [v for v in validations if v["level"] == "in_db_only"]
        if db_only:
            html += '<details><summary>⚠️ Zitiert, aber nicht in Quellen</summary><ul>'
            for v in db_only[:6]:
                html += f'<li>{v["reference"]}</li>'
            html += '</ul></details>'

        missing = [v for v in validations if v["level"] == "missing"]
        if missing:
            html += '<details><summary>⚠️ Halluzinationsverdacht</summary><ul>'
            for v in missing[:6]:
                html += f'<li>{v["reference"]}</li>'
            html += '</ul></details>'

    html += '</div>'
    return html


def format_db_stats() -> str:
    """Formatiert die Datenbankstatistiken dynamisch aus ChromaDB."""
    raw = get_db_stats()
    # Aggregierte Kategorien
    gesetze = raw.get("gesetz", 0) + raw.get("gesetz_granular", 0)
    urteile = raw.get("urteil", 0) + raw.get("urteil_segmentiert", 0)
    leitlinien = raw.get("leitlinie", 0)
    mw = raw.get("methodenwissen", 0)
    gesamt = raw.get("GESAMT", 0)

    rows = [
        f"| 📘 Gesetze (Paragraphen + granular) | {gesetze:,} |",
        f"| 📗 Urteile (Volltexte + segmentiert) | {urteile:,} |",
        f"| 📙 Leitlinien & Behörden | {leitlinien:,} |",
        f"| 🟣 Methodenwissen | {mw:,} |",
        f"| **📦 Gesamt** | **{gesamt:,}** |",
    ]
    return "| Kategorie | Chunks |\n|---|---|\n" + "\n".join(rows)


# Chat-Funktion (Streaming-Generator)
def chat_stream(message: str, history: list[list[str]]):
    """Generator: Retrieval → LLM-Stream → Validation. Yields (partial_response, sources_md, chunks)."""

    # Retrieval (mit History-Kontext für Folgefragen)
    chunks = retrieve(message, history)
    context = format_context(chunks)
    sources_placeholder = format_sources(chunks, [], question=message) + '<p style="color:#888"><em>⏳ Validierung läuft nach Abschluss der Antwort...</em></p>'

    # Chat-History aufbereiten
    llm_history = []
    for user_msg, bot_msg in (history or []):
        llm_history.append({"role": "user", "content": user_msg})
        llm_history.append({"role": "assistant", "content": bot_msg})

    # LLM-Messages bauen
    messages = _build_llm_messages(message, context, llm_history)

    # Cascading Provider Stream
    full_response = ""
    model_label = ""
    ollama_warning_shown = False
    for token, provider_display in stream_with_fallback(messages):
        model_label = provider_display
        # FIX 2: Ollama-Warnung VOR der Antwort
        if not ollama_warning_shown and "Ollama" in provider_display:
            ollama_warning_shown = True
            full_response = ("⚠️ **Hinweis:** Diese Antwort wurde mit einem lokalen Modell "
                             f"({provider_display}) generiert. Die Qualität ist eingeschränkt. "
                             "Für bessere Ergebnisse setzen Sie `HF_TOKEN`, `OPENROUTER_KEY` "
                             "oder `MISTRAL_KEY`.\n\n---\n\n")
        full_response += token
        yield full_response, sources_placeholder, chunks

    if not full_response.strip():
        fallback = _sources_fallback("⚠️ **Kein LLM-Provider erreichbar.**\n\n", chunks)
        yield fallback, sources_placeholder, chunks
        return

    # FIX 1: Abgeschnittene Antworten erkennen und Hinweis anfügen
    _TRUNCATION_NOTICE = ("Die Antwort wurde aus Platzgründen gekürzt. "
                          "Für eine vollständige Analyse stellen Sie bitte eine "
                          "spezifischere Frage.")
    stripped = full_response.rstrip()
    if (stripped and stripped[-1] not in ".!?:)\u201d\u201c*_`"
            and _TRUNCATION_NOTICE not in full_response):
        full_response += f"\n\n---\n*{_TRUNCATION_NOTICE}*"
        yield full_response, sources_placeholder, chunks

    # Validierung nach komplettem Streaming
    validations = validate_response(full_response, chunks)

    # Post-Processing: Normen die NICHT in den Quellen stehen inline markieren
    for v in validations:
        if v["level"] == "missing" and v["reference"] in full_response:
            full_response = full_response.replace(
                v["reference"],
                f'{v["reference"]} ⚠️*(nicht in den bereitgestellten Quellen – möglicherweise fehlerhaft)*',
                1,
            )

    sources_md = format_sources(chunks, validations, question=message)
    n_docs = len(group_chunks_to_docs(chunks))
    full_response += f"\n\n---\n*Modell: {model_label} | {n_docs} Dokumente ({len(chunks)} Chunks) | {len(validations)} Referenzen validiert*"
    yield full_response, sources_md, chunks


def _sources_fallback(prefix: str, chunks: list[dict]) -> str:
    """Erzeugt eine Antwort mit Quellen wenn kein LLM verfügbar ist."""
    response = prefix + "---\n\n**Gefundene Quellen zum Thema:**\n\n"
    for i, chunk in enumerate(chunks[:5], 1):
        meta = chunk["meta"]
        label = meta.get("volladresse") or meta.get("thema") or meta.get("paragraph") or ""
        response += f"{i}. {label}: {chunk['text'][:200]}...\n\n"
    return response


def build_app() -> gr.Blocks:
    """Erstellt die Gradio-App."""

    db_stats_md = format_db_stats()
    provider_status = get_provider_status()

    with gr.Blocks(
        title="OpenLex – Datenschutzrecht MVP",
    ) as app:
        gr.Markdown(
            "# ⚖️ OpenLex – Datenschutzrecht MVP\n"
            "*Open-Source Rechts-KI für deutsches und europäisches Datenschutzrecht*",
            elem_id="openlex-header",
        )

        with gr.Row():
            # ── Links: Chat (70%) ──
            with gr.Column(scale=7):
                chatbot = gr.Chatbot(
                    label="Chat",
                    height=550,
                )
                msg_input = gr.Textbox(
                    placeholder="Ihre datenschutzrechtliche Frage...",
                    label="Frage",
                    lines=2,
                    show_label=False,
                )
                with gr.Row():
                    submit_btn = gr.Button("📤 Fragen", variant="primary")
                    clear_btn = gr.Button("🔄 Neues Gespräch")

                # Kopierbare letzte Antwort
                with gr.Accordion("📋 Letzte Antwort (kopierbar)", open=False):
                    last_answer = gr.Markdown(
                        value="*Hier erscheint die letzte Antwort als kopierbarer Text.*",
                        elem_id="last-answer",
                    )

                gr.Examples(
                    examples=[
                        "Darf mein Arbeitgeber meine E-Mails lesen?",
                        "Ist Videoüberwachung im Laden nach Art. 6 Abs. 1 lit. f DSGVO zulässig?",
                        "Was sind die Voraussetzungen für eine wirksame Einwilligung?",
                        "Wie hat der EuGH den Schadensersatz nach Art. 82 DSGVO ausgelegt?",
                        "Darf ich als Unternehmen Daten in die USA übermitteln?",
                        "Was sagt die DSK zu Microsoft 365?",
                    ],
                    inputs=msg_input,
                    label="Beispiel-Fragen",
                )

            # ── Rechts: Quellen (30%) ──
            with gr.Column(scale=3):
                sources_display = gr.HTML(
                    value='<div style="padding:8px"><h3>📚 Quellen</h3><p><em>Stellen Sie eine Frage um Quellen zu sehen.</em></p></div>',
                )

        # ── Disclaimer ──
        gr.Markdown(
            '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:6px;padding:8px 12px;margin:8px 0;font-size:13px;color:#856404">'
            'OpenLex ist ein Recherche-Werkzeug, keine Rechtsberatung und derzeit noch in einem frühen Teststadium. '
            'Fehler werden kommen. Meldet sie uns gerne.</div>'
        )

        # ── Unten: Provider-Status + DB-Statistiken ──
        gr.Markdown(f"*{provider_status}*")
        with gr.Accordion("📊 Datenbankstatistiken", open=False):
            gr.Markdown(db_stats_md)

        # ── Footer ──
        gr.Markdown(
            '<div style="text-align:center;color:#888;font-size:12px;padding:12px 0;border-top:1px solid #e0e0e0;margin-top:12px">'
            'OpenLex – Open Source Legal AI für Datenschutzrecht | '
            '<a href="mailto:contact@open-lex.cloud" style="color:#888">contact@open-lex.cloud</a> | '
            '<a href="https://open-lex.cloud" style="color:#888" target="_blank">open-lex.cloud</a></div>'
        )

        # ── Event-Handler (Streaming) ──
        def respond(message, chat_history):
            if not message.strip():
                yield chat_history, "", "", ""
                return

            # Gradio 6: chat_history is list[dict] with role/content
            history_tuples = []
            if chat_history:
                user_msg = None
                for msg in chat_history:
                    role = msg.get("role", "") if isinstance(msg, dict) else ""
                    content = msg.get("content", "") if isinstance(msg, dict) else ""
                    if role == "user":
                        user_msg = content
                    elif role == "assistant" and user_msg:
                        history_tuples.append((user_msg, content))
                        user_msg = None

            # Ladeindikator als temporäre Bot-Antwort
            chat_history = list(chat_history or [])
            chat_history.append({"role": "user", "content": message})
            chat_history.append({"role": "assistant", "content": "⏳ *OpenLex recherchiert...*"})
            yield chat_history, "", "", ""

            # Stream tokens
            for partial_response, sources_md, chunks in chat_stream(message, history_tuples):
                chat_history[-1]["content"] = partial_response
                yield chat_history, sources_md, partial_response, ""

        submit_btn.click(
            respond,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, sources_display, last_answer, msg_input],
        )

        msg_input.submit(
            respond,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, sources_display, last_answer, msg_input],
        )

        _SOURCES_EMPTY = '<div style="padding:8px"><h3>📚 Quellen</h3><p><em>Stellen Sie eine Frage um Quellen zu sehen.</em></p></div>'
        clear_btn.click(
            lambda: ([], _SOURCES_EMPTY,
                     "*Hier erscheint die letzte Antwort als kopierbarer Text.*", ""),
            outputs=[chatbot, sources_display, last_answer, msg_input],
        )

    return app


# ═══════════════════════════════════════════════════════════════════════════
# Start
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("OpenLex – Datenschutzrecht MVP")
    print("=" * 60)
    print(f"\n  ChromaDB: {CHROMADB_DIR}")
    print(f"  Collection: {COLLECTION_NAME}")
    print(f"  Embedding-Modell: {MODEL_NAME}")
    print(f"\n  Lade Modell und Datenbank ...")

    # Vorladen
    get_model()
    get_reranker()
    col = get_collection()
    print(f"  ChromaDB: {col.count()} Chunks geladen.")
    print(f"  Reranker: {RERANKER_MODEL}")
    _load_urteilsnamen()

    # Provider-Status
    print(f"\n  {get_provider_status()}")

    print(f"\n  Starte Gradio auf http://0.0.0.0:7860 ...")
    print("=" * 60)

    app = build_app()
    app.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        root_path=os.environ.get("GRADIO_ROOT_PATH", ""),
        theme=gr.themes.Soft(),
        css="""
        * { font-family: 'DM Sans', Arial, Helvetica, sans-serif !important; }
        .source-panel { max-height: 80vh; overflow-y: auto; }
        footer { display: none !important; }
        /* Full-width in iframe: remove all Gradio container constraints */
        .gradio-container { max-width: 100% !important; width: 100% !important; padding: 0 !important; margin: 0 !important; }
        .gradio-container > .main { padding: 0 !important; margin: 0 !important; }
        .gradio-container > .main > .wrap { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
        .contain { max-width: 100% !important; padding: 0 !important; }
        /* Hide header — shown via landing page context already */
        #openlex-header { display: none !important; }
        .message, .message p, .message span, .message li, .message code,
        .message h1, .message h2, .message h3, .message h4,
        .bot, .user, [class*="message"] {
            user-select: text !important;
            -webkit-user-select: text !important;
            -moz-user-select: text !important;
            cursor: text !important;
            font-size: 14px !important;
        }
        .message h1, .message h2, .message h3, .message h4 {
            font-weight: bold !important;
            margin: 8px 0 4px 0 !important;
        }
        #last-answer { max-height: 60vh; overflow-y: auto; padding: 12px;
            border: 1px solid #e0e0e0; border-radius: 8px; }
        #last-answer * { font-size: 14px !important; }
        """,
    )
