#!/usr/bin/env python3
"""
telemetry_report.py – Aggregation über JSONL-Telemetrie.
Usage: python scripts/telemetry_report.py [--days 7] [--log-path PATH]
"""
import sys
import json
import time
import argparse
from pathlib import Path
from collections import Counter

sys.path.insert(0, "/opt/openlex-mvp")

DEFAULT_LOG = "/opt/openlex-mvp/logs/telemetry.jsonl"


def load_events(log_path: str, since_ts: float) -> list[dict]:
    p = Path(log_path)
    if not p.exists():
        print(f"Log-Datei nicht gefunden: {log_path}")
        return []
    events = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                if ev.get("ts", 0) >= since_ts:
                    events.append(ev)
            except json.JSONDecodeError:
                continue
    return events


def main():
    parser = argparse.ArgumentParser(description="OpenLex Telemetrie-Report")
    parser.add_argument("--days", type=int, default=7, help="Zeitraum in Tagen (default: 7)")
    parser.add_argument("--log-path", default=DEFAULT_LOG, help="Pfad zur JSONL-Datei")
    args = parser.parse_args()

    since_ts = time.time() - args.days * 86400
    events = load_events(args.log_path, since_ts)

    if not events:
        print(f"Keine Events in den letzten {args.days} Tagen.")
        return 0

    print(f"\n{'='*60}")
    print(f"  OpenLex Telemetrie-Report — letzte {args.days} Tage")
    print(f"{'='*60}")
    print(f"  Events: {len(events)}")

    # Unique Queries (dedupliziert nach hash)
    unique_hashes = {ev["query_hash"] for ev in events}
    print(f"  Unique Queries: {len(unique_hashes)}")

    # Fehlerquote
    errors = [ev for ev in events if ev.get("error")]
    print(f"  Fehlerquote: {len(errors)}/{len(events)} ({len(errors)/len(events)*100:.1f}%)")

    # Durchschnittliche Dauer
    durations = [ev["duration_ms"] for ev in events if ev.get("duration_ms", 0) > 0]
    if durations:
        print(f"  Ø Dauer: {sum(durations)/len(durations):.0f} ms  "
              f"(p95: {sorted(durations)[int(len(durations)*0.95)]:.0f} ms)")

    # Intent-Verteilung
    intent_events = [ev for ev in events if ev.get("intent")]
    if intent_events:
        print(f"\n  --- Intent-Verteilung ({len(intent_events)} Events) ---")
        intent_types = Counter(ev["intent"].get("type", "?") for ev in intent_events)
        for itype, cnt in intent_types.most_common():
            pct = cnt / len(intent_events) * 100
            print(f"    {itype:25s}: {cnt:4d} ({pct:5.1f}%)")

        clarif = sum(1 for ev in intent_events if ev["intent"].get("clarification"))
        print(f"  Clarification-Rate: {clarif}/{len(intent_events)} ({clarif/len(intent_events)*100:.1f}%)")

        from_cache = sum(1 for ev in intent_events if ev["intent"].get("from_cache"))
        print(f"  Intent-Cache-Rate: {from_cache}/{len(intent_events)} ({from_cache/len(intent_events)*100:.1f}%)")

    # Retrieval-Stats
    ret_events = [ev for ev in events if ev.get("retrieval")]
    if ret_events:
        print(f"\n  --- Retrieval ({len(ret_events)} Events) ---")
        chunks_list = [ev["retrieval"].get("chunks_returned", 0) for ev in ret_events]
        scores = [ev["retrieval"].get("top_score", 0) for ev in ret_events if ev["retrieval"].get("top_score")]
        if chunks_list:
            print(f"  Ø Chunks returned: {sum(chunks_list)/len(chunks_list):.1f}")
        if scores:
            print(f"  Ø Top-Score: {sum(scores)/len(scores):.3f}")

        # Source-Type-Verteilung über alle Retrieval-Events
        all_sts = []
        for ev in ret_events:
            all_sts.extend(ev["retrieval"].get("source_types", []))
        if all_sts:
            st_dist = Counter(all_sts)
            print(f"  Source-Types in Retrieval:")
            for st, cnt in st_dist.most_common(8):
                print(f"    {st:30s}: {cnt}")

    # Validator-Stats
    val_events = [ev for ev in events if ev.get("validator")]
    if val_events:
        print(f"\n  --- Norm-Validator ({len(val_events)} Events) ---")
        unknown = sum(ev["validator"].get("unknown_norms", 0) for ev in val_events)
        ungrounded = sum(ev["validator"].get("ungrounded_norms", 0) for ev in val_events)
        warned = sum(1 for ev in val_events if ev["validator"].get("warning_shown"))
        print(f"  Unbekannte Normen total: {unknown}")
        print(f"  Unverankerte Normen total: {ungrounded}")
        print(f"  Warnings angezeigt: {warned} ({warned/len(val_events)*100:.1f}%)")

    # Rewrite-Stats
    rew_events = [ev for ev in events if ev.get("rewrite")]
    if rew_events:
        print(f"\n  --- Query-Rewriter ({len(rew_events)} Events) ---")
        used = sum(1 for ev in rew_events if ev["rewrite"].get("used"))
        print(f"  Rewrite aktiv: {used}/{len(rew_events)} ({used/len(rew_events)*100:.1f}%)")

    print(f"\n{'='*60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
