#!/usr/bin/env python3
"""
OpenLex Eval v4 — stratifizierte Metriken mit sauberem Gold-Matching.

Unterschiede zu v3:
- Nutzt must_contain_chunk_ids DIREKT (kein Normalization auf Thema)
- forbidden_contain_chunk_ids als Strafmetrik
- Stratifizierung nach rechtsgebiet × anfrage_typ
- Adversarial- und Deep-Eval-Subsets als separate Reports
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, "/opt/openlex-mvp")

EVAL_PATH = Path("/opt/openlex-mvp/eval_sets/v4/queries.json")
RESULTS_DIR = Path("/opt/openlex-mvp/experiment_results")
RESULTS_DIR.mkdir(exist_ok=True)


def load_eval():
    if not EVAL_PATH.exists():
        raise FileNotFoundError(
            f"Eval-Set fehlt: {EVAL_PATH}\n"
            "Erst annotation_tool.py starten und Gold-Annotation durchführen."
        )
    with open(EVAL_PATH) as f:
        return json.load(f)


# ─── Metriken ────────────────────────────────────────────────────────────────

def hit_at_k(must_ids: list, retrieved_ids: list, k: int) -> bool:
    return any(mid in retrieved_ids[:k] for mid in must_ids)


def full_hit_at_k(must_ids: list, retrieved_ids: list, k: int) -> bool:
    if not must_ids:
        return False
    return all(mid in retrieved_ids[:k] for mid in must_ids)


def recall_at_k(must_ids: list, retrieved_ids: list, k: int) -> float:
    if not must_ids:
        return 0.0
    return sum(1 for mid in must_ids if mid in retrieved_ids[:k]) / len(must_ids)


def reciprocal_rank(must_ids: list, retrieved_ids: list) -> float:
    for rank, rid in enumerate(retrieved_ids, 1):
        if rid in must_ids:
            return 1.0 / rank
    return 0.0


def forbidden_hit(forbidden_ids: list, retrieved_ids: list, k: int) -> bool:
    if not forbidden_ids:
        return False
    return any(fid in retrieved_ids[:k] for fid in forbidden_ids)


# ─── Retrieval ────────────────────────────────────────────────────────────────

def load_retrieve_fn():
    os.environ["OPENLEX_TRACE_MODE"] = "false"
    os.environ["OPENLEX_INTENT_ANALYSIS_ENABLED"] = "false"
    import importlib
    import app
    importlib.reload(app)
    return app.retrieve


def run_eval(queries: list, adversarial_only=False, deep_only=False, quick=False):
    retrieve = load_retrieve_fn()

    filtered = queries
    if adversarial_only:
        filtered = [q for q in filtered if q.get("is_adversarial")]
    if deep_only:
        filtered = [q for q in filtered if q.get("is_deep_eval")]
    # Nur Queries mit Annotationen
    filtered = [q for q in filtered if q.get("must_contain_chunk_ids")]
    if quick:
        filtered = filtered[:20]

    print(f"Evaluating {len(filtered)} Queries...")

    results = []
    for i, q in enumerate(filtered, 1):
        start = time.time()
        try:
            r = retrieve(q["query"])
            if isinstance(r, dict):
                results.append({**q, "retrieved_ids": [], "error": "clarification"})
                continue

            # Chunk-IDs aus Retrieval-Ergebnis extrahieren
            retrieved_ids = []
            for chunk in (r or []):
                cid = (chunk.get("meta") or {}).get("chunk_id") or chunk.get("id") or ""
                if cid:
                    retrieved_ids.append(cid)

        except Exception as e:
            results.append({**q, "retrieved_ids": [], "error": str(e)[:200]})
            continue

        duration_ms = (time.time() - start) * 1000
        must = q.get("must_contain_chunk_ids", [])
        forb = q.get("forbidden_contain_chunk_ids", [])

        metrics = {
            "hit_at_3": hit_at_k(must, retrieved_ids, 3),
            "hit_at_5": hit_at_k(must, retrieved_ids, 5),
            "hit_at_10": hit_at_k(must, retrieved_ids, 10),
            "full_hit_at_3": full_hit_at_k(must, retrieved_ids, 3),
            "full_hit_at_10": full_hit_at_k(must, retrieved_ids, 10),
            "recall_at_10": recall_at_k(must, retrieved_ids, 10),
            "mrr": reciprocal_rank(must, retrieved_ids),
            "forbidden_hit_at_10": forbidden_hit(forb, retrieved_ids, 10),
        }

        results.append({**q, "retrieved_ids": retrieved_ids,
                        "duration_ms": round(duration_ms, 1),
                        "metrics": metrics})

        if i % 10 == 0:
            running_h3 = sum(r.get("metrics", {}).get("hit_at_3", 0)
                             for r in results if r.get("metrics")) / max(1, len(results))
            print(f"  [{i:3d}/{len(filtered)}] Running Hit@3={running_h3:.3f}")

    return results


# ─── Aggregation ──────────────────────────────────────────────────────────────

def mean(items, key):
    vals = [x["metrics"][key] for x in items if x.get("metrics")]
    return sum(vals) / len(vals) if vals else 0.0


def aggregate(results: list) -> dict:
    valid = [r for r in results if r.get("metrics")]
    if not valid:
        return {}

    overall = {
        "n": len(valid),
        **{k: mean(valid, k) for k in [
            "hit_at_3", "hit_at_5", "hit_at_10",
            "full_hit_at_3", "full_hit_at_10",
            "recall_at_10", "mrr", "forbidden_hit_at_10",
        ]},
    }

    by_rg = defaultdict(list)
    for r in valid:
        for rg in r.get("tags", {}).get("rechtsgebiete", []):
            by_rg[rg].append(r)

    by_at = defaultdict(list)
    for r in valid:
        for at in r.get("tags", {}).get("anfrage_typen", []):
            by_at[at].append(r)

    return {
        "overall": overall,
        "by_rechtsgebiet": {
            rg: {"n": len(items), "hit_at_3": mean(items, "hit_at_3"),
                 "mrr": mean(items, "mrr")}
            for rg, items in by_rg.items()
        },
        "by_anfrage_typ": {
            at: {"n": len(items), "hit_at_3": mean(items, "hit_at_3"),
                 "mrr": mean(items, "mrr")}
            for at, items in by_at.items()
        },
    }


# ─── Report ───────────────────────────────────────────────────────────────────

def write_markdown(agg: dict, out_path: Path, label: str = ""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# eval_v4 Report{' — ' + label if label else ''} — {ts}", ""]

    o = agg.get("overall", {})
    if o:
        lines += [
            "## Overall", "",
            "| Metrik | Wert |", "|---|---|",
        ]
        for k, v in o.items():
            if isinstance(v, float):
                lines.append(f"| {k} | {v:.3f} |")
            else:
                lines.append(f"| {k} | {v} |")

    rg = agg.get("by_rechtsgebiet", {})
    if rg:
        lines += ["", "## Pro Rechtsgebiet", "",
                  "| Rechtsgebiet | n | Hit@3 | MRR |", "|---|---|---|---|"]
        for k, m in sorted(rg.items()):
            lines.append(f"| {k} | {m['n']} | {m['hit_at_3']:.3f} | {m['mrr']:.3f} |")

    at = agg.get("by_anfrage_typ", {})
    if at:
        lines += ["", "## Pro Anfrage-Typ", "",
                  "| Anfrage-Typ | n | Hit@3 | MRR |", "|---|---|---|---|"]
        for k, m in sorted(at.items()):
            lines.append(f"| {k} | {m['n']} | {m['hit_at_3']:.3f} | {m['mrr']:.3f} |")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report: {out_path}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="OpenLex Eval v4")
    ap.add_argument("--quick", action="store_true", help="Nur 20 Queries")
    ap.add_argument("--adversarial", action="store_true", help="Nur adversarial")
    ap.add_argument("--deep-eval", action="store_true", help="Nur deep-eval")
    args = ap.parse_args()

    queries = load_eval()
    results = run_eval(queries,
                       adversarial_only=args.adversarial,
                       deep_only=args.deep_eval,
                       quick=args.quick)
    agg = aggregate(results)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    parts = ["quick"] * args.quick + ["adv"] * args.adversarial + ["deep"] * args.deep_eval
    sfx = "_".join(parts) if parts else "full"

    json_out = RESULTS_DIR / f"eval_v4_{sfx}_{ts}.json"
    md_out   = RESULTS_DIR / f"eval_v4_{sfx}_{ts}.md"

    with open(json_out, "w") as f:
        json.dump({"aggregate": agg, "results": results},
                  f, indent=2, ensure_ascii=False, default=str)

    write_markdown(agg, md_out, label=sfx)

    o = agg.get("overall", {})
    if o:
        print(f"\n=== eval_v4 [{sfx}] ===")
        print(f"n:                  {o['n']}")
        print(f"Hit@3:              {o['hit_at_3']:.3f}")
        print(f"Hit@5:              {o['hit_at_5']:.3f}")
        print(f"Hit@10:             {o['hit_at_10']:.3f}")
        print(f"Full-Hit@3:         {o['full_hit_at_3']:.3f}")
        print(f"Full-Hit@10:        {o['full_hit_at_10']:.3f}")
        print(f"Recall@10:          {o['recall_at_10']:.3f}")
        print(f"MRR:                {o['mrr']:.3f}")
        print(f"Forbidden-Hit@10:   {o['forbidden_hit_at_10']:.3f}")
    else:
        print("Keine Ergebnisse — noch keine Annotation vorhanden.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
