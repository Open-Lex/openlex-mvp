#!/usr/bin/env python3
"""
Faithfulness-Messung über beide Eval-Sets mit Rewrite + ohne Rewrite.
Nutzt die bestehende app.py-Pipeline für Retrieval + Answer-Generation.
"""
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

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


def run_for_mode(
    mode_name: str,
    eval_set_name: str,
    eval_set: list,
    flags: dict,
    max_queries: int = None,
) -> dict:
    """Läuft Retrieval + Answer + Faithfulness-Messung für einen Modus."""
    for k, v in flags.items():
        os.environ[k] = v
    for k in ("OPENLEX_REWRITE_ENABLED", "OPENLEX_BM25_ENABLED"):
        if k not in flags:
            os.environ[k] = "false"

    import importlib
    import app as _app
    importlib.reload(_app)

    from faithfulness import measure_faithfulness, generate_answer_from_chunks

    queries = eval_set[:max_queries] if max_queries else eval_set
    results = []
    t0 = time.time()

    for i, entry in enumerate(queries):
        q = get_query(entry)
        if not q:
            continue
        print(f"  [{i+1:3d}/{len(queries)}] {mode_name}/{eval_set_name}: {q[:55]}...")

        try:
            # Retrieval
            retrieved = _app.retrieve(q)
            context_chunks = [c.get("text", "") for c in retrieved if c.get("text")]

            # Generate Answer
            answer = generate_answer_from_chunks(q, retrieved)

            if not answer or len(answer) < 20:
                print(f"    WARNING: short answer ({len(answer)} chars)")
                results.append({
                    "query_id": entry.get("id", f"q{i}"),
                    "query": q,
                    "error": "answer_too_short",
                    "answer": answer,
                })
                continue

            # Faithfulness
            fr = measure_faithfulness(answer, context_chunks)

            results.append({
                "query_id": entry.get("id", f"q{i}"),
                "query": q,
                "answer": answer[:500],  # Platz sparen
                "n_chunks": len(context_chunks),
                "total_claims": fr.total_claims,
                "supported": fr.supported,
                "contradicted": fr.contradicted,
                "ungrounded": fr.ungrounded,
                "supported_rate": fr.supported_rate,
                "contradiction_rate": fr.contradiction_rate,
                "ungrounded_rate": fr.ungrounded_rate,
                "verdicts": [
                    {
                        "claim": v.claim,
                        "label": v.label,
                        "score": round(v.score, 4),
                        "evidence_excerpt": (v.evidence_excerpt or "")[:150],
                    }
                    for v in fr.verdicts
                ],
            })
            print(f"    supp={fr.supported_rate:.2f} contra={fr.contradiction_rate:.2f} "
                  f"ungr={fr.ungrounded_rate:.2f} claims={fr.total_claims}")

        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)
            results.append({
                "query_id": entry.get("id", f"q{i}"),
                "query": q,
                "error": str(e),
            })

    duration = time.time() - t0
    valid = [r for r in results if "error" not in r and r.get("total_claims", 0) > 0]

    if not valid:
        return {
            "mode": mode_name, "eval_set": eval_set_name,
            "n_queries": len(queries), "n_valid": 0,
            "duration_s": round(duration, 1), "error": "no_valid_results",
        }

    total_claims = sum(r["total_claims"] for r in valid)
    total_supp = sum(r["supported"] for r in valid)
    total_contra = sum(r["contradicted"] for r in valid)
    total_ungr = sum(r["ungrounded"] for r in valid)

    return {
        "mode": mode_name,
        "eval_set": eval_set_name,
        "n_queries": len(queries),
        "n_valid": len(valid),
        "total_claims": total_claims,
        "avg_claims_per_query": round(total_claims / len(valid), 1),
        "supported_rate_micro": round(total_supp / total_claims, 4) if total_claims else 0,
        "contradiction_rate_micro": round(total_contra / total_claims, 4) if total_claims else 0,
        "ungrounded_rate_micro": round(total_ungr / total_claims, 4) if total_claims else 0,
        "supported_rate_macro": round(
            sum(r["supported_rate"] for r in valid) / len(valid), 4),
        "contradiction_rate_macro": round(
            sum(r["contradiction_rate"] for r in valid) / len(valid), 4),
        "duration_s": round(duration, 1),
        "results": results,
    }


def write_markdown(path, timestamp, runs, max_queries):
    lines = [
        f"# Faithfulness-Baseline — {timestamp}",
        f"",
        f"Subset: {max_queries} Queries je Set. NLI-Modell: cross-encoder/nli-deberta-v3-large",
        f"",
        "## Aggregate (Micro-Average über Claims)",
        "",
        "| Modus | Set | N(valid) | Claims | Supported | Contradicted | Ungrounded |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in runs:
        if r.get("error"):
            lines.append(f"| {r['mode']} | {r['eval_set']} | ERROR | | | | |")
            continue
        lines.append(
            f"| {r['mode']} | {r['eval_set']} | {r['n_valid']} | "
            f"{r['total_claims']} | "
            f"{r['supported_rate_micro']:.1%} | "
            f"{r['contradiction_rate_micro']:.1%} | "
            f"{r['ungrounded_rate_micro']:.1%} |"
        )

    lines.extend([
        "",
        "## Vergleich zu Commercial Tools (Stanford Magesh et al. 2024/26)",
        "",
        "| System | Contradiction-Rate | Supported-Rate (est.) |",
        "|---|---|---|",
        "| Westlaw AI (Jan 2026) | 8 % | ~75% |",
        "| Lexis+ AI (Jan 2026) | 11 % | ~70% |",
        "| Practical Law AI | ~17 % | ~65% |",
        "| GPT-4 ohne RAG (2024) | 58 % | ~30% |",
    ])

    rewrite_messy = next(
        (r for r in runs if r["mode"] == "rewrite" and r["eval_set"] == "messy"
         and not r.get("error")), None
    )
    if rewrite_messy:
        lines.append(
            f"| **OpenLex (rewrite, messy, {max_queries}Q)** | "
            f"**{rewrite_messy['contradiction_rate_micro']:.1%}** | "
            f"**{rewrite_messy['supported_rate_micro']:.1%}** |"
        )

    lines.extend(["", "## Interpretation", ""])
    if rewrite_messy:
        cr = rewrite_messy["contradiction_rate_micro"]
        sr = rewrite_messy["supported_rate_micro"]
        if cr <= 0.05 and sr >= 0.75:
            lines.append(
                f"**Baseline stark.** Contradiction {cr:.1%} unter Westlaw AI (8 %). "
                f"Supported {sr:.1%}. NLnet-Claim: OpenLex zeigt sehr gute Faithfulness "
                f"auf deutschem Datenschutzrecht."
            )
        elif cr <= 0.11:
            lines.append(
                f"**Baseline konkurrenzfähig.** Contradiction {cr:.1%} "
                f"zwischen Westlaw (8 %) und Lexis+ (11 %)."
            )
        elif cr <= 0.20:
            lines.append(
                f"**Handlungsrelevant.** Contradiction {cr:.1%} über Lexis+. "
                f"Systemprompt-Verschärfung oder Grounding-Enforcement vor NLnet nötig."
            )
        else:
            lines.append(
                f"**Problematisch.** Contradiction {cr:.1%}. Debug vor NLnet."
            )

    lines.extend(["", "## Top Contradictions (Rewrite-Modus, Messy)", ""])
    for r in runs:
        if r.get("error") or r["mode"] != "rewrite" or r["eval_set"] != "messy":
            continue
        contradictions = []
        for res in r.get("results", []):
            if "error" in res:
                continue
            for v in res.get("verdicts", []):
                if v["label"] == "contradiction":
                    contradictions.append((
                        v["score"], res["query"], v["claim"],
                        v.get("evidence_excerpt", "")
                    ))
        contradictions.sort(reverse=True)
        for score, query, claim, excerpt in contradictions[:5]:
            lines.extend([
                f"**score={score:.3f}** | Query: _{query[:70]}_",
                f"- Claim: {claim}",
                f"- Evidence: {excerpt[:150]}",
                "",
            ])

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    max_queries = int(os.getenv("FAITHFULNESS_MAX_QUERIES", "30"))
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_json = RESULTS_DIR / f"faithfulness_{timestamp}.json"
    out_md = RESULTS_DIR / f"faithfulness_{timestamp}.md"

    eval_sets = {
        "canonical": load_eval_set("canonical"),
        "messy": load_eval_set("messy"),
    }

    modes = [
        ("no_rewrite", {}),
        ("rewrite", {"OPENLEX_REWRITE_ENABLED": "true"}),
    ]

    runs = []
    for mode_name, flags in modes:
        for set_name, eval_set in eval_sets.items():
            print(f"\n=== {mode_name} / {set_name} (N={max_queries}) ===")
            run = run_for_mode(mode_name, set_name, eval_set, flags, max_queries)
            runs.append(run)
            if not run.get("error"):
                print(f"  Supported={run['supported_rate_micro']:.1%} "
                      f"Contradiction={run['contradiction_rate_micro']:.1%} "
                      f"Ungrounded={run['ungrounded_rate_micro']:.1%} "
                      f"({run['n_valid']}/{run['n_queries']} valid, {run['duration_s']}s)")

    # JSON (ohne volle Antworten um Größe zu reduzieren)
    output = {
        "timestamp": timestamp,
        "max_queries": max_queries,
        "nli_model": "cross-encoder/nli-deberta-v3-large",
        "runs": [
            {k: v for k, v in r.items() if k != "results"}
            for r in runs
        ],
    }
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2, default=str)

    # Volle Ergebnisse in separate Datei
    full_path = RESULTS_DIR / f"faithfulness_full_{timestamp}.json"
    with open(full_path, "w") as f:
        json.dump({"timestamp": timestamp, "max_queries": max_queries, "runs": runs},
                  f, indent=2, default=str, ensure_ascii=False)

    write_markdown(out_md, timestamp, runs, max_queries)
    print(f"\nJSON: {out_json}")
    print(f"Full: {full_path}")
    print(f"MD:   {out_md}")
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
