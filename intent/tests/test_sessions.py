"""Wave-4-Tests: 6 Beispiel-Sessions (LLM gemockt → deterministisch, offline)
plus Unit-Tests für SchemaLibrary, SlotStore, synth_ag_id, compute_confidence."""
from __future__ import annotations

import config
import heuristics
from coach import Coach
from engine import IntentEngine, SchemaLibrary, SignalMatcher, SlotStore
from models import Extraction, compute_confidence
from session import SessionState

LIB = SchemaLibrary(config.SCHEMA_DIR)


class FakeLLM:
    """Liefert vorgegebene Extraction-Objekte der Reihe nach."""
    def __init__(self, *extractions: Extraction):
        self.queue = list(extractions)

    def extract(self, history, user_text, state=None) -> Extraction:
        return self.queue.pop(0) if self.queue else Extraction()


def make_engine(*extractions: Extraction) -> tuple[IntentEngine, SessionState]:
    coach = Coach(LIB)
    engine = IntentEngine(LIB, SignalMatcher(LIB), FakeLLM(*extractions), coach)
    state = SessionState.new()
    engine.start(state)
    return engine, state


def skills(state) -> set[str]:
    return {k.skill for k in state.vermutete_rechtsgebiete}


# ── Test 1: Laie, einfach ────────────────────────────────────────────────
def test_1_laie_mietrecht():
    eng, st = make_engine(Extraction(
        woraus="Vermieter heizt die Wohnung nicht",
        von_wem="Vermieter", erkannte_signale=["vermieter", "heizung"], sprachstil="laie"))
    resp = eng.step(st, "Mein Vermieter heizt nicht")
    assert resp.modus == "frage"                 # was/wer fehlen noch
    assert "mietrecht" in skills(st)
    assert st.sprachstil == "laie"
    # AG-Abdeckung über Matcher
    m = SignalMatcher(LIB).match("vermieter heizung")
    assert any("§ 536 BGB" in n for n in m.norm_hits)


# ── Test 2: Profi, knapp → Handoff in einem Turn ──────────────────────────
def test_2_profi_einturn_handoff():
    eng, st = make_engine(Extraction(
        woraus="Mietminderung wegen Heizungsausfall", was="Mietminderung",
        von_wem="Vermieter", wer="Mieter", erkannte_signale=["mietminderung"],
        sprachstil="profi"))
    resp = eng.step(st, "Anspruch des Mieters aus § 536 BGB auf Mietminderung")
    assert st.sprachstil == "profi"              # §-Regex in heuristics.resolve
    assert resp.modus == "handoff"
    assert resp.handoff.sprachstil == "profi"
    assert resp.handoff.vollstaendig is True


# ── Test 3: Multi-Skill ───────────────────────────────────────────────────
def test_3_multiskill_miete_datenschutz():
    eng, st = make_engine(Extraction(
        woraus="Vermieter hat private Daten an die Schufa weitergegeben",
        von_wem="Vermieter", was="Löschung und Unterlassung", wer="Mieter",
        erkannte_signale=["vermieter", "privates verbreitet"], sprachstil="laie"))
    eng.step(st, "Mein Vermieter gab private Daten an die Schufa weiter")
    assert "mietrecht" in skills(st)
    assert "datenschutz" in skills(st)           # via querverstrebung privatheit_daten


# ── Test 4: Vage Laie → erste Slot-Frage (woraus) ─────────────────────────
def test_4_vage_laie_fragt_woraus():
    eng, st = make_engine(Extraction())          # nichts extrahiert
    resp = eng.step(st, "Ich habe Probleme")
    assert resp.modus == "frage"
    assert resp.frage in LIB.frageketten["woraus"]["laie"]


# ── Test 5: Abbruch nach MAX_TURNS ────────────────────────────────────────
def test_5_abbruch_zwangshandoff():
    eng, st = make_engine(*[Extraction() for _ in range(config.MAX_TURNS)])
    resp = None
    for _ in range(config.MAX_TURNS):
        resp = eng.step(st, "hmm weiß nicht so genau")
    assert resp.modus == "handoff"
    assert resp.handoff.vollstaendig is False
    assert resp.handoff.offene_punkte                # fehlende Pflicht-Slots gelistet


# ── Test 6: Querverstrebung (Begehr-Klärung → Tiefe-Frage → Handoff) ────────
def test_6_querverstrebung_koerperverletzung():
    # StR-Fälle benötigen tatbestand_subj (Vorsatz/Fahrlässigkeit) bevor Handoff
    # möglich ist — Turn 2 liefert Tiefe, Turn 3 ist Handoff.
    eng, st = make_engine(
        Extraction(woraus="Nachbar hat mich geschlagen",
                   was="Schmerzensgeld und Anzeige", von_wem="Nachbar",
                   wer="Geschädigter", erkannte_signale=["geschlagen", "schmerzensgeld"],
                   sprachstil="laie"),
        Extraction(),   # Begehr-Antwort "beides" → Engine stellt Tiefe-Frage (subj. TB)
        Extraction(rechtssystem_tiefe={"tatbestand_subj": "absichtlich, aus Wut"}))
    r1 = eng.step(st, "Mein Nachbar hat mich geschlagen, ich will Schmerzensgeld und Anzeige")
    assert r1.modus == "frage"                    # Begehr-Klärung bei Sensibilität
    assert st.sensibilitaet == "hoch"
    assert ("Anzeige" in r1.frage or "Schmerzensgeld" in r1.frage)
    assert "strafrecht" in skills(st)

    r2 = eng.step(st, "beides bitte")
    assert r2.modus == "frage"                    # StR: tatbestand_subj noch unbekannt
    assert r2.frage                               # Frage nach Absicht/Fahrlässigkeit

    r3 = eng.step(st, "ja er hat mich absichtlich aus Wut geschlagen")
    assert r3.modus == "handoff"
    normen = {a.norm for a in r3.handoff.vermutete_anspruchsgrundlagen}
    assert any("§ 223 StGB" in n for n in normen)
    assert any("§ 823" in n for n in normen)
    assert any("§ 253" in n for n in normen)
    assert r3.handoff.sensibilitaet == "hoch"
    # Tiefe im Handoff verfügbar
    assert r3.handoff.sachverhalts_tiefe.get("tatbestand_subj")


# ── Test 7: Multi-Facetten-Fall (Kern/Kontext + Konstellationen) ──────────
def test_7_multifacet_konstellationen():
    eng, st = make_engine(
        Extraction(woraus="beschimpft, geschlagen und bestohlen",
                   was="rechtliche Einschätzung", von_wem="jemand", wer="Ich",
                   erkannte_signale=["beschimpft", "geschlagen", "weggenommen"],
                   sprachstil="laie"),
        Extraction())
    eng.step(st, "mich hat jemand beschimpft und geschlagen und mir was weggenommen")
    r = eng.step(st, "nur rechtliche Einschätzung")
    assert r.modus == "handoff"
    h = r.handoff
    assert h.schema_version == "intent-handoff/1.1"
    ids = {k.id for k in h.vermutete_konstellationen}
    assert {"koerperverletzung", "diebstahl_unterschlagung",
            "beleidigung_uebleNachrede"} <= ids          # alle 3 Facetten
    normen = {a.norm for a in h.vermutete_anspruchsgrundlagen}
    assert any("§ 185" in n for n in normen)             # Beleidigung
    assert any("§ 242" in n for n in normen)             # Diebstahl
    assert any("§ 223" in n for n in normen)             # Körperverletzung
    skills = {k.skill for k in h.vermutete_rechtsgebiete}
    assert "verkehrsrecht" not in skills                 # Kontext-Breite gefiltert
    assert "familienrecht" not in skills


# ── Test 8: LLM-geführte, konkrete Folgefrage wird verwendet ──────────────
def test_8_llm_gefuehrte_frage():
    q = ("Von wem haben Sie die Abmahnung bekommen — von Ihrem Arbeitgeber, "
         "oder z.B. wegen Urheberrecht/Filesharing?")
    eng, st = make_engine(
        Extraction(woraus="Abmahnung erhalten", erkannte_signale=["abmahnung"],
                   naechste_frage=q, sprachstil="laie"))
    r = eng.step(st, "ich bin abgemahnt worden")
    assert r.modus == "frage"
    assert r.frage == q                              # konkrete LLM-Frage, kein Allgemeinplatz


# ── Test 8b: genug_infos → Handoff (adaptive Tiefe) ───────────────────────
def test_8b_genug_infos_handoff():
    eng, st = make_engine(
        Extraction(woraus="Vom Arbeitgeber wegen Zuspätkommens abgemahnt",
                   von_wem="Arbeitgeber", was="wissen ob wirksam", wer="Arbeitnehmer",
                   erkannte_signale=["abmahnung", "arbeitgeber"],
                   genug_infos=True, sprachstil="laie"))
    r = eng.step(st, "abmahnung vom arbeitgeber wegen zu spät kommen, will wissen ob wirksam")
    assert r.modus == "handoff"
    assert r.handoff.vollstaendig is True
    assert "arbeitsrecht" in {k.skill for k in r.handoff.vermutete_rechtsgebiete}


# ── Test 9: Wiederholtes Ausweichen terminiert (kein Endlos-Loop) ─────────
def test_9_deflection_terminiert():
    eng, st = make_engine(
        Extraction(woraus="Streit mit einem Kollegen", sprachstil="laie"),
        Extraction(), Extraction(), Extraction())
    eng.step(st, "ich hatte streit mit einem kollegen")  # Fortschritt
    eng.step(st, "weiss nicht")                          # no_progress = 1
    r = eng.step(st, "keine ahnung")                     # no_progress = 2 → Zwangs-Handoff
    assert r.modus == "handoff"
    assert r.handoff.vollstaendig is False
    assert "Einschätzung" in (st.slots.active("was") or "")   # was weich befüllt


# ── Test 10: Morphologie — Wortabwandlungen matchen ───────────────────────
def test_10_morphologie_flexion():
    import morphology as m
    # Flexionsvarianten teilen denselben Stamm
    assert m.stem("Vermietern") == m.stem("Vermieter")
    assert m.stem("Abmahnungen") == m.stem("Abmahnung")
    assert m.stem("kündigen") == m.stem("Kündigung")
    assert m.stem("mieten") == m.stem("Miete")
    # keine Über-Merges bei unverwandten Wörtern
    assert m.stem("Recht") != m.stem("Rechnung")
    assert m.stem("Vertrag") != m.stem("vertreten")


def test_10b_variant_routing():
    sm = SignalMatcher(LIB)
    # Flexion direkt im Text
    r = sm.match("meine vermietern haben gekündigt")
    assert "mietrecht" in r.signal_score
    # Derivation via LLM-Grundform (Nutzer schrieb "abgemahnt")
    r2 = sm.match("ich bin abgemahnt worden", ["Abmahnung"])
    assert "arbeitsrecht" in r2.signal_score


# ── Test 11: Deflection-Erkennung robust + Begehr-Default ─────────────────
def test_11_deflection_robust():
    import heuristics as h
    # Wortstellungs-Varianten werden erkannt (vorher Lücke bei "es" dazwischen)
    for s in ["ich weiss es nicht", "ich weiß es nicht", "weiss nicht",
              "keine ahnung", "sag du es mir", "ist mir egal", "kein plan"]:
        assert h.is_deflection(s), s
    # echte Antworten sind KEINE Deflection
    for s in ["vom arbeitgeber", "die zweite abmahnung", "er hat mich beleidigt"]:
        assert not h.is_deflection(s), s


def test_11b_begehr_default_bei_ausweichen():
    eng, st = make_engine(
        Extraction(woraus="Vom Arbeitgeber abgemahnt", von_wem="Arbeitgeber",
                   wer="Arbeitnehmer", erkannte_signale=["Abmahnung", "Arbeitgeber"],
                   sprachstil="laie"),
        Extraction())
    eng.step(st, "ich bin vom chef abgemahnt worden")   # was fehlt → fragt
    eng.step(st, "ich weiss es nicht")                   # Ausweichen → was weich gesetzt
    assert "Einschätzung" in (st.slots.active("was") or "")


# ── Test 12: Stopwörter killen das grundrechte-Rauschen ───────────────────
def test_12_stopword_kein_rauschen():
    sm = SignalMatcher(LIB)
    # Possessiv "mein" darf NICHT das Signal "Meinung"→grundrechte triggern
    assert "grundrechte" not in sm.match("mein vermieter reagiert nicht").signal_score
    # echtes "Meinung" wird weiterhin erkannt
    assert "grundrechte" in sm.match("meine meinung wurde unterdrückt").signal_score


# ── Test 13: LLM-gestütztes Routing hebt den Recall ───────────────────────
def test_13_llm_routing_boost():
    from models import LLMRechtsgebiet
    _ext = Extraction(
        woraus="Ein Ex hat private Fotos von mir online gestellt",
        vermutete_rechtsgebiete=[LLMRechtsgebiet(skill="datenschutz", confidence=0.8),
                                 LLMRechtsgebiet(skill="quatschrecht", confidence=0.9)],
        genug_infos=True, sprachstil="laie")
    # genug_infos-Handoff erst ab Turn 2 — Turn 1 liefert eine Rückfrage
    eng, st = make_engine(_ext, _ext)
    eng.step(st, "mein ex hat private fotos von mir online gestellt")   # Turn 1 → frage
    r = eng.step(st, "ja, er hat sie oeffentlich gepostet")             # Turn 2 → handoff
    sk = {k.skill for k in r.handoff.vermutete_rechtsgebiete}
    assert "datenschutz" in sk          # vom LLM beigesteuert (Signal-Matching verfehlt)
    assert "quatschrecht" not in sk     # ungültiger Slug wird verworfen


# ── Test 14: LLM-Normen führen die AGs an + Validierung ───────────────────
def test_14_llm_normen_fuehren():
    from models import LLMRechtsgebiet
    eng, st = make_engine(Extraction(
        woraus="Fristlose Kündigung vom Arbeitgeber wegen angeblicher Arbeitsverweigerung",
        von_wem="Arbeitgeber", was="prüfen ob wirksam", wer="Arbeitnehmer",
        erkannte_signale=["Kündigung", "Arbeitgeber"],
        vermutete_rechtsgebiete=[LLMRechtsgebiet(skill="arbeitsrecht", confidence=0.9)],
        vermutete_normen=["§ 626 BGB", "§ 1 KSchG", "§ 12 QuatschG"],  # letzte: Fake-Gesetz
        genug_infos=True, sprachstil="laie"))
    r = eng.step(st, "fristlose kündigung erhalten, angeblich arbeitsverweigerung")
    normen = {a.norm for a in r.handoff.vermutete_anspruchsgrundlagen}
    assert "§ 626 BGB" in normen and "§ 1 KSchG" in normen
    assert not any("QuatschG" in n for n in normen)   # ungültiges Gesetz verworfen
    # LLM-Normen vorhanden → kein Signal-Beifang (z.B. Verjährung)
    assert normen == {"§ 626 BGB", "§ 1 KSchG"}


# ── Test 15: Sekundär-Rauschen-Filter ─────────────────────────────────────
def test_15_sekundaer_filter():
    from models import MatchResult
    coach = Coach(LIB)
    eng = IntentEngine(LIB, SignalMatcher(LIB), FakeLLM(), coach)
    # Primär hoch, Sekundärs schwach (0.33) und ohne starke Einzelevidenz → raus
    m = MatchResult(signal_score={"arbeitsrecht": 0.92, "mietrecht": 0.33,
                                  "verkehrsrecht": 0.33})
    skills = [k.skill for k in eng._skill_kandidaten(m, {})]
    assert skills == ["arbeitsrecht"]
    # Wenn die LLM-Evidenz für einen Sekundär stark ist, bleibt er drin
    skills2 = {k.skill for k in eng._skill_kandidaten(m, {"mietrecht": 0.6})}
    assert "arbeitsrecht" in skills2 and "mietrecht" in skills2


# ── Test 16: Orchestrator-Antwort-Extraktion (Regression-Guard) ───────────
def test_16_orchestrator_extract_answer():
    """Garantiert, dass die _extract_answer-Methode existiert und die
    Gradio-Tuple-Antwort korrekt parst (sonst Bug wie nach Iteration 2)."""
    from orchestrator import Orchestrator
    orch = Orchestrator()
    # Neues role/content-Format (Gradio 4+/6+)
    history = [{"role": "user", "content": [{"type": "text", "text": "Hallo"}]},
               {"role": "assistant", "content": "Antwort vom Skill."}]
    result = ("", history, "", None)
    assert orch._extract_answer(result) == "Antwort vom Skill."
    # Altes Tuple-Format
    history2 = [("Hallo", "Antwort 2")]
    assert "Antwort 2" in orch._extract_answer(("", history2, "", None))
    # Multi-Part-content-list mit text-Dicts
    history3 = [{"role": "assistant",
                 "content": [{"type": "text", "text": "Teil A"},
                             {"type": "text", "text": "Teil B"}]}]
    assert orch._extract_answer(("", history3, "", None)) == "Teil A\nTeil B"


# ── Unit-Tests ────────────────────────────────────────────────────────────
def test_schema_library_stats():
    st = LIB.stats()
    assert st["signals_total"] > 200
    assert st["pruefreihenfolge_stufen"] == 5
    assert st["pflicht_slots"] == 4


def test_synth_ag_id():
    assert heuristics.synth_ag_id("§ 823 Abs. 1 BGB") == "ag_bgb_823_1"
    assert heuristics.synth_ag_id("§ 223 StGB") == "ag_stgb_223"
    assert heuristics.synth_ag_id("Art. 6 DSGVO") == "ag_dsgvo_art_6"
    assert heuristics.synth_ag_id("§ 1004 BGB analog") == "ag_bgb_1004"


def test_compute_confidence_renorm():
    assert compute_confidence(0.5, None) == 0.5          # Gewicht 1.0
    assert compute_confidence(0.5, 0.8) == 0.62          # 0.6/0.4
    assert compute_confidence(2.0, None) == 1.0          # geklemmt


def test_slotstore_konflikt():
    s = SlotStore()
    assert s.update("was", "Geld zurück", 1) is False
    assert s.update("was", "Reparatur", 2) is True       # Konflikt erkannt
    assert s.active("was") == "Reparatur"                # jüngster Wert aktiv
    assert s.missing_pflicht(["wer", "was"]) == ["wer"]


def test_signal_dedup_quer_vorrang():
    # "geschlagen" matcht in straf (1.0) UND quer (1.5); pro (skill,term) ein
    # Treffer, Querverstrebung bevorzugt → strafrecht-Score auf quer-Gewicht.
    m = SignalMatcher(LIB).match("geschlagen")
    assert m.signal_score["strafrecht"] == round(1.5 / (1.5 + config.SATURATION_K), 3)
    assert m.sensibilitaet == "hoch"


# ── Test 17: Alltagssignale erweitern Signal-Coverage ─────────────────────
def test_17_alltagssignale_coverage():
    """Neue alltagssignale.yaml deckt vorher fehlende Alltagsbegriffe ab."""
    sm = SignalMatcher(LIB)
    # Widerruf → verbraucherrecht
    assert "verbraucherrecht" in sm.match("ich will widerrufen Haustür").signal_score
    # Arzt / Operation → medizinrecht
    assert "medizinrecht" in sm.match("der Arzt hat einen Fehler gemacht Operation").signal_score
    # Nachbar / Grundstück → nachbarrecht
    assert "nachbarrecht" in sm.match("mein Nachbar baut direkt an meine Grundstücksgrenze").signal_score
    # SaaS / Software → it_recht
    assert "it_recht" in sm.match("unser SaaS-Anbieter erhöht die Preise").signal_score
    # Filesharing → urheberrecht
    assert "urheberrecht" in sm.match("Abmahnung wegen Filesharing Film").signal_score
    # Mobbing → arbeitsrecht
    assert "arbeitsrecht" in sm.match("mein Chef demütigt mich vor Kollegen Mobbing").signal_score


# ── Test 18: Dynamische Begehr-Optionen je Konstellation ──────────────────
def test_18_dynamische_begehr_optionen():
    from coach import Coach
    from models import Sachverhalt
    coach = Coach(LIB)
    sv = Sachverhalt(woraus="Nachbar hat mich geschlagen", von_wem="Nachbar")

    # Körperverletzung → Strafanzeige + Schmerzensgeld in den Optionen
    txt_kv = coach.hypothesen_test(sv, "hoch", ["koerperverletzung"])
    assert "Strafanzeige" in txt_kv
    assert "Schmerzensgeld" in txt_kv

    # Beleidigung → Unterlassung
    txt_bel = coach.hypothesen_test(sv, "hoch", ["beleidigung_uebleNachrede"])
    assert "Unterlassung" in txt_bel

    # Haeusliche Gewalt → Annäherungs-/Kontaktverbot
    sv2 = Sachverhalt(woraus="Partner hat mich geschlagen", von_wem="Partner")
    txt_hg = coach.hypothesen_test(sv2, "sehr hoch", ["haeusliche_gewalt"])
    assert "Kontakt" in txt_hg or "Näherungs" in txt_hg

    # Default (unbekannte Konstellation) → generische Optionen enthalten Unterlassung
    txt_def = coach.hypothesen_test(sv, "hoch", ["unbekannt_xyz"])
    assert "unterlässt" in txt_def.lower()


# ── Test 19: Offline-Eval-Gate läuft und besteht ──────────────────────────
def test_19_offline_eval_gate():
    """Regressions-Gate: offline eval muss Gate bestehen (kein Server nötig)."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "eval"))
    from run_eval_offline import run
    recall, fp, n = run(verbose=False)
    assert n >= 30, f"Zu wenige Cases: {n}"
    assert recall >= 0.80, f"Recall {recall:.0%} unter Gate 80%"
    assert fp <= 0.30, f"FP-Rate {fp:.0%} über Limit 30%"
