"""Session-State: Dataclass + atomare JSON-Persistenz + TTL-Bereinigung."""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import config
from engine import SlotStore
from models import SkillKandidat


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SessionState:
    session_id: str
    created_at: str
    updated_at: str
    turns: int = 0
    sprachstil: str = "laie"
    sensibilitaet: str = "keine"
    begehr_geklaert: bool = False
    vollstaendig: bool = False
    pending_slot: Optional[str] = None                 # zuletzt erfragter Slot
    slot_attempts: dict = field(default_factory=dict)  # slot → Anzahl Nachfragen
    skipped_slots: list[str] = field(default_factory=list)
    no_progress: int = 0                               # Turns ohne neuen Pflicht-Slot
    geklaerte_anker: list[str] = field(default_factory=list)  # bereits geklärte Anker
    weichen_slots: dict = field(default_factory=dict)
    geklärte_weichen: list = field(default_factory=list)
    pending_weiche: Optional[str] = None
    messages: list[dict] = field(default_factory=list)
    slots: SlotStore = field(default_factory=SlotStore)
    signale: list[str] = field(default_factory=list)   # kumuliert über Turns
    llm_rechtsgebiete: dict = field(default_factory=dict)  # skill→conf (LLM, kumuliert)
    llm_normen: list[str] = field(default_factory=list)    # LLM-Norm-Vorschläge, kumuliert
    vermutete_rechtsgebiete: list[SkillKandidat] = field(default_factory=list)
    last_handoff: Optional[dict] = None  # letztes Handoff-JSON (für Orchestrator-Query)
    rechtssystem: Optional[str] = None          # "ZR" | "StR" | "ÖR"
    sachverhalts_tiefe: dict = field(default_factory=dict)  # akkumulierte Tiefenfelder

    @classmethod
    def new(cls) -> "SessionState":
        ts = _now_iso()
        return cls(session_id=uuid.uuid4().hex, created_at=ts, updated_at=ts)

    def reset(self) -> None:
        self.session_id = uuid.uuid4().hex
        self.created_at = self.updated_at = _now_iso()
        self.turns = 0
        self.sprachstil = "laie"
        self.sensibilitaet = "keine"
        self.begehr_geklaert = False
        self.vollstaendig = False
        self.pending_slot = None
        self.slot_attempts = {}
        self.skipped_slots = []
        self.no_progress = 0
        self.geklaerte_anker = []
        self.weichen_slots = {}
        self.geklärte_weichen = []
        self.pending_weiche = None
        self.messages = []
        self.slots = SlotStore()
        self.signale = []
        self.llm_rechtsgebiete = {}
        self.llm_normen = []
        self.vermutete_rechtsgebiete = []
        self.last_handoff = None
        self.rechtssystem = None
        self.sachverhalts_tiefe = {}

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id, "created_at": self.created_at,
            "updated_at": self.updated_at, "turns": self.turns,
            "sprachstil": self.sprachstil, "sensibilitaet": self.sensibilitaet,
            "begehr_geklaert": self.begehr_geklaert, "vollstaendig": self.vollstaendig,
            "pending_slot": self.pending_slot, "slot_attempts": self.slot_attempts,
            "skipped_slots": self.skipped_slots, "no_progress": self.no_progress,
            "geklaerte_anker": self.geklaerte_anker,
            "weichen_slots": self.weichen_slots,
            "geklärte_weichen": self.geklärte_weichen,
            "pending_weiche": self.pending_weiche,
            "messages": self.messages, "slots": self.slots.to_dict(),
            "signale": self.signale, "llm_rechtsgebiete": self.llm_rechtsgebiete,
            "llm_normen": self.llm_normen, "last_handoff": self.last_handoff,
            "vermutete_rechtsgebiete": [k.model_dump() for k in self.vermutete_rechtsgebiete],
            "rechtssystem": self.rechtssystem,
            "sachverhalts_tiefe": self.sachverhalts_tiefe,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SessionState":
        st = cls(session_id=d["session_id"], created_at=d["created_at"],
                 updated_at=d["updated_at"], turns=d.get("turns", 0),
                 sprachstil=d.get("sprachstil", "laie"),
                 sensibilitaet=d.get("sensibilitaet", "keine"),
                 begehr_geklaert=d.get("begehr_geklaert", False),
                 vollstaendig=d.get("vollstaendig", False),
                 pending_slot=d.get("pending_slot"),
                 slot_attempts=d.get("slot_attempts", {}),
                 skipped_slots=d.get("skipped_slots", []),
                 no_progress=d.get("no_progress", 0),
                 geklaerte_anker=d.get("geklaerte_anker", []),
                 messages=d.get("messages", []))
        st.signale = d.get("signale", [])
        st.llm_rechtsgebiete = d.get("llm_rechtsgebiete", {})
        st.llm_normen = d.get("llm_normen", [])
        st.last_handoff = d.get("last_handoff")
        st.slots = SlotStore.from_dict(d.get("slots", {}))
        st.vermutete_rechtsgebiete = [SkillKandidat(**k) for k in d.get("vermutete_rechtsgebiete", [])]
        st.weichen_slots = d.get("weichen_slots", {})
        st.geklärte_weichen = d.get("geklärte_weichen", [])
        st.pending_weiche = d.get("pending_weiche")
        st.rechtssystem = d.get("rechtssystem")
        st.sachverhalts_tiefe = d.get("sachverhalts_tiefe", {})
        return st


def _path(session_id: str) -> Path:
    return config.STATE_DIR / f"{session_id}.json"


def save(state: SessionState) -> None:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    state.updated_at = _now_iso()
    target = _path(state.session_id)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(state.to_dict(), ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, target)


def load(session_id: str) -> SessionState | None:
    p = _path(session_id)
    if not p.exists():
        return None
    return SessionState.from_dict(json.loads(p.read_text(encoding="utf-8")))


def delete(session_id: str) -> bool:
    """DSGVO Art. 17: Löschung der Session-Datei. Gibt True zurück, wenn gelöscht."""
    p = _path(session_id)
    if not p.exists():
        return False
    try:
        p.unlink()
        return True
    except OSError:
        return False


def cleanup_expired() -> int:
    """Löscht Session-Dateien älter als TTL. Gibt Anzahl gelöschter zurück."""
    if not config.STATE_DIR.exists():
        return 0
    cutoff = time.time() - config.SESSION_TTL_H * 3600
    removed = 0
    for f in config.STATE_DIR.glob("*.json"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            pass
    return removed
