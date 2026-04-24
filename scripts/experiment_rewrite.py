#!/usr/bin/env python3
"""
Experiment: vier Modi vergleichen.
- baseline:         keine Flags
- bm25_only:        OPENLEX_BM25_ENABLED=true
- rewrite_only:     OPENLEX_REWRITE_ENABLED=true
- bm25_plus_rewrite: beide aktiv

Misst Hit@3, Hit@5, MRR, Recall@40 und Kategorien-Verteilung.
Zusätzlich: Cache-Hit-Rate, Rewrite-Durchlaufzeit, Fallback-Rate.
"""
import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from collections import Counter

sys.path.insert(0, "/opt/openlex-mvp")

EVAL_SETS_DIR = Path("/opt/openlex-mvp/eval_sets")
RESULTS_DIR = Path("/opt/openlex-mvp/experiment_results")
RESULTS_DIR.mkdir(exist_ok=True)


def load_eval_set(name: str) -> list:
    for suffix in ("", "_v3"):
        path = EVAL_SETS_DIR / f"{name}{suffix}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
    raise FileNotFoundError(name)


def get_query(entry: dict) -> str:
    return entry.get("query") or entry.get("question", "")


def get_must_ids(entry: dict) -> list:
    rg = entry.get("retrieval_gold", {})
    must = rg.get("must_contain_chunk_ids") or []
    if must:
        return must
    return entry.get("gold_ids", [])


def compute_metrics(eval_results: list) -> dict:
    hit3 = hit5 = 0
    rrs = []
    recall40 = []
    n_gold = 0

    for r in eval_results:
        must_ids = set(r.get("must_contain_chunk_ids", []))
        if not must_ids:
            continue
        n_gold += 1
        retrieved_ids = [c["id"] for c in r.get("retrieved", []) if c.get("id")]

        if any(rid in must_ids for rid in retrieved_ids[:3]):
            hit3 += 1
        if any(rid in must_ids for rid in retrieved_ids[:5]):
            hit5 += 1

        rr = 0.0
        for rank, rid in enumerate(retrieved_ids, start=1):
            if rid in must_ids:
                rr = 1.0 / rank
                break
        rrs.append(rr)

        pool = set(c["id"] for c in r.get("candidate_pool_top40", []) if c.get("id"))
        if pool:
            recall40.append(len(must_ids & pool) / len(must_ids))

    return {
        "n_total": len(eval_results),
        "n_gold": n_gold,
        "hit_at_3": round(hit3 / n_gold, 3) if n_gold else 0,
        "hit_at_5": round(hit5 / n_gold, 3) if n_gold else 0,
        "mrr": round(sum(rrs) / n_gold, 3) if n_gold else 0,
        "recall_at_40": round(sum(recall40) / len(recall40), 3) if recall40 else 0,
    }


def classify_failure(r: dict) -> str | None:
    """Kategorisiert Hit@3-Failures. Gibt None zurück wenn Hit@3 erreicht."""
    must_ids = set(r.get("must_contain_chunk_ids", []))
    if not must_ids:
        return None
    retrieved_ids = [c["id"] for c in r.get("retrieved", []) if c.get("id")]
    if any(rid in must_ids for rid in retrieved_ids[:3]):
        return None  # Hit@3 erreicht, kein Failure

    trace = r.get("trace") or {}
    chunks_trace = trace.get("chunks", {}) if isinstance(trace, dict) else {}
    gold_traces = [chunks_trace[gid] for gid in must_ids if gid in chunks_trace]

    if not gold_traces:
        return "A"  # Pool-Miss

    if any(t["ce_rank"] != -1 and t["ce_rank"] <= 5 and t["final_rank"] == -1
           for t in gold_traces):
        return "E"  # Post-Rerank-Filter

    if any((t["rrf_rank"] != -1 and t["rrf_rank"] <= 40)
           and (t["ce_rank"] == -1 or t["ce_rank"] > 10)
           for t in gold_traces):
        return "B"  # CE-Filter

    if any(t["rrf_rank"] > 20 for t in gold_traces):
        return "C"  # Retrieval-Ceiling

    def prefix(cid):
        parts = cid.split("_")
        return "_".join(parts[:3]) if len(parts) >= 3 else cid

    gold_pfx = {prefix(gid) for gid in must_ids}
    top3_pfx = {prefix(rid) for rid in retrieved_ids[:3]}
    if gold_pfx & top3_pfx:
        return "D"  # Eval-Artefakt

    return "F"


def run_mode(mode_name: str, eval_set_name: str, eval_set: list, flags: dict) -> tuple:
    """Führt einen Modus aus. flags: dict der Env-Vars die gesetzt werden."""
    # Alle Flags zunächst aus
    for k in ("OPENLEX_BM25_ENABLED", "OPENLEX_REWRITE_ENABLED", "OPENLEX_TRACE_MODE"):
        os.environ[k] = "false"
    # Gewünschte Flags setzen
    for k, v in flags.items():
        os.environ[k] = v
    # Trace immer an für Kategorisierung
    os.environ["OPENLEX_TRACE_MODE"] = "true"

    # Reload um Flag-Cache zu umgehen
    import importlib
    import app
    importlib.reload(app)

    results = []
    rewrite_stats = {"calls": 0, "cache_hits": 0, "fallbacks": 0, "total_ms": 0.0}
    t0 = time.time()

    for i, entry in enumerate(eval_set):
        q = get_query(entry)
        must_ids = get_must_ids(entry)

        if i % 10 == 0:
            print(f"    [{i+1}/{len(eval_set)}] {q[:55]}...")

        try:
            retrieved, trace = app.retrieve(
                q, return_trace=True, trace_format="rich"
            )

            # Rewrite-Stats sammeln
            rw = trace.get("rewrite") if isinstance(trace, dict) else None
            if rw and rw.get("used"):
                rewrite_stats["calls"] += 1
                if rw.get("from_cache"):
                    rewrite_stats["cache_hits"] += 1
                if rw.get("error"):
                    rewrite_stats["fallbacks"] += 1
                rewrite_stats["total_ms"] += rw.get("duration_ms", 0)

            # Candidate-Pool aus Trace ableiten (Top-40 nach rrf_rank)
            chunks_trace = (trace.get("chunks", {}) if isinstance(trace, dict) else {}) or {}
            sorted_by_rrf = sorted(
                chunks_trace.items(),
                key=lambda x: x[1]["rrf_rank"] if x[1]["rrf_rank"] > 0 else 999999,
            )
            candidate_pool_top40 = [{"id": cid} for cid, _ in sorted_by_rrf[:40]]

            results.append({
                "query_id": entry.get("id", f"q{i}"),
                "question": q,
                "must_contain_chunk_ids": must_ids,
                "retrieved": [{"id": c.get("id", ""), "ce_score": c.get("ce_score")}
                               for c in retrieved],
                "candidate_pool_top40": candidate_pool_top40,
                "trace": {"chunks": {k: {kk: vv for kk, vv in v.items() if kk != "sources"}
                                     for k, v in chunks_trace.items()},
                          "rewrite": rw},
            })

        except Exception as e:
            print(f"  ERROR query {i}: {e}", file=sys.stderr)
            results.append({
                "query_id": entry.get("id", f"q{i}"),
                "question": q,
                "must_contain_chunk_ids": must_ids,
                "retrieved": [],
                "candidate_pool_top40": [],
                "trace": None,
                "error": str(e),
            })

    duration = time.time() - t0
    metrics = compute_metrics(results)
    metrics.update({
        "duration_s": round(duration, 1),
        "eval_set": eval_set_name,
        "mode": mode_name,
        "rewrite_stats": rewrite_stats,
    })
    return results, metrics


def write_markdown_report(path, timestamp, all_metrics, categories):
    lines = [
        f"# Rewrite-Experiment — {timestamp}",
        "",
        "## Metriken",
        "",
        "| Modus | Eval-Set | N | N(Gold) | Hit@3 | Hit@5 | MRR | Recall@40 | Dauer |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for m in all_metrics:
        lines.append(
            f"| {m['mode']} | {m['eval_set']} | {m['n_total']} | "
            f"{m['n_gold']} | {m['hit_at_3']:.3f} | {m['hit_at_5']:.3f} | "
            f"{m['mrr']:.3f} | {m['recall_at_40']:.3f} | {m['duration_s']}s |"
        )

    lines.extend([
        "",
        "## Rewrite-Statistik",
        "",
        "| Modus | Set | Calls | Cache-Hits | Cache-Rate | Fallbacks | Ø ms/Call |",
        "|---|---|---|---|---|---|---|",
    ])
    for m in all_metrics:
        rs = m["rewrite_stats"]
        if rs["calls"] == 0:
            continue
        hit_rate = rs["cache_hits"] / rs["calls"] * 100 if rs["calls"] else 0
        avg_ms = rs["total_ms"] / rs["calls"] if rs["calls"] else 0
        lines.append(
            f"| {m['mode']} | {m['eval_set']} | {rs['calls']} | "
            f"{rs['cache_hits']} | {hit_rate:.0f}% | "
            f"{rs['fallbacks']} | {avg_ms:.0f} |"
        )

    lines.extend([
        "",
        "## Deltas zur Baseline (Messy)",
        "",
        "| Modus | Hit@3 | Δ | MRR | Δ | Recall@40 | Δ |",
        "|---|---|---|---|---|---|---|",
    ])
    baseline_m = next((m for m in all_metrics
                       if m["mode"] == "baseline" and m["eval_set"] == "messy"), None)
    if baseline_m:
        for m in all_metrics:
            if m["eval_set"] != "messy" or m["mode"] == "baseline":
                continue
            lines.append(
                f"| {m['mode']} | {m['hit_at_3']:.3f} | "
                f"{m['hit_at_3'] - baseline_m['hit_at_3']:+.3f} | "
                f"{m['mrr']:.3f} | {m['mrr'] - baseline_m['mrr']:+.3f} | "
                f"{m['recall_at_40']:.3f} | "
                f"{m['recall_at_40'] - baseline_m['recall_at_40']:+.3f} |"
            )

    cat_desc = {
        "A": "Pool-Miss", "B": "CE-Filter", "C": "Retrieval-Ceiling",
        "D": "Eval-Artefakt", "E": "Post-Rerank-Filter", "F": "Sonstige",
    }
    for set_label in ("canonical", "messy"):
        lines.extend([
            "",
            f"## Failure-Kategorien ({set_label.capitalize()})",
            "",
            "| Modus | A | B | C | D | E | F | Total |",
            "|---|---|---|---|---|---|---|---|",
        ])
        for mode_name in ("baseline", "bm25_only", "rewrite_only", "bm25_plus_rewrite"):
            c = categories.get(f"{mode_name}__{set_label}", {})
            total = sum(c.values())
            lines.append(
                f"| {mode_name} | {c.get('A',0)} | {c.get('B',0)} | "
                f"{c.get('C',0)} | {c.get('D',0)} | {c.get('E',0)} | "
                f"{c.get('F',0)} | {total} |"
            )

    # Interpretation
    lines.extend(["", "## KW-19-Empfehlung", ""])
    rewrite_m = next((m for m in all_metrics
                      if m["mode"] == "rewrite_only" and m["eval_set"] == "messy"), None)
    combo_m = next((m for m in all_metrics
                    if m["mode"] == "bm25_plus_rewrite" and m["eval_set"] == "messy"), None)

    if baseline_m and rewrite_m and combo_m:
        d_rw = rewrite_m["hit_at_3"] - baseline_m["hit_at_3"]
        d_combo = combo_m["hit_at_3"] - baseline_m["hit_at_3"]

        if d_combo >= 0.10:
            lines.append(
                f"**Hypothese bestätigt.** BM25+Rewrite hebt Messy Hit@3 um {d_combo:+.3f}. "
                f"Rewrite bleibt im Stack. Nächster Schritt: Contextual Retrieval / "
                f"Parent-Document für DSGVO-Granularität."
            )
        elif d_rw >= 0.10:
            lines.append(
                f"**Rewrite wirkt, Kombi nicht.** Rewrite-only: {d_rw:+.3f}, "
                f"Combo: {d_combo:+.3f}. BM25 verdünnt Rewrite-Effekt. "
                f"BM25 deaktivieren, Rewrite allein deployen."
            )
        elif 0.03 <= max(d_rw, d_combo) < 0.10:
            lines.append(
                f"**Moderate Verbesserung.** Rewrite-Δ={d_rw:+.3f}, Combo-Δ={d_combo:+.3f}. "
                f"Failure-Kategorien prüfen: wenn A dominant → Prompt schärfen; "
                f"wenn B dominant → Reranker-Swap."
            )
        else:
            lines.append(
                f"**Hypothese nicht bestätigt.** Rewrite-Δ={d_rw:+.3f}, Combo-Δ={d_combo:+.3f}. "
                f"Strukturelles Embedding-Problem. Domain-Embedding-Fine-Tune wird P1. "
                f"EuroHPC-Antrag oder QLoRA auf bge-m3 erwägen."
            )

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Nur 10 Queries pro Set")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_json = RESULTS_DIR / f"experiment_rewrite_{timestamp}.json"
    out_md = RESULTS_DIR / f"experiment_rewrite_{timestamp}.md"

    eval_sets = {}
    for name in ("canonical", "messy"):
        data = load_eval_set(name)
        if args.smoke:
            data = data[:10]
        eval_sets[name] = data
        print(f"  Loaded {name}: {len(data)} queries")

    modes = [
        ("baseline", {}),
        ("bm25_only", {"OPENLEX_BM25_ENABLED": "true"}),
        ("rewrite_only", {"OPENLEX_REWRITE_ENABLED": "true"}),
        ("bm25_plus_rewrite", {"OPENLEX_BM25_ENABLED": "true",
                                "OPENLEX_REWRITE_ENABLED": "true"}),
    ]

    all_results = {}
    all_metrics = []

    for mode_name, flags in modes:
        for set_name, eval_set in eval_sets.items():
            key = f"{mode_name}__{set_name}"
            print(f"\n=== {key} ({len(eval_set)} queries) ===")
            results, metrics = run_mode(mode_name, set_name, eval_set, flags)
            all_results[key] = results
            all_metrics.append(metrics)
            rs = metrics["rewrite_stats"]
            cache_rate = (f"{rs['cache_hits']}/{rs['calls']} "
                          f"({rs['cache_hits']/rs['calls']*100:.0f}%)"
                          if rs["calls"] else "n/a")
            print(f"  Hit@3={metrics['hit_at_3']:.3f} Hit@5={metrics['hit_at_5']:.3f} "
                  f"MRR={metrics['mrr']:.3f} Recall@40={metrics['recall_at_40']:.3f} "
                  f"({metrics['duration_s']}s) Cache={cache_rate}")

    # Kategorien-Analyse
    categories = {}
    for key, results in all_results.items():
        cats = Counter()
        for r in results:
            c = classify_failure(r)
            if c:
                cats[c] += 1
        categories[key] = dict(cats)
        print(f"  Kategorien {key}: {dict(cats)}")

    # JSON speichern (ohne den vollen Trace-Dict wegen Größe)
    output = {
        "timestamp": timestamp,
        "smoke": args.smoke,
        "metrics": all_metrics,
        "categories": categories,
        "results": {
            k: [{kk: vv for kk, vv in r.items() if kk != "trace"} for r in v]
            for k, v in all_results.items()
        },
    }
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2, default=str, ensure_ascii=False)

    write_markdown_report(out_md, timestamp, all_metrics, categories)

    print(f"\nJSON: {out_json}")
    print(f"MD:   {out_md}")

    # Summary
    baseline_m = next((m for m in all_metrics
                       if m["mode"] == "baseline" and m["eval_set"] == "messy"), None)
    rewrite_m = next((m for m in all_metrics
                      if m["mode"] == "rewrite_only" and m["eval_set"] == "messy"), None)
    if baseline_m and rewrite_m:
        delta = rewrite_m["hit_at_3"] - baseline_m["hit_at_3"]
        print(f"\nMessy Hit@3: {baseline_m['hit_at_3']:.3f} → "
              f"{rewrite_m['hit_at_3']:.3f} ({delta:+.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
