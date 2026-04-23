#!/usr/bin/env python3
"""compare_runs.py – Top-3 Change Rate zwischen zwei Eval-Runs.

Verwendung:
  python compare_runs.py <before.json> <after.json>
"""
import sys
import json

def top3_ids(result: dict) -> list[str]:
    return result.get("retrieved_raw_ids_top10", result.get("retrieved_ids_top10", []))[:3]

def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python compare_runs.py <before.json> <after.json>")

    before_path, after_path = sys.argv[1], sys.argv[2]
    with open(before_path) as f: before = json.load(f)
    with open(after_path)  as f: after  = json.load(f)

    before_by_id = {r["id"]: r for r in before["results"]}
    after_by_id  = {r["id"]: r for r in after["results"]}

    common_ids = sorted(set(before_by_id) & set(after_by_id))
    n = len(common_ids)
    if n == 0:
        sys.exit("Keine gemeinsamen Query-IDs gefunden.")

    identical_order = 0   # gleiche IDs, gleiche Reihenfolge
    same_set        = 0   # gleiche IDs, Reihenfolge egal
    any_change      = 0   # mind. eine andere ID

    changed_examples = []

    for qid in common_ids:
        b3 = top3_ids(before_by_id[qid])
        a3 = top3_ids(after_by_id[qid])

        if b3 == a3:
            identical_order += 1
            same_set        += 1
        elif set(b3) == set(a3):
            same_set += 1
            any_change += 1
        else:
            any_change += 1

        if b3 != a3 and len(changed_examples) < 5:
            changed_examples.append((qid, b3, a3))

    print("=" * 60)
    print("  Top-3 Change Rate")
    print("=" * 60)
    print(f"  Gemeinsame Queries: {n}")
    print()
    print(f"  {'Identisch (Menge + Reihenfolge):':<35} {identical_order:3d} ({identical_order/n*100:.0f}%)")
    print(f"  {'Gleiche Menge, andere Reihenfolge:':<35} {same_set - identical_order:3d} ({(same_set-identical_order)/n*100:.0f}%)")
    print(f"  {'Mind. eine neue ID:':<35} {any_change - (same_set - identical_order) - 0:3d}*")
    print()
    # Corrected: any_change counts all non-identical-order
    truly_different = any_change  # already excludes identical_order
    print(f"  top3_identical_rate:  {identical_order/n:.3f}  ({identical_order/n*100:.0f}%)")
    print(f"  top3_same_set_rate:   {same_set/n:.3f}  ({same_set/n*100:.0f}%)")
    print(f"  top3_any_change_rate: {any_change/n:.3f}  ({any_change/n*100:.0f}%)")

    if changed_examples:
        print("\n  Beispiele geänderter Top-3:")
        for qid, b3, a3 in changed_examples:
            print(f"  [{qid}]")
            print(f"    Before: {b3}")
            print(f"    After:  {a3}")

    print("=" * 60)


if __name__ == "__main__":
    main()
