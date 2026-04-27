#!/usr/bin/env python3
"""
Analysiert per_source_retrieval.jsonl:
- Avg Overhead
- Avg Overlap zwischen Single-Call und Per-Source
- Pro Source-Type: durchschnittliche Treffer
"""
import sys
from collections import Counter

sys.path.insert(0, "/opt/openlex-mvp")
from per_source_telemetry import read_recent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    recent = read_recent(n)

    if not recent:
        print("Keine Telemetrie-Daten.")
        return

    # Filter Errors
    valid = [r for r in recent if not r.get("error")]
    print(f"Total: {len(recent)} | Valid: {len(valid)} | Errors: {len(recent) - len(valid)}")

    if not valid:
        return

    # Performance
    avg_single = sum(r["single_call_duration_ms"] for r in valid) / len(valid)
    avg_per_source = sum(r["per_source_duration_ms"] for r in valid) / len(valid)
    avg_overhead = sum(r["overhead_ms"] for r in valid) / len(valid)

    print(f"\n=== Performance ===")
    print(f"Avg Single-Call: {avg_single:.0f}ms")
    print(f"Avg Per-Source:  {avg_per_source:.0f}ms")
    print(f"Avg Overhead:    {avg_overhead:.0f}ms")

    # Overlap
    overlap_counts = [r["n_overlap"] for r in valid]
    avg_overlap = sum(overlap_counts) / len(valid)
    overlap_dist = Counter(overlap_counts)

    print(f"\n=== Overlap Single-Call vs. Per-Source-Budget ===")
    print(f"Avg Overlap: {avg_overlap:.1f}/10")
    print(f"Verteilung:")
    for n_overlap in sorted(overlap_dist):
        bar = "#" * overlap_dist[n_overlap]
        print(f"  {n_overlap}/10: {overlap_dist[n_overlap]:3d}  {bar}")

    # Per Source-Type
    print(f"\n=== Treffer pro Source-Type (in Per-Source-Top-5) ===")
    type_chunk_counts = Counter()
    for r in valid:
        for st, ids in r.get("per_source_top_per_type", {}).items():
            type_chunk_counts[st] += len(ids)

    for st, count in type_chunk_counts.most_common():
        avg = count / len(valid)
        print(f"  {st}: avg {avg:.1f} chunks")

    # Queries mit niedrigem Overlap (potentiell am stärksten von Per-Source zu profitieren)
    low_overlap = sorted(valid, key=lambda r: r["n_overlap"])[:5]
    print(f"\n=== Top-5 Queries mit niedrigstem Overlap (Per-Source ≠ Single) ===")
    for r in low_overlap:
        print(f"  [{r['n_overlap']}/10] {r['query'][:70]}")


if __name__ == "__main__":
    main()
