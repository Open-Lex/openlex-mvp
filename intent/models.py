"""Zentrale Datenmodelle des Intent-Skills.

- Pydantic-Modelle für API-I/O und das Übergabe-Schema (intent-handoff/1.0).
- Leichtgewichtige dataclasses für interne Hot-Path-DTOs (kein Validierungs-
  Overhead im Signal-Matching).
- compute_confidence(): re-normalisierte Confidence eines Skill-Kandidaten.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────
# Confidence-Berechnung
# ─────────────────────────────────────────────────────────────────────────
def compute_confidence(signal_score: float, llm_vermutung: Optional[float]) -> float:
    """Confidence eines Skill-Kandidaten aus Signal-Score und LLM-Vermutung.

    Gewichtung:
      - LLM-Vermutung vorhanden:  0.6 * signal_score + 0.4 * llm_vermutung
      - LLM-Vermutung fehlt (None): confidence = signal_score   (Gewicht 1.0)

    Re-Normalisierung (Schärfung Phase 1): Würde man bei fehlender LLM-
    Vermutung weiter mit 0.6 multiplizieren, läge die maximal erreichbare
    Confidence bei 0.6 und der Aufnahme-Threshold (CONFIDENCE_THRESHOLD, 0.3)
    entspräche effektiv 50 % des Maximums. Durch Re-Normalisierung auf
    Gewicht 1.0 bleibt der Threshold konsistent — unabhängig davon, ob das
    LLM eine Vermutung geliefert hat. In Stufe B liefert Mistral i.d.R. keine
    Pro-Skill-Vermutung, sodass das Signal-Matching dominiert.

    Beide Eingaben werden in [0, 1] erwartet; das Ergebnis ist auf [0, 1]
    geklemmt und auf 3 Nachkommastellen gerundet.
    """
    if llm_vermutung is None:
        c = signal_score
    else:
        c = signal_score * 0.6 + llm_vermutung * 0.4
    return round(max(0.0, min(1.0, c)), 3)


# ─────────────────────────────────────────────────────────────────────────
# Interne DTOs (dataclasses)
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SignalEntry:
    """Ein normalisiertes Signal aus den Schicht-A-YAMLs."""
    term: str                       # lowercased Signal-Begriff
    skills: tuple[str, ...]         # Ziel-Slug(s); leer = nur Norm-Hints
    norm_hints: tuple[str, ...]     # zugehörige Normen / Gesetze
    sensibilitaet: Optional[str]    # "hoch" | "sehr hoch" | None
    quelle: str                     # "straf" | "zivil" | "oer" | "quer"
    weight: float                   # 1.0; Querverstrebung kern=QUER_WEIGHT, kontext=KONTEXT_WEIGHT
    konstellation: Optional[str] = None  # nur quer: id der Konstellation
    rolle: str = "kern"             # "kern" | "kontext" (nur quer relevant)


@dataclass
class SlotVersion:
    wert: str
    turn: int
    quelle: Literal["llm", "user_confirm"] = "llm"


@dataclass
class MatchResult:
    signal_score: dict[str, float] = field(default_factory=dict)   # slug → [0,1]
    norm_hits: list[str] = field(default_factory=list)
    sensibilitaet: str = "keine"
    matched_terms: list[str] = field(default_factory=list)
    konstellationen: dict[str, float] = field(default_factory=dict)  # id → confidence


# ─────────────────────────────────────────────────────────────────────────
# LLM-Extraktion (validiert)
# ─────────────────────────────────────────────────────────────────────────
class LLMRechtsgebiet(BaseModel):
    skill: str
    confidence: float = 0.5


class Extraction(BaseModel):
    wer: Optional[str] = None
    was: Optional[str] = None
    von_wem: Optional[str] = None
    woraus: Optional[str] = None
    erkannte_signale: list[str] = Field(default_factory=list)
    vermutete_rechtsgebiete: list[LLMRechtsgebiet] = Field(default_factory=list)
    vermutete_konstellationen: list[str] = Field(default_factory=list)
    vermutete_normen: list[str] = Field(default_factory=list)
    sprachstil: Literal["laie", "profi", "unklar"] = "unklar"
    offene_punkte: list[str] = Field(default_factory=list)
    # LLM-geführte Gesprächsführung (eine konkrete, am Fall orientierte Folgefrage;
    # genug_infos=True signalisiert, dass eine sinnvolle Triage-Übergabe möglich ist)
    naechste_frage: Optional[str] = None
    genug_infos: bool = False
    weichen_slot_extraktionen: Optional[dict] = None
    # Rechtssystem-spezifische Tiefenfelder (StR: Tatbestand/Rechtswidrigkeit/Schuld;
    # ÖR: Interessenabwägung; ZR: Fristen/Beweise/bisherige Schritte).
    # Nur befüllen wenn der Kontext-Block ein SACHVERHALTSTIEFE-Abschnitt zeigt.
    rechtssystem_tiefe: Optional[dict] = None


# ─────────────────────────────────────────────────────────────────────────
# Übergabe-Schema (intent-handoff/1.0)
# ─────────────────────────────────────────────────────────────────────────
class AnspruchsGrundlage(BaseModel):
    id: str
    norm: str
    confidence: float


class SkillKandidat(BaseModel):
    skill: str
    confidence: float


class KonstellationKandidat(BaseModel):
    """Eine erkannte juristische Facette des Falls (z.B. Körperverletzung).
    Trägt ihre Normen kategorisiert, damit der Orchestrator je Facette
    parallel oder sequentiell weiterarbeiten kann."""
    id: str
    titel: str
    rechtsgebiete: list[str] = Field(default_factory=list)          # Kern-Skills
    kern_normen: list[AnspruchsGrundlage] = Field(default_factory=list)
    weitere_normen: list[AnspruchsGrundlage] = Field(default_factory=list)
    confidence: float = 0.0
    sensibilitaet: Literal["keine", "hoch", "sehr hoch"] = "keine"


class Sachverhalt(BaseModel):
    wer: Optional[str] = None
    was: Optional[str] = None
    von_wem: Optional[str] = None
    woraus: Optional[str] = None


class Handoff(BaseModel):
    schema_version: Literal["intent-handoff/1.1"] = "intent-handoff/1.1"
    session_id: str
    created_at: str
    sachverhalt: Sachverhalt
    vermutete_konstellationen: list[KonstellationKandidat] = Field(default_factory=list)
    # flach, aus den Konstellationen abgeleitet (Abwärtskompatibilität)
    vermutete_anspruchsgrundlagen: list[AnspruchsGrundlage] = Field(default_factory=list)
    vermutete_rechtsgebiete: list[SkillKandidat] = Field(default_factory=list)
    sprachstil: Literal["laie", "profi"] = "laie"
    sensibilitaet: Literal["keine", "hoch", "sehr hoch"] = "keine"
    offene_punkte: list[str] = Field(default_factory=list)
    vollstaendig: bool = False
    turns: int = 0
    weichen_slots: dict = Field(default_factory=dict)
    weichen_offene: list = Field(default_factory=list)
    # Akkumulierte Sachverhalts-Tiefenfelder über alle Turns
    sachverhalts_tiefe: dict = Field(default_factory=dict)
    # Erkanntes Rechtssystem: "ZR" | "StR" | "ÖR" | None
    rechtssystem: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────
# API-I/O
# ─────────────────────────────────────────────────────────────────────────
class StartSessionResponse(BaseModel):
    session_id: str
    frage: str


class MessageRequest(BaseModel):
    session_id: str
    text: str


class MessageResponse(BaseModel):
    session_id: str
    modus: Literal["frage", "handoff"]
    frage: Optional[str] = None
    handoff: Optional[Handoff] = None
    turns: int = 0
    debug: Optional[dict] = None


class RouteResponse(BaseModel):
    """Antwort des Orchestrators: weiterleitete Skill-Antwort + Routing-Info."""
    session_id: str
    skill_id: str
    skill_confidence: float
    secondary_skills: list[str] = Field(default_factory=list)
    query: str
    answer: str = ""
    error: Optional[str] = None


class RouteMultiResponse(BaseModel):
    """Bei Multi-Facetten: Antworten mehrerer parallel angefragter Skills."""
    session_id: str
    query: str
    results: list[RouteResponse] = Field(default_factory=list)
