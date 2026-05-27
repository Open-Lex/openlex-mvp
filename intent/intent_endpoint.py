"""FastAPI-Endpoint des Intent-Skills (Port 7870, isoliert von der Live-App)."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool

import config
import session
import telemetry
from concurrent.futures import ThreadPoolExecutor

# ── Log-Filter: PII aus uvicorn/app-Logs fernhalten ─────────────────────────
class _PiiFilter(logging.Filter):
    """Unterdrückt Zeilen, die Session-IDs oder Request-Bodies enthalten könnten."""
    _BLOCK = ("session_id", "text", "password", "content")
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage().lower()
        # Nur uvicorn access-Zeilen mit body-artigen Inhalten blockieren
        return not any(k in msg for k in self._BLOCK) or record.name != "uvicorn.access"

logging.getLogger("uvicorn.access").addFilter(_PiiFilter())

from coach import Coach
from engine import IntentEngine, SchemaLibrary, SignalMatcher
from llm_caller import LLMCaller
from models import (
    MessageRequest, MessageResponse, RouteMultiResponse, RouteResponse,
    StartSessionResponse,
)
from orchestrator import Orchestrator

# Menschenlesbare Labels für Wrong-Collection-Guard-Hinweise
_SKILL_LABELS: dict[str, str] = {
    "strafrecht": "Strafrecht", "grundrechte": "Grundrechte / Verfassungsrecht",
    "verbraucherrecht": "Verbraucherrecht", "kaufrecht": "Kaufrecht",
    "mietrecht": "Mietrecht", "arbeitsrecht": "Arbeitsrecht",
    "familienrecht": "Familienrecht", "erbrecht": "Erbrecht",
    "verwaltungsrecht": "Verwaltungsrecht", "gesellschaftsrecht": "Gesellschaftsrecht",
    "insolvenzrecht": "Insolvenzrecht", "datenschutz": "Datenschutz",
    "it_recht": "IT-Recht", "europarecht": "Europarecht",
    "staatsorganisationsrecht": "Staatsorganisationsrecht",
    "verfassungsprozessrecht": "Verfassungsprozessrecht",
    "wirtschaftsstrafrecht": "Wirtschaftsstrafrecht",
    "sozialrecht": "Sozialrecht", "steuerrecht": "Steuerrecht",
    "umweltrecht": "Umweltrecht", "baurecht": "Baurecht",
}
# Unterhalb dieser Confidence wird ein Routing-Hinweis angezeigt
_LOW_CONF_ROUTING_THRESHOLD = 0.32

app = FastAPI(title="OpenLex Intent-Skill", version="intent-handoff/1.0")

# Singletons (einmalig beim Start)
_lib = SchemaLibrary(config.SCHEMA_DIR)
_matcher = SignalMatcher(_lib)
_coach = Coach(_lib)
_llm = LLMCaller(_coach)
_engine = IntentEngine(_lib, _matcher, _llm, _coach)
_orch = Orchestrator()


@app.on_event("startup")
def _startup() -> None:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    session.cleanup_expired()


def _health_payload() -> dict:
    return {
        "status": "ok",
        "providers_available": {
            "mistral": bool(config.MISTRAL_KEY),
            "ollama": _llm._ollama_model() is not None,
        },
        "signals": len(_lib.signals),
    }


@app.get("/admin/health")
@app.get("/admin/")
def admin_health() -> dict:
    """Admin-Diagnose — nur über /admin/ erreichbar (nginx blockiert /intent/health extern)."""
    return _health_payload()


@app.get("/admin/metrics")
def admin_metrics() -> dict:
    """Aggregierte Telemetrie-Metriken (kein PII). Nginx schützt mit Basic-Auth."""
    return telemetry.metrics()


@app.get("/intent/health")
def health() -> dict:
    """Interner Health-Check (nur per SSH-Tunnel / direktem curl auf 127.0.0.1:7870)."""
    return _health_payload()


@app.post("/intent/session", response_model=StartSessionResponse)
def start_session() -> StartSessionResponse:
    session.cleanup_expired()
    state = session.SessionState.new()
    frage = _engine.start(state)
    session.save(state)
    telemetry.record("session_started", state.session_id, sprachstil=state.sprachstil)
    return StartSessionResponse(session_id=state.session_id, frage=frage)


@app.post("/intent/message", response_model=MessageResponse)
def message(req: MessageRequest) -> MessageResponse:
    state = session.load(req.session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen")
    had_progress = state.no_progress == 0
    resp = _engine.step(state, req.text)
    session.save(state)
    # DSGVO/PII: debug-Feld (matched_terms etc.) nur im Dev-Modus zurückgeben
    if not config.INCLUDE_DEBUG_IN_RESPONSE:
        resp.debug = None
    # Telemetrie
    telemetry.record("turn", state.session_id, turn_nr=state.turns,
                     slot_progress=had_progress)
    if resp.modus == "handoff" and resp.handoff:
        h = resp.handoff
        top = h.vermutete_rechtsgebiete[0] if h.vermutete_rechtsgebiete else None
        telemetry.record("handoff", state.session_id,
                         turns=state.turns,
                         skill=top.skill if top else None,
                         confidence=top.confidence if top else None,
                         vollstaendig=h.vollstaendig,
                         sprachstil=state.sprachstil)
    return resp


@app.post("/intent/message/stream")
async def message_stream(req: MessageRequest) -> StreamingResponse:
    """SSE-Endpoint: verarbeitet die Nachricht blockend, streamt dann die Antwort wortweise."""
    state = session.load(req.session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen")

    # engine.step() blockiert (LLM-Call) → in Thread-Pool auslagern
    resp = await run_in_threadpool(_engine.step, state, req.text)
    session.save(state)
    if not config.INCLUDE_DEBUG_IN_RESPONSE:
        resp.debug = None

    async def generate():
        if resp.modus == "frage":
            text = resp.frage or ""
            words = text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'t': chunk})}\n\n"
                delay = 0.055 if chunk.rstrip() and chunk.rstrip()[-1] in ".?!:;" else 0.030
                await asyncio.sleep(delay)
            yield f"data: {json.dumps({'done': True, 'modus': 'frage'})}\n\n"
        else:
            # Handoff: kurzen Bestätigungstext streamen, dann Metadaten senden
            hdict = resp.handoff.dict() if resp.handoff else {}
            rgs = hdict.get("vermutete_rechtsgebiete", [])
            strong = [k for k in rgs if k.get("confidence", 0) >= 0.4]
            label = " + ".join(k["skill"] for k in strong[:2]) if strong else (rgs[0]["skill"] if rgs else "?")
            text = f"✓ Sachverhalt erfasst ({label})."
            words = text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'t': chunk})}\n\n"
                await asyncio.sleep(0.035)
            yield f"data: {json.dumps({'done': True, 'modus': 'handoff', 'handoff': hdict})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _build_skill_query(state) -> str:
    """Reichhaltiger Query: alle User-Aussagen + Handoff-Kontext."""
    # Weichen-Präambel (Layer 2) — natural language für besseres Embedding + RAG-LLM-Kontext
    w_lib = getattr(_lib, 'weichenstellungen', {}) or {}
    wslots = getattr(state, 'weichen_slots', None) or {}
    preamble_lines = []
    for _wid in (getattr(state, 'geklärte_weichen', None) or []):
        _wdef = w_lib.get(_wid, {})
        if not _wdef:
            continue
        _bslot = _wdef.get("branch_slot", _wid)
        _stored = wslots.get(_bslot)
        _frage_kurz = (_wdef.get("frage") or _wid).strip()[:65].rstrip(".,? \n")
        # Passendes Option-Label + Recht suchen
        _opt_label, _opt_recht = None, None
        for _o in (_wdef.get("optionen") or []):
            if _o.get("wert") == _stored:
                _opt_label = _o.get("label", "")
                _opt_recht = _o.get("recht", "")
                break
        if _opt_label:
            _val_display = _opt_label
        elif _stored is True:
            _val_display = "ja"
        elif _stored is False:
            _val_display = "nein"
        elif _stored is None:
            _val_display = "unklar"
        else:
            _val_display = str(_stored)
        _line = "- " + _frage_kurz + ": " + _val_display
        if _opt_recht:
            _line += " -> " + _opt_recht
        preamble_lines.append(_line)
    preamble = (
        "Bereits geklärte Rahmenbedingungen (NICHT erneut erfragen!):\n"
        + "\n".join(preamble_lines) + "\n\n"
    ) if preamble_lines else ""

    # Sachverhalts-Tiefe je Rechtssystem (StR/ÖR/ZR — strukturierte Zusatzinfos)
    _tiefe_label = {
        "tatbestand_obj":                   "Tathandlung/Taterfolg",
        "tatbestand_subj":                  "Vorsatz/Fahrlässigkeit",
        "rechtfertigungsgrund":             "Rechtfertigungsgrund",
        "schuldfaktor":                     "Schuldfaktoren",
        "bescheid_art":                     "Behördliche Maßnahme/Bescheid",
        "betroffene_grundrechte_interessen": "Betroffene Grundrechte/Interessen",
        "oeffentliches_interesse":           "Öffentliches Interesse (Gegenseite)",
        "verhaeltnismaessigkeit":            "Verhältnismäßigkeit/Mildere Mittel",
        "fristen_verjährung":               "Fristen/Verjährung",
        "bisherige_schritte":               "Bisherige Schritte",
        "beweismittel":                     "Beweismittel",
    }
    _tiefe = getattr(state, 'sachverhalts_tiefe', {}) or {}
    _tiefe_lines = [
        "- " + _tiefe_label.get(k, k.replace('_', ' ')) + ": " + str(v)
        for k, v in _tiefe.items() if v
    ]
    if _tiefe_lines:
        preamble += "Weitere Sachverhaltsdetails:\n" + "\n".join(_tiefe_lines) + "\n\n"

    h = state.last_handoff or {}
    sv = h.get("sachverhalt") or {}
    woraus = sv.get("woraus") or state.slots.active("woraus") or ""
    was = sv.get("was") or state.slots.active("was") or "eine rechtliche Einschätzung"
    user_msgs = [m["content"] for m in state.messages if m.get("role") == "user"]
    user_corpus = "\n".join(f"- {m}" for m in user_msgs)
    konst = ", ".join(k.get("titel", k.get("id", ""))
                      for k in (h.get("vermutete_konstellationen") or []))
    ags = ", ".join(a.get("norm", "") for a in (h.get("vermutete_anspruchsgrundlagen") or []))
    return (preamble +
            "Mandantenaufnahme (Originaltext):\n" + user_corpus + "\n\n" +
            f"Zusammenfassung: {woraus}\n" +
            f"Anliegen des Mandanten: {was}\n" +
            (f"Erkannte juristische Facetten: {konst}\n" if konst else "") +
            (f"Mutmaßlich einschlägige Normen: {ags}\n" if ags else "") +
            "Bitte eine erste rechtliche Einschätzung — gehe auf die zentralen "
            "Normen ein und nenne die nächsten Schritte für den Mandanten.")


def _call_one(target, query, secondary, sid) -> RouteResponse:
    err, answer = None, ""
    try:
        answer = _orch.query(target.skill, query)
        if answer:
            answer = answer.rstrip() + "\n\n---\n_" + config.DISCLAIMER + "_"
    except Exception as e:
        err = repr(e)
    return RouteResponse(session_id=sid, skill_id=target.skill,
                         skill_confidence=target.confidence,
                         secondary_skills=secondary, query=query, answer=answer, error=err)


@app.post("/intent/route_stream/{session_id}")
async def route_stream(session_id: str, skill: str | None = None) -> StreamingResponse:
    """SSE-Streaming-Variante von /route: Gradio-Chunks werden live durchgeschleift."""
    state = session.load(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session nicht gefunden")
    if not state.vermutete_rechtsgebiete:
        raise HTTPException(status_code=400, detail="Kein Rechtsgebiet erkannt — Handoff erforderlich")

    # Ghost-Skills: haben (noch) keinen ChromaDB-Bestand → automatisch skippen
    _GHOST_SKILLS: set[str] = {"ipr", "europarecht", "polizei_ordnungsrecht", "kommunalrecht"}

    target = None
    if skill:
        for k in state.vermutete_rechtsgebiete:
            if k.skill == skill:
                target = k; break
        if target is None:
            raise HTTPException(status_code=400, detail=f"Skill '{skill}' nicht im Ranking")
        # Explizit angeforderter Skill ist ein Ghost → Fallback auf besten verfügbaren Skill
        if target.skill in _GHOST_SKILLS:
            fallback = next((k for k in state.vermutete_rechtsgebiete if k.skill not in _GHOST_SKILLS), None)
            if fallback:
                target = fallback
            # else: kein Fallback → Ghost direkt nutzen (SkillNotAvailableError greift auf app-Seite)
    else:
        # Top-Skill wählen; Ghost-Skills überspringen (kein ChromaDB-Bestand)
        for k in state.vermutete_rechtsgebiete:
            if k.skill not in _GHOST_SKILLS:
                target = k
                break
        if target is None:
            target = state.vermutete_rechtsgebiete[0]  # Fallback: erstes (auch Ghost)

    other = [k.skill for k in state.vermutete_rechtsgebiete if k.skill != target.skill]
    query = _build_skill_query(state)

    async def generate():
        # Meta-Event: Skill-ID + secondary (damit das Frontend den Titel kennt)
        yield f"data: {json.dumps({'meta': {'skill_id': target.skill, 'confidence': target.confidence, 'secondary': other}})}\n\n"

        # Wrong-Collection-Guard: Routing-Hinweis bei niedriger Confidence
        # Verhindert stumme Fehlrouting-Erfahrungen und zeigt alternative Rechtsgebiete an.
        if target.confidence < _LOW_CONF_ROUTING_THRESHOLD and other:
            _skill_label = _SKILL_LABELS.get(target.skill, target.skill)
            _alt_label   = _SKILL_LABELS.get(other[0], other[0])
            _warning = (
                f"⚠️ *Hinweis: Diese Anfrage wurde mit geringer Sicherheit "
                f"dem Rechtsgebiet **{_skill_label}** zugeordnet "
                f"({target.confidence:.0%} Konfidenz). "
                f"Alternativ könnte **{_alt_label}** relevant sein. "
                f"Bitte prüfen Sie die Antwort kritisch.*\n\n"
            )
            yield f"data: {json.dumps({'t': _warning})}\n\n"
            await asyncio.sleep(0)

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def producer():
            try:
                for chunk in _orch.query_stream(target.skill, query):
                    loop.call_soon_threadsafe(queue.put_nowait, ("t", chunk))
                # Disclaimer ans Ende
                disc = f"\n\n---\n_{config.DISCLAIMER}_"
                loop.call_soon_threadsafe(queue.put_nowait, ("t", disc))
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
                telemetry.record("skill_routed", session_id,
                                 skill=target.skill, streamed=True)
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, ("error", repr(exc)))

        import threading
        threading.Thread(target=producer, daemon=True).start()

        while True:
            kind, data = await queue.get()
            if kind == "t":
                yield f"data: {json.dumps({'t': data})}\n\n"
            elif kind == "done":
                yield f"data: {json.dumps({'done': True, 'skill_id': target.skill})}\n\n"
                break
            else:  # error
                yield f"data: {json.dumps({'error': data})}\n\n"
                break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/intent/route/{session_id}", response_model=RouteResponse)
def route(session_id: str, skill: str | None = None) -> RouteResponse:
    """Orchestrator-Aufruf: schickt den Sachverhalt an einen Skill (Dev-App,
    Gradio-API) und liefert dessen Antwort zurück. Default: top-bewerteter Skill;
    via Query-Param `?skill=<slug>` ein anderer der vermuteten Rechtsgebiete."""
    state = session.load(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session nicht gefunden")
    if not state.vermutete_rechtsgebiete:
        raise HTTPException(status_code=400, detail="Kein Rechtsgebiet erkannt — Handoff erforderlich")

    target = None
    if skill:
        for k in state.vermutete_rechtsgebiete:
            if k.skill == skill:
                target = k; break
        if target is None:
            raise HTTPException(status_code=400, detail=f"Skill '{skill}' nicht im Ranking")
    else:
        target = state.vermutete_rechtsgebiete[0]
    other = [k.skill for k in state.vermutete_rechtsgebiete if k.skill != target.skill]
    return _call_one(target, _build_skill_query(state), other, session_id)


@app.post("/intent/route_all/{session_id}", response_model=RouteMultiResponse)
def route_all(session_id: str, max: int = None) -> RouteMultiResponse:
    """Multi-Skill: top-N Skills (conf ≥ MULTI_SKILL_MIN_CONF, max MAX_AUTO_SKILLS)
    parallel aufrufen — sinnvoll bei Multi-Facetten-Fällen."""
    state = session.load(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session nicht gefunden")
    if not state.vermutete_rechtsgebiete:
        raise HTTPException(status_code=400, detail="Kein Rechtsgebiet erkannt — Handoff erforderlich")

    cap = max if max else config.MAX_AUTO_SKILLS
    selected = [k for k in state.vermutete_rechtsgebiete
                if k.confidence >= config.MULTI_SKILL_MIN_CONF][:cap]
    if not selected:                                                # mind. Top-1
        selected = state.vermutete_rechtsgebiete[:1]
    query = _build_skill_query(state)
    chosen = {k.skill for k in selected}
    other = [k.skill for k in state.vermutete_rechtsgebiete if k.skill not in chosen]

    with ThreadPoolExecutor(max_workers=len(selected)) as pool:
        futures = [pool.submit(_call_one, k, query, other, session_id) for k in selected]
        results = [f.result() for f in futures]
    return RouteMultiResponse(session_id=session_id, query=query, results=results)


@app.get("/intent/session/{session_id}")
def get_session(session_id: str) -> dict:
    state = session.load(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session nicht gefunden")
    return state.to_dict()


@app.delete("/intent/session/{session_id}")
def delete_session(session_id: str) -> dict:
    """DSGVO Art. 17: Recht auf Löschung — entfernt die Session-Datei sofort."""
    removed = session.delete(session_id)
    return {"deleted": removed, "session_id": session_id}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(config.STATIC_DIR / "index.html")


@app.get("/intent/")
def intent_index() -> FileResponse:
    """Test-UI auch unter /intent/ erreichbar (für nginx-Proxy-Zugang)."""
    return FileResponse(config.STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
