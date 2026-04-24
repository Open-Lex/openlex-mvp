#!/usr/bin/env python3
"""
Gradio-Interface für Gold-Annotation von eval_v4-Queries.
Port 7861 (nicht 7860 = Production).
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/opt/openlex-mvp")
import gradio as gr
import chromadb as _chromadb

INPUT_PATH = Path(os.getenv("OPENLEX_EVAL_V4_QUERIES_PATH",
                            "/opt/openlex-mvp/eval_sets/v4/queries_with_candidates.json"))
if not INPUT_PATH.exists():
    INPUT_PATH = Path("/opt/openlex-mvp/eval_sets/v4/queries_raw.json")

OUTPUT_PATH = Path(os.getenv("OPENLEX_EVAL_V4_OUTPUT_PATH",
                              "/opt/openlex-mvp/eval_sets/v4/queries.json"))
BACKUP_DIR = Path("/opt/openlex-mvp/eval_sets/v4/annotation_backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# ─── ChromaDB ─────────────────────────────────────────────────────────────────
try:
    _col = _chromadb.PersistentClient("/opt/openlex-mvp/chromadb").get_collection("openlex_datenschutz")
except Exception as _e:
    _col = None
    print(f"[annotation_tool] ChromaDB nicht ladbar: {_e}", flush=True)

_chunk_cache: dict = {}


def get_full_chunk_text(chunk_id: str) -> str:
    if chunk_id in _chunk_cache:
        return _chunk_cache[chunk_id]
    if _col is None:
        return ""
    try:
        r = _col.get(ids=[chunk_id], include=["documents"])
        if r["ids"]:
            text = r["documents"][0] or ""
            _chunk_cache[chunk_id] = text
            return text
    except Exception:
        pass
    _chunk_cache[chunk_id] = ""
    return ""


def get_chunk_meta(chunk_id: str) -> dict:
    if _col is None:
        return {}
    try:
        r = _col.get(ids=[chunk_id], include=["metadatas"])
        if r["ids"]:
            return r["metadatas"][0] or {}
    except Exception:
        pass
    return {}


# ─── Lazy retrieve ────────────────────────────────────────────────────────────
_retrieve_fn = None


def get_retrieve():
    global _retrieve_fn
    if _retrieve_fn is not None:
        return _retrieve_fn
    try:
        os.environ.setdefault("OPENLEX_INTENT_ANALYSIS_ENABLED", "false")
        os.environ.setdefault("OPENLEX_TRACE_MODE", "false")
        import importlib
        import app as _app
        importlib.reload(_app)
        _retrieve_fn = _app.retrieve
        print("[annotation_tool] retrieve() geladen.", flush=True)
    except Exception as e:
        print(f"[annotation_tool] retrieve() nicht ladbar: {e}", flush=True)
        _retrieve_fn = None
    return _retrieve_fn


# ─── Tag-Optionen ─────────────────────────────────────────────────────────────
RECHTSGEBIETE_OPTIONS = [
    # ── Grundlagen & Prinzipien ───────────────────────────────────────────────
    "anwendungsbereich_definitionen",   # Art. 2–4 DSGVO — Was sind PBD, wer ist Verantwortlicher …
    "verarbeitungsgrundsaetze_art5",    # Art. 5 DSGVO — Zweckbindung, Datenminimierung …
    "rechtsgrundlagen_verarbeitung",    # Art. 6 DSGVO — berechtigtes Interesse, Vertrag …
    "einwilligung",                     # Art. 7–8 DSGVO
    "besondere_kategorien",             # Art. 9 — Gesundheit, Religion, Gewerkschaft …
    # ── Informationspflichten ─────────────────────────────────────────────────
    "informationspflichten",            # Art. 13–14 DSGVO
    # ── Betroffenenrechte ─────────────────────────────────────────────────────
    "betroffenenrechte",                # Art. 12 allgemein / mehrere Rechte zusammen
    "auskunftsrecht",                   # Art. 15 DSGVO
    "berichtigung_loeschung",           # Art. 16–17 DSGVO
    "recht_auf_vergessen",              # Art. 17 DSGVO (Suchmaschinen, Social Media)
    "verarbeitungseinschraenkung",      # Art. 18 DSGVO
    "datenportabilitaet",               # Art. 20 DSGVO
    "widerspruchsrecht",                # Art. 21 DSGVO
    "automatisierte_entscheidung",      # Art. 22 DSGVO — Profiling, SCHUFA-Score
    # ── Pflichten des Verantwortlichen ───────────────────────────────────────
    "datenschutz_by_design",            # Art. 25 DSGVO
    "auftragsverarbeitung",             # Art. 28 DSGVO
    "gemeinsame_verantwortlichkeit",    # Art. 26 DSGVO
    "datensicherheit",                  # Art. 32 DSGVO — TOMs
    "datenpanne_meldepflicht",          # Art. 33–34 DSGVO
    "datenschutz_folgenabschaetzung",   # Art. 35–36 DSGVO
    "datenschutzbeauftragter",          # Art. 37–39 DSGVO
    # ── Drittlandübermittlung ─────────────────────────────────────────────────
    "datenuebermittlung_drittland",     # Art. 44–49 DSGVO — SCCs, Adequacy …
    # ── Aufsicht & Durchsetzung ───────────────────────────────────────────────
    "aufsicht_bussgelder",              # Art. 51ff, Art. 83–84 DSGVO
    # ── Spezifische Verarbeitungskontexte ─────────────────────────────────────
    "beschaeftigtendatenschutz",        # § 26 BDSG
    "gesundheitsdaten",                 # Art. 9 Abs. 2 lit. h, § 22 BDSG
    "kinder_jugendliche",               # Art. 8, ErwG 38
    "videoüberwachung",                 # § 4 BDSG, Art. 6 Abs. 1 lit. f
    "cookie_tracking",                  # TDDDG, Art. 6 Abs. 1 lit. a
    "marketing_werbung",                # Art. 6 Abs. 1 lit. f, § 7 UWG
    "scoring_profiling",                # § 31 BDSG, Art. 22 — SCHUFA, Bonitätsprüfung
    "ki_automatisierung",               # Art. 22, KI-VO
    "wissenschaft_forschung",           # Art. 89 DSGVO, § 27 BDSG
    "oeffentliche_stellen",             # §§ 3, 45ff BDSG
    "strafverfolgung_sicherheit",       # JI-Richtlinie, §§ 45–84 BDSG
    # ── Sonstiges ─────────────────────────────────────────────────────────────
    "out_of_domain",
]

ANFRAGE_TYPEN_OPTIONS = [
    "rechtsfrage",
    "praxisfall",
    "normlookup",
    "definition",
    "vergleich",
    "checkliste",
    "verfahren",
    "adversarial",
    "deep_eval",
]


# === State ====================================================================
def load_data():
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            return json.load(f)
    with open(INPUT_PATH) as f:
        return json.load(f)


queries = load_data()


def save_data_to_disk(queries_list):
    if OUTPUT_PATH.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = BACKUP_DIR / f"queries_{ts}.json"
        backup.write_text(OUTPUT_PATH.read_text())
    with open(OUTPUT_PATH, "w") as f:
        json.dump(queries_list, f, indent=2, ensure_ascii=False)


def get_progress_text():
    annotated = sum(1 for q in queries if q.get("must_contain_chunk_ids"))
    total = len(queries)
    pct = annotated / total * 100 if total else 0
    return f"**{annotated}/{total} annotiert ({pct:.0f}%)**"


def _make_label(chunk_id: str, score, volladr: str, snippet: str, meta: dict = None) -> str:
    """Einheitliches Label-Format für alle Quellen.
    Für Urteile (kein volladresse/gesetz): gericht + aktenzeichen als Fallback."""
    score_str = f"{score:.3f}" if isinstance(score, float) else str(score)
    clean = " ".join(snippet.split())[:800]
    if not volladr and meta:
        gericht = meta.get("gericht") or ""
        az      = meta.get("aktenzeichen") or ""
        if gericht or az:
            volladr = f"{gericht} {az}".strip()
    return f"[{score_str}] {chunk_id} | {volladr} | {clean}"


def build_candidate_choices(q) -> list[str]:
    """
    Checkbox-Choices aus retrieval_candidates.
    Manuell hinzugefügte IDs (not in candidates) werden aus ChromaDB ergänzt.
    """
    choices = []
    seen_ids = set()

    for c in q.get("retrieval_candidates", []):
        cid = c.get("chunk_id", "")
        seen_ids.add(cid)
        volladr  = c.get("volladresse") or c.get("gesetz") or ""
        snippet  = c.get("snippet") or ""
        label    = _make_label(cid, c.get("score", 0.0), volladr, snippet, meta=c)
        choices.append(label)

    # Manuell gesetzte IDs, die nicht in candidates sind → aus DB nachladen
    for cid in q.get("must_contain_chunk_ids", []):
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        meta    = get_chunk_meta(cid)
        volladr = meta.get("volladresse") or meta.get("gesetz") or ""
        snippet = get_full_chunk_text(cid)
        label   = _make_label(cid, "manual", volladr, snippet, meta=meta)
        choices.append(label)

    return choices


def build_forbidden_choices(q) -> list[str]:
    return [str(fid) for fid in q.get("forbidden_candidates", [])]


def build_candidates_markdown(q) -> str:
    candidates = q.get("retrieval_candidates", [])
    if not candidates:
        return "_Keine Kandidaten vorhanden._"
    parts = []
    for i, c in enumerate(candidates, 1):
        cid    = c.get("chunk_id", "")
        score  = c.get("score", 0.0)
        gesetz = c.get("gesetz") or ""
        vol    = c.get("volladresse") or ""
        src    = c.get("source_type") or ""
        # Urteile: gericht+aktenzeichen als Fallback wenn gesetz/volladresse leer
        if not gesetz and not vol:
            db_meta = get_chunk_meta(cid)
            gericht = db_meta.get("gericht") or ""
            az      = db_meta.get("aktenzeichen") or ""
            gesetz  = gericht
            vol     = az
        full   = get_full_chunk_text(cid) or c.get("snippet") or "_Volltext nicht ladbar_"
        if len(full) > 2000:
            full = full[:2000] + "\n\n_(… gekürzt auf 2000 Zeichen)_"
        parts.append(
            f"### {i}. `{cid}` · Score {score:.3f}\n"
            f"**Gesetz:** {gesetz}  ·  **Volladresse:** {vol}  ·  **Source-Type:** {src}\n\n"
            f"{full}\n\n---"
        )
    return "\n\n".join(parts)


def extract_chunk_id(label: str) -> str:
    if "|" in label:
        part = label.split("|")[0].strip()
    else:
        part = label.strip()
    if "] " in part:
        return part.split("] ", 1)[1].strip()
    return part.strip()


def get_query_data(idx: int):
    if not (0 <= idx < len(queries)):
        return ("", "", "", [], [], [], [],
                [], [], "", "", False, "_Keine Kandidaten vorhanden._", get_progress_text())

    q = queries[idx]
    must_choices = build_candidate_choices(q)
    forb_choices = build_forbidden_choices(q)

    pre_must = []
    for sel_id in q.get("must_contain_chunk_ids", []):
        for label in must_choices:
            if sel_id in label:
                pre_must.append(label)
                break

    pre_forb = []
    for sel_id in q.get("forbidden_contain_chunk_ids", []):
        if sel_id in forb_choices:
            pre_forb.append(sel_id)

    tags = q.get("tags", {})
    pre_rg  = [r for r in tags.get("rechtsgebiete", []) if r in RECHTSGEBIETE_OPTIONS]
    pre_at  = [a for a in tags.get("anfrage_typen", []) if a in ANFRAGE_TYPEN_OPTIONS]
    nb_str  = ", ".join(tags.get("normbezug", []))

    candidates_md = build_candidates_markdown(q)

    return (
        q.get("query_id", ""),
        q.get("query_source", ""),
        q.get("query", ""),
        must_choices, pre_must,
        forb_choices, pre_forb,
        pre_rg, pre_at, nb_str,
        q.get("notes", ""),
        bool(q.get("is_deep_eval", False)),
        candidates_md,
        get_progress_text(),
    )


def navigate(idx: int, delta: int = 0, target: int = None):
    if target is not None:
        new_idx = max(0, min(len(queries) - 1, target))
    else:
        new_idx = max(0, min(len(queries) - 1, idx + delta))
    return get_query_data(new_idx) + (new_idx,)


def go_next_unannotated(idx: int):
    for i in range(idx + 1, len(queries)):
        if not queries[i].get("must_contain_chunk_ids"):
            return navigate(i, target=i)
    return navigate(idx, target=idx)


def go_filter(status: str, idx: int):
    for i, q in enumerate(queries):
        if status == "unannotiert"       and not q.get("must_contain_chunk_ids"):  return navigate(idx, target=i)
        if status == "adversarial"       and q.get("is_adversarial"):              return navigate(idx, target=i)
        if status == "real_needs_query"  and str(q.get("query","")).startswith("[TO BE FILLED"): return navigate(idx, target=i)
        if status == "deep_eval"         and q.get("is_deep_eval"):                return navigate(idx, target=i)
    return navigate(idx, target=idx)


def save_annotation(idx, must_sel, forb_sel, query_text,
                    rechtsgebiete_sel, anfrage_sel, normbezug_str,
                    notes, is_deep):
    if not (0 <= idx < len(queries)):
        return "❌ Ungültiger Index"
    q = queries[idx]

    must_ids = [extract_chunk_id(lbl) for lbl in (must_sel or [])]
    must_ids = [x for x in must_ids if x]
    forb_ids = [fid.strip() for fid in (forb_sel or []) if fid.strip()]

    q["must_contain_chunk_ids"]      = must_ids
    q["forbidden_contain_chunk_ids"] = forb_ids
    q["query"]      = query_text or q["query"]
    q["notes"]      = notes or ""
    q["is_deep_eval"] = bool(is_deep)

    normbezug = [n.strip() for n in (normbezug_str or "").split(",") if n.strip()]
    q["tags"] = {
        "rechtsgebiete": list(rechtsgebiete_sel or []),
        "anfrage_typen": list(anfrage_sel or []),
        "normbezug":     normbezug,
    }

    save_data_to_disk(queries)
    return f"✅ Gespeichert — {q['query_id']} ({len(must_ids)} must-IDs)"


# ─── Such-Handler ─────────────────────────────────────────────────────────────

def do_search(search_text: str):
    """Freitext → retrieve() → neue Choices in search_results_cbg."""
    if not search_text.strip():
        return gr.update(choices=[], value=[]), "Bitte Suchbegriff eingeben."

    retrieve = get_retrieve()
    if retrieve is None:
        return gr.update(choices=[], value=[]), "❌ retrieve() nicht verfügbar."

    try:
        results = retrieve(search_text.strip())
    except Exception as e:
        return gr.update(choices=[], value=[]), f"❌ Fehler: {e}"

    if isinstance(results, dict):
        return gr.update(choices=[], value=[]), "⚠️ Rückfrage ausgelöst — bitte konkreteren Suchbegriff."

    choices = []
    for r in (results or [])[:10]:
        meta    = r.get("meta") or r.get("metadata") or {}
        cid     = meta.get("chunk_id") or r.get("id") or ""
        score   = r.get("ce_score") or r.get("score") or 0.0
        volladr = meta.get("volladresse") or meta.get("gesetz") or ""
        snippet = r.get("document") or r.get("text") or ""
        label   = _make_label(cid, float(score), volladr, snippet, meta=meta)
        choices.append(label)

    msg = f"✅ {len(choices)} Ergebnisse — auswählen und 'Hinzufügen' klicken."
    return gr.update(choices=choices, value=[]), msg


def do_add_direct(direct_id: str, must_choices: list, must_val: list):
    """Direkte Chunk-ID → prüfen → zu Must-Contain hinzufügen."""
    cid = direct_id.strip()
    if not cid:
        return gr.update(), gr.update(), "Bitte Chunk-ID eingeben."

    # Schon vorhanden?
    existing_ids = [extract_chunk_id(lbl) for lbl in (must_choices or [])]
    if cid in existing_ids:
        # Nur selektieren
        new_val = list(must_val or [])
        for lbl in (must_choices or []):
            if cid in lbl and lbl not in new_val:
                new_val.append(lbl)
        return gr.update(choices=must_choices, value=new_val), gr.update(), f"ℹ️ `{cid}` war schon in der Liste, jetzt selektiert."

    # In DB nachschlagen
    meta    = get_chunk_meta(cid)
    if not meta and _col is not None:
        return gr.update(), gr.update(), f"❌ Chunk-ID `{cid}` nicht in ChromaDB gefunden."

    volladr = meta.get("volladresse") or meta.get("gesetz") or ""
    snippet = get_full_chunk_text(cid)
    label   = _make_label(cid, "manual", volladr, snippet)

    new_choices = list(must_choices or []) + [label]
    new_val     = list(must_val or []) + [label]
    return (
        gr.update(choices=new_choices, value=new_val),
        gr.update(choices=new_choices, value=new_val),
        f"✅ `{cid}` hinzugefügt.",
    )


def do_add_search_to_must(search_sel: list, must_choices: list, must_val: list):
    """Ausgewählte Suchergebnisse → Must-Contain übernehmen."""
    if not search_sel:
        return gr.update(), gr.update(), gr.update(choices=[], value=[]), "Nichts ausgewählt."

    new_choices = list(must_choices or [])
    new_val     = list(must_val or [])
    added = 0
    for lbl in search_sel:
        if lbl not in new_choices:
            new_choices.append(lbl)
            added += 1
        if lbl not in new_val:
            new_val.append(lbl)

    return (
        gr.update(choices=new_choices, value=new_val),
        gr.update(choices=new_choices, value=new_val),
        gr.update(choices=[], value=[]),
        f"✅ {added} Chunk(s) zu Must-Contain hinzugefügt.",
    )


# ─── Gradio UI ────────────────────────────────────────────────────────────────
CSS = """
.annotation-header { font-size: 1.1rem; font-weight: 600; }
.status-bar { background: #1a1a2e; padding: 8px 12px; border-radius: 6px; }
"""

with gr.Blocks(title="OpenLex Eval v4 Annotation", css=CSS) as demo:
    idx_state = gr.State(value=0)

    gr.Markdown("# 📋 OpenLex Eval v4 — Gold-Annotation")

    with gr.Row():
        progress_md = gr.Markdown(get_progress_text())

    with gr.Row():
        btn_prev  = gr.Button("◀ Zurück", size="sm")
        btn_next  = gr.Button("Weiter ▶", size="sm")
        btn_unann = gr.Button("⏭ Nächste unannotierte", size="sm")
        jump_num  = gr.Number(label="Springe zu #", value=1, precision=0, minimum=1,
                               maximum=len(queries), scale=1)
        btn_jump  = gr.Button("Go", size="sm")

    with gr.Row():
        filter_dd  = gr.Dropdown(
            choices=["unannotiert", "adversarial", "real_needs_query", "deep_eval"],
            label="Filter", scale=2)
        btn_filter = gr.Button("Zu nächster →", size="sm")

    with gr.Row():
        qid_tb = gr.Textbox(label="Query-ID", interactive=False, scale=1)
        src_tb = gr.Textbox(label="Quelle",   interactive=False, scale=1)

    query_tb = gr.Textbox(label="Query (editierbar — z.B. für real_* Templates)", lines=3)

    # ─── Tags ─────────────────────────────────────────────────────────────────
    with gr.Row():
        rechtsgebiete_cbg = gr.CheckboxGroup(
            choices=RECHTSGEBIETE_OPTIONS, label="Rechtsgebiete (mindestens 1)", scale=2)
        anfrage_typen_cbg = gr.CheckboxGroup(
            choices=ANFRAGE_TYPEN_OPTIONS, label="Anfrage-Typen (mindestens 1)", scale=1)
    normbezug_tb = gr.Textbox(
        label="Normbezug (kommagetrennt, z.B. Art. 6 DSGVO, § 26 BDSG)",
        placeholder="Art. 6 DSGVO, Art. 13 DSGVO", lines=1)

    # ─── Must-Contain ─────────────────────────────────────────────────────────
    gr.Markdown("### ✅ Must-Contain-Chunks (1–5 auswählen)")
    must_cbg = gr.CheckboxGroup(label="Kandidaten (Vorauswahl + manuell hinzugefügte)", choices=[])

    # ── Freitext-Suche ────────────────────────────────────────────────────────
    with gr.Accordion("🔍 Eigene Suche — Schlagworte eingeben, bessere Chunks finden", open=False):
        with gr.Row():
            search_tb  = gr.Textbox(
                label="Suchbegriff / Schlagworte / Normen",
                placeholder="z.B. automatisierte Entscheidung SCHUFA Art. 22 DSGVO",
                scale=4, lines=1)
            btn_search = gr.Button("Suchen", size="sm", scale=1)
        search_status_tb = gr.Textbox(label="", interactive=False, lines=1, show_label=False)
        search_results_cbg = gr.CheckboxGroup(label="Suchergebnisse", choices=[])
        btn_add_search = gr.Button("➕ Ausgewählte zu Must-Contain hinzufügen", size="sm")

        gr.Markdown("**Oder direkte Chunk-ID:**")
        with gr.Row():
            direct_id_tb  = gr.Textbox(
                label="Chunk-ID (z.B. gran_DSGVO_Art._22_Abs.1)",
                placeholder="gran_DSGVO_...", scale=4, lines=1)
            btn_add_direct = gr.Button("➕ Hinzufügen", size="sm", scale=1)
        direct_status_tb = gr.Textbox(label="", interactive=False, lines=1, show_label=False)

    # ── Volltext-Panel ────────────────────────────────────────────────────────
    with gr.Accordion("📖 Volltexte der Kandidaten (zum Nachschlagen)", open=False):
        candidates_detail_md = gr.Markdown(value="")

    # ─── Forbidden ────────────────────────────────────────────────────────────
    gr.Markdown("### 🚫 Forbidden-Contain-Chunks (optional)")
    forb_cbg = gr.CheckboxGroup(label="Forbidden-Kandidaten", choices=[])

    with gr.Row():
        deep_cb  = gr.Checkbox(label="Deep-Eval (Legal Sufficiency)")
        notes_tb = gr.Textbox(label="Notizen", lines=2, scale=3)

    with gr.Row():
        btn_save    = gr.Button("💾 Speichern", variant="primary")
        save_status = gr.Textbox(label="Status", interactive=False)

    # ─── Output-Liste für Navigation (15 Elemente) ────────────────────────────
    ALL_OUTPUTS = [
        qid_tb, src_tb, query_tb,
        must_cbg, must_cbg,           # choices + value
        forb_cbg, forb_cbg,           # choices + value
        rechtsgebiete_cbg,
        anfrage_typen_cbg,
        normbezug_tb,
        notes_tb, deep_cb,
        candidates_detail_md,
        progress_md,
        idx_state,
    ]

    def unpack(data_tuple):
        (qid, src, query,
         must_choices, must_val,
         forb_choices, forb_val,
         rg_val, at_val, nb_val,
         notes, deep,
         cand_md, progress,
         new_idx) = data_tuple
        return (
            qid, src, query,
            gr.update(choices=must_choices, value=must_val),
            gr.update(choices=must_choices, value=must_val),
            gr.update(choices=forb_choices, value=forb_val),
            gr.update(choices=forb_choices, value=forb_val),
            rg_val, at_val, nb_val,
            notes, deep,
            cand_md, progress,
            new_idx,
        )

    def do_prev(idx):       return unpack(navigate(idx, delta=-1))
    def do_next(idx):       return unpack(navigate(idx, delta=+1))
    def do_unann(idx):      return unpack(go_next_unannotated(idx))
    def do_jump(n):         return unpack(navigate(0, target=int(n) - 1))
    def do_filter(s, idx):  return unpack(go_filter(s, idx))

    demo.load(lambda: unpack(navigate(0, target=0)), outputs=ALL_OUTPUTS)

    btn_prev.click(do_prev,     inputs=[idx_state],              outputs=ALL_OUTPUTS)
    btn_next.click(do_next,     inputs=[idx_state],              outputs=ALL_OUTPUTS)
    btn_unann.click(do_unann,   inputs=[idx_state],              outputs=ALL_OUTPUTS)
    btn_jump.click(do_jump,     inputs=[jump_num],               outputs=ALL_OUTPUTS)
    btn_filter.click(do_filter, inputs=[filter_dd, idx_state],   outputs=ALL_OUTPUTS)

    btn_save.click(
        save_annotation,
        inputs=[idx_state, must_cbg, forb_cbg, query_tb,
                rechtsgebiete_cbg, anfrage_typen_cbg, normbezug_tb,
                notes_tb, deep_cb],
        outputs=[save_status],
    )

    # Such-Button
    btn_search.click(
        do_search,
        inputs=[search_tb],
        outputs=[search_results_cbg, search_status_tb],
    )

    # Suchergebnisse → Must-Contain
    btn_add_search.click(
        do_add_search_to_must,
        inputs=[search_results_cbg, must_cbg, must_cbg],
        outputs=[must_cbg, must_cbg, search_results_cbg, search_status_tb],
    )

    # Direkte Chunk-ID
    btn_add_direct.click(
        do_add_direct,
        inputs=[direct_id_tb, must_cbg, must_cbg],
        outputs=[must_cbg, must_cbg, direct_status_tb],
    )


if __name__ == "__main__":
    port = int(os.getenv("OPENLEX_EVAL_V4_ANNOTATION_PORT", "7861"))
    demo.launch(server_name="0.0.0.0", server_port=port, share=False,
                show_error=True)
