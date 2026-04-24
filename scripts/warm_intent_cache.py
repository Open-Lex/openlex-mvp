#!/usr/bin/env python3
"""Wärmt den Intent-Cache für alle Eval-Queries."""
import sys
import json
import time
from pathlib import Path
from collections import Counter

sys.path.insert(0, "/opt/openlex-mvp")
from intent_analyzer import analyze, cache_stats

EVAL_SETS_DIR = Path("/opt/openlex-mvp/eval_sets")


def load_set(name: str) -> list:
    for suf in ("", "_v3"):
        p = EVAL_SETS_DIR / f"{name}{suf}.json"
        if p.exists():
            with open(p) as f:
                return json.load(f)
    raise FileNotFoundError(name)


def main():
    queries = []
    for name in ("canonical", "messy"):
        for entry in load_set(name):
            q = entry.get("query") or entry.get("question", "")
            if q:
                queries.append((name, q))

    print(f"Warming intent cache for {len(queries)} queries...")
    t0 = time.time()
    errors = 0
    intent_dist = Counter()
    compl_buckets = Counter()
    clarifications = []

    for i, (set_name, q) in enumerate(queries, 1):
        r = analyze(q)
        # 0.8s pause between fresh LLM calls to respect rate limit (~1 req/s)
        if not r.from_cache and not r.error:
            time.sleep(0.8)
        if r.error:
            errors += 1

        intent_dist[r.intent_type] += 1
        bucket = "low" if r.completeness_score < 0.5 else (
            "mid" if r.completeness_score < 0.8 else "high"
        )
        compl_buckets[bucket] += 1

        if r.clarification_question:
            clarifications.append((q, r.clarification_question, r.completeness_score))

        cache_tag = "CACHE" if r.from_cache else r.intent_type
        if i % 10 == 0 or i <= 5:
            print(f"[{i:3d}/{len(queries)}] {set_name:10s} {cache_tag:20s} "
                  f"compl={r.completeness_score:.2f} | {q[:55]}")

    print()
    print(f"=== Summary ===")
    print(f"Total: {len(queries)}, Errors: {errors}")
    print(f"Intent distribution: {dict(intent_dist)}")
    print(f"Completeness buckets: {dict(compl_buckets)}")
    clar_rate = len(clarifications) / len(queries) * 100
    print(f"Clarifications triggered: {len(clarifications)} ({clar_rate:.1f}%)")
    print(f"Duration: {time.time()-t0:.1f}s")
    print(f"Final cache: {cache_stats()}")

    if clarifications:
        print()
        print("=== Clarifications (first 10) ===")
        for q, cq, score in clarifications[:10]:
            print(f"  Q [{score:.2f}]: {q}")
            print(f"     -> {cq}")

    error_rate = errors / len(queries) if queries else 0
    if error_rate > 0.10:
        print(f"\nWARNUNG: Error-Rate {error_rate:.0%} > 10% — LLM-Probleme prüfen")
        return 1
    if clar_rate > 30:
        print(f"\nWARNUNG: Clarification-Rate {clar_rate:.0f}% > 30% — Prompt zu streng")
    elif clar_rate < 3:
        print(f"\nHINWEIS: Clarification-Rate {clar_rate:.0f}% sehr niedrig")
    else:
        print(f"\nClarification-Rate {clar_rate:.1f}% — plausibel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
