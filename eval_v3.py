#!/usr/bin/env python3
"""
eval_v3.py – Zweistufiges Eval-Framework für OpenLex MVP.

Stufe 1: Retrieval-Eval (schnell, kostenlos)
  – Hit@K, MRR, NDCG@K, Forbidden-Hit
  – Nutzt ChromaDB direkt (kein Gradio-Import)

Stufe 2: Answer-Eval (mit LLM-Kosten)
  – Norm-Match, Keyword-Match, Forbidden-Norm-Check
  – Liest LLM-Antwort aus app.py-Funktionen

Fragen-Schema (eval_sets/*.json):
{
  "id": "mw_art4_begriffsbestimmungen_q1",   # eindeutig, z.B. aus MW-Chunk-ID
  "question": "Was bedeutet Pseudonymisierung?",
  "gold_ids": ["mw_art4_begriffsbestimmungen"],  # MUSS in Top-K sein
  "should_ids": ["mw_art5_grundsaetze"],         # SOLLTE in Top-K sein (nDCG)
  "forbidden_ids": [],                            # DARF NICHT in Top-K sein
  "expected_norms": ["Art. 4 Nr. 5 DSGVO"],
  "expected_keywords": ["Pseudonymisierung", "Anonymisierung"],
  "forbidden_norms": [],
  "category": "grundlagen",
  "source_chunk": "mw_art4_begriffsbestimmungen"  # ursprünglicher MW-Chunk
}

Verwendung:
  python eval_v3.py --eval-set eval_sets/canonical_auto.json --retrieval-only
  python eval_v3.py --eval-set eval_sets/canonical_auto.json
  python eval_v3.py --eval-set eval_sets/canonical_auto.json --k 5 10 20
  python eval_v3.py --eval-set eval_sets/canonical_auto.json --out-dir eval_results_v3/run1
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CHROMADB_DIR = str(BASE_DIR / "chromadb")
COLLECTION_NAME = "openlex_datenschutz"
MODEL_NAME = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"

DEFAULT_K_VALUES = [3, 5, 10]

# ─────────────────────────────────────────────
# Metriken
# ─────────────────────────────────────────────

def hit_at_k(retrieved_ids: list[str], gold_ids: list[str], k: int) -> float:
    """Anteil der Gold-IDs in Top-K. Range [0,1]."""
    top_k = retrieved_ids[:k]
    if not gold_ids:
        return 1.0
    hits = sum(1 for gid in gold_ids if gid in top_k)
    return hits / len(gold_ids)


def mrr(retrieved_ids: list[str], gold_ids: list[str]) -> float:
    """1/Position der ersten Gold-ID in Retrieved. Range [0,1]."""
    for i, rid in enumerate(retrieved_ids):
        if rid in gold_ids:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(retrieved_ids: list[str], gold_ids: list[str],
               should_ids: list[str], k: int) -> float:
    """NDCG@K mit Relevanz must=2, should=1, else=0."""
    def relevance(doc_id: str) -> int:
        if doc_id in gold_ids:
            return 2
        if doc_id in should_ids:
            return 1
        return 0

    top_k = retrieved_ids[:k]
    dcg = sum(relevance(did) / math.log2(i + 2) for i, did in enumerate(top_k))

    all_relevant = [(2, gid) for gid in gold_ids] + [
        (1, sid) for sid in should_ids if sid not in gold_ids
    ]
    all_relevant.sort(reverse=True)
    ideal = all_relevant[:k]
    idcg = sum(rel / math.log2(i + 2) for i, (rel, _) in enumerate(ideal))

    return dcg / idcg if idcg > 0 else 0.0


def forbidden_hit(retrieved_ids: list[str], forbidden_ids: list[str], k: int) -> bool:
    """True wenn eine Forbidden-ID in Top-K ist."""
    return any(fid in retrieved_ids[:k] for fid in forbidden_ids)


# ─────────────────────────────────────────────
# ChromaDB-Retrieval (direkt, ohne app.py-Import)
# ─────────────────────────────────────────────

_collection = None
_model = None


def get_chroma_collection():
    global _collection
    if _collection is None:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMADB_DIR)
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


def get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _normalize_id(meta: dict, doc: str) -> str:
    """Normalisiert eine Chunk-ID konsistent zu app.py."""
    chunk_id = (
        meta.get("chunk_id", "")
        or meta.get("volladresse", "")
        or meta.get("thema", "")
        or doc[:60]
    )
    return chunk_id.strip()


# Lazy-Import: app.retrieve nur einmalig laden
_app_retrieve_fn = None
# Lazy-Lookup: doc-Prefix → ChromaDB-ID für Chunks ohne chunk_id in meta (z.B. MW-Chunks)
_doc_to_chroma_id: dict | None = None


def _get_app_retrieve():
    global _app_retrieve_fn
    if _app_retrieve_fn is None:
        import sys
        sys.path.insert(0, str(BASE_DIR))
        # app.py importieren – Gradio startet nicht (nur in if __name__=="__main__")
        import app as _app_mod
        _app_retrieve_fn = _app_mod.retrieve
    return _app_retrieve_fn


def _get_doc_to_chroma_id() -> dict:
    """Baut einmalig ein Lookup-Dict {doc[:80] → chroma_id} für alle Chunks ohne chunk_id.

    Nötig weil MW-Chunks (source_type=methodenwissen) kein chunk_id in meta haben,
    aber die Gold-IDs im eval_set die echten ChromaDB-IDs enthalten.
    """
    global _doc_to_chroma_id
    if _doc_to_chroma_id is None:
        col = get_chroma_collection()
        res = col.get(
            where={"source_type": "methodenwissen"},
            include=["documents"],
        )
        _doc_to_chroma_id = {}
        for cid, doc in zip(res["ids"], res["documents"] or []):
            if doc:
                _doc_to_chroma_id[doc[:80]] = cid
    return _doc_to_chroma_id


def _get_raw_chroma_id(meta: dict, doc: str) -> str:
    """Ermittelt die echte ChromaDB-ID für einen Chunk.

    Für Chunks mit chunk_id in meta: direkt verwenden.
    Für Chunks ohne chunk_id (z.B. MW-Chunks): Lookup über doc-Prefix.
    """
    raw_id = meta.get("chunk_id", "") or meta.get("volladresse", "")
    if raw_id:
        return raw_id
    # Kein chunk_id – via doc-Prefix nachschlagen (MW-Chunks)
    lookup = _get_doc_to_chroma_id()
    return lookup.get(doc[:80], doc[:50])


def _retrieve_ids_direct(question: str, max_k: int = 20):
    """Fallback: direktes collection.query() ohne app.py-Pipeline."""
    col = get_chroma_collection()
    model = get_embedding_model()

    q_embedding = model.encode([question]).tolist()
    results = col.query(
        query_embeddings=q_embedding,
        n_results=min(max_k, col.count()),
        include=["documents", "metadatas", "distances"],
    )

    ids = []
    raw_ids = []
    seen = set()
    chroma_ids_raw = results.get("ids", [[]])[0]
    for idx, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        cid = _normalize_id(meta, doc)
        if cid not in seen:
            seen.add(cid)
            ids.append(cid)
            raw_ids.append(chroma_ids_raw[idx] if idx < len(chroma_ids_raw) else cid)

    return ids, raw_ids


def retrieve_ids(question: str, max_k: int = 20):
    """Retrieval via app.py-Pipeline (hybrid search, reranker, boosts).
    Gibt (normalized_ids, raw_chroma_ids) zurück."""
    try:
        retrieve_fn = _get_app_retrieve()
        chunks = retrieve_fn(question)  # list[dict] mit keys: text, meta, distance, ...

        ids = []
        raw_ids = []
        seen = set()

        for chunk in chunks[:max_k]:
            meta = chunk.get("meta", {})
            doc = chunk.get("text", "")
            # app.retrieve() liefert die ChromaDB-ID direkt als chunk["id"]
            # → bevorzugt nutzen, Fallback auf meta-Lookup für ältere Pfade
            raw_id = chunk.get("id") or _get_raw_chroma_id(meta, doc)
            norm_id = _normalize_id(meta, doc)

            if raw_id not in seen:
                seen.add(raw_id)
                raw_ids.append(raw_id)
                ids.append(norm_id)

        return ids, raw_ids

    except Exception as e:
        print(f"\n  [WARN] app.retrieve() fehlgeschlagen ({e}), Fallback auf collection.query()")
        return _retrieve_ids_direct(question, max_k)


# ─────────────────────────────────────────────
# Answer-Eval Hilfsfunktionen
# ─────────────────────────────────────────────

_OBSOLETE_NORMS = [
    "§ 4a BDSG", "§ 28 BDSG", "§ 28a BDSG", "§ 29 BDSG",
    "§ 4b BDSG", "§ 4c BDSG", "§ 6b BDSG", "§ 4f BDSG",
    "§ 4g BDSG", "§ 11 BDSG", "§ 13 TMG", "§ 15 TMG",
]


def _norm_in_text(norm: str, text: str) -> bool:
    norm_lower = norm.lower().strip()
    text_lower = text.lower()
    if norm_lower in text_lower:
        return True
    base = re.sub(
        r"\s*(DSGVO|BDSG|UWG|TDDDG|TTDSG|TMG|GG|GRCh)\s*$", "", norm, flags=re.I
    ).strip()
    return base.lower() in text_lower


def evaluate_answer(q: dict, response: str) -> dict:
    """Bewertet die LLM-Antwort auf Norm- und Keyword-Ebene."""
    resp_lower = response.lower()

    # Norm-Check
    expected_norms = q.get("expected_norms", [])
    norms_found = [n for n in expected_norms if _norm_in_text(n, response)]
    norm_score = len(norms_found) / len(expected_norms) if expected_norms else 1.0

    # Forbidden-Norm-Check
    forbidden_norms = q.get("forbidden_norms", [])
    forbidden_norms_found = [n for n in forbidden_norms if _norm_in_text(n, response)]
    forbidden_norm_score = max(0.0, 1.0 - 0.25 * len(forbidden_norms_found))

    # Obsolete-Norm-Check
    obsolete_found = [n for n in _OBSOLETE_NORMS if _norm_in_text(n, response)]

    # Keyword-Check
    expected_kw = q.get("expected_keywords", [])
    kw_found = [kw for kw in expected_kw if kw.lower() in resp_lower]
    kw_score = len(kw_found) / len(expected_kw) if expected_kw else 1.0

    # Gesamtscore Answer-Level (einfache Gewichtung)
    answer_score = (norm_score * 0.5 + forbidden_norm_score * 0.2 + kw_score * 0.3) * 100

    return {
        "answer_score": round(answer_score, 1),
        "norm_score": round(norm_score, 3),
        "kw_score": round(kw_score, 3),
        "forbidden_norm_score": round(forbidden_norm_score, 3),
        "norms_found": norms_found,
        "norms_missing": [n for n in expected_norms if n not in norms_found],
        "kw_found": kw_found,
        "kw_missing": [kw for kw in expected_kw if kw not in kw_found],
        "forbidden_norms_found": forbidden_norms_found,
        "obsolete_norms_found": obsolete_found,
    }


def run_llm_answer(question: str) -> str:
    """Ruft die LLM-Pipeline aus app.py auf (nur wenn nicht --retrieval-only)."""
    os.chdir(BASE_DIR)
    sys.path.insert(0, str(BASE_DIR))
    # Lazy-Import damit Gradio nicht sofort startet – wir importieren nur die Funktionen
    from app import retrieve, format_context, _build_llm_messages, stream_with_fallback
    chunks = retrieve(question)
    context = format_context(chunks)
    messages = _build_llm_messages(question, context, [])
    full_response = ""
    for token, _ in stream_with_fallback(messages):
        full_response += token
    return full_response


# ─────────────────────────────────────────────
# Eval-Runner
# ─────────────────────────────────────────────

def run_eval(
    questions: list[dict],
    k_values: list[int],
    retrieval_only: bool,
    out_dir: Path,
) -> dict:
    max_k = max(k_values)
    results = []
    t_start = time.time()

    print(f"\nOpenLex Eval v3 – {len(questions)} Fragen, K={k_values}")
    if retrieval_only:
        print("  Modus: --retrieval-only (kein LLM)\n")
    else:
        print("  Modus: full (Retrieval + LLM)\n")

    for i, q in enumerate(questions, 1):
        qid = q.get("id", f"q{i}")
        question_text = q["question"]
        print(f"  [{i:2d}/{len(questions)}] {qid}: {question_text[:55]}...", end="", flush=True)
        t0 = time.time()

        # Retrieval – gibt (normalized_ids, raw_chroma_ids) zurück
        retrieved_ids, retrieved_raw_ids = retrieve_ids(question_text, max_k=max_k)

        # Bevorzugt retrieval_gold-Schema (v4), Fallback auf Top-Level (v3-kompatibel)
        rg = q.get("retrieval_gold", {})
        use_rg = bool(rg)
        if use_rg:
            gold_ids = rg.get("must_contain_chunk_ids") or []
            should_ids = rg.get("should_contain_chunk_ids") or []
            forbidden_ids = rg.get("forbidden_chunk_ids") or []
            # retrieval_gold enthält rohe ChromaDB-IDs → raw_ids zum Vergleich nutzen
            eval_ids = retrieved_raw_ids
        else:
            gold_ids = q.get("gold_ids", [])
            should_ids = q.get("should_ids", [])
            forbidden_ids = q.get("forbidden_ids", [])
            # top-level gold_ids sind normalized → normalized_ids nutzen
            eval_ids = retrieved_ids

        # Metriken berechnen
        retrieval_metrics: dict[str, float | bool] = {}
        for k in k_values:
            retrieval_metrics[f"hit@{k}"] = round(hit_at_k(eval_ids, gold_ids, k), 3)
            retrieval_metrics[f"ndcg@{k}"] = round(ndcg_at_k(eval_ids, gold_ids, should_ids, k), 3)
            retrieval_metrics[f"forbidden_hit@{k}"] = forbidden_hit(eval_ids, forbidden_ids, k)
        retrieval_metrics["mrr"] = round(mrr(eval_ids, gold_ids), 3)

        result: dict = {
            "id": qid,
            "question": question_text,
            "category": q.get("category", ""),
            "gold_ids": gold_ids,
            "retrieved_ids_top10": retrieved_ids[:10],
            "retrieval_metrics": retrieval_metrics,
            "duration_s": round(time.time() - t0, 2),
        }

        # Answer-Level
        if not retrieval_only:
            try:
                response = run_llm_answer(question_text)
                answer_eval = evaluate_answer(q, response)
                result["answer_eval"] = answer_eval
                result["response_preview"] = response[:300]
            except Exception as e:
                result["answer_eval"] = {"error": str(e)}

        results.append(result)
        hit3 = retrieval_metrics.get("hit@3", 0.0)
        print(f"  Hit@3={hit3:.2f}  MRR={retrieval_metrics['mrr']:.2f}  ({result['duration_s']:.1f}s)")

    duration = time.time() - t_start

    # Aggregierte Metriken
    summary = _compute_summary(results, k_values, retrieval_only)
    summary["duration_s"] = round(duration, 1)
    summary["n_questions"] = len(questions)
    summary["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    output = {
        "summary": summary,
        "results": results,
    }

    # Ausgabe speichern
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "retrieval" if retrieval_only else "full"
    json_path = out_dir / f"eval_{mode}_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    md_path = out_dir / f"eval_{mode}_{ts}.md"
    _write_markdown_report(output, md_path, k_values, retrieval_only)

    _print_summary(summary, k_values, retrieval_only)
    print(f"\n  JSON:     {json_path}")
    print(f"  Markdown: {md_path}\n")

    return output


def _compute_summary(results: list[dict], k_values: list[int], retrieval_only: bool) -> dict:
    n = len(results)
    if n == 0:
        return {}

    agg: dict[str, float] = {}
    for k in k_values:
        hits = [r["retrieval_metrics"].get(f"hit@{k}", 0.0) for r in results]
        ndcgs = [r["retrieval_metrics"].get(f"ndcg@{k}", 0.0) for r in results]
        fhits = [1.0 if r["retrieval_metrics"].get(f"forbidden_hit@{k}", False) else 0.0
                 for r in results]
        agg[f"avg_hit@{k}"] = round(sum(hits) / n, 3)
        agg[f"avg_ndcg@{k}"] = round(sum(ndcgs) / n, 3)
        agg[f"forbidden_hit_rate@{k}"] = round(sum(fhits) / n, 3)

    mrrs = [r["retrieval_metrics"].get("mrr", 0.0) for r in results]
    agg["avg_mrr"] = round(sum(mrrs) / n, 3)

    # Per-Kategorie
    by_cat: dict[str, list[float]] = defaultdict(list)
    for r in results:
        by_cat[r.get("category", "unknown")].append(r["retrieval_metrics"].get("mrr", 0.0))
    agg["by_category"] = {
        cat: round(sum(vals) / len(vals), 3) for cat, vals in sorted(by_cat.items())
    }

    if not retrieval_only:
        answer_scores = [
            r["answer_eval"].get("answer_score", 0.0)
            for r in results
            if "answer_eval" in r and "error" not in r.get("answer_eval", {})
        ]
        if answer_scores:
            agg["avg_answer_score"] = round(sum(answer_scores) / len(answer_scores), 1)

    return agg


def _print_summary(summary: dict, k_values: list[int], retrieval_only: bool):
    print("\n" + "=" * 60)
    print("  OpenLex Eval v3 – Ergebnis-Zusammenfassung")
    print("=" * 60)
    print(f"  Timestamp: {summary.get('timestamp', '')}")
    print(f"  Fragen:    {summary.get('n_questions', 0)}")
    print(f"  Dauer:     {summary.get('duration_s', 0):.1f}s\n")

    print("  Retrieval-Metriken:")
    for k in k_values:
        h = summary.get(f"avg_hit@{k}", 0.0)
        nd = summary.get(f"avg_ndcg@{k}", 0.0)
        fh = summary.get(f"forbidden_hit_rate@{k}", 0.0)
        bar = "█" * int(h * 20) + "░" * (20 - int(h * 20))
        print(f"    Hit@{k:<3d}  {bar} {h:.3f}   nDCG={nd:.3f}   ForbHit={fh:.3f}")
    print(f"    MRR        {'':20s} {summary.get('avg_mrr', 0.0):.3f}")

    by_cat = summary.get("by_category", {})
    if by_cat:
        print("\n  MRR pro Kategorie:")
        for cat, val in sorted(by_cat.items(), key=lambda x: -x[1]):
            bar = "█" * int(val * 20) + "░" * (20 - int(val * 20))
            print(f"    {cat:<25s} {bar} {val:.3f}")

    if not retrieval_only and "avg_answer_score" in summary:
        print(f"\n  Answer-Score (Ø): {summary['avg_answer_score']:.1f} / 100")

    print("=" * 60)


def _write_markdown_report(output: dict, path: Path, k_values: list[int], retrieval_only: bool):
    summary = output["summary"]
    results = output["results"]

    lines = [
        "# OpenLex Eval v3 – Report",
        f"",
        f"**Timestamp:** {summary.get('timestamp', '')}  ",
        f"**Fragen:** {summary.get('n_questions', 0)}  ",
        f"**Dauer:** {summary.get('duration_s', 0):.1f}s  ",
        f"**Modus:** {'Retrieval-only' if retrieval_only else 'Full (Retrieval + LLM)'}",
        "",
        "## Retrieval-Metriken",
        "",
        "| Metrik | Wert |",
        "|--------|------|",
    ]
    for k in k_values:
        lines.append(f"| Hit@{k} | {summary.get(f'avg_hit@{k}', 0.0):.3f} |")
        lines.append(f"| nDCG@{k} | {summary.get(f'avg_ndcg@{k}', 0.0):.3f} |")
        lines.append(f"| ForbiddenHit@{k} | {summary.get(f'forbidden_hit_rate@{k}', 0.0):.3f} |")
    lines.append(f"| MRR | {summary.get('avg_mrr', 0.0):.3f} |")

    by_cat = summary.get("by_category", {})
    if by_cat:
        lines += ["", "## MRR pro Kategorie", "", "| Kategorie | MRR |", "|-----------|-----|"]
        for cat, val in sorted(by_cat.items(), key=lambda x: -x[1]):
            lines.append(f"| {cat} | {val:.3f} |")

    if not retrieval_only and "avg_answer_score" in summary:
        lines += ["", f"## Answer-Score (Ø): {summary['avg_answer_score']:.1f} / 100"]

    lines += ["", "## Einzelergebnisse", ""]
    for r in results:
        lines.append(f"### {r['id']}")
        lines.append(f"**Frage:** {r['question']}  ")
        lines.append(f"**Kategorie:** {r.get('category', '')}  ")
        rm = r["retrieval_metrics"]
        k_str = " | ".join(f"Hit@{k}={rm.get(f'hit@{k}', 0):.2f}" for k in k_values)
        lines.append(f"**Retrieval:** {k_str} | MRR={rm.get('mrr', 0):.2f}  ")
        lines.append(f"**Gold-IDs:** {', '.join(r.get('gold_ids', []))}  ")
        lines.append(f"**Retrieved Top-5:** {', '.join(r.get('retrieved_ids_top10', [])[:5])}  ")
        if "answer_eval" in r and "error" not in r.get("answer_eval", {}):
            ae = r["answer_eval"]
            lines.append(f"**Answer-Score:** {ae.get('answer_score', 0):.1f}  ")
            if ae.get("norms_missing"):
                lines.append(f"**Normen fehlen:** {', '.join(ae['norms_missing'])}  ")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OpenLex Eval v3 – Zweistufiges Eval-Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--eval-set", required=True,
        help="Pfad zur Eval-Set-JSON (z.B. eval_sets/canonical_auto.json)",
    )
    parser.add_argument(
        "--retrieval-only", action="store_true",
        help="Nur Retrieval-Eval (kein LLM)",
    )
    parser.add_argument(
        "--k", type=int, nargs="+", default=DEFAULT_K_VALUES,
        help=f"K-Werte für Hit@K und nDCG@K (default: {DEFAULT_K_VALUES})",
    )
    parser.add_argument(
        "--out-dir", default="eval_results_v3",
        help="Ausgabeverzeichnis für Reports (default: eval_results_v3)",
    )
    parser.add_argument(
        "--category", type=str,
        help="Nur Fragen dieser Kategorie evaluieren",
    )
    args = parser.parse_args()

    os.chdir(BASE_DIR)

    eval_path = Path(args.eval_set)
    if not eval_path.is_absolute():
        eval_path = BASE_DIR / eval_path
    if not eval_path.exists():
        print(f"FEHLER: Eval-Set nicht gefunden: {eval_path}", file=sys.stderr)
        sys.exit(1)

    with open(eval_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    if args.category:
        questions = [q for q in questions if q.get("category") == args.category]
        print(f"  Filter: category={args.category} → {len(questions)} Fragen")

    if not questions:
        print("FEHLER: Keine Fragen im Eval-Set.", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = BASE_DIR / out_dir

    run_eval(
        questions=questions,
        k_values=sorted(set(args.k)),
        retrieval_only=args.retrieval_only,
        out_dir=out_dir,
    )


if __name__ == "__main__":
    main()
