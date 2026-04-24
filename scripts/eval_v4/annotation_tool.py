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

# ─── ChromaDB Volltext-Cache ───────────────────────────────────────────────────
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
        _chunk_cache[chunk_id] = ""
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


# ─── Tag-Optionen ─────────────────────────────────────────────────────────────
RECHTSGEBIETE_OPTIONS = [
    # ── Grundlagen & Prinzipien ───────────────────────────────────────────────
    "datenschutz_grundlagen",           # allgemeine Einführung, Begriffe
    "datenschutz_grundsaetze",          # Art. 5 DSGVO — Zweckbindung, Sparsamkeit …
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


# === State ===
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


def build_candidate_choices(q):
    """Checkbox-Labels mit 800-Zeichen-Snippet + volladresse (ohne echte Newlines)."""
    choices = []
    for c in q.get("retrieval_candidates", []):
        cid   = c.get("chunk_id", "")
        score = c.get("score", 0.0)
        volladr = c.get("volladresse") or c.get("gesetz") or ""
        raw_snippet = c.get("snippet") or ""
        # Newlines normalisieren — Gradio bricht Labels bei \n
        snippet = " ".join(raw_snippet.split())[:800]
        label = f"[{score:.3f}] {cid} | {volladr} | {snippet}"
        choices.append(label)
    return choices


def build_forbidden_choices(q):
    choices = []
    for fid in q.get("forbidden_candidates", []):
        choices.append(str(fid))
    return choices


def build_candidates_markdown(q) -> str:
    """Volltext-Details aller Kandidaten für das Accordion-Panel."""
    candidates = q.get("retrieval_candidates", [])
    if not candidates:
        return "_Keine Kandidaten vorhanden._"
    parts = []
    for i, c in enumerate(candidates, 1):
        cid     = c.get("chunk_id", "")
        score   = c.get("score", 0.0)
        gesetz  = c.get("gesetz") or ""
        vol     = c.get("volladresse") or ""
        src     = c.get("source_type") or ""
        # Volltext aus ChromaDB nachladen (gecacht)
        full_text = get_full_chunk_text(cid)
        if not full_text:
            full_text = c.get("snippet") or "_Volltext nicht ladbar_"
        # Auf 2000 Zeichen begrenzen, damit Gradio nicht hängt
        if len(full_text) > 2000:
            full_text = full_text[:2000] + "\n\n_(… gekürzt auf 2000 Zeichen)_"
        parts.append(
            f"### {i}. `{cid}` · Score {score:.3f}\n"
            f"**Gesetz:** {gesetz}  ·  **Volladresse:** {vol}  ·  **Source-Type:** {src}\n\n"
            f"{full_text}\n\n---"
        )
    return "\n\n".join(parts)


def extract_chunk_id(label: str) -> str:
    """Extrahiert chunk_id aus Checkbox-Label: '[score] chunk_id | volladr | snippet'"""
    if "|" in label:
        part = label.split("|")[0].strip()
    else:
        part = label.strip()
    if "] " in part:
        return part.split("] ", 1)[1].strip()
    return part.strip()


def get_query_data(idx: int):
    """
    Gibt alle UI-Werte für Query bei idx zurück.
    Rückgabe (14 Werte):
      0  qid
      1  src
      2  query
      3  must_choices
      4  pre_must
      5  forb_choices
      6  pre_forb
      7  pre_rechtsgebiete
      8  pre_anfrage_typen
      9  normbezug_str
      10 notes
      11 is_deep
      12 candidates_md
      13 progress
    """
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
    pre_rechtsgebiete = [r for r in tags.get("rechtsgebiete", []) if r in RECHTSGEBIETE_OPTIONS]
    pre_anfrage_typen = [a for a in tags.get("anfrage_typen", []) if a in ANFRAGE_TYPEN_OPTIONS]
    normbezug_str     = ", ".join(tags.get("normbezug", []))

    candidates_md = build_candidates_markdown(q)

    return (
        q.get("query_id", ""),
        q.get("query_source", ""),
        q.get("query", ""),
        must_choices,
        pre_must,
        forb_choices,
        pre_forb,
        pre_rechtsgebiete,
        pre_anfrage_typen,
        normbezug_str,
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
    data = get_query_data(new_idx)
    return data + (new_idx,)


def go_next_unannotated(idx: int):
    for i in range(idx + 1, len(queries)):
        if not queries[i].get("must_contain_chunk_ids"):
            return navigate(i, target=i)
    return navigate(idx, target=idx)


def go_filter(status: str, idx: int):
    for i, q in enumerate(queries):
        if status == "unannotiert" and not q.get("must_contain_chunk_ids"):
            return navigate(idx, target=i)
        if status == "adversarial" and q.get("is_adversarial"):
            return navigate(idx, target=i)
        if status == "real_needs_query" and str(q.get("query", "")).startswith("[TO BE FILLED"):
            return navigate(idx, target=i)
        if status == "deep_eval" and q.get("is_deep_eval"):
            return navigate(idx, target=i)
    return navigate(idx, target=idx)


def save_annotation(idx, must_sel, forb_sel, query_text,
                    rechtsgebiete_sel, anfrage_sel, normbezug_str,
                    notes, is_deep):
    if not (0 <= idx < len(queries)):
        return "❌ Ungültiger Index"
    q = queries[idx]

    must_ids = [extract_chunk_id(label) for label in (must_sel or [])]
    must_ids = [x for x in must_ids if x]
    forb_ids = [fid.strip() for fid in (forb_sel or []) if fid.strip()]

    q["must_contain_chunk_ids"]     = must_ids
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

    # ─── Strukturierte Tag-Felder ─────────────────────────────────────────────
    with gr.Row():
        rechtsgebiete_cbg = gr.CheckboxGroup(
            choices=RECHTSGEBIETE_OPTIONS,
            label="Rechtsgebiete (mindestens 1)",
            scale=2,
        )
        anfrage_typen_cbg = gr.CheckboxGroup(
            choices=ANFRAGE_TYPEN_OPTIONS,
            label="Anfrage-Typen (mindestens 1)",
            scale=1,
        )
    normbezug_tb = gr.Textbox(
        label="Normbezug (kommagetrennt, z.B. Art. 6 DSGVO, § 26 BDSG)",
        placeholder="Art. 6 DSGVO, Art. 13 DSGVO",
        lines=1,
    )

    gr.Markdown("### ✅ Must-Contain-Chunks (1–5 auswählen)")
    must_cbg = gr.CheckboxGroup(label="Retrieval-Kandidaten", choices=[])

    with gr.Accordion("📖 Volltexte der Kandidaten (zum Nachschlagen)", open=False):
        candidates_detail_md = gr.Markdown(value="")

    gr.Markdown("### 🚫 Forbidden-Contain-Chunks (optional)")
    forb_cbg = gr.CheckboxGroup(label="Forbidden-Kandidaten", choices=[])

    with gr.Row():
        deep_cb  = gr.Checkbox(label="Deep-Eval (Legal Sufficiency)")
        notes_tb = gr.Textbox(label="Notizen", lines=2, scale=3)

    with gr.Row():
        btn_save    = gr.Button("💾 Speichern", variant="primary")
        save_status = gr.Textbox(label="Status", interactive=False)

    # ─── Output-Liste (15 Elemente inkl. idx_state) ───────────────────────────
    # get_query_data() → 14 Werte; navigate() hängt new_idx an → 15
    ALL_OUTPUTS = [
        qid_tb, src_tb, query_tb,
        must_cbg, must_cbg,           # choices + value
        forb_cbg, forb_cbg,           # choices + value
        rechtsgebiete_cbg,            # value
        anfrage_typen_cbg,            # value
        normbezug_tb,                 # value
        notes_tb, deep_cb,
        candidates_detail_md,         # ← neu
        progress_md,
        idx_state,
    ]

    def unpack(data_tuple):
        """
        Wandelt navigate()-Rückgabe (15 Werte) in gr.update()-Aufrufe um.
        Reihenfolge entspricht get_query_data() + new_idx.
        """
        (qid, src, query,
         must_choices, must_val,
         forb_choices, forb_val,
         rechtsgebiete_val, anfrage_val, normbezug_val,
         notes, deep,
         candidates_md,
         progress,
         new_idx) = data_tuple
        return (
            qid, src, query,
            gr.update(choices=must_choices, value=must_val),
            gr.update(choices=must_choices, value=must_val),
            gr.update(choices=forb_choices, value=forb_val),
            gr.update(choices=forb_choices, value=forb_val),
            rechtsgebiete_val,
            anfrage_val,
            normbezug_val,
            notes, deep,
            candidates_md,
            progress,
            new_idx,
        )

    def do_prev(idx):       return unpack(navigate(idx, delta=-1))
    def do_next(idx):       return unpack(navigate(idx, delta=+1))
    def do_unann(idx):      return unpack(go_next_unannotated(idx))
    def do_jump(n):         return unpack(navigate(0, target=int(n) - 1))
    def do_filter(s, idx):  return unpack(go_filter(s, idx))

    # Initial load
    demo.load(
        lambda: unpack(navigate(0, target=0)),
        outputs=ALL_OUTPUTS,
    )

    btn_prev.click(do_prev,   inputs=[idx_state],            outputs=ALL_OUTPUTS)
    btn_next.click(do_next,   inputs=[idx_state],            outputs=ALL_OUTPUTS)
    btn_unann.click(do_unann, inputs=[idx_state],            outputs=ALL_OUTPUTS)
    btn_jump.click(do_jump,   inputs=[jump_num],             outputs=ALL_OUTPUTS)
    btn_filter.click(do_filter, inputs=[filter_dd, idx_state], outputs=ALL_OUTPUTS)

    btn_save.click(
        save_annotation,
        inputs=[idx_state, must_cbg, forb_cbg, query_tb,
                rechtsgebiete_cbg, anfrage_typen_cbg, normbezug_tb,
                notes_tb, deep_cb],
        outputs=[save_status],
    )


if __name__ == "__main__":
    port = int(os.getenv("OPENLEX_EVAL_V4_ANNOTATION_PORT", "7861"))
    demo.launch(server_name="0.0.0.0", server_port=port, share=False,
                show_error=True)
