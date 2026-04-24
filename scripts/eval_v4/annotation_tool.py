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

INPUT_PATH = Path(os.getenv("OPENLEX_EVAL_V4_QUERIES_PATH",
                            "/opt/openlex-mvp/eval_sets/v4/queries_with_candidates.json"))
# Fallback auf queries_raw wenn with_candidates noch nicht existiert
if not INPUT_PATH.exists():
    INPUT_PATH = Path("/opt/openlex-mvp/eval_sets/v4/queries_raw.json")

OUTPUT_PATH = Path(os.getenv("OPENLEX_EVAL_V4_OUTPUT_PATH",
                              "/opt/openlex-mvp/eval_sets/v4/queries.json"))
BACKUP_DIR = Path("/opt/openlex-mvp/eval_sets/v4/annotation_backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# ─── Tag-Optionen ─────────────────────────────────────────────────────────────
RECHTSGEBIETE_OPTIONS = [
    "datenschutz_grundlagen",
    "betroffenenrechte",
    "auftragsverarbeitung",
    "einwilligung",
    "beschaeftigtendatenschutz",
    "cookie_tracking",
    "datenschutzbeauftragter",
    "datenpanne_meldepflicht",
    "datenuebermittlung_drittland",
    "videoüberwachung",
    "marketing_werbung",
    "gesundheitsdaten",
    "kinder_jugendliche",
    "ki_automatisierung",
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
    choices = []
    for c in q.get("retrieval_candidates", []):
        cid = c.get("chunk_id", "")
        score = c.get("score", 0.0)
        gesetz = c.get("gesetz", "")
        snippet = (c.get("snippet") or "")[:120]
        label = f"[{score:.3f}] {cid} | {gesetz} | {snippet}"
        choices.append(label)
    return choices


def build_forbidden_choices(q):
    choices = []
    for fid in q.get("forbidden_candidates", []):
        choices.append(str(fid))
    return choices


def extract_chunk_id(label: str) -> str:
    """Extrahiert chunk_id aus Checkbox-Label: '[score] chunk_id | gesetz | snippet'"""
    if "|" in label:
        part = label.split("|")[0].strip()
    else:
        part = label.strip()
    if "] " in part:
        return part.split("] ", 1)[1].strip()
    return part.strip()


def get_query_data(idx: int):
    """Gibt alle UI-Werte für den Query bei idx zurück."""
    if not (0 <= idx < len(queries)):
        return ("", "", "", [], [], [], [],
                [], [], "", "", False, get_progress_text())

    q = queries[idx]
    must_choices = build_candidate_choices(q)
    forb_choices = build_forbidden_choices(q)

    # Bereits ausgewählte must-Chunks
    pre_must = []
    for sel_id in q.get("must_contain_chunk_ids", []):
        for label in must_choices:
            if sel_id in label:
                pre_must.append(label)
                break

    # Bereits ausgewählte forbidden-Chunks
    pre_forb = []
    for sel_id in q.get("forbidden_contain_chunk_ids", []):
        if sel_id in forb_choices:
            pre_forb.append(sel_id)

    # Tags aufschlüsseln
    tags = q.get("tags", {})
    pre_rechtsgebiete = [r for r in tags.get("rechtsgebiete", []) if r in RECHTSGEBIETE_OPTIONS]
    pre_anfrage_typen = [a for a in tags.get("anfrage_typen", []) if a in ANFRAGE_TYPEN_OPTIONS]
    normbezug_str = ", ".join(tags.get("normbezug", []))

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

    # Extrahiere Chunk-IDs
    must_ids = [extract_chunk_id(label) for label in (must_sel or [])]
    must_ids = [x for x in must_ids if x]
    forb_ids = [fid.strip() for fid in (forb_sel or []) if fid.strip()]

    q["must_contain_chunk_ids"] = must_ids
    q["forbidden_contain_chunk_ids"] = forb_ids
    q["query"] = query_text or q["query"]
    q["notes"] = notes or ""
    q["is_deep_eval"] = bool(is_deep)

    # Tags aus strukturierten Feldern
    normbezug = [n.strip() for n in (normbezug_str or "").split(",") if n.strip()]
    q["tags"] = {
        "rechtsgebiete": list(rechtsgebiete_sel or []),
        "anfrage_typen": list(anfrage_sel or []),
        "normbezug": normbezug,
    }

    save_data_to_disk(queries)
    return f"✅ Gespeichert — {q['query_id']} ({len(must_ids)} must-IDs)"


# ─── Gradio UI ───────────────────────────────────────────────────────────────
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
        btn_prev     = gr.Button("◀ Zurück", size="sm")
        btn_next     = gr.Button("Weiter ▶", size="sm")
        btn_unann    = gr.Button("⏭ Nächste unannotierte", size="sm")
        jump_num     = gr.Number(label="Springe zu #", value=1, precision=0, minimum=1,
                                  maximum=len(queries), scale=1)
        btn_jump     = gr.Button("Go", size="sm")

    with gr.Row():
        filter_dd = gr.Dropdown(
            choices=["unannotiert", "adversarial", "real_needs_query", "deep_eval"],
            label="Filter", scale=2)
        btn_filter = gr.Button("Zu nächster →", size="sm")

    with gr.Row():
        qid_tb  = gr.Textbox(label="Query-ID", interactive=False, scale=1)
        src_tb  = gr.Textbox(label="Quelle", interactive=False, scale=1)

    query_tb = gr.Textbox(label="Query (editierbar — z.B. für real_* Templates)", lines=3, scale=1)

    # ─── Strukturierte Tag-Felder ──────────────────────────────────────────────
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

    gr.Markdown("### 🚫 Forbidden-Contain-Chunks (optional)")
    forb_cbg = gr.CheckboxGroup(label="Forbidden-Kandidaten", choices=[])

    with gr.Row():
        deep_cb  = gr.Checkbox(label="Deep-Eval (Legal Sufficiency)")
        notes_tb = gr.Textbox(label="Notizen", lines=2, scale=3)

    with gr.Row():
        btn_save    = gr.Button("💾 Speichern", variant="primary")
        save_status = gr.Textbox(label="Status", interactive=False)

    # Alle UI-Outputs (ohne idx_state, der wird separat angehängt)
    # get_query_data returns 13 values; navigate returns 14 (+ new_idx)
    ALL_OUTPUTS = [
        qid_tb, src_tb, query_tb,
        must_cbg, must_cbg,       # choices + value
        forb_cbg, forb_cbg,       # choices + value
        rechtsgebiete_cbg,        # value
        anfrage_typen_cbg,        # value
        normbezug_tb,             # value
        notes_tb, deep_cb, progress_md,
        idx_state,
    ]

    def unpack(data_tuple):
        """Wandelt navigate()-Rückgabe in gr.update()-Aufrufe um."""
        (qid, src, query,
         must_choices, must_val,
         forb_choices, forb_val,
         rechtsgebiete_val, anfrage_val, normbezug_val,
         notes, deep, progress,
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
            notes, deep, progress,
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

    btn_prev.click(do_prev, inputs=[idx_state], outputs=ALL_OUTPUTS)
    btn_next.click(do_next, inputs=[idx_state], outputs=ALL_OUTPUTS)
    btn_unann.click(do_unann, inputs=[idx_state], outputs=ALL_OUTPUTS)
    btn_jump.click(do_jump, inputs=[jump_num], outputs=ALL_OUTPUTS)
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
