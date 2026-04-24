#!/usr/bin/env python3
"""
CE-Swap-Experiment: Vergleich mmarco-mMiniLMv2 vs BAAI/bge-reranker-v2-m3
unter Rewrite-Bedingungen.

Modi:
  rewrite_mmarco  — REWRITE=true, RERANKER=mmarco  (Kontrolle = aktuell deployed)
  rewrite_bge     — REWRITE=true, RERANKER=bge-v2-m3

Eval-Sets: canonical_v3, messy (je 78 / 74 Queries, voller Lauf)
Metriken:  Hit@3, Hit@5, MRR, Recall@40
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
RESULTS_DIR   = Path("/opt/openlex-mvp/experiment_results")
RESULTS_DIR.mkdir(exist_ok=True)

MMARCO = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
BGE    = "BAAI/bge-reranker-v2-m3"


def load_eval_set(name: str) -> list:
    for suffix in ("", "_v3"):
        p = EVAL_SETS_DIR / f"{name}{suffix}.json"
        if p.exists():
            with open(p) as f:
                return json.load(f)
    raise FileNotFoundError(name)


def get_must_ids(entry: dict) -> list:
    rg = entry.get("retrieval_gold", {})
    must = rg.get("must_contain_chunk_ids") or []
    return must if must else entry.get("gold_ids", [])


def compute_metrics(eval_results: list) -> dict:
    h3, h5, rr = [], [], []
    n_gold = 0
    for r in eval_results:
        must = set(r.get("must_contain_chunk_ids", []))
        ids  = [c["id"] for c in r.get("retrieved", []) if c.get("id")]
        if not must:
            continue
        n_gold += 1
        h3.append(int(any(i in must for i in ids[:3])))
        h5.append(int(any(i in must for i in ids[:5])))
        mrr_val = 0.0
        for rank, i in enumerate(ids, 1):
            if i in must:
                mrr_val = 1.0 / rank
                break
        rr.append(mrr_val)
    n = n_gold or 1
    # Recall@40
    recall40 = []
    for r in eval_results:
        must = set(r.get("must_contain_chunk_ids", []))
        ids  = [c["id"] for c in r.get("retrieved", []) if c.get("id")]
        if not must:
            continue
        recall40.append(int(any(i in must for i in ids[:40])))
    return {
        "n": len(eval_results),
        "n_with_gold": n_gold,
        "hit_at_3":  round(sum(h3) / n, 3),
        "hit_at_5":  round(sum(h5) / n, 3),
        "mrr":       round(sum(rr)  / n, 3),
        "recall_40": round(sum(recall40) / n, 3) if recall40 else 0.0,
    }


def categorize_failures(trace_results: list) -> dict:
    """Analog KW17/KW18 Kategorien A-F."""
    counts = Counter()
    for r in trace_results:
        must = set(r.get("must_contain_chunk_ids", []))
        ids  = [c["id"] for c in r.get("retrieved", []) if c.get("id")]
        trace = r.get("trace") or {}
        if not must:
            continue
        if any(i in must for i in ids[:3]):
            continue  # Hit@3 — kein Failure
        gold_t = [trace[g] for g in must if g in trace]
        if not gold_t:
            counts["A"] += 1; continue
        if any(t["ce_rank"] != -1 and t["ce_rank"] <= 5 and t["final_rank"] == -1 for t in gold_t):
            counts["E"] += 1; continue
        if any((t["rrf_rank"] != -1 and t["rrf_rank"] <= 40) and (t["ce_rank"] == -1 or t["ce_rank"] > 10) for t in gold_t):
            counts["B"] += 1; continue
        if any(t["rrf_rank"] > 20 for t in gold_t):
            counts["C"] += 1; continue
        def pfx(c):
            p = c.split("_"); return "_".join(p[:3]) if len(p) >= 3 else c
        if {pfx(g) for g in must} & {pfx(i) for i in ids[:3]}:
            counts["D"] += 1; continue
        counts["F"] += 1
    return dict(counts)


def run_mode(mode_name: str, eval_set_name: str, eval_set: list,
             reranker_model: str, smoke: bool = False) -> tuple:
    os.environ["OPENLEX_REWRITE_ENABLED"] = "true"
    os.environ["OPENLEX_BM25_ENABLED"]    = "false"
    os.environ["OPENLEX_TRACE_MODE"]      = "true"
    os.environ["RERANKER_MODEL"]          = reranker_model

    import importlib
    import app
    importlib.reload(app)

    queries = eval_set[:5] if smoke else eval_set
    results = []
    t0 = time.time()

    for i, entry in enumerate(queries):
        q = entry.get("question") or entry.get("query", "")
        must_ids = get_must_ids(entry)
        if i % 10 == 0:
            print(f"    [{i+1:3d}/{len(queries)}] {q[:55]}...")
        try:
            retrieved, trace = app.retrieve(q, return_trace=True)
            results.append({
                "query_id": entry.get("id", f"q{i}"),
                "question": q,
                "category": entry.get("category", "unbekannt"),
                "must_contain_chunk_ids": must_ids,
                "retrieved": [
                    {"id": c.get("id", ""), "source": c.get("source", ""), "ce_score": c.get("ce_score")}
                    for c in retrieved
                ],
                "trace": trace,
            })
        except Exception as e:
            print(f"  ERROR q{i}: {e}", file=sys.stderr)
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
    metrics.update({
        "duration_s": round(duration, 1),
        "eval_set":   eval_set_name,
        "mode":       mode_name,
        "reranker":   reranker_model,
    })
    return results, metrics


def write_markdown(path, timestamp, all_metrics, cats, smoke):
    lines = [
        f"# CE-Swap-Experiment — {timestamp}",
        f"{'(SMOKE TEST — nur erste 5 Queries)' if smoke else ''}",
        "",
        "## Metriken",
        "",
        "| Modus | Eval-Set | N | N(Gold) | Hit@3 | Hit@5 | MRR | Recall@40 | Dauer |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for m in all_metrics:
        lines.append(
            f"| {m['mode']} | {m['eval_set']} | {m['n']} | {m.get('n_with_gold', '?')} | "
            f"{m['hit_at_3']:.3f} | {m['hit_at_5']:.3f} | {m['mrr']:.3f} | "
            f"{m.get('recall_40', 0.0):.3f} | {m['duration_s']}s |"
        )

    lines.extend([
        "",
        "## Delta mmarco → BGE",
        "",
        "| Eval-Set | Hit@3 | Δ | Hit@5 | Δ | MRR | Δ |",
        "|---|---|---|---|---|---|---|",
    ])
    for sn in ("canonical", "messy"):
        b = next((m for m in all_metrics if m["mode"] == "rewrite_mmarco" and m["eval_set"] == sn), None)
        t = next((m for m in all_metrics if m["mode"] == "rewrite_bge"    and m["eval_set"] == sn), None)
        if b and t:
            lines.append(
                f"| {sn} | "
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
        "| Kat | rewrite_mmarco canonical | rewrite_mmarco messy | rewrite_bge canonical | rewrite_bge messy | Beschreibung |",
        "|---|---|---|---|---|---|",
    ])
    for cat in ["A", "B", "C", "D", "E", "F"]:
        lines.append(
            f"| {cat} | "
            f"{cats.get('rewrite_mmarco__canonical',{}).get(cat,0)} | "
            f"{cats.get('rewrite_mmarco__messy',{}).get(cat,0)} | "
            f"{cats.get('rewrite_bge__canonical',{}).get(cat,0)} | "
            f"{cats.get('rewrite_bge__messy',{}).get(cat,0)} | "
            f"{cat_desc[cat]} |"
        )

    # Empfehlung
    b_m = next((m for m in all_metrics if m["mode"] == "rewrite_mmarco" and m["eval_set"] == "messy"), None)
    t_m = next((m for m in all_metrics if m["mode"] == "rewrite_bge"    and m["eval_set"] == "messy"), None)
    lines.extend(["", "## Empfehlung", ""])
    if b_m and t_m:
        delta = t_m["hit_at_3"] - b_m["hit_at_3"]
        cat_b_bge = cats.get("rewrite_bge__messy", {}).get("B", 0)
        total_bge  = sum(cats.get("rewrite_bge__messy", {}).values()) or 1
        if delta >= 0.03:
            lines.append(
                f"**BGE deployen.** Δ Messy Hit@3 = {delta:+.3f}. "
                f"Kategorie-B-Failures: {cat_b_bge}/{total_bge} ({cat_b_bge/total_bge:.0%})."
            )
        elif delta >= -0.02:
            lines.append(
                f"**Neutral.** Δ = {delta:+.3f}. Kein klarer Vorteil; mmarco behalten "
                f"(geringere Modellgröße, gleiches Deployment-Risiko)."
            )
        else:
            lines.append(
                f"**mmarco behalten.** BGE schlechter: Δ = {delta:+.3f}. Deployment abbrechen."
            )

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Nur erste 5 Queries")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_json  = RESULTS_DIR / f"experiment_ce_swap_{timestamp}.json"
    out_md    = RESULTS_DIR / f"experiment_ce_swap_{timestamp}.md"

    eval_sets = {}
    for name in ("canonical_v3", "messy"):
        short = name.replace("_v3", "")
        data = load_eval_set(name)
        eval_sets[short] = data
        print(f"  Loaded {short}: {len(data)} queries")

    modes = [
        ("rewrite_mmarco", MMARCO),
        ("rewrite_bge",    BGE),
    ]

    all_results = {}
    all_metrics = []
    cats = {}

    for mode_name, reranker in modes:
        for set_name, eval_set in eval_sets.items():
            key = f"{mode_name}__{set_name}"
            print(f"\n=== {key} ({len(eval_set) if not args.smoke else 5} queries) ===")
            results, metrics = run_mode(mode_name, set_name, eval_set, reranker, smoke=args.smoke)
            all_results[key] = results
            all_metrics.append(metrics)
            cats[key] = categorize_failures(results)
            print(f"  Hit@3={metrics['hit_at_3']:.3f}  Hit@5={metrics['hit_at_5']:.3f}  "
                  f"MRR={metrics['mrr']:.3f}  Recall@40={metrics.get('recall_40',0):.3f}  "
                  f"Dauer={metrics['duration_s']}s")
            print(f"  Failures: {cats[key]}")

    output = {
        "timestamp": timestamp,
        "smoke": args.smoke,
        "metrics": all_metrics,
        "categories": cats,
        "results": {
            k: [{kk: vv for kk, vv in r.items() if kk != "trace"} for r in v]
            for k, v in all_results.items()
        },
    }
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2, default=str, ensure_ascii=False)

    write_markdown(out_md, timestamp, all_metrics, cats, smoke=args.smoke)
    print(f"\nJSON: {out_json}")
    print(f"MD:   {out_md}")

    # Summary
    b = next((m for m in all_metrics if m["mode"] == "rewrite_mmarco" and m["eval_set"] == "messy"), None)
    t = next((m for m in all_metrics if m["mode"] == "rewrite_bge"    and m["eval_set"] == "messy"), None)
    if b and t:
        print(f"\nMessy Hit@3: {b['hit_at_3']:.3f} (mmarco) → {t['hit_at_3']:.3f} (bge)  Δ={t['hit_at_3']-b['hit_at_3']:+.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
