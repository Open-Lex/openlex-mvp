#!/usr/bin/env python3
"""
BM25-Experiment: Läuft Eval-Sets in drei Modi und vergleicht.
Unterstützte Modi: baseline, bm25_rrf, bm25_rrf_trace
"""
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from collections import Counter

sys.path.insert(0, "/opt/openlex-mvp")

EVAL_SETS_DIR = Path("/opt/openlex-mvp/eval_sets")
RESULTS_DIR = Path("/opt/openlex-mvp/experiment_results")
RESULTS_DIR.mkdir(exist_ok=True)


def load_eval_set(name: str) -> list:
    """Lädt Canonical oder Messy Eval-Set."""
    for suffix in ["", "_v3"]:
        path = EVAL_SETS_DIR / f"{name}{suffix}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
    raise FileNotFoundError(f"Eval-Set nicht gefunden: {name}")


def get_must_ids(entry: dict) -> list:
    """Extrahiert must_contain_chunk_ids aus entry."""
    rg = entry.get("retrieval_gold", {})
    must = rg.get("must_contain_chunk_ids") or []
    if must:
        return must
    return entry.get("gold_ids", [])


def compute_metrics(eval_results: list) -> dict:
    """Berechnet Hit@3, Hit@5, MRR aus Eval-Ergebnissen."""
    hit_at_3_vals = []
    hit_at_5_vals = []
    reciprocal_ranks = []
    n_with_gold = 0

    for r in eval_results:
        must_ids = set(r.get("must_contain_chunk_ids", []))
        retrieved_ids = [c["id"] for c in r.get("retrieved", []) if c.get("id")]

        if not must_ids:
            continue
        n_with_gold += 1

        h3 = int(any(rid in must_ids for rid in retrieved_ids[:3]))
        h5 = int(any(rid in must_ids for rid in retrieved_ids[:5]))
        hit_at_3_vals.append(h3)
        hit_at_5_vals.append(h5)

        rr = 0.0
        for rank, rid in enumerate(retrieved_ids, start=1):
            if rid in must_ids:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

    n = n_with_gold or 1
    return {
        "n": len(eval_results),
        "n_with_gold": n_with_gold,
        "hit_at_3": round(sum(hit_at_3_vals) / n, 3),
        "hit_at_5": round(sum(hit_at_5_vals) / n, 3),
        "mrr": round(sum(reciprocal_ranks) / n, 3),
    }


def run_mode(
    mode_name: str,
    eval_set_name: str,
    eval_set: list,
    bm25_enabled: bool,
    trace_mode: bool,
) -> tuple:
    """Führt einen Modus auf einem Eval-Set aus."""
    os.environ["OPENLEX_BM25_ENABLED"] = "true" if bm25_enabled else "false"
    os.environ["OPENLEX_TRACE_MODE"] = "true" if trace_mode else "false"

    import importlib
    import app
    importlib.reload(app)

    results = []
    t0 = time.time()

    for i, entry in enumerate(eval_set):
        q = entry.get("question") or entry.get("query", "")
        must_ids = get_must_ids(entry)

        if i % 10 == 0:
            print(f"    [{i+1}/{len(eval_set)}] {q[:50]}...")

        try:
            if trace_mode:
                retrieved, trace = app.retrieve(q, return_trace=True)
            else:
                retrieved = app.retrieve(q)
                trace = None

            results.append({
                "query_id": entry.get("id", f"q{i}"),
                "question": q,
                "category": entry.get("category", "unbekannt"),
                "must_contain_chunk_ids": must_ids,
                "retrieved": [{"id": c.get("id", ""), "source": c.get("source", ""), "ce_score": c.get("ce_score")} for c in retrieved],
                "trace": trace,
            })
        except Exception as e:
            print(f"  ERROR query {i}: {e}", file=sys.stderr)
            results.append({
                "query_id": entry.get("id", f"q{i}"),
                "question": q,
                "must_contain_chunk_ids": must_ids,
                "retrieved": [],
                "trace": None,
                "error": str(e),
            })

    duration = time.time() - t0
    metrics = compute_metrics(results)
    metrics["duration_s"] = round(duration, 1)
    metrics["eval_set"] = eval_set_name
    metrics["mode"] = mode_name
    return results, metrics


def categorize_failures(trace_results: list) -> dict:
    """Kategorisiert Hit@3-Failures für Queries mit Trace-Daten.

    A: Pool-Miss — Gold nie im Trace-Pool
    B: CE-Filter — Gold im Pool, ce_rank hoch oder -1, final_rank -1
    C: Retrieval-Ceiling — Gold tief im Pool (rrf_rank > 20), CE kann nicht helfen
    D: Eval-Artefakt — Top-3 hat gleiches Dokument-Prefix wie Gold
    E: Post-Rerank-Filter — Gold hatte guten CE-Rank aber filter_reason gesetzt
    F: Sonstige
    """
    counts = Counter()
    for r in trace_results:
        must_ids = set(r.get("must_contain_chunk_ids", []))
        retrieved_ids = [c["id"] for c in r.get("retrieved", []) if c.get("id")]
        trace = r.get("trace") or {}

        if not must_ids:
            continue

        # Hit@3 erreicht? → kein Failure
        if any(rid in must_ids for rid in retrieved_ids[:3]):
            continue

        gold_traces = [trace[gid] for gid in must_ids if gid in trace]

        if not gold_traces:
            counts["A"] += 1
            continue

        # E: Gold hatte CE-Rank ≤ 5 aber final_rank > 3 (filter weggenommen)
        if any(t["ce_rank"] != -1 and t["ce_rank"] <= 5 and t["final_rank"] == -1
               for t in gold_traces):
            counts["E"] += 1
            continue

        # B: Gold im Pool, aber CE-Rank schlecht oder -1
        if any((t["rrf_rank"] != -1 and t["rrf_rank"] <= 40)
               and (t["ce_rank"] == -1 or t["ce_rank"] > 10)
               for t in gold_traces):
            counts["B"] += 1
            continue

        # C: Gold erst tief im Pool (rrf_rank > 20)
        if any(t["rrf_rank"] > 20 for t in gold_traces):
            counts["C"] += 1
            continue

        # D: Gleiches Dokument-Prefix in Top-3
        def prefix(cid):
            parts = cid.split("_")
            return "_".join(parts[:3]) if len(parts) >= 3 else cid

        gold_pfx = {prefix(gid) for gid in must_ids}
        top3_pfx = {prefix(rid) for rid in retrieved_ids[:3]}
        if gold_pfx & top3_pfx:
            counts["D"] += 1
            continue

        counts["F"] += 1

    return dict(counts)


def write_markdown_report(path, timestamp, all_metrics, categories_canonical, categories_messy, baseline_c, baseline_m, bm25_c, bm25_m):
    lines = [
        f"# BM25-Experiment — {timestamp}",
        "",
        "## Metriken",
        "",
        "| Modus | Eval-Set | N | N(Gold) | Hit@3 | Hit@5 | MRR | Dauer |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for m in all_metrics:
        lines.append(
            f"| {m['mode']} | {m['eval_set']} | {m['n']} | {m.get('n_with_gold', '?')} | "
            f"{m['hit_at_3']:.3f} | {m['hit_at_5']:.3f} | {m['mrr']:.3f} | {m['duration_s']}s |"
        )

    lines.extend([
        "",
        "## Delta Baseline → BM25+RRF",
        "",
        "| Eval-Set | Hit@3 | Δ | Hit@5 | Δ | MRR | Δ |",
        "|---|---|---|---|---|---|---|",
    ])
    for set_name, b, t in [("canonical", baseline_c, bm25_c), ("messy", baseline_m, bm25_m)]:
        if b and t:
            lines.append(
                f"| {set_name} | "
                f"{b['hit_at_3']:.3f} → {t['hit_at_3']:.3f} | {t['hit_at_3']-b['hit_at_3']:+.3f} | "
                f"{b['hit_at_5']:.3f} → {t['hit_at_5']:.3f} | {t['hit_at_5']-b['hit_at_5']:+.3f} | "
                f"{b['mrr']:.3f} → {t['mrr']:.3f} | {t['mrr']-b['mrr']:+.3f} |"
            )

    cat_desc = {
        "A": "Pool-Miss (Gold nie im Trace-Pool)",
        "B": "CE-Filter (Gold im Pool, CE drückt runter / cut)",
        "C": "Retrieval-Ceiling (Gold erst tief im Pool, rrf_rank > 20)",
        "D": "Eval-Artefakt (Top-3 hat gleiches Dok-Prefix wie Gold)",
        "E": "Post-Rerank-Filter (Boost/Dedup/Cutoff entfernt Gold)",
        "F": "Sonstige/Mixed",
    }
    lines.extend([
        "",
        "## Kategorien-Verteilung Hit@3-Failures (Trace-Modus)",
        "",
        "| Kat | Canonical | Messy | Beschreibung |",
        "|---|---|---|---|",
    ])
    for cat in ["A", "B", "C", "D", "E", "F"]:
        c_n = categories_canonical.get(cat, 0)
        m_n = categories_messy.get(cat, 0)
        lines.append(f"| {cat} | {c_n} | {m_n} | {cat_desc[cat]} |")

    # KW-18-Empfehlung
    delta_messy = (bm25_m["hit_at_3"] - baseline_m["hit_at_3"]) if (bm25_m and baseline_m) else 0
    total_m = sum(categories_messy.values()) or 1
    cat_a_pct = categories_messy.get("A", 0) / total_m
    cat_b_pct = categories_messy.get("B", 0) / total_m
    cat_c_pct = categories_messy.get("C", 0) / total_m

    lines.extend(["", "## KW-18-Empfehlung", ""])
    if delta_messy >= 0.10:
        lines.append(
            f"**Szenario 1 — Contextual Retrieval / BM25 weiter ausbauen.** "
            f"BM25+RRF hebt Messy Hit@3 um {delta_messy:+.3f}. Match-Grundlage-Hypothese bestätigt."
        )
    elif delta_messy < 0.03:
        lines.append(
            f"**Szenario 3 — LLM-Query-Rewriting.** "
            f"BM25+RRF hebt Messy Hit@3 nur um {delta_messy:+.3f}. "
            f"Vocabulary-Mismatch ist zu tief; Query-Reformulierung vor Retrieval nötig."
        )
    else:
        if cat_a_pct >= 0.30:
            lines.append(f"**Szenario 2a — LLM-Query-Rewriting.** Δ={delta_messy:+.3f}. Kategorie A: {cat_a_pct:.0%} ≥ 30%.")
        elif cat_b_pct >= 0.40:
            lines.append(f"**Szenario 2b — Reranker-Swap.** Δ={delta_messy:+.3f}. Kategorie B: {cat_b_pct:.0%} ≥ 40%.")
        elif cat_c_pct >= 0.40:
            lines.append(f"**Szenario 2c — Contextual Retrieval.** Δ={delta_messy:+.3f}. Kategorie C: {cat_c_pct:.0%} ≥ 40%.")
        else:
            lines.append(
                f"**Mixed.** Δ={delta_messy:+.3f}. "
                f"A={cat_a_pct:.0%} B={cat_b_pct:.0%} C={cat_c_pct:.0%}. "
                f"Priorität: LLM-Rewrite > Contextual Retrieval > Reranker."
            )

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    # Eval-Sets laden
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Nur 10 Queries pro Set")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_json = RESULTS_DIR / f"experiment_bm25_{timestamp}.json"
    out_md = RESULTS_DIR / f"experiment_bm25_{timestamp}.md"

    eval_sets = {}
    for name in ["canonical_v3", "messy"]:
        short = name.replace("_v3", "")
        data = load_eval_set(name)
        if args.smoke:
            data = data[:10]
        eval_sets[short] = data
        print(f"  Loaded {short}: {len(data)} queries")

    # Drei Modi: baseline, bm25_rrf, bm25_rrf_trace
    all_results = {}
    all_metrics = []

    for mode_name, bm25, trace in [
        ("baseline", False, False),
        ("bm25_rrf", True, False),
        ("bm25_rrf_trace", True, True),
    ]:
        for set_name, eval_set in eval_sets.items():
            key = f"{mode_name}__{set_name}"
            print(f"\n=== {key} ({len(eval_set)} queries) ===")
            results, metrics = run_mode(mode_name, set_name, eval_set, bm25, trace)
            all_results[key] = results
            all_metrics.append(metrics)
            print(f"  Hit@3={metrics['hit_at_3']:.3f}  Hit@5={metrics['hit_at_5']:.3f}  MRR={metrics['mrr']:.3f}  Dauer={metrics['duration_s']}s")

    # Baseline + BM25 Metriken für Vergleich
    baseline_c = next((m for m in all_metrics if m["mode"] == "baseline" and m["eval_set"] == "canonical"), None)
    baseline_m = next((m for m in all_metrics if m["mode"] == "baseline" and m["eval_set"] == "messy"), None)
    bm25_c = next((m for m in all_metrics if m["mode"] == "bm25_rrf" and m["eval_set"] == "canonical"), None)
    bm25_m = next((m for m in all_metrics if m["mode"] == "bm25_rrf" and m["eval_set"] == "messy"), None)

    # Kategorien-Analyse aus Trace-Modus
    trace_c = all_results.get("bm25_rrf_trace__canonical", [])
    trace_m = all_results.get("bm25_rrf_trace__messy", [])
    categories_canonical = categorize_failures(trace_c)
    categories_messy = categorize_failures(trace_m)

    print(f"\n=== Kategorien Canonical: {categories_canonical}")
    print(f"=== Kategorien Messy:    {categories_messy}")

    # JSON speichern (ohne Trace, der ist zu groß)
    output = {
        "timestamp": timestamp,
        "smoke": args.smoke,
        "metrics": all_metrics,
        "categories_canonical": categories_canonical,
        "categories_messy": categories_messy,
        "results": {
            k: [{kk: vv for kk, vv in r.items() if kk != "trace"} for r in v]
            for k, v in all_results.items()
        },
    }
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2, default=str, ensure_ascii=False)

    write_markdown_report(
        out_md, timestamp, all_metrics,
        categories_canonical, categories_messy,
        baseline_c, baseline_m, bm25_c, bm25_m,
    )

    print(f"\nJSON:   {out_json}")
    print(f"Report: {out_md}")

    # Summary
    if baseline_m and bm25_m:
        delta = bm25_m["hit_at_3"] - baseline_m["hit_at_3"]
        print(f"\nMessy Hit@3: {baseline_m['hit_at_3']:.3f} → {bm25_m['hit_at_3']:.3f} ({delta:+.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
