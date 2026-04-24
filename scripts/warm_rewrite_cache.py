#!/usr/bin/env python3
"""Wärmt den Rewrite-Cache für alle Eval-Queries auf (mit Retry bei 429)."""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, "/opt/openlex-mvp")
from query_rewriter import rewrite, cache_stats, _call_mistral, _cache_put, _is_valid_rewrite, _MODEL

EVAL_SETS_DIR = Path("/opt/openlex-mvp/eval_sets")
CALL_DELAY_S = 1.0   # Pause zwischen LLM-Calls
MAX_RETRIES = 3


def load_eval_set(name: str) -> list:
    for suffix in ("", "_v3"):
        path = EVAL_SETS_DIR / f"{name}{suffix}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
    raise FileNotFoundError(name)


def get_query(entry: dict) -> str:
    return entry.get("query") or entry.get("question", "")


def rewrite_with_retry(q: str) -> tuple:
    """Gibt (rewritten, status, duration_ms) zurück. Status: 'CACHE'|'LLM'|'ERR'."""
    from query_rewriter import _cache_get
    start = time.time()

    cached = _cache_get(q, _MODEL)
    if cached is not None:
        return cached, "CACHE", (time.time() - start) * 1000

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = _call_mistral(q)
            if _is_valid_rewrite(q, raw):
                _cache_put(q, raw, _MODEL)
                return raw, "LLM", (time.time() - start) * 1000
            else:
                return q, "INVALID", (time.time() - start) * 1000
        except Exception as e:
            msg = str(e)
            if "429" in msg or "rate" in msg.lower():
                wait = 2 ** attempt  # Backoff: 2s, 4s, 8s
                print(f"      Rate-limited, waiting {wait}s (attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(wait)
            else:
                return q, f"ERR({msg[:40]})", (time.time() - start) * 1000

    return q, "ERR(max_retries)", (time.time() - start) * 1000


def main():
    queries = []
    seen = set()
    for set_name in ("canonical", "messy"):
        eval_set = load_eval_set(set_name)
        for entry in eval_set:
            q = get_query(entry)
            if q and q not in seen:
                queries.append((set_name, q))
                seen.add(q)

    print(f"Warming cache for {len(queries)} unique queries...")
    t0 = time.time()
    errors = 0
    llm_calls = 0
    cache_hits_start = cache_stats()["total_entries"]

    for i, (set_name, q) in enumerate(queries, start=1):
        rewritten, status, dur_ms = rewrite_with_retry(q)
        if status == "ERR" or status.startswith("ERR("):
            errors += 1
        elif status == "LLM":
            llm_calls += 1
            time.sleep(CALL_DELAY_S)  # Rate-Limit-Schutz nach LLM-Call
        print(f"[{i:3d}/{len(queries)}] {set_name:10s} {status:14s} "
              f"{dur_ms:5.0f}ms | {q[:60]}")

    duration = time.time() - t0
    cache_hits_end = cache_stats()["total_entries"]
    new_entries = cache_hits_end - cache_hits_start

    print()
    print(f"Done. Unique queries: {len(queries)}")
    print(f"New cache entries: {new_entries}")
    print(f"LLM calls made: {llm_calls}")
    print(f"Errors: {errors}")
    print(f"Total duration: {duration:.1f}s")
    return 1 if errors > len(queries) * 0.1 else 0


if __name__ == "__main__":
    sys.exit(main())
