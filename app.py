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
import subprocess
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
OLLAMA_MODELS = ["gemma4:e4b"]
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

ZWINGENDE FORMATIERUNG:
- Verwende KEINE horizontalen Trennlinien (---).
- Nummerierung IMMER in dieser Hierarchie: Oberste Ebene: I., II., III. Darunter: 1., 2., 3. Darunter: a), b), c). Darunter: (1), (2), (3). Verwende NIEMALS andere Nummerierungsformate. Auch einzelne Aufzählungen beginnen mit I., II., III.
- Verwende Fließtext statt überflüssiger Zwischenüberschriften.

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
    r"(?:Art(?:ikel)?\.?\s*)\d+\s*"
    r"(?:(?:Abs(?:atz)?\.?\s*)\d+\s*)?"
    r"(?:(?:lit\.?\s*[a-z]|Buchst(?:abe)?\.?\s*[a-z]|Nr\.?\s*\d+)\s*)?"
    r"(?:(?:UAbs\.?\s*\d+|S(?:atz)?\.?\s*\d+)\s*)?"
    r"(?:DSGVO|DS-GVO|GDPR|GRCh|AEUV|BDSG|TDDDG|TTDSG|TKG|SGB|AO|BetrVG|KUG|GG)"
    r"|(?:§§?|Paragraph)\s*\d+[a-z]?\s*"
    r"(?:(?:Abs(?:atz)?\.?\s*)\d+\s*)?"
    r"(?:(?:S(?:atz)?\.?\s*\d+|Nr\.?\s*\d+)\s*)?"
    r"(?:DSGVO|BDSG|TDDDG|TTDSG|TKG|SGB|AO|BetrVG|KUG|GG|StGB|ZPO|BGB)",
    re.UNICODE,
)

# Aktenzeichen
AZ_RE = re.compile(
    r"(?:(?:Rechtssache|Rs\.?|Az\.?)\s+)?"
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
        urteile_az: set[str] = set()
        leitlinien_titel: set[str] = set()
        for meta in sample["metadatas"]:
            st = meta.get("source_type", "unbekannt")
            counts[st] = counts.get(st, 0) + 1
            # Count unique documents
            if st in ("urteil", "urteil_segmentiert"):
                az = meta.get("aktenzeichen", "")
                if az:
                    urteile_az.add(az)
            elif st == "leitlinie":
                titel = meta.get("titel", "")
                if titel:
                    leitlinien_titel.add(titel)
        # Scale up if sampled
        if len(sample["metadatas"]) < total:
            scale = total / len(sample["metadatas"])
            counts = {k: int(v * scale) for k, v in counts.items()}
        counts["GESAMT"] = total
        counts["urteile_docs"] = len(urteile_az)
        counts["leitlinien_docs"] = len(leitlinien_titel)
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
        ("id:seg_eugh_c_582_14_tenor", None),
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
    "oeffnungsklausel": [
        ("id:mw_vollharmonisierung_oeffnungsklauseln", None),
        ("Art. 88", "gesetz_granular"),
    ],
    "unmittelbar": [
        ("id:mw_unmittelbare_geltung_dsgvo", None),
    ],
    "erlaubnisvorbehalt": [
        ("id:mw_verbot_mit_erlaubnisvorbehalt", None),
        ("Verarbeitung ist nur rechtmäßig", "gesetz_granular"),
    ],
    "anonymisierung": [
        ("Art. 4 Nr. 5", "gesetz_granular"),              # Definition Pseudonymisierung
        ("Erwägungsgrund 26", "eg_granular"),               # Anonymisierung / Personenbezug
        ("Erwägungsgrund 28", "eg_granular"),               # Pseudonymisierung
        ("Erwägungsgrund 29", "eg_granular"),               # Pseudonymisierung Zusatzinfo
        ("Art. 25", "gesetz_granular"),                     # Privacy by Design (Pseudonymisierung)
        ("Art. 32 Abs. 1 lit. a", "gesetz_granular"),      # Pseudonymisierung als TOM
        ("Art. 89", "gesetz_granular"),                     # Forschung + Pseudonymisierung
    ],
}

# Keyword → Themen-Schlüssel
THEMEN_KEYWORDS_MAP: list[tuple[list[str], str]] = [
    (["usa", "amerika", "drittland", "transfer", "cloud", "dpf", "schrems", "privacy shield", "safe harbor", "angemessenheitsbeschluss"], "drittland"),
    (["videoüberwachung", "videoueberwachung", "kamera", "überwachungskamera", "cctv", "bodycam", "dashcam"], "video"),
    (["videoüberwachung", "videoueberwachung", "kamera", "überwachungskamera", "cctv", "bodycam", "dashcam"], "video_edpb"),
    (["cookie", "banner", "tracking"], "cookie"),
    (["einwilligung", "consent", "opt-in", "opt in", "newsletter", "e-mail-werbung", "double opt"], "einwilligung"),
    (["arbeitgeber", "beschäftigte", "beschaeftigte", "arbeitsplatz", "betriebsvereinbarung",
      "mitarbeiter", "e-mail lesen", "e-mails lesen"], "beschaeftigt"),
    (["schadensersatz", "schaden", "art. 82"], "schaden"),
    (["dsfa", "folgenabschätzung", "folgenabschaetzung", "datenschutz-folgenabschätzung"], "dsfa"),
    (["personenbezogene daten", "definition", "definiert",
      "begriff", "begriffsbestimmung"], "definition"),
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
      "kontopflicht", "kontenzwang", "registrierungspflicht", "gastzugang",
      "account löschen", "konto löschen", "account loeschen"], "kundenkonto"),
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
    (["öffnungsklausel", "oeffnungsklausel", "vollharmonisierung",
      "spielraum", "strenger als die dsgvo", "nationales recht"], "oeffnungsklausel"),
    (["unmittelbar", "anwendungsvorrang", "vorrang", "direkt geltend",
      "umsetzung", "gilt unmittelbar", "direkt anwendbar"], "unmittelbar"),
    (["erlaubnisvorbehalt", "grundsätzlich verboten", "grundsaetzlich verboten",
      "verarbeitungsverbot"], "erlaubnisvorbehalt"),
    (["anonymisierung", "anonymisieren", "anonymisiert", "pseudonymisierung",
      "pseudonymisieren", "pseudonym", "de-identifikation", "k-anonymität",
      "differential privacy", "personenbezug aufheben"], "anonymisierung"),
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
                    "id": cid,
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
# ---------------------------------------------------------------------------
# Provider 2: OpenRouter (OpenAI-kompatibel, Fallback)
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
# Provider 1: Mistral API (OpenAI-kompatibel, primär)
# ---------------------------------------------------------------------------

_MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
_MISTRAL_MODEL = "mistral-medium-latest"


def _mistral_available() -> bool:
    return bool(MISTRAL_KEY)


def _stream_mistral(messages: list[dict]):
    """Streamt von Mistral. Yields Strings. Raises bei Fehler."""
    yield from _stream_openai_compat(
        _MISTRAL_URL, MISTRAL_KEY, _MISTRAL_MODEL, messages,
    )


# ---------------------------------------------------------------------------
# Provider 3: Lokales Ollama (Fallback)
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
        "name": "Mistral",
        "display": "Mistral Medium via Mistral",
        "is_available": _mistral_available,
        "stream": _stream_mistral,
    },
    {
        "name": "OpenRouter",
        "display": "Qwen3-235B via OpenRouter",
        "is_available": _openrouter_available,
        "stream": _stream_openrouter,
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
           "- MISTRAL_KEY setzen für Mistral\n"
           "- OPENROUTER_KEY setzen für OpenRouter\n"
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

    def _normalize_ref(text: str) -> str:
        """Normalisiert Norm- und AZ-Referenzen für Vergleich."""
        t = text.lower()
        t = t.replace("ds-gvo", "dsgvo").replace("ds gvo", "dsgvo")
        # Norm-Synonyme: "Artikel" → "art.", "Paragraph" → "§", "Absatz" → "abs.", "Buchstabe" → "lit."
        t = re.sub(r"\bartikel\s+", "art. ", t)
        t = re.sub(r"\bparagraph\s+", "§ ", t)
        t = re.sub(r"\babsatz\s+", "abs. ", t)
        t = re.sub(r"\bbuchstabe\s+", "lit. ", t)
        # "Abs " ohne Punkt → "Abs. "
        t = re.sub(r"\babs\s+", "abs. ", t)
        # Leerzeichen nach Art./§ normalisieren: "Art.17" → "Art. 17", "Art.  17" → "Art. 17"
        t = re.sub(r"(art\.?)\s*(\d)", r"art. \2", t)
        t = re.sub(r"(§§?)\s*(\d)", r"§ \2", t)
        # AZ-Präfixe entfernen (Gerichts- und Verfahrensbezeichnungen)
        _az_prefixes = (
            r"rechtssache", r"rs\.?", r"az\.?", r"urteil\s+vom\s+[\d.]+\s*[-–—]?\s*",
            r"beschluss\s+vom\s+[\d.]+\s*[-–—]?\s*",
            r"eugh", r"bgh", r"bverfg", r"bag", r"bverwg", r"bsg",
            r"olg", r"lg", r"ag", r"vg", r"vgh", r"lag",
        )
        for prefix in _az_prefixes:
            t = re.sub(rf"\b{prefix}\s*[,:]?\s*", "", t)
        # Mehrfach-Leerzeichen
        t = re.sub(r"\s+", " ", t)
        return t.strip()

    # Kontext-Texte für Stufe-1-Prüfung (war es in den übergebenen Quellen?)
    # a) Label/Metadaten-Suche (schnell, exakt)
    ctx_meta = _normalize_ref(" ".join(
        str(c["meta"].get("volladresse", "")) + " " +
        str(c["meta"].get("aktenzeichen", "")) + " " +
        str(c["meta"].get("thema", "")) + " " +
        str(c["meta"].get("chunk_id", ""))
        for c in chunks
    ))
    # b) Volltext-Suche (fängt granulare Referenzen in übergeordneten Artikeln ab)
    ctx_fulltext = _normalize_ref(" ".join(c["text"] for c in chunks))

    # FIX 2: Gesetze die NICHT in der Datenschutz-DB sind → "external" statt "missing"
    _EXTERN_GESETZE = {"BGB", "HGB", "StGB", "ZPO", "GG", "AktG", "GmbHG",
                       "InsO", "UWG", "MarkenG", "UrhG", "PatG", "VwGO",
                       "VwVfG", "SGG", "ArbGG", "BetrVG", "KSchG", "AGG"}

    def _is_extern_gesetz(ref: str) -> bool:
        """Prüft ob eine Norm aus einem Gesetz stammt das nicht in der DS-DB ist."""
        ref_upper = ref.upper()
        for g in _EXTERN_GESETZE:
            if ref_upper.endswith(g) or f" {g} " in ref_upper or f" {g})" in ref_upper:
                return True
        return False

    def _hierarchy_variants(ref: str) -> list[str]:
        """Erzeugt hierarchische Fallback-Varianten einer Normreferenz.

        'Art. 13 Abs. 2 lit. e DSGVO' → ['Art. 13 Abs. 2 DSGVO', 'Art. 13 DSGVO']
        """
        variants = []
        r = ref
        # Schritt 1: lit./Buchst. entfernen
        stripped = re.sub(r"\s*(?:lit\.?|Buchst(?:abe)?\.?)\s*[a-z]\s*", " ", r)
        if stripped != r:
            variants.append(re.sub(r"\s+", " ", stripped).strip())
        # Schritt 2: Abs. entfernen
        stripped2 = re.sub(r"\s*Abs(?:atz)?\.?\s*\d+\s*", " ", stripped if stripped != r else r)
        if stripped2 != r and stripped2 not in variants:
            variants.append(re.sub(r"\s+", " ", stripped2).strip())
        return variants

    def _check(ref: str, ref_type: str, db_threshold: float) -> dict:
        ref_normalized = _normalize_ref(ref)
        # Stufe 1a: Label/Metadaten-Match
        in_context = ref_normalized in ctx_meta
        # Stufe 1b: Volltext-Match (z.B. "Art. 7 Abs. 3" im Text von Quelle "Art. 7 DSGVO")
        if not in_context:
            in_context = ref_normalized in ctx_fulltext
        # FIX 1: Hierarchischer Fallback (lit. → Abs. → Art.)
        if not in_context and ref_type == "norm":
            for variant in _hierarchy_variants(ref):
                v_norm = _normalize_ref(variant)
                if v_norm in ctx_meta or v_norm in ctx_fulltext:
                    in_context = True
                    break

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
            # 3) Hierarchische Keyword-Suche
            if not in_db and ref_type == "norm":
                for variant in _hierarchy_variants(ref):
                    try:
                        kw = col.get(where_document={"$contains": variant}, limit=1, include=[])
                        if kw["ids"]:
                            in_db = True
                            break
                    except Exception:
                        pass
        else:
            in_db = True  # Wenn in Kontext, dann sicher auch in DB

        if in_context:
            level = "verified"
        elif in_db:
            level = "in_db_only"
        elif ref_type == "norm" and _is_extern_gesetz(ref):
            level = "external"
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
.src-panel details{margin:4px 0;padding:8px 10px;border-radius:8px;background:rgba(255,255,255,0.03);border:1px solid #2a2a30}
.src-panel summary{cursor:pointer;font-weight:500;font-size:13px;padding:2px 0;color:#e0e0e0}
.src-panel summary::-webkit-details-marker{color:#6b6b70}
.src-panel mark{background:rgba(212,168,67,0.25);color:#d4a843;padding:0 2px;border-radius:2px}
.src-panel .highlight-query{background:rgba(88,214,141,0.15);color:#58d68d;padding:0 2px;border-radius:2px}
.src-panel .meta-line{color:#6b6b70;font-size:11px;margin-top:4px;border-top:1px solid #2a2a30;padding-top:4px}
.src-panel .chunk-text{font-size:12px;line-height:1.5;padding:6px 0;white-space:pre-wrap;word-break:break-word;color:#8a8a8f}
.src-panel .val-box{padding:8px 12px;border-radius:8px;background:rgba(255,255,255,0.03);margin:6px 0;border:1px solid #2a2a30;color:#e0e0e0;font-size:13px}
.src-panel .val-box small{color:#6b6b70}
.src-panel .sub-chunk{margin:4px 0 4px 12px;padding:4px 6px;border-left:2px solid #2a2a30}
</style>"""

    html = f'{css}<div class="src-panel"><h3>QUELLEN</h3>'

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
            f'<details id="quelle-{doc_nr}" data-quelle="{doc_nr}">'
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
        html += '<h4 style="margin:6px 0">🟣 Methodenwissen</h4>'
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

        external = [v for v in validations if v["level"] == "external"]
        if external:
            html += '<details><summary>📘 Ergänzende Normen (nicht in Datenschutz-DB)</summary><ul>'
            for v in external[:6]:
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
                             "Für bessere Ergebnisse setzen Sie `MISTRAL_KEY` "
                             "oder `OPENROUTER_KEY`.\n\n---\n\n")
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


PWA_HEAD = (
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
    '<link rel="manifest" href="/static/manifest.json">'
    '<link rel="apple-touch-icon" href="/static/apple-touch-icon.png">'
    '<meta name="apple-mobile-web-app-capable" content="yes">'
    '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
    '<meta name="apple-mobile-web-app-title" content="OpenLex">'
    '<meta name="theme-color" content="#111114">'
    '<meta property="og:title" content="OpenLex – Datenschutzrecht">'
    '<meta property="og:description" content="Open-Source Rechts-KI für europäisches Datenschutzrecht">'
    '<meta property="og:type" content="website">'
    '<meta property="og:url" content="https://app.open-lex.cloud">'
    '<meta name="description" content="Open-Source Rechts-KI für europäisches Datenschutzrecht">'
    '<meta name="application-name" content="OpenLex">'
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,700;1,8..60,400&display=swap" rel="stylesheet">'
    '<script>if(window.self !== window.top){document.documentElement.classList.add("in-iframe")}</script>'
    '<script>'
    '(function(){'
    '  function linkAll(){'
    '    var cb=document.getElementById("ol-chatbot");'
    '    if(!cb)return;'
    '    var re=/\\[Quelle[ns]?\\s+(\\d+)[^\\]]*\\]/g;'
    '    var w=document.createTreeWalker(cb,NodeFilter.SHOW_TEXT,null);'
    '    var ns=[];'
    '    while(w.nextNode()){'
    '      var tn=w.currentNode;'
    '      if(tn.parentNode.closest&&tn.parentNode.closest(".quelle-link"))continue;'
    '      if(re.test(tn.nodeValue)){re.lastIndex=0;ns.push(tn);}'
    '    }'
    '    ns.forEach(function(tn){'
    '      var h=tn.nodeValue.replace(/\\[Quelle[ns]?\\s+(\\d+)([^\\]]*)\\]/g,function(full,num){'
    '        return "<a class=\\"quelle-link\\" data-qn=\\""+num+"\\">[Quelle "+num+"]</a>";'
    '      });'
    '      if(h!==tn.nodeValue){'
    '        var sp=document.createElement("span");sp.innerHTML=h;'
    '        tn.parentNode.replaceChild(sp,tn);'
    '      }'
    '    });'
    '  }'
    '  document.addEventListener("click",function(e){'
    '    var a=e.target.closest&&e.target.closest(".quelle-link");'
    '    if(!a)return;'
    '    e.preventDefault();'
    '    var n=a.getAttribute("data-qn");'
    '    var cb=document.getElementById("ol-chatbot");'
    '    if(!cb)return;'
    '    var det=cb.querySelector("details.src-collapse");'
    '    if(det)det.open=true;'
    '    var el=cb.querySelector("#quelle-"+n)||cb.querySelector("[data-quelle=\\""+n+"\\"]");'
    '    if(el){el.open=true;setTimeout(function(){el.scrollIntoView({behavior:"smooth",block:"center"});},100);}'
    '  });'
    '  setInterval(linkAll,800);'
    '})();'
    '</script>'
)


def build_app() -> gr.Blocks:
    """Erstellt die Gradio-App im Clean Chat Layout."""

    provider_status = get_provider_status()
    raw_stats = get_db_stats()
    total_chunks = raw_stats.get("GESAMT", 0)
    urteile_docs = raw_stats.get("urteile_docs", 0)
    leitlinien_docs = raw_stats.get("leitlinien_docs", 0)
    mw_chunks = raw_stats.get("methodenwissen", 0)

    try:
        _git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        _git_hash = "unknown"

    # ── Beispielfragen ──
    EXAMPLES = [
        "Darf mein Arbeitgeber meine E-Mails lesen?",
        "Was sind die Voraussetzungen für eine wirksame Einwilligung?",
        "Wie hat der EuGH den Schadensersatz nach Art. 82 DSGVO ausgelegt?",
        "Darf ich als Unternehmen Daten in die USA übermitteln?",
        "Ist Videoüberwachung im Laden zur Diebstahlprävention zulässig?",
    ]

    FILL_JS = (
        "document.querySelector('#msg-input textarea').value=this.textContent;"
        "document.querySelector('#msg-input textarea').dispatchEvent(new Event('input',{bubbles:true}));"
    )
    CLOSE_MENU = (
        "document.getElementById('menu-panel').classList.add('menu-closed');"
        "document.getElementById('menu-backdrop').classList.add('menu-closed');"
    )
    TOGGLE_MENU = (
        "document.getElementById('menu-panel').classList.toggle('menu-closed');"
        "document.getElementById('menu-backdrop').classList.toggle('menu-closed');"
    )

    eq_welcome = "\n".join(
        f'<button class="eq" onclick="{FILL_JS}">{q}</button>'
        for q in EXAMPLES
    )
    eq_menu = "\n".join(
        f'<button class="menu-eq" onclick="{FILL_JS}{CLOSE_MENU}">{q}</button>'
        for q in EXAMPLES
    )

    WELCOME_HTML = f"""<div id="welcome-screen">
<h1 class="welcome-title">Datenschutzrecht<br><span class="gold">recherchieren.</span></h1>
<p class="welcome-sub">Quellenbasierte Antworten zum europäischen Datenschutzrecht.</p>
<div class="example-questions">{eq_welcome}</div>
</div>"""

    COPY_JS = (
        "var el=document.querySelector('#copy-store textarea');"
        "if(el&&el.value){navigator.clipboard.writeText(el.value)"
        ".then(function(){alert('Kopiert!')})}"
        "else{alert('Noch keine Antwort vorhanden')};"
    )

    HEADER_MENU_HTML = (
        '<div id="ol-header">'
        '<div class="ol-brand"><span class="ol-open">Open</span><span class="ol-lex">Lex</span></div>'
        f'<div class="ol-hamburger" onclick="{TOGGLE_MENU}">\u2630</div>'
        '</div>'
        '<div id="menu-panel" class="menu-closed">'
        '<div class="menu-top">'
        '<span class="menu-title">Menu</span>'
        f'<span class="menu-close" onclick="{CLOSE_MENU}">\u2715</span>'
        '</div>'
        '<div class="menu-body">'
        '<div class="menu-section">'
        '<div class="menu-label">BEISPIELFRAGEN</div>'
        f'{eq_menu}'
        '</div>'
        '<div class="menu-section">'
        f'<button class="menu-action" onclick="document.querySelector(\'#clear-trigger\').click();{CLOSE_MENU}">\U0001f504 Neues Gespräch</button>'
        f'<button class="menu-action" onclick="{COPY_JS}{CLOSE_MENU}">\U0001f4cb Letzte Antwort kopieren</button>'
        '</div>'
        '<div class="menu-section">'
        '<button class="menu-action" onclick="'
        "document.getElementById('legal-overlay').style.display='flex';"
        "document.getElementById('menu-panel').classList.add('menu-closed');"
        "document.getElementById('menu-backdrop').classList.add('menu-closed');"
        '">\U0001f4c4 Impressum / Rechtliches</button>'
        '<a class="menu-link" href="https://open-lex.cloud" target="_blank">\U0001f310 open-lex.cloud</a>'
        '</div>'
        f'<div class="menu-stats">{urteile_docs} Urteile \u00b7 {leitlinien_docs} Leitlinien \u00b7 {mw_chunks}x Methodenwissen \u00b7 {total_chunks:,} Chunks<br>Commit: {_git_hash}</div>'
        '</div>'
        '</div>'
        f'<div id="menu-backdrop" class="menu-closed" onclick="{CLOSE_MENU}"></div>'
        '<div id="legal-overlay" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;z-index:2000;background:#111114;flex-direction:column">'
        '<div style="display:flex;align-items:center;justify-content:space-between;padding:calc(env(safe-area-inset-top,0px) + 12px) 16px 10px;border-bottom:1px solid #2a2a30;background:#111114">'
        '<span style="color:#e0e0e0;font-size:0.95rem;font-weight:600">Impressum / Rechtliches</span>'
        '<button style="color:#d4a843;font-size:1.5rem;cursor:pointer;padding:8px 12px;background:none;border:none;-webkit-tap-highlight-color:transparent" '
        'onclick="document.getElementById(\'legal-overlay\').style.display=\'none\'">\u2715</button>'
        '</div>'
        '<iframe src="/rechtliches?embed=1" style="flex:1;border:none;width:100%;height:100%;background:#111114"></iframe>'
        '</div>'
    )

    _SRC_STYLE_RE = re.compile(r'<style>.*?</style>', re.DOTALL)

    with gr.Blocks(
        title="OpenLex \u2013 Datenschutzrecht",
        elem_id="openlex-app",
    ) as app:

        # ── Header + Menu ──
        gr.HTML(HEADER_MENU_HTML)

        # ── Welcome ──
        welcome = gr.HTML(value=WELCOME_HTML, elem_id="welcome-container")

        # ── Chat ──
        chatbot = gr.Chatbot(
            height=600,
            elem_id="ol-chatbot",
            show_label=False,
            autoscroll=False,
        )

        # ── Footer ──
        gr.HTML(
            '<div id="ol-footer">'
            'Testphase \u00b7 KI kann Fehler machen \u00b7 Keine Rechtsberatung'
            '</div>'
        )

        # ── Input (fixed at bottom via CSS) ──
        with gr.Row(elem_id="input-row"):
            msg_input = gr.Textbox(
                placeholder="Frage eingeben...",
                label="",
                lines=1,
                show_label=False,
                elem_id="msg-input",
                scale=8,
            )
            submit_btn = gr.Button("\u279c", variant="primary", elem_id="submit-btn", scale=1)

        # ── Hidden ──
        clear_trigger = gr.Button("", visible=False, elem_id="clear-trigger")
        copy_store = gr.Textbox(value="", visible=False, elem_id="copy-store")

        # ── Event-Handler (Streaming) ──
        def respond(message, chat_history):
            if not message.strip():
                yield chat_history, "", "", WELCOME_HTML
                return

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

            chat_history = list(chat_history or [])
            chat_history.append({"role": "user", "content": message})
            chat_history.append({"role": "assistant", "content": "\u23f3 *OpenLex recherchiert...*"})
            yield chat_history, "", "", ""

            for partial_response, sources_md, chunks in chat_stream(message, history_tuples):
                full_msg = partial_response
                if sources_md:
                    clean_src = _SRC_STYLE_RE.sub('', sources_md)
                    full_msg += '\n\n<details class="src-collapse"><summary>\U0001f4da Quellen anzeigen</summary>\n\n' + clean_src + '\n\n</details>'
                chat_history[-1]["content"] = full_msg
                yield chat_history, partial_response, "", ""

        submit_btn.click(
            respond,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, copy_store, msg_input, welcome],
        )
        msg_input.submit(
            respond,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, copy_store, msg_input, welcome],
        )
        clear_trigger.click(
            lambda: ([], "", "", WELCOME_HTML),
            outputs=[chatbot, copy_store, msg_input, welcome],
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
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        root_path=os.environ.get("GRADIO_ROOT_PATH", ""),
        favicon_path=os.path.join(static_dir, "apple-touch-icon.png"),
        allowed_paths=[static_dir],
        head=PWA_HEAD,
        css="""
        /* ═══ OpenLex Clean Chat ═══ */
        :root {
            --bg: #111114; --surface: #16161a; --border: #2a2a30;
            --gold: #d4a843; --text: #e0e0e0; --dim: #6b6b70;
        }

        /* ── Base ── */
        html, body, .gradio-container { background: var(--bg) !important; color: var(--text) !important;
            overflow-x: hidden !important; max-width: 100vw !important; overscroll-behavior-x: none !important; }
        * { font-family: 'Outfit', system-ui, sans-serif !important; }
        h1, h2, h3, h4, .welcome-title { font-family: 'Source Serif 4', Georgia, serif !important; }

        /* ── Kill Gradio defaults ── */
        footer, .built-with, a[href*="gradio.app"], .footer-links { display: none !important; }
        .gradio-container { max-width: 100% !important; margin: 0 !important; padding: 0 !important; }
        .contain { max-width: 100% !important; }
        .block { background: transparent !important; border: none !important; box-shadow: none !important; }
        .panel { background: transparent !important; border: none !important; }
        .main, .main.fillable { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
        .wrap, .wrapper, .bubble-wrap, .chatbot, #ol-chatbot > *,
        #ol-chatbot > * > *, #ol-chatbot > * > * > * {
            background: transparent !important; border: none !important;
            box-shadow: none !important; border-radius: 0 !important; }
        #ol-chatbot > .wrap { overflow: visible !important; height: 100% !important; }
        #ol-chatbot .bubble-wrap { padding: 0 !important; }

        /* ── Header ── */
        #ol-header {
            position: fixed; top: 0; left: 0; right: 0;
            display: flex; align-items: center; justify-content: space-between;
            padding: calc(env(safe-area-inset-top, 0px) + 8px) 24px 8px;
            background: var(--bg);
            border-bottom: 1px solid var(--border);
            z-index: 50; pointer-events: auto !important;
        }
        .ol-brand { font-family: 'Source Serif 4', Georgia, serif !important;
                     font-size: 1.2rem; font-weight: 700; letter-spacing: -0.5px; }
        .ol-open { color: #fff; }
        .ol-lex { color: var(--gold); }
        .ol-hamburger { color: var(--gold); font-size: 1.4rem; cursor: pointer;
                        padding: 4px 8px; user-select: none; pointer-events: auto !important; position: relative; z-index: 100; }
        .ol-hamburger:hover { color: #e0b84e; }

        /* ── Hamburger Menu ── */
        #menu-panel {
            position: fixed; top: 0; right: 0; width: 320px; height: 100vh;
            background: var(--surface); border-left: 1px solid var(--border);
            z-index: 1000; transform: translateX(0);
            transition: transform 0.3s ease; overflow-y: auto;
            pointer-events: auto !important;
        }
        #menu-panel.menu-closed { transform: translateX(100%); }
        #menu-backdrop {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5); z-index: 999;
        }
        #menu-backdrop.menu-closed { display: none; }
        .menu-top { display: flex; justify-content: space-between; align-items: center;
                     padding: 14px 20px; border-bottom: 1px solid var(--border); }
        .menu-title { color: var(--text); font-weight: 600; }
        .menu-close { color: var(--dim); font-size: 1.3rem; cursor: pointer; }
        .menu-close:hover { color: var(--text); }
        .menu-body { padding: 16px 20px; }
        .menu-section { margin-bottom: 20px; }
        .menu-label { font-size: 0.68rem; font-weight: 600; letter-spacing: 0.1em;
                      color: var(--dim); text-transform: uppercase; margin-bottom: 10px; }
        .menu-eq { display: block; width: 100%; text-align: left;
                   background: rgba(255,255,255,0.03) !important; border: 1px solid var(--border) !important;
                   color: var(--text) !important; padding: 10px 12px !important; border-radius: 8px !important;
                   font-size: 0.82rem !important; cursor: pointer !important; margin-bottom: 6px; }
        .menu-eq:hover { border-color: var(--gold) !important; }
        .menu-action { display: block; width: 100%; text-align: left;
                       background: transparent !important; border: none !important;
                       border-bottom: 1px solid var(--border) !important;
                       color: var(--text) !important; padding: 12px 0 !important;
                       font-size: 0.88rem !important; cursor: pointer !important; }
        .menu-action:hover { color: var(--gold) !important; }
        .menu-link { display: block; color: var(--dim) !important; text-decoration: none;
                     padding: 10px 0; font-size: 0.85rem; }
        .menu-link:hover { color: var(--gold) !important; }
        .menu-stats { color: var(--dim); font-size: 0.72rem; padding-top: 16px;
                      border-top: 1px solid var(--border); }

        /* ── Welcome ── */
        #welcome-container { text-align: center; padding-top: 22vh; }
        #welcome-container:has(#welcome-screen) ~ #ol-chatbot { display: none !important; }
        .welcome-title { font-size: 2.6rem !important; font-weight: 700 !important; line-height: 1.2 !important;
                         color: #fff !important; margin: 0 0 16px !important; }
        .welcome-title .gold { color: var(--gold); }
        .welcome-sub { color: var(--dim); font-size: 1.05rem; margin-bottom: 32px; }
        .example-questions { display: flex; flex-direction: column; gap: 8px; max-width: 520px; margin: 0 auto; }
        .eq { background: var(--surface) !important; border: 1px solid var(--border) !important;
              color: var(--text) !important; padding: 12px 16px !important; border-radius: 10px !important;
              text-align: left !important; font-size: 0.9rem !important; cursor: pointer !important; }
        .eq:hover { border-color: var(--gold) !important; color: #fff !important; }

        /* ── Welcome: hide when empty ── */
        #welcome-container:not(:has(#welcome-screen)) { display: none !important; overflow: hidden !important; height: 0 !important; padding: 0 !important; margin: 0 !important; }

        /* ── Chatbot ── */
        #ol-chatbot {
            position: fixed !important;
            top: calc(57px + env(safe-area-inset-top, 0px)) !important;
            bottom: calc(70px + env(safe-area-inset-bottom, 0px)) !important;
            left: 0 !important; right: 0 !important;
            height: auto !important; max-height: none !important;
            background: var(--bg) !important; border: none !important;
            margin: 0 !important; padding: 0 !important;
            overflow-x: hidden !important;
            overflow-y: visible !important;
            overscroll-behavior: none !important;
            z-index: 10;
        }
        #ol-chatbot .bubble-wrap {
            padding: 8px 0 20px 0 !important; gap: 0 !important;
            min-height: auto !important;
            height: 100% !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            overscroll-behavior-x: none !important;
            -webkit-overflow-scrolling: touch !important;
        }
        #ol-chatbot .wrapper {
            padding: 0 !important; gap: 0 !important;
            min-height: auto !important;
        }
        #ol-chatbot .message-row { max-width: 100% !important; padding: 6px 12px !important; margin: 0 !important; overflow-x: hidden !important; }
        #ol-chatbot .message-wrap { overflow-x: hidden !important; }
        #ol-chatbot .message { max-width: 100% !important; margin: 0 !important; padding: 0 !important; }
        /* Hide Gradio default action buttons (share, delete, copy) */
        #ol-chatbot .message-buttons-right, #ol-chatbot .message-buttons-left,
        #ol-chatbot button.share, #ol-chatbot button.copy, #ol-chatbot button.delete,
        #ol-chatbot .icon-buttons, #ol-chatbot .icon-button,
        #ol-chatbot .bot-icon, #ol-chatbot .user-icon,
        #ol-chatbot [class*="action"], #ol-chatbot [class*="likeable"] { display: none !important; }
        /* User */
        #ol-chatbot .user.message, #ol-chatbot [data-testid="user"] {
            background: transparent !important; border: none !important;
            color: #fff !important; font-weight: 500 !important; }
        /* Bot */
        #ol-chatbot .bot.message, #ol-chatbot [data-testid="bot"] {
            background: transparent !important; border: none !important;
            color: var(--text) !important; }
        .message, .message p, .message span, .message li, .message code,
        .message h1, .message h2, .message h3, .message h4 {
            user-select: text !important; -webkit-user-select: text !important;
            font-size: 17px !important; color: var(--text) !important; line-height: 1.7 !important; }
        .message h1, .message h2, .message h3, .message h4 {
            font-family: 'Source Serif 4', Georgia, serif !important;
            font-weight: 700 !important; margin: 12px 0 4px !important; }
        .message code { background: rgba(212,168,67,0.1) !important; color: var(--gold) !important;
                        padding: 1px 5px !important; border-radius: 3px !important; }
        .message hr { display: none !important; }
        /* Ordered list hierarchy: I → 1 → a) → (1) */
        .message ol { list-style-type: upper-roman !important; padding-left: 24px !important; }
        .message ol ol { list-style-type: decimal !important; }
        .message ol ol ol { list-style-type: lower-alpha !important; }
        .message ol ol ol ol { list-style-type: decimal !important; }
        .message ol ol ol ol li::marker { content: "(" counter(list-item) ") "; }
        .message a { color: var(--gold) !important; }
        .message a.quelle-link { color: var(--gold) !important; text-decoration: none !important;
                                  border-bottom: 1px dotted var(--gold); cursor: pointer; }
        .message a.quelle-link:hover { text-decoration: underline !important; }
        /* Tables: horizontal scroll instead of squeezing */
        .message table { display: block; overflow-x: auto; -webkit-overflow-scrolling: touch;
                         border-collapse: collapse; white-space: nowrap; margin: 12px 0; }
        .message th, .message td { padding: 8px 14px !important; border: 1px solid var(--border) !important;
                                    font-size: 15px !important; white-space: normal; min-width: 140px; }
        .message th { background: var(--surface) !important; font-weight: 600 !important; }
        .message td { background: transparent !important; }

        /* ── Inline Sources (collapsed in chat message) ── */
        .src-collapse { margin-top: 16px !important; border-top: 1px solid var(--border); padding-top: 8px; }
        .src-collapse > summary { cursor: pointer; color: var(--dim) !important; font-size: 0.85rem !important;
                                   user-select: none; padding: 4px 0; list-style: none; }
        .src-collapse > summary::-webkit-details-marker { display: none; }
        .src-collapse > summary:hover { color: var(--gold) !important; }
        .src-collapse[open] > summary { color: var(--gold) !important; }
        .src-panel h3 { font-size: 0.72rem !important; font-weight: 600 !important; letter-spacing: 0.12em !important;
                        color: var(--dim) !important; text-transform: uppercase !important; margin-bottom: 12px !important; }
        .src-panel details { margin: 4px 0 !important; padding: 8px 10px !important; border-radius: 8px !important;
                             background: rgba(255,255,255,0.03) !important; border: 1px solid var(--border) !important; }
        .src-panel summary { cursor: pointer; font-weight: 500 !important; font-size: 13px !important;
                             color: var(--text) !important; padding: 2px 0; }
        .src-panel .chunk-text { font-size: 12px !important; line-height: 1.5 !important; color: var(--dim) !important; }
        .src-panel .meta-line { color: var(--dim) !important; font-size: 11px !important;
                                border-top: 1px solid var(--border) !important; padding-top: 4px; margin-top: 4px; }
        .src-panel mark { background: rgba(212,168,67,0.25) !important; color: var(--gold) !important;
                          padding: 0 2px; border-radius: 2px; }
        .src-panel .val-box { padding: 8px 12px !important; border-radius: 8px !important;
                              background: rgba(255,255,255,0.03) !important; border: 1px solid var(--border) !important; }
        .src-panel h4 { color: var(--dim) !important; font-size: 0.8rem !important; }
        .src-panel .sub-chunk { border-left: 2px solid var(--border); }

        /* ── Footer (hidden, text moved into input area) ── */
        #ol-footer { display: none !important; }

        /* ── Input Row (fixed bottom) ── */
        #input-row {
            position: fixed !important; bottom: 0 !important; left: 50% !important;
            transform: translateX(-50%) !important;
            width: 100% !important; max-width: 840px !important;
            background: var(--bg) !important; padding: 8px 20px 14px !important;
            gap: 10px !important; z-index: 50; align-items: center !important;
        }
        #msg-input, #msg-input *, #input-row > div {
            background: transparent !important; border: none !important;
            box-shadow: none !important; outline: none !important; }
        #msg-input textarea {
            background: var(--surface) !important; border: 1px solid var(--border) !important;
            border-radius: 24px !important; color: var(--text) !important;
            padding: 12px 20px !important; font-size: 0.95rem !important; resize: none !important; }
        #msg-input textarea:focus {
            border-color: rgba(212,168,67,0.4) !important;
            box-shadow: 0 0 0 2px rgba(212,168,67,0.1) !important; }
        #msg-input textarea::placeholder { color: var(--dim) !important; }
        #submit-btn {
            background: var(--gold) !important; color: #111 !important; border: none !important;
            border-radius: 50% !important; width: 44px !important; height: 44px !important;
            min-width: 44px !important; max-width: 44px !important;
            font-size: 1.2rem !important; padding: 0 !important;
            display: flex !important; align-items: center !important; justify-content: center !important; }
        #submit-btn:hover { background: #e0b84e !important; }

        /* ── Hidden ── */
        #copy-store { display: none !important; }

        /* ── Gradio dark fixes ── */
        .label-wrap, label, .tab-nav button { color: var(--dim) !important; }
        .border-none { border: none !important; }
        input, textarea, select { background: var(--surface) !important; color: var(--text) !important;
            border-color: var(--border) !important; }

        /* ── Safe area ── */
        body { padding: env(safe-area-inset-top) env(safe-area-inset-right)
               env(safe-area-inset-bottom) env(safe-area-inset-left); }

        /* ── Mobile ── */
        @media (max-width: 768px) {
            .gradio-container { padding: 0 !important; }
            #welcome-container { padding-top: 15vh; }
            .welcome-title { font-size: 1.8rem !important; }
            #ol-chatbot { top: calc(56px + env(safe-area-inset-top, 0px)) !important; }
            #ol-chatbot .message-row { padding: 4px 8px !important; }
            #input-row { padding: 8px 12px 12px !important; }
            #menu-panel { width: 85vw; }
            .eq { font-size: 0.82rem !important; padding: 10px 14px !important; }
            button { min-height: 44px !important; }
            textarea { font-size: 16px !important; }
        }

        """,
    )
