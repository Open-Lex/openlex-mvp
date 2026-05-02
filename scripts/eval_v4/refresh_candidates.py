#!/usr/bin/env python3
"""
Refresh der queries_with_candidates.json nach Hebel 1+2.
top_k=25, aktuelle Pipeline (Per-Source-Budget aktiv).

Angepasst an tatsaechliche API:
- retrieve() akzeptiert kein top_k -> retrieve_candidates_only(top_k=25)
- meta hat: chunk_id, gesetz, volladresse, source_type (kein aktenzeichen/gericht)
"""
import json, sys, time, os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/opt/openlex-mvp")
os.environ["OPENLEX_PER_SOURCE_RETRIEVAL_ENABLED"] = "true"
os.environ["OPENLEX_PER_SOURCE_BUDGET_ACTIVE"] = "true"
os.environ["OPENLEX_INTENT_ANALYSIS_ENABLED"] = "false"
os.environ["OPENLEX_TRACE_MODE"] = "false"

INPUT  = Path("/opt/openlex-mvp/eval_sets/v4/queries_with_candidates.json")
REPORT = Path("/opt/openlex-mvp/eval_sets/v4/refresh_diff_report.md")
TOP_K  = 25

def main():
    with open(INPUT) as f:
        data = json.load(f)
    queries = data if isinstance(data, list) else list(data.values())
    print(f"Loaded {len(queries)} queries from {INPUT}")

    import importlib, app
    importlib.reload(app)
    from app import retrieve_candidates_only
    print(f"Pipeline loaded. MAX_DOCS={app.MAX_DOCS}")

    diffs, errors = [], []
    t_start = time.time()

    for i, q in enumerate(queries, 1):
        query_text = q.get("query") or q.get("question") or q.get("text", "")
        if not query_text or str(query_text).startswith("[TO BE"):
            # Skip placeholder entries — not counted as errors
            continue

        # Detect candidates field name
        cands_field = "retrieval_candidates" if "retrieval_candidates" in q else "candidates"
        old_cands = q.get(cands_field, [])
        old_ids = [c.get("chunk_id") or c.get("id","") for c in old_cands if isinstance(c, dict)]
        old_ids = [x for x in old_ids if x]

        try:
            results = retrieve_candidates_only(query_text, top_k=TOP_K)
            if isinstance(results, dict):
                errors.append({"idx": i, "query": query_text[:60], "error": "clarification"})
                continue

            new_cands = []
            new_ids = []
            for r in results[:TOP_K]:
                meta = r.get("meta") or r.get("metadata") or {}
                cid = r.get("id") or meta.get("chunk_id") or ""
                if not cid:
                    continue
                new_cands.append({
                    "chunk_id":    cid,
                    "score":       round(r.get("ce_score") or r.get("score") or r.get("adjusted_distance") or 0.0, 4),
                    "source_type": meta.get("source_type", ""),
                    "gesetz":      meta.get("gesetz") or meta.get("volladresse") or "",
                    "snippet":     (r.get("text") or r.get("document") or "")[:300],
                    "volladresse": meta.get("volladresse") or "",
                })
                new_ids.append(cid)

            q[cands_field] = new_cands

            overlap  = set(old_ids) & set(new_ids)
            new_only = set(new_ids) - set(old_ids)
            removed  = set(old_ids) - set(new_ids)

            diffs.append({
                "idx": i, "query": query_text[:80],
                "old_n": len(old_ids), "new_n": len(new_ids),
                "overlap": len(overlap), "new_only": len(new_only), "removed": len(removed),
                "new_only_ids": list(new_only)[:5], "removed_ids": list(removed)[:5],
            })

            if i % 10 == 0 or i <= 3:
                elapsed = time.time() - t_start
                eta = (len(queries) - i) / (i / elapsed) if i > 0 else 0
                print(f"  [{i}/{len(queries)}] elapsed={elapsed:.0f}s ETA={eta:.0f}s overlap={len(overlap)}/{len(new_ids)}")

        except Exception as e:
            errors.append({"idx": i, "query": query_text[:60], "error": str(e)})
            print(f"  [{i}] ERROR: {e}")

    elapsed_total = time.time() - t_start
    attempted = len(diffs) + len(errors)
    error_rate = len(errors) / attempted if attempted > 0 else 0.0
    print(f"\nDone in {elapsed_total:.0f}s ({elapsed_total/60:.1f} min)")
    print(f"Success: {len(diffs)}/{attempted} attempted queries, Errors: {len(errors)} ({error_rate:.1%})")

    if error_rate > 0.2:
        print("ERROR RATE > 20% -- aborting write, check errors above")
        for e in errors[:10]:
            print(f"  #{e['idx']}: {e.get('query','?')[:50]} -- {e['error']}")
        sys.exit(1)

    with open(INPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Written: {INPUT}")

    # Diff report
    avg_ov  = sum(d["overlap"]  for d in diffs) / len(diffs) if diffs else 0
    avg_new = sum(d["new_only"] for d in diffs) / len(diffs) if diffs else 0
    avg_rem = sum(d["removed"]  for d in diffs) / len(diffs) if diffs else 0
    by_change = sorted(diffs, key=lambda d: d["overlap"])[:10]

    lines = [
        "# Kandidaten-Refresh Diff-Report",
        "",
        f"Datum: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Queries: {len(diffs)} OK, {len(errors)} Errors, top_k={TOP_K}",
        "",
        "## Aggregat",
        "",
        "| Metrik | Wert |",
        "|--------|------|",
        f"| Avg Overlap (alt & neu) | {avg_ov:.1f}/{TOP_K} |",
        f"| Avg neue Chunks (nur in neu) | {avg_new:.1f} |",
        f"| Avg verlorene Chunks (nur in alt) | {avg_rem:.1f} |",
        "",
        "## Top 10 Queries mit groesstem Wechsel",
        "",
    ]
    for d in by_change:
        lines += [
            f"### {d['idx']}. {d['query']}",
            f"- Overlap: {d['overlap']}/{d['new_n']}",
            f"- Neu: {d['new_only']} Chunks -- {', '.join(d['new_only_ids'][:3])}",
            f"- Verloren: {d['removed']} Chunks -- {', '.join(d['removed_ids'][:3])}",
            "",
        ]
    if errors:
        lines += ["## Errors", ""]
        for e in errors[:20]:
            lines.append(f"- #{e['idx']}: {e.get('query','?')[:60]} -- {e['error']}")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Diff report: {REPORT}")

if __name__ == "__main__":
    main()
