"""Engine des Intent-Skills: SchemaLibrary, SignalMatcher, SlotStore, IntentEngine."""
from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Optional

import yaml

import config
import heuristics
from morphology import stem_phrase
from models import (
    AnspruchsGrundlage, Extraction, Handoff, KonstellationKandidat, MatchResult,
    MessageResponse, Sachverhalt, SignalEntry, SkillKandidat, SlotVersion,
    compute_confidence,
)

_SOURCE_FILES = {
    "strafrecht_systematik.yaml": "straf",
    "zivilrecht_systematik.yaml": "zivil",
    "oeffentliches_recht_systematik.yaml": "oer",
    "querverstrebungen.yaml": "quer",
    "alltagssignale.yaml": "zivil",   # Alltagsbegriffe ohne Eingriff in Taxonomie
}
_NORM_LIST_KEYS = (
    "normen", "bereiche", "strafrechtlich", "zivilrechtlich",
    "oeffentlich_rechtlich", "weitere_rechtsbereiche", "buecher",
)
_NORM_ITEM_KEYS = ("norm", "gesetz", "sgb")
_SENS_RANK = {"keine": 0, "hoch": 1, "sehr hoch": 2}
_SENS_BY_RANK = {0: "keine", 1: "hoch", 2: "sehr hoch"}
_RESET_PATTERNS = ("neuer fall", "von vorne", "neu anfangen", "reset", "neue frage")
_DEFAULT_BEGEHR = "unklar – möchte zunächst eine rechtliche Einschätzung der Lage"
_QUESTION_SIM_THRESHOLD = 0.78


def _normalize_q(s: str) -> str:
    return re.sub(r"[^a-zäöüß ]+", " ", (s or "").lower()).strip()


def _too_similar(a: str, b: str) -> bool:
    """True wenn zwei Fragen praktisch identisch sind (verhindert Re-Asking)."""
    if not a or not b:
        return False
    return difflib.SequenceMatcher(None, _normalize_q(a), _normalize_q(b)).ratio() > _QUESTION_SIM_THRESHOLD


def _norm_sens(value) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None
    v = value.lower()
    if "sehr hoch" in v:
        return "sehr hoch"
    if "hoch" in v:
        return "hoch"
    return None


def _collect_norm_hints(node: dict) -> list[str]:
    seen, out = set(), []
    for key, val in node.items():
        if key in _NORM_LIST_KEYS and isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    for nk in _NORM_ITEM_KEYS:
                        if item.get(nk) and item[nk] not in seen:
                            seen.add(item[nk])
                            out.append(str(item[nk]))
    return out


# ─────────────────────────────────────────────────────────────────────────
class SchemaLibrary:
    """Lädt + normalisiert die Schemata. Walker löst beide Datenformen
    (Liste vs. Dict), Abschnitt/Gesetz→Slug-Mapping und Sensibilität auf."""

    def __init__(self, schema_dir: Path):
        self.schema_dir = Path(schema_dir)
        tax = self._load("rechtsgebiete_taxonomie.yaml")
        self.section_to_slug = tax.get("section_to_slug", {}) or {}
        self.gesetz_to_slug = tax.get("gesetz_to_slug", {}) or {}
        self.source_default = tax.get("source_default", {}) or {}
        self.konstellation_kern = tax.get("konstellation_kern", {}) or {}
        self.valid_slugs = set(config.SKILLS)

        slots = self._load("sachverhalts_slots.yaml")
        self.pflicht_slots = slots.get("pflicht_slots", [])
        self.pflicht_reihenfolge = slots.get("pflicht_reihenfolge", [])
        self.optional_slots = slots.get("optional_slots", [])
        self.pflicht_ids = [s["id"] for s in self.pflicht_slots]

        self.frageketten = self._load("frageketten.yaml")
        self.anker_klaerung = (self._load("anker_klaerung.yaml") or {}).get("anker", {}) or {}
        self.weichenstellungen: dict = (self._load("weichenstellungen.yaml") or {}).get("weichenstellungen", {}) or {}

        self.quer_weight = config.QUER_WEIGHT
        self.kontext_weight = config.KONTEXT_WEIGHT
        self.signals: list[SignalEntry] = []
        self.norm_alias: dict[str, list[str]] = {}
        self.pruefreihenfolge: list[dict] = []
        self.quer_meta: dict = {}
        self.konstellationen: dict[str, dict] = {}
        self._build_signal_index()
        self.known_gesetze = self._build_known_gesetze()

    def _load(self, name: str) -> dict:
        with (self.schema_dir / name).open(encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    def _build_signal_index(self) -> None:
        for fname, quelle in _SOURCE_FILES.items():
            data = self._load(fname)
            self._walk(data, quelle, [])
            self._collect_aliases(data)
            if quelle == "zivil" and not self.pruefreihenfolge:
                # Nur beim ersten zivil-File setzen (zivilrecht_systematik.yaml);
                # nachgelagerte zivil-Dateien (alltagssignale.yaml) überschreiben
                # die Prüfreihenfolge sonst mit einer leeren Liste.
                pr = data.get("anspruchssystem_pruefungsreihenfolge", {})
                self.pruefreihenfolge = pr.get("reihenfolge", []) if isinstance(pr, dict) else []
            if quelle == "quer":
                self.quer_meta = data.get("verwendung_im_intent_skill", {}) or {}
                self._build_konstellationen(data)

    def _walk(self, node, quelle: str, path: list[str]) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("signale"), list):
                self._emit(node, quelle, path)
            for key, val in node.items():
                if key != "signale":
                    self._walk(val, quelle, path + [key])
        elif isinstance(node, list):
            for item in node:
                self._walk(item, quelle, path)

    def _emit(self, node: dict, quelle: str, path: list[str]) -> None:
        norm_hints = tuple(_collect_norm_hints(node))
        sens = _norm_sens(node.get("sensibilitaet"))
        terms = [t.lower().strip() for t in node["signale"]
                 if isinstance(t, str) and t.strip()]

        if quelle == "quer" and len(path) >= 2 and path[0] == "querverstrebungen":
            konst_id = path[1]
            overlay = self.konstellation_kern.get(konst_id)
            if overlay:
                kern = [str(s) for s in (overlay.get("kern") or [])]
                kontext = [str(s) for s in (overlay.get("kontext") or [])]
            else:  # un-migrierte Konstellation → alles Kern
                kern = [str(s) for s in (node.get("typische_rechtsgebiete") or [])]
                kontext = []
            for term in terms:
                for s in kern:
                    self.signals.append(SignalEntry(term, (s,), norm_hints, sens,
                        "quer", self.quer_weight, konst_id, "kern"))
                for s in kontext:
                    self.signals.append(SignalEntry(term, (s,), norm_hints, sens,
                        "quer", self.kontext_weight, konst_id, "kontext"))
                if not kern and not kontext:   # Norm-Hints trotzdem erhalten
                    self.signals.append(SignalEntry(term, (), norm_hints, sens,
                        "quer", self.quer_weight, konst_id, "kern"))
            return

        skills = tuple(self._resolve_skills(node, quelle, path))
        for term in terms:
            self.signals.append(SignalEntry(term, skills, norm_hints, sens, quelle, 1.0))

    def _build_konstellationen(self, data: dict) -> None:
        def norms(node: dict, key: str) -> list[str]:
            return [str(x["norm"]) for x in (node.get(key) or [])
                    if isinstance(x, dict) and x.get("norm")]
        for kid, node in (data.get("querverstrebungen") or {}).items():
            if not isinstance(node, dict):
                continue
            weitere = [str(x.get("gesetz") or x.get("norm"))
                       for x in (node.get("weitere_rechtsbereiche") or [])
                       if isinstance(x, dict) and (x.get("gesetz") or x.get("norm"))]
            overlay = self.konstellation_kern.get(kid, {})
            kern_skills = overlay.get("kern") or node.get("typische_rechtsgebiete") or []
            self.konstellationen[kid] = {
                "titel": node.get("titel", kid),
                "rechtsgebiete": [str(s) for s in kern_skills],
                "straf": norms(node, "strafrechtlich"),
                "zivil": norms(node, "zivilrechtlich"),
                "oeff": norms(node, "oeffentlich_rechtlich"),
                "weitere": weitere,
                "sensibilitaet": _norm_sens(node.get("sensibilitaet")) or "keine",
                "signale": [str(s).lower().strip()
                            for s in (node.get("signale") or []) if isinstance(s, str)],
            }

    def _resolve_skills(self, node: dict, quelle: str, path: list[str]) -> list[str]:
        tr = node.get("typische_rechtsgebiete")
        if tr:
            return [str(s) for s in tr]
        gesetz = node.get("gesetz")
        if gesetz and gesetz in self.gesetz_to_slug:
            return [self.gesetz_to_slug[gesetz]]
        for key in reversed(path):
            if key in self.section_to_slug:
                return [self.section_to_slug[key]]
        return list(self.source_default.get(quelle, []))

    def _collect_aliases(self, data: dict) -> None:
        block = data.get("aliases_und_alltagsbegriffe")
        if not isinstance(block, dict):
            return
        for m in block.get("mappings", []) or []:
            if isinstance(m, dict):
                alltag = m.get("alltag")
                normen = m.get("normen") or m.get("normen_kandidaten") or []
                if alltag and normen:
                    self.norm_alias[str(alltag).lower().strip()] = [str(n) for n in normen]

    _LAW_NOISE = {"Abs", "Art", "Nr", "Halbs", "ff", "analog", "iVm", "Satz", "S",
                  "i", "V", "m", "und"}

    def law_token(self, s: str) -> Optional[str]:
        """Extrahiert das Gesetzeskürzel aus einem Norm-String (für Validierung)."""
        toks = re.findall(r"[A-ZÄÖÜ][A-Za-zÄÖÜß]+", s or "")
        cand = [t for t in toks if t not in self._LAW_NOISE]
        return cand[-1].lower() if cand else None

    def _build_known_gesetze(self) -> set:
        g = set()
        def add(s):
            lt = self.law_token(s)
            if lt:
                g.add(lt)
        for e in self.signals:
            for n in e.norm_hints:
                add(n)
        for normen in self.norm_alias.values():
            for n in normen:
                add(n)
        for meta in self.konstellationen.values():
            for key in ("straf", "zivil", "oeff", "weitere"):
                for n in meta.get(key, []):
                    add(n)
        for k in self.gesetz_to_slug:
            add(k)
        return g

    def stats(self) -> dict:
        skills = {s for e in self.signals for s in e.skills}
        with_skill = sum(1 for e in self.signals if e.skills)
        return {
            "signals_total": len(self.signals), "signals_with_skill": with_skill,
            "signals_norm_only": len(self.signals) - with_skill,
            "distinct_skills": len(skills), "skills": sorted(skills),
            "norm_alias": len(self.norm_alias),
            "pruefreihenfolge_stufen": len(self.pruefreihenfolge),
            "pflicht_slots": len(self.pflicht_slots), "optional_slots": len(self.optional_slots),
        }


# ─────────────────────────────────────────────────────────────────────────
class SignalMatcher:
    def __init__(self, lib: SchemaLibrary):
        self.lib = lib
        # Drei Match-Pfade je Signal-Begriff:
        #  1) Stamm-Teilfolge (Flexion: "Vermietern"→"vermiet"),
        #  2) LLM-Grundform-Signale (Derivation: "abgemahnt"→"Abmahnung"),
        #  3) Wortgrenzen-Substring (Komposita: "Mietminderungsanspruch"; verhindert
        #     zugleich Substring-Fehltreffer wie "eid" in "beides").
        terms = {e.term for e in lib.signals}
        terms |= {a for a in lib.norm_alias}
        self._pat = {term: re.compile(r"\b" + re.escape(term)) for term in terms}
        self._sig_stem = {term: stem_phrase(term) for term in terms}

    def konst_grounded(self, kid: str, text: str, llm_signale: Optional[list[str]] = None) -> bool:
        """Prüft, ob eine vom LLM genannte Konstellation durch ein eigenes Signal
        im Nutzertext ODER in den LLM-Signalen belegt ist (gegen Halluzination)."""
        meta = self.lib.konstellationen.get(kid)
        if not meta:
            return False
        text_low = (text or "").lower()
        text_stem_str = " " + stem_phrase(text_low, drop_stopwords=True) + " "
        llm_stem = {stem_phrase(s) for s in (llm_signale or []) if s and s.strip()}
        for sig in meta.get("signale") or []:
            if self._matches(sig, text_low, text_stem_str, llm_stem):
                return True
        return False

    def _matches(self, term: str, raw_text: str, text_stem_str: str,
                 llm_stem: set[str]) -> bool:
        sig = self._sig_stem.get(term) or term
        if sig and f" {sig} " in text_stem_str:
            return True
        if sig in llm_stem:
            return True
        pat = self._pat.get(term)
        return bool(pat.search(raw_text)) if pat else (term in raw_text)

    def match(self, text: str, llm_signale: Optional[list[str]] = None) -> MatchResult:
        t = (text or "").lower()
        # Text-Stämme OHNE Stopwörter (verhindert "mein"→Signal "Meinung").
        # Multiwort-Signale mit Funktionswörtern fängt weiterhin der \b-Fallback.
        text_stem_str = " " + stem_phrase(t, drop_stopwords=True) + " "
        llm_stem = {stem_phrase(s) for s in (llm_signale or []) if s and s.strip()}
        # Pro (skill, term) genau ein Treffer; Querverstrebung als Quelle bevorzugt.
        best: dict[tuple[str, str], SignalEntry] = {}
        # Norm-Hinweise nach Quelle puffern; Querverstrebung zuerst (kuratiert,
        # cross-domain), danach zivil/straf/oer, zuletzt Aliases.
        by_src: dict[str, list[str]] = {"quer": [], "zivil": [], "straf": [], "oer": []}
        alias_norms: list[str] = []
        sens_rank = 0
        matched_terms: set[str] = set()
        konst_terms: dict[str, set[str]] = {}

        for e in self.lib.signals:
            if not self._matches(e.term, t, text_stem_str, llm_stem):
                continue
            matched_terms.add(e.term)
            sens_rank = max(sens_rank, _SENS_RANK.get(e.sensibilitaet or "keine", 0))
            by_src.setdefault(e.quelle, []).extend(e.norm_hints)
            if e.konstellation:
                konst_terms.setdefault(e.konstellation, set()).add(e.term)
            for skill in e.skills:
                key = (skill, e.term)
                prev = best.get(key)
                if prev is None or (e.quelle == "quer" and prev.quelle != "quer"):
                    best[key] = e

        raw: dict[str, float] = {}
        for (skill, _term), e in best.items():
            raw[skill] = raw.get(skill, 0.0) + e.weight

        k = config.SATURATION_K
        signal_score = {s: round(v / (v + k), 3) for s, v in raw.items()}

        for alltag, normen in self.lib.norm_alias.items():
            if self._matches(alltag, t, text_stem_str, llm_stem):
                alias_norms.extend(normen)

        norm_hits: list[str] = []
        seen: set[str] = set()
        for src in ("quer", "zivil", "straf", "oer"):
            for n in by_src.get(src, []):
                if n not in seen:
                    seen.add(n)
                    norm_hits.append(n)
        for n in alias_norms:
            if n not in seen:
                seen.add(n)
                norm_hits.append(n)

        q = config.QUER_WEIGHT
        konstellationen = {kid: round((q * len(terms)) / (q * len(terms) + k), 3)
                           for kid, terms in konst_terms.items()}

        return MatchResult(
            signal_score=signal_score, norm_hits=norm_hits,
            sensibilitaet=_SENS_BY_RANK[sens_rank], matched_terms=sorted(matched_terms),
            konstellationen=konstellationen,
        )


# ─────────────────────────────────────────────────────────────────────────
class SlotStore:
    def __init__(self):
        self.data: dict[str, list[SlotVersion]] = {}

    @staticmethod
    def _is_refinement(old: str, new: str) -> bool:
        """True, wenn new eine Präzisierung von old ist (Substring in eine Richtung).

        'Vermieter' → 'Vermieter Herr Schmidt'  → True  (Präzisierung)
        'Vermieter' → 'Arbeitgeber'              → False (echter Wechsel)
        """
        a, b = old.lower().strip(), new.lower().strip()
        return a != b and (a in b or b in a)

    def update(self, slot_id: str, wert: Optional[str], turn: int) -> bool:
        """Fügt eine Slot-Version hinzu.

        Rückgabe: True = echter Widerspruch (Identitätswechsel),
                  False = neu, gleich oder Präzisierung (kein Widerspruch).
        """
        if not wert or not str(wert).strip():
            return False
        wert = str(wert).strip()
        cur = self.active(slot_id)
        # Echter Konflikt: Wert ändert sich UND ist keine Substring-Präzisierung
        conflict = bool(cur and cur != wert and not self._is_refinement(cur, wert))
        self.data.setdefault(slot_id, []).append(SlotVersion(wert=wert, turn=turn))
        return conflict

    def active(self, slot_id: str) -> Optional[str]:
        versions = self.data.get(slot_id)
        return versions[-1].wert if versions else None

    def filled(self, slot_id: str) -> bool:
        return self.active(slot_id) is not None

    def missing_pflicht(self, pflicht_ids: list[str]) -> list[str]:
        return [s for s in pflicht_ids if not self.filled(s)]

    def to_dict(self) -> dict:
        return {k: [{"wert": v.wert, "turn": v.turn, "quelle": v.quelle} for v in vs]
                for k, vs in self.data.items()}

    @classmethod
    def from_dict(cls, d: dict) -> "SlotStore":
        store = cls()
        for k, vs in (d or {}).items():
            store.data[k] = [SlotVersion(**v) for v in vs]
        return store


# ─────────────────────────────────────────────────────────────────────────
class IntentEngine:
    def __init__(self, lib: SchemaLibrary, matcher: SignalMatcher, llm, coach):
        self.lib = lib
        self.matcher = matcher
        self.llm = llm
        self.coach = coach

    # state ist ein SessionState (session.py)
    def start(self, state) -> str:
        frage = self.coach.start_frage("laie")
        state.pending_slot = "woraus"   # die offene Startfrage erhebt den Sachverhalt
        state.messages.append({"role": "assistant", "content": frage})
        return frage

    def step(self, state, user_text: str) -> MessageResponse:
        if any(p in user_text.lower() for p in _RESET_PATTERNS):
            state.reset()
            frage = self.start(state)
            return MessageResponse(session_id=state.session_id, modus="frage",
                                   frage=frage, turns=state.turns)

        state.turns += 1
        state.messages.append({"role": "user", "content": user_text})

        store = self.slots(state)
        prev_filled = {s for s in self.lib.pflicht_ids if store.filled(s)}
        prev_signale = set(state.signale)

        # ── Layer 2: Weichenstellungs-Frage prüfen ───────────────────────────────
        _anker_active = bool(getattr(state, 'pending_anker', None))
        if (state.turns >= 2
                and not _anker_active
                and not state.pending_weiche
                and config.ENABLE_WEICHEN):
            _pw = self._pending_weiche(state)
            if _pw:
                _wid, _wdef = _pw
                _opts = "  ".join(
                    f"[{i+1}] {o['label']}" for i, o in enumerate(_wdef.get("optionen", []))
                )
                _frage = _wdef["frage"].strip() + "\n\n" + _opts
                state.pending_weiche = _wid
                # Weichenstellungs-Frage in History eintragen, damit _too_similar
                # eine Wiederholung durch das LLM im Folgeturn erkennt.
                state.messages.append({"role": "assistant", "content": _frage})
                return MessageResponse(session_id=state.session_id, modus="frage",
                                       frage=_frage, turns=state.turns)

        # Kombinierter Call: Extraktion + (LLM-geführte) nächste Frage.
        extraction: Extraction = self.llm.extract(state.messages, user_text, state)
        for sid in self.lib.pflicht_ids:
            store.update(sid, getattr(extraction, sid, None), state.turns)

        # ── Layer 2: Weichen-Antwort verarbeiten ─────────────────────────────────
        if state.pending_weiche:
            _wid = state.pending_weiche
            _wdef = self.lib.weichenstellungen.get(_wid, {})
            _bslot = _wdef.get("branch_slot")
            _extracted = (extraction.weichen_slot_extraktionen or {}).get(_bslot) if _bslot else None
            if _bslot:
                state.weichen_slots[_bslot] = _extracted  # True/False/str/None
            state.geklärte_weichen.append(_wid)
            state.pending_weiche = None
            # Sofort nächste Weiche prüfen — bevor genug_infos den Handoff auslöst.
            # Nur wenn kein Anker aktiv und Weichen aktiviert.
            if config.ENABLE_WEICHEN and not getattr(state, 'pending_anker', None):
                _next = self._pending_weiche(state)
                if _next:
                    _wid2, _wdef2 = _next
                    _opts2 = "  ".join(
                        f"[{i+1}] {o['label']}" for i, o in enumerate(_wdef2.get("optionen", []))
                    )
                    _frage2 = _wdef2["frage"].strip() + "\n\n" + _opts2
                    state.pending_weiche = _wid2
                    state.messages.append({"role": "assistant", "content": _frage2})
                    return MessageResponse(session_id=state.session_id, modus="frage",
                                           frage=_frage2, turns=state.turns)

        # Fortschritt: reine Ausweich-Antwort ohne neue Info zählt als "kein
        # Fortschritt". Nach MAX_NO_PROGRESS solchen Turns → Zwangs-Handoff.
        newly = {s for s in self.lib.pflicht_ids if store.filled(s)} - prev_filled
        deflect = heuristics.is_deflection(user_text)
        new_signals = bool(set(extraction.erkannte_signale or []) - prev_signale)
        made_progress = bool(newly) or new_signals or not deflect
        state.no_progress = 0 if made_progress else state.no_progress + 1

        # Bei Ausweichen das Begehr weich festlegen → nicht erneut nach dem Ziel
        # fragen (der Nutzer möchte dann i.d.R. nur eine Einschätzung).
        if deflect and not store.filled("was"):
            store.update("was", _DEFAULT_BEGEHR, state.turns)

        # Kumulierter Match (Rechtsgebiete/Konstellationen bleiben über Turns stabil)
        state.signale = list(dict.fromkeys(state.signale + (extraction.erkannte_signale or [])))
        corpus = " ".join(m["content"] for m in state.messages if m["role"] == "user")
        match = self.matcher.match(f"{corpus} {store.active('woraus') or ''}", state.signale)
        state.sprachstil = heuristics.resolve(user_text, extraction.sprachstil)
        state.sensibilitaet = _SENS_BY_RANK[max(
            _SENS_RANK[state.sensibilitaet], _SENS_RANK[match.sensibilitaet])]
        # LLM-Rechtsgebiet-Vorschläge (validiert) kumulativ mergen (max je Skill)
        for rg in (extraction.vermutete_rechtsgebiete or []):
            if rg.skill in self.lib.valid_slugs:
                state.llm_rechtsgebiete[rg.skill] = max(
                    state.llm_rechtsgebiete.get(rg.skill, 0.0),
                    max(0.0, min(1.0, rg.confidence)))
        state.vermutete_rechtsgebiete = self._skill_kandidaten(match, state.llm_rechtsgebiete)
        # LLM-Norm-Vorschläge validieren (nur Normen real existierender Gesetze)
        for nrm in (extraction.vermutete_normen or []):
            lt = self.lib.law_token(nrm)
            if lt and lt in self.lib.known_gesetze and nrm.strip() not in state.llm_normen:
                state.llm_normen.append(nrm.strip())
        # P9+F2 mit Halluzinations-Schutz: LLM-Konstellationen nur dann verwenden,
        # wenn mind. ein zugehöriges Signal im Korpus oder den LLM-Signalen
        # belegt ist (verhindert Fälle wie Kartellrecht→stalking_nachstellung).
        corpus_for_grounding = " ".join(m["content"] for m in state.messages if m.get("role") == "user")
        all_signale = list(state.signale)
        validated_konst = []
        for kid in (extraction.vermutete_konstellationen or []):
            if self.matcher.konst_grounded(kid, corpus_for_grounding, all_signale):
                validated_konst.append(kid)
        for kid in validated_konst:
            meta = self.lib.konstellationen.get(kid)
            if meta:
                state.sensibilitaet = _SENS_BY_RANK[max(
                    _SENS_RANK[state.sensibilitaet],
                    _SENS_RANK.get(meta.get("sensibilitaet") or "keine", 0))]
                for skill in (meta.get("rechtsgebiete") or []):
                    if skill in self.lib.valid_slugs:
                        state.llm_rechtsgebiete[skill] = max(
                            state.llm_rechtsgebiete.get(skill, 0.0), 0.7)
        # F2: nach allen Updates erneut die Kandidaten berechnen — damit der
        # Konstellations-Fallback in dieser Runde schon das Routing setzt.
        state.vermutete_rechtsgebiete = self._skill_kandidaten(match, state.llm_rechtsgebiete)

        # B2C-Kopplungsregel: kaufrecht → verbraucherrecht immer zusammen, außer B2B.
        # Juristisch: Verbraucherrecht ist eine Schutzschicht auf dem Kaufrecht;
        # greift immer wenn Privatperson (§ 13 BGB) ↔ Unternehmer (§ 14 BGB).
        _skills_now = {rg.skill for rg in state.vermutete_rechtsgebiete}
        if "kaufrecht" in _skills_now and "verbraucherrecht" not in _skills_now:
            _corpus_lc = corpus.lower()
            _b2b_buyer = ("als unternehmer", "als gewerblich", "für mein unternehmen",
                          "für meine firma", "mein betrieb ", "mein unternehmen ",
                          "geschäftlich bestellt", "gewerblich tätig",
                          "für unsere firma", "für unseren betrieb")
            if not any(s in _corpus_lc for s in _b2b_buyer):
                state.llm_rechtsgebiete["verbraucherrecht"] = max(
                    state.llm_rechtsgebiete.get("verbraucherrecht", 0.0), 0.7)
                state.vermutete_rechtsgebiete = self._skill_kandidaten(
                    match, state.llm_rechtsgebiete)

        # Rechtssystem aktualisieren + Sachverhalts-Tiefe mergen
        if state.vermutete_rechtsgebiete:
            state.rechtssystem = config.rechtssystem_fuer_skill(
                state.vermutete_rechtsgebiete[0].skill)
        if extraction.rechtssystem_tiefe:
            for _tk, _tv in extraction.rechtssystem_tiefe.items():
                if _tv is not None and str(_tv).strip():
                    state.sachverhalts_tiefe[_tk] = str(_tv).strip()

        # P7: explizite Einschätzungs-Anfragen als Begehr verbuchen (überspringt
        # hypothesen_test, wenn Nutzer das Ziel schon klar genannt hat).
        was_now = store.active("was") or ""
        if was_now and ("einschätz" in was_now.lower() or "rechtlich" in was_now.lower()):
            state.begehr_geklaert = True

        offene = list(dict.fromkeys(extraction.offene_punkte))
        missing = [s for s in self.lib.pflicht_ids
                   if not store.filled(s) and s not in state.skipped_slots]
        force = (state.turns >= config.MAX_TURNS
                 or state.no_progress >= config.MAX_NO_PROGRESS)
        debug = {"matched_terms": match.matched_terms, "signal_score": match.signal_score,
                 "no_progress": state.no_progress, "genug_infos": extraction.genug_infos}

        # Begehr-Klärung bei Sensibilität (einmalig, vor dem Handoff).
        # Greift auch bei Single-Skill-Fällen (z.B. KV mit nur strafrecht), damit
        # alle Begehr-Pfade inkl. Schmerzensgeld/Schadensersatz sichtbar werden.
        # Erst nach 2 LLM-Konkretisierungs-Turns ODER wenn alle Pflicht-Slots
        # gefüllt sind — sonst greift sie zu früh.
        if (not force and state.sensibilitaet in ("hoch", "sehr hoch")
                and state.vermutete_rechtsgebiete
                and not state.begehr_geklaert
                and (not missing or state.turns >= 3)):
            state.begehr_geklaert = True
            # Konstellations-IDs für kontextgenaue Hilfsangebote: signal-belegte +
            # vom LLM validierte Konstellationen, dedupliziert.
            konst_ids = list(dict.fromkeys(list(match.konstellationen.keys()) + validated_konst))
            frage = self.coach.hypothesen_test(self._sachverhalt(store),
                                               state.sensibilitaet, konst_ids)
            state.messages.append({"role": "assistant", "content": frage})
            return MessageResponse(session_id=state.session_id, modus="frage",
                                   frage=frage, turns=state.turns, debug=debug)

        # P6/F1: Doppelfragen-Filter — gegen die letzten N Bot-Fragen prüfen
        # (nicht nur die direkt vorherige), sonst rutschen Wiederholungen von
        # Frage 3↔7 durch.
        last_bots = [m["content"] for m in reversed(state.messages)
                     if m.get("role") == "assistant"][:6]
        if extraction.naechste_frage and any(_too_similar(extraction.naechste_frage, b)
                                              for b in last_bots):
            extraction.naechste_frage = None
            debug["question_repeat_dropped"] = True

        # Handoff, wenn: LLM meldet genug_infos · ODER alle Pflicht-Slots gefüllt
        # ohne offene Frage · ODER P10 (alle Slots + Begehr geklärt + starkes
        # Routing) · ODER Force-Stop.
        ask_more = bool(extraction.naechste_frage) and not extraction.genug_infos
        # Sachverhaltstiefe ausreichend? StR: tatbestand_subj nötig; ÖR: bescheid_art
        # oder Grundrechte; ZR: keine zusätzliche Bedingung.
        tiefe_ok = self._tiefe_ausreichend(state)
        # genug_infos-Handoff erst ab Turn 2 UND Tiefe ausreichend — mindestens EINE
        # Rückfrage muss gestellt und die rechtssystem-spez. Mindestinfos bekannt sein.
        genug = (extraction.genug_infos and store.filled("woraus")
                 and state.turns >= 2 and tiefe_ok)
        top_conf = state.vermutete_rechtsgebiete[0].confidence if state.vermutete_rechtsgebiete else 0.0
        # Vollständig: alle Pflicht-Slots + Begehr + gutes Routing + Tiefe ausreichend
        strong_done = (not missing and state.begehr_geklaert and top_conf > 0.7 and tiefe_ok)
        # F4: Profis brauchen weniger Konkretisierung — nach 2 Turns mit
        # gefülltem woraus + halbwegs sicherem Routing direkt zum Handoff (keine Tiefe-Pflicht).
        profi_done = (state.sprachstil == "profi" and state.turns >= 2
                      and store.filled("woraus") and top_conf > 0.6)
        if force or genug or strong_done or profi_done or (not missing and not ask_more and tiefe_ok):
            if not store.filled("was"):
                store.update("was", _DEFAULT_BEGEHR, state.turns)
            for s in missing:
                if s != "was" and s not in state.skipped_slots:
                    state.skipped_slots.append(s)
            offene = list(dict.fromkeys(
                offene + [f"{s} nicht angegeben" for s in state.skipped_slots]))
            return self._handoff(state, match, offene,
                                 vollstaendig=not state.skipped_slots, debug=debug)

        # Weiterfragen: bevorzugt die LLM-geführte konkrete Frage; sonst statischer
        # Fallback (frageketten) auf den ersten fehlenden Pflicht-Slot.
        if extraction.naechste_frage:
            frage = extraction.naechste_frage.strip()
            state.pending_slot = None
        else:
            # Statischer Tiefe-Fallback: wenn alle Pflicht-Slots gefüllt, aber
            # rechtssystem-spezifische Mindestinfos noch fehlen.
            tiefe_fallback = self._tiefe_naechste_frage(state) if not missing else None
            if tiefe_fallback:
                frage = tiefe_fallback
                state.pending_slot = None
            else:
                nxt = next((s for s in self.lib.pflicht_reihenfolge if s in missing),
                           missing[0] if missing else "woraus")
                state.pending_slot = nxt
                frage = self.coach.frage(nxt, state.sprachstil, state.turns)
        state.messages.append({"role": "assistant", "content": frage})
        return MessageResponse(session_id=state.session_id, modus="frage",
                               frage=frage, turns=state.turns, debug=debug)

    # ── Helfer ───────────────────────────────────────────────────────────
    def _tiefe_ausreichend(self, state) -> bool:
        """True wenn die rechtssystem-spezifischen Mindest-Tiefenfelder vorliegen.

        StR: subjektiver Tatbestand (Vorsatz/Fahrlässigkeit) muss bekannt sein.
        ÖR:  Bescheid-Art ODER betroffene Grundrechte/Interessen muss bekannt sein.
        ZR:  keine zusätzliche Pflicht — woraus allein reicht für ZR.
        """
        if not state.vermutete_rechtsgebiete:
            return True
        rs = config.rechtssystem_fuer_skill(state.vermutete_rechtsgebiete[0].skill)
        tiefe = getattr(state, 'sachverhalts_tiefe', {}) or {}
        if rs == "StR":
            return bool(tiefe.get("tatbestand_subj"))
        if rs == "ÖR":
            return bool(tiefe.get("bescheid_art")
                        or tiefe.get("betroffene_grundrechte_interessen"))
        return True  # ZR

    def _tiefe_naechste_frage(self, state) -> Optional[str]:
        """Statische Fallback-Frage für das nächste offene Tiefe-Feld.

        Wird verwendet, wenn das LLM keine naechste_frage liefert, aber noch
        Mindestinfos fehlen. Fragt das jeweils erste noch offene Tiefe-Feld ab.
        Laiengerecht formuliert, kein Juristendeutsch.
        """
        if not state.vermutete_rechtsgebiete:
            return None
        rs = config.rechtssystem_fuer_skill(state.vermutete_rechtsgebiete[0].skill)
        tiefe = getattr(state, 'sachverhalts_tiefe', {}) or {}
        # Nur Pflicht-Felder im statischen Fallback — Optional-Felder werden nie
        # systematisch als statischer Fallback eingesetzt.
        if rs == "StR":
            _felder = [
                ("tatbestand_subj",
                 "Gibt es Anzeichen dafür, dass der andere nicht mit Absicht gehandelt hat — "
                 "also nicht wusste, was er tat, oder es gar nicht so wollte? "
                 "Oder spricht alles für ein bewusstes Vorgehen?"),
            ]
        elif rs == "ÖR":
            _felder = [
                ("bescheid_art",
                 "Was für einen Bescheid oder welche Maßnahme haben Sie von der Behörde "
                 "erhalten — gibt es ein Schreiben oder eine mündliche Entscheidung?"),
                ("betroffene_grundrechte_interessen",
                 "Welche Ihrer Rechte oder Interessen sind durch die behördliche "
                 "Maßnahme konkret beeinträchtigt?"),
            ]
        else:
            return None
        for _fid, _frage in _felder:
            if not tiefe.get(_fid):
                return _frage
        return None

    def _pending_weiche(self, state) -> Optional[tuple]:
        """Returns (weiche_id, weiche_def) for the highest-priority unfired Weichenstellung, or None."""
        if not config.ENABLE_WEICHEN:
            return None
        if not state.vermutete_rechtsgebiete:
            return None
        top_skill = state.vermutete_rechtsgebiete[0].skill
        top_conf  = state.vermutete_rechtsgebiete[0].confidence
        corpus = " ".join(
            m.get("content", "") for m in state.messages if m.get("role") == "user"
        ).lower()
        # LLM-normalisierte Signale (Grundformen, z.B. "Kündigung" statt "gekuendigt")
        llm_sig_set = {s.lower() for s in (state.signale or [])}
        candidates = []
        for wid, wdef in self.lib.weichenstellungen.items():
            if wdef.get("skill") != top_skill:
                continue
            if top_conf < wdef.get("trigger_confidence", 0.6):
                continue
            if wid in state.geklärte_weichen:
                continue
            signals = [s.lower() for s in (wdef.get("trigger_signals") or [])]
            # Rohkorpus-Check (direkte Substrings) ODER LLM-Grundform-Check
            if not (any(s in corpus for s in signals)
                    or any(s in llm_sig_set for s in signals)):
                continue
            candidates.append((wdef.get("priority", 99), wid, wdef))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        _, wid, wdef = candidates[0]
        return wid, wdef

    def slots(self, state) -> SlotStore:
        return state.slots

    def _skill_kandidaten(self, match: MatchResult, llm_rg: dict) -> list[SkillKandidat]:
        # Noisy-OR aus Signal-Score und LLM-Vorschlag pro Skill.
        all_ = []
        for sk in set(match.signal_score) | set(llm_rg):
            s = match.signal_score.get(sk, 0.0)
            l = max(0.0, min(1.0, llm_rg.get(sk, 0.0)))
            conf = round(1 - (1 - s) * (1 - 0.9 * l), 3)
            if conf > config.CONFIDENCE_THRESHOLD:
                all_.append((sk, conf, s, l))
        all_.sort(key=lambda x: -x[1])
        if not all_:
            return []
        # Primär immer behalten; Sekundär nur, wenn deutlich nahe am Primärwert
        # ODER eigene starke Evidenz (Signal- oder LLM-Confidence ≥ 0.5).
        primary_conf = all_[0][1]
        cutoff = max(config.CONFIDENCE_THRESHOLD, primary_conf * config.SECONDARY_MIN_RATIO)
        keep = [all_[0]]
        for sk, conf, s, l in all_[1:]:
            if conf >= cutoff or s >= 0.5 or l >= 0.5:
                keep.append((sk, conf, s, l))
        keep = keep[:config.MAX_RECHTSGEBIETE]
        return [SkillKandidat(skill=sk, confidence=conf) for sk, conf, _, _ in keep]

    def _sachverhalt(self, store: SlotStore) -> Sachverhalt:
        return Sachverhalt(wer=store.active("wer"), was=store.active("was"),
                           von_wem=store.active("von_wem"), woraus=store.active("woraus"))

    def _ag_from_norms(self, norms: list[str], base: float) -> list[AnspruchsGrundlage]:
        out, seen = [], set()
        for i, n in enumerate(norms):
            aid = heuristics.synth_ag_id(n)
            if aid in seen:
                continue
            seen.add(aid)
            out.append(AnspruchsGrundlage(id=aid, norm=n,
                       confidence=round(max(0.4, min(0.95, base - 0.05 * i)), 3)))
        return out

    def _konstellation_kandidaten(self, match: MatchResult) -> list[KonstellationKandidat]:
        out = []
        for kid, conf in sorted(match.konstellationen.items(), key=lambda x: -x[1]):
            meta = self.lib.konstellationen.get(kid)
            if not meta:
                continue
            straf, zivil = meta["straf"], meta["zivil"]
            kern_norms = straf[:1] + zivil[:1]                       # Lead-AG je Facette
            weitere_norms = straf[1:3] + zivil[1:3] + meta["oeff"][:1] + meta["weitere"][:1]
            out.append(KonstellationKandidat(
                id=kid, titel=meta["titel"], rechtsgebiete=meta["rechtsgebiete"],
                kern_normen=self._ag_from_norms(kern_norms, min(0.95, conf + 0.1)),
                weitere_normen=self._ag_from_norms(weitere_norms, conf),
                confidence=conf, sensibilitaet=meta["sensibilitaet"]))
        return out[:config.MAX_RECHTSGEBIETE]

    def _flat_ags(self, konstellationen: list[KonstellationKandidat],
                  match: MatchResult, llm_normen: list[str]) -> list[AnspruchsGrundlage]:
        out, seen, per_group = [], set(), {}

        def grp(aid: str) -> str:
            p = aid.split("_")
            return p[1] if len(p) > 1 else aid

        def push(ag: AnspruchsGrundlage) -> bool:
            if ag.id in seen or per_group.get(grp(ag.id), 0) >= config.AG_MAX_PER_GESETZ:
                return False
            seen.add(ag.id)
            per_group[grp(ag.id)] = per_group.get(grp(ag.id), 0) + 1
            out.append(ag)
            return len(out) >= config.MAX_ANSPRUCHSGRUNDLAGEN

        # 0) LLM-vorgeschlagene Normen ZUERST (fallkonkret, validiert)
        for i, nrm in enumerate(llm_normen):
            if push(AnspruchsGrundlage(id=heuristics.synth_ag_id(nrm), norm=nrm,
                    confidence=round(max(0.5, 0.9 - 0.05 * i), 3))):
                return out
        # 1) aus den Konstellationen (Kern zuerst, dann weitere)
        for pool in ("kern_normen", "weitere_normen"):
            for kand in konstellationen:
                for ag in getattr(kand, pool):
                    if push(ag):
                        return out
        # 2) Signal-Norm-Hits NUR als Fallback, wenn das LLM keine Normen lieferte
        #    (Signal-Hits sind die Hauptquelle für Substring-Fehltreffer, z.B.
        #    "zu spät kam" → Verjährung §194-196).
        if not llm_normen:
            top = max(match.signal_score.values(), default=0.6)
            for i, norm in enumerate(match.norm_hits):
                ag = AnspruchsGrundlage(id=heuristics.synth_ag_id(norm), norm=norm,
                                        confidence=round(max(0.4, min(0.95, top - 0.05 * i)), 3))
                if push(ag):
                    return out
        return out

    def _handoff(self, state, match, offene, vollstaendig, debug) -> MessageResponse:
        store = self.slots(state)
        konstellationen = self._konstellation_kandidaten(match)
        handoff = Handoff(
            session_id=state.session_id, created_at=state.created_at,
            sachverhalt=self._sachverhalt(store),
            vermutete_konstellationen=konstellationen,
            vermutete_anspruchsgrundlagen=self._flat_ags(konstellationen, match, state.llm_normen),
            vermutete_rechtsgebiete=state.vermutete_rechtsgebiete,
            sprachstil=state.sprachstil, sensibilitaet=state.sensibilitaet,
            offene_punkte=offene, vollstaendig=vollstaendig, turns=state.turns,
            weichen_slots=dict(getattr(state, 'weichen_slots', {})),
            weichen_offene=[wid for wid in self.lib.weichenstellungen
                            if wid not in getattr(state, 'geklärte_weichen', [])],
            sachverhalts_tiefe=dict(getattr(state, 'sachverhalts_tiefe', {})),
            rechtssystem=getattr(state, 'rechtssystem', None),
        )
        state.vollstaendig = vollstaendig
        state.last_handoff = handoff.model_dump()   # für Orchestrator-Query
        return MessageResponse(session_id=state.session_id, modus="handoff",
                               handoff=handoff, turns=state.turns, debug=debug)


if __name__ == "__main__":
    import json
    lib = SchemaLibrary(config.SCHEMA_DIR)
    print(json.dumps(lib.stats(), ensure_ascii=False, indent=2))
