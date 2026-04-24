#!/usr/bin/env python3
"""
Intent-Analysis-Experiment: 3 Modi auf beiden Eval-Sets.
Vergleicht: baseline_rewrite_only vs. intent_boosts_no_clarify vs. intent_full
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


def load_set(name):
    for suf in ("", "_v3"):
        p = EVAL_SETS_DIR / f"{name}{suf}.json"
        if p.exists():
            with open(p) as f:
                return json.load(f)
    raise FileNotFoundError(name)


def get_must_ids(entry):
    rg = entry.get("retrieval_gold", {})
    must = rg.get("must_contain_chunk_ids") or []
    if must:
        return must
    return entry.get("gold_ids", [])


def compute_metrics(results):
    hit3 = hit5 = 0
    rrs = []
    n_gold = 0
    n_clarified = 0
    for r in results:
        if r.get("clarification_triggered"):
            n_clarified += 1
            continue
        must = set(r.get("must_contain_chunk_ids", []))
        if not must:
            continue
        n_gold += 1
        rids = [c["id"] for c in r.get("retrieved", []) if c.get("id")]
        if any(x in must for x in rids[:3]):
            hit3 += 1
        if any(x in must for x in rids[:5]):
            hit5 += 1
        rr = 0.0
        for rank, rid in enumerate(rids, 1):
            if rid in must:
                rr = 1.0 / rank
                break
        rrs.append(rr)
    n = n_gold or 1
    return {
        "n_total": len(results),
        "n_clarified": n_clarified,
        "n_gold": n_gold,
        "hit_at_3": round(hit3 / n, 3),
        "hit_at_5": round(hit5 / n, 3),
        "mrr": round(sum(rrs) / n, 3),
    }


def run_mode(mode_name, set_name, eval_set, flags, allow_clarification=True):
    for k, v in flags.items():
        os.environ[k] = v
    for k in ("OPENLEX_INTENT_ANALYSIS_ENABLED", "OPENLEX_REWRITE_ENABLED",
              "OPENLEX_BM25_ENABLED"):
        if k not in flags:
            os.environ[k] = "false"
    os.environ["OPENLEX_TRACE_MODE"] = "true"
    os.environ["OPENLEX_INTENT_CLARIFY_ENABLED"] = "true" if allow_clarification else "false"

    import importlib
    import app
    importlib.reload(app)

    results = []
    intent_stats = Counter()
    t0 = time.time()

    for i, entry in enumerate(eval_set):
        q = entry.get("query") or entry.get("question", "")
        must_ids = get_must_ids(entry)

        if i % 10 == 0:
            print(f"    [{i+1}/{len(eval_set)}] {q[:50]}...")

        try:
            ret = app.retrieve(q, return_trace=True, trace_format="rich",
                               allow_clarification=allow_clarification)

            if isinstance(ret, tuple):
                retrieved, trace = ret
            else:
                retrieved, trace = ret, {}

            intent = trace.get("intent", {}) if isinstance(trace, dict) else {}
            intent_stats[intent.get("intent_type", "none")] += 1

            if isinstance(retrieved, dict) and retrieved.get("type") == "clarification_needed":
                results.append({
                    "query_id": entry.get("id", f"q{i}"),
                    "query": q,
                    "must_contain_chunk_ids": must_ids,
                    "clarification_triggered": True,
                    "clarification_question": retrieved.get("clarification_question"),
                    "intent": intent,
                })
                continue

            results.append({
                "query_id": entry.get("id", f"q{i}"),
                "query": q,
                "must_contain_chunk_ids": must_ids,
                "retrieved": [{"id": c.get("id", "")} for c in retrieved],
                "clarification_triggered": False,
                "intent": intent,
            })
        except Exception as e:
            print(f"  ERROR q{i}: {e}", file=sys.stderr)
            results.append({
                "query_id": entry.get("id", f"q{i}"),
                "query": q,
                "must_contain_chunk_ids": must_ids,
                "error": str(e),
                "clarification_triggered": False,
            })

    duration = time.time() - t0
    m = compute_metrics(results)
    m["duration_s"] = round(duration, 1)
    m["intent_distribution"] = dict(intent_stats)
    return {"mode": mode_name, "eval_set": set_name, "metrics": m, "results": results}


def write_md(path, ts, runs):
    lines = [
        f"# Intent-Experiment — {ts}",
        "",
        "Alle Läufe mit Rewrite aktiv, BM25 aus.",
        "",
        "## Metriken",
        "",
        "| Modus | Set | N_total | N_clar | N_gold | Hit@3 | Hit@5 | MRR | Dauer |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in runs:
        m = r["metrics"]
        lines.append(
            f"| {r['mode']} | {r['eval_set']} | {m['n_total']} | "
            f"{m['n_clarified']} | {m['n_gold']} | "
            f"{m['hit_at_3']:.3f} | {m['hit_at_5']:.3f} | "
            f"{m['mrr']:.3f} | {m['duration_s']}s |"
        )

    lines.extend(["", "## Intent-Verteilung", ""])
    for r in runs:
        dist = r["metrics"].get("intent_distribution", {})
        lines.append(f"**{r['mode']} / {r['eval_set']}**: {dist}")
        lines.append("")

    lines.extend(["", "## Clarifications (aus intent_full-Modus)", ""])
    for r in runs:
        if r["mode"] != "intent_full":
            continue
        clars = [res for res in r["results"] if res.get("clarification_triggered")]
        if not clars:
            lines.append(f"*(keine Clarifications bei {r['eval_set']})*")
        for c in clars[:10]:
            lines.append(f"**[{r['eval_set']}]** Q: {c['query']}")
            lines.append(f"  → {c['clarification_question']}")
            lines.append("")

    def get_m(mode, set_name):
        return next((r["metrics"] for r in runs
                     if r["mode"] == mode and r["eval_set"] == set_name), None)

    lines.extend(["", "## Delta-Analyse (Messy)", ""])
    baseline = get_m("baseline_rewrite_only", "messy")
    boosts = get_m("intent_boosts_no_clarify", "messy")
    full = get_m("intent_full", "messy")

    if baseline:
        lines.append(f"Baseline Messy Hit@3: {baseline['hit_at_3']:.3f}")
    if boosts and baseline:
        d = boosts["hit_at_3"] - baseline["hit_at_3"]
        lines.append(f"Intent-Boosts (kein Clarify): {boosts['hit_at_3']:.3f} ({d:+.3f})")
    if full and baseline:
        d = full["hit_at_3"] - baseline["hit_at_3"]
        clar_rate = full["n_clarified"] / full["n_total"] * 100
        lines.append(f"Intent-Full: {full['hit_at_3']:.3f} ({d:+.3f}), "
                     f"Clarification-Rate: {clar_rate:.0f}%")

    lines.extend(["", "## Delta-Analyse (Canonical)", ""])
    baseline_c = get_m("baseline_rewrite_only", "canonical")
    full_c = get_m("intent_full", "canonical")
    if baseline_c:
        lines.append(f"Baseline Canonical Hit@3: {baseline_c['hit_at_3']:.3f}")
    if full_c and baseline_c:
        d = full_c["hit_at_3"] - baseline_c["hit_at_3"]
        lines.append(f"Intent-Full Canonical: {full_c['hit_at_3']:.3f} ({d:+.3f})")

    lines.extend(["", "## Interpretation", ""])
    if baseline and full:
        d = full["hit_at_3"] - baseline["hit_at_3"]
        clar_rate = full["n_clarified"] / full["n_total"] * 100

        if clar_rate > 30:
            lines.append(f"WARNUNG: Clarification-Rate {clar_rate:.0f}% > 30%. "
                         "Nicht production-deploy in dieser Konfiguration.")
        elif clar_rate < 5:
            lines.append(f"Clarification-Rate {clar_rate:.0f}% sehr niedrig — Feature wirkt kaum auf Eval-Set.")
        else:
            lines.append(f"Clarification-Rate {clar_rate:.0f}% — plausibel.")

        if d >= 0.03:
            lines.append(f"Intent-Boosts + Clarification heben Messy Hit@3 um {d:+.3f}. "
                         "Empfehlung: in Production deployen.")
        elif d >= 0.0:
            lines.append(f"Marginaler Effekt ({d:+.3f}). "
                         "Deployment sinnvoll wegen Clarification-UX.")
        else:
            lines.append(f"Negativer Effekt ({d:+.3f}). "
                         "Intent-Boosts prüfen — ggf. Multiplikatoren reduzieren.")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_json = RESULTS_DIR / f"intent_{ts}.json"
    out_md = RESULTS_DIR / f"intent_{ts}.md"

    sets = {}
    for name in ("canonical", "messy"):
        data = load_set(name)
        sets[name] = data
        print(f"  Loaded {name}: {len(data)} queries")

    modes = [
        ("baseline_rewrite_only",
         {"OPENLEX_REWRITE_ENABLED": "true"},
         False),
        ("intent_boosts_no_clarify",
         {"OPENLEX_REWRITE_ENABLED": "true", "OPENLEX_INTENT_ANALYSIS_ENABLED": "true"},
         False),
        ("intent_full",
         {"OPENLEX_REWRITE_ENABLED": "true", "OPENLEX_INTENT_ANALYSIS_ENABLED": "true"},
         True),
    ]

    all_runs = []
    for mode_name, flags, allow_clarif in modes:
        for set_name, eval_set in sets.items():
            print(f"\n=== {mode_name} / {set_name} ({len(eval_set)} queries) ===")
            run = run_mode(mode_name, set_name, eval_set, flags, allow_clarif)
            all_runs.append(run)
            m = run["metrics"]
            print(f"  Hit@3={m['hit_at_3']:.3f} Hit@5={m['hit_at_5']:.3f} "
                  f"MRR={m['mrr']:.3f} n_clar={m['n_clarified']} ({m['duration_s']}s)")

    with open(out_json, "w") as f:
        json.dump({"timestamp": ts, "runs": all_runs}, f, indent=2, default=str)

    write_md(out_md, ts, all_runs)
    print(f"\nJSON: {out_json}")
    print(f"MD:   {out_md}")

    # Summary
    for mode_name, _, _ in modes:
        for set_name in ("canonical", "messy"):
            m = next((r["metrics"] for r in all_runs
                      if r["mode"] == mode_name and r["eval_set"] == set_name), None)
            if m:
                print(f"  {mode_name}/{set_name}: Hit@3={m['hit_at_3']:.3f}")


if __name__ == "__main__":
    main()
