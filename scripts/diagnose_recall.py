#!/usr/bin/env python3
"""
diagnose_recall.py – Candidate-Recall@K vor Cross-Encoder und Cutoff.

Misst: Sind die Gold-Chunks ÜBERHAUPT im Candidate-Pool (vor Reranking)?

Das ist die Vorstufe zur Hit@K-Messung: eval_v3 misst ob Gold-Chunks
nach Reranking in Top-3/5/10 landen — diagnose_recall misst ob sie
überhaupt im Pool der bis zu 150 Kandidaten auftauchen.

Nutzt app.retrieve_candidates_only() (added via Option A).

Verwendung:
  python scripts/diagnose_recall.py --eval-set eval_sets/canonical_v3.json
  python scripts/diagnose_recall.py --eval-set eval_sets/messy.json
  python scripts/diagnose_recall.py --eval-set eval_sets/canonical_v3.json --output /tmp/diagnose.json
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

K_VALUES = [20, 40, 80, 150]  # 40 = aktueller Cutoff in app.py


def load_env():
    env = BASE_DIR / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def get_gold_ids(entry: dict) -> list[str]:
    """Gibt must_contain_chunk_ids aus retrieval_gold zurück (oder gold_ids fallback)."""
    rg = entry.get("retrieval_gold", {})
    must = rg.get("must_contain_chunk_ids") or []
    if must:
        return must
    return entry.get("gold_ids", [])


def recall_at_k(candidate_ids: list[str], gold_ids: list[str], k: int) -> float:
    """Anteil der Gold-IDs, die in den Top-K Kandidaten vorkommen."""
    if not gold_ids:
        return 1.0  # Kein Gold definiert → trivial erfüllt, aus Statistik raus
    top_k = set(candidate_ids[:k])
    hits = sum(1 for g in gold_ids if g in top_k)
    return hits / len(gold_ids)


def main():
    parser = argparse.ArgumentParser(
        description="Candidate-Recall@K Diagnose (vor Cross-Encoder)",
        epilog="Beispiel: python scripts/diagnose_recall.py --eval-set eval_sets/messy.json"
    )
    parser.add_argument("--eval-set", required=True)
    parser.add_argument("--output", default=None, help="JSON-Output-Pfad (optional)")
    parser.add_argument("--k", type=int, nargs="+", default=K_VALUES)
    args = parser.parse_args()

    load_env()

    eval_path = Path(args.eval_set)
    if not eval_path.is_absolute():
        eval_path = BASE_DIR / eval_path
    if not eval_path.exists():
        sys.exit(f"FEHLER: {eval_path} nicht gefunden")

    with open(eval_path) as f:
        questions = json.load(f)

    print(f"\nCandidate-Recall Diagnose – {eval_path.name}")
    print(f"  {len(questions)} Queries, K={args.k}")
    print(f"  Nutzt app.retrieve_candidates_only() (vor Cross-Encoder, vor Cutoff)\n")

    # app.py laden
    import app as _app
    retrieve_fn = _app.retrieve_candidates_only

    results = []
    recall_by_k: dict[int, list[float]] = defaultdict(list)
    recall_by_cat: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    zero_recall_150: list[dict] = []

    max_k = max(args.k)
    t_start = time.time()

    for i, entry in enumerate(questions, 1):
        qid    = entry.get("id", f"q{i}")
        q_text = entry["question"]
        gold   = get_gold_ids(entry)
        cat    = entry.get("category", "unbekannt")

        print(f"  [{i:2d}/{len(questions)}] {qid}: {q_text[:60]}...", end="", flush=True)

        t0 = time.time()
        candidates = retrieve_fn(q_text, top_k=max_k)
        elapsed = time.time() - t0

        cand_ids = [
            c.get("id") or c.get("meta", {}).get("chunk_id", "") or c.get("text", "")[:50]
            for c in candidates
        ]

        row = {
            "id": qid,
            "category": cat,
            "gold_ids": gold,
            "n_candidates": len(cand_ids),
            "duration_s": round(elapsed, 2),
            "recall": {},
        }

        for k in args.k:
            r = recall_at_k(cand_ids, gold, k)
            row["recall"][f"recall@{k}"] = round(r, 3)
            if gold:  # Nur Queries mit Gold in Statistik
                recall_by_k[k].append(r)
                recall_by_cat[cat][k].append(r)

        results.append(row)

        # Recall@150 = 0 trotz Gold vorhanden
        if gold and row["recall"].get(f"recall@{max_k}", 0) == 0:
            zero_recall_150.append({"id": qid, "category": cat, "gold": gold})

        r40 = row["recall"].get("recall@40", 0)
        r150 = row["recall"].get(f"recall@{max_k}", 0)
        print(f"  Recall@40={r40:.2f}  Recall@{max_k}={r150:.2f}  ({elapsed:.1f}s)")

    duration = time.time() - t_start
    n_with_gold = len(recall_by_k.get(max_k, []))

    # ── Aggregation ──
    def avg(lst):
        return round(sum(lst) / len(lst), 3) if lst else 0.0

    agg_recall = {f"avg_recall@{k}": avg(recall_by_k[k]) for k in args.k}

    cat_recall_40 = {
        cat: avg(vals[40]) for cat, vals in recall_by_cat.items()
    }

    # ── Report ausgeben ──
    print(f"\n{'=' * 58}")
    print(f"  Candidate-Recall – {eval_path.name}")
    print(f"{'=' * 58}")
    print(f"  Queries gesamt: {len(questions)}  (mit Gold: {n_with_gold})")
    print(f"  Dauer: {duration:.1f}s\n")

    print(f"  {'Metrik':<14}", end="")
    for k in args.k:
        flag = " ← aktueller Cutoff" if k == 40 else ""
        print(f"  Recall@{k}{flag}", end="")
    print()
    print(f"  {'':14}", end="")
    for k in args.k:
        v = agg_recall[f"avg_recall@{k}"]
        bar = "█" * int(v * 20) + "░" * (20 - int(v * 20))
        print(f"  {bar} {v:.3f}", end="")
    print()

    print(f"\n  Recall@40 nach Kategorie (schlechteste zuerst):")
    for cat, val in sorted(cat_recall_40.items(), key=lambda x: x[1]):
        bar = "█" * int(val * 20) + "░" * (20 - int(val * 20))
        print(f"    {cat:<28s} {bar} {val:.3f}")

    print(f"\n  Queries mit Recall@{max_k}=0 (Gold nie im Pool): {len(zero_recall_150)}")
    for z in zero_recall_150:
        print(f"    [{z['category']}] {z['id']}: gold={z['gold']}")

    # Interpretation
    r40 = agg_recall.get("avg_recall@40", 0)
    r150 = agg_recall.get(f"avg_recall@{max_k}", 0)
    print(f"\n  Interpretation:")
    if r40 < 0.5:
        print(f"    ⚠ Recall@40={r40:.3f} < 0.5 → Hypothese bestätigt:")
        print(f"      Candidate-Set ist Nadelöhr. Query Understanding / BM25 ist der richtige Hebel.")
    elif r40 >= 0.5 and r40 < 0.75:
        print(f"    ~ Recall@40={r40:.3f}: Moderates Problem. Top-K-Erhöhung bringt Quick-Win.")
    else:
        print(f"    ✓ Recall@40={r40:.3f}: Candidate-Set OK. Reranking ist Nadelöhr.")

    if r150 - r40 > 0.1:
        print(f"    → Recall@{max_k}={r150:.3f}: +{r150-r40:.3f} bei Top-{max_k}.")
        print(f"      Quick-Win durch höheres Top-K möglich (ohne Architekturänderung).")
    print(f"{'=' * 58}")

    # JSON speichern
    output = {
        "eval_set": eval_path.name,
        "n_questions": len(questions),
        "n_with_gold": n_with_gold,
        "k_values": args.k,
        "aggregate": agg_recall,
        "by_category_recall40": cat_recall_40,
        "zero_recall_at_max_k": zero_recall_150,
        "results": results,
        "duration_s": round(duration, 1),
    }

    out_path = args.output
    if not out_path:
        stem = eval_path.stem
        out_path = str(BASE_DIR / "eval_results_v3" / f"diagnose_recall_{stem}.json")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  JSON: {out_path}")


if __name__ == "__main__":
    main()
