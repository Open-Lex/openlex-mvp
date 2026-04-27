#!/usr/bin/env python3
"""
A/B: Single-Call (Mode 2, Shadow) vs. Per-Source-Aktiv (Mode 3, Budget aktiv).
Misst Chunk-Differenzen und Source-Type-Verteilung.
"""
import sys, os, json, importlib, time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/opt/openlex-mvp")

TEST_QUERIES = [
    "Sind Cookies ohne Einwilligung erlaubt?",
    "Was ist eine Auftragsverarbeitung?",
    "Welche Rechte habe ich nach DSGVO?",
    "Wann ist eine DSFA verpflichtend?",
    "Datenschutz im Verein",
    "Wie lange darf eine Bewerbung gespeichert werden?",
    "Was hat der EuGH zu Schrems II entschieden?",
    "Welche rechtlichen Anforderungen gelten für biometrische Daten?",
    "Darf mein Arbeitgeber meine E-Mails lesen?",
    "Wann muss ich eine Datenpanne melden?",
    "Was ist Pseudonymisierung?",
    "Kann ich Schadensersatz nach SCHUFA-Urteil verlangen?",
    "Welche Rechtsgrundlage gilt für Werbung per E-Mail?",
    "Muss eine Datenschutzbeauftragter bestellt werden?",
    "Was sind besondere Kategorien personenbezogener Daten?",
    "Welche Pflichten hat ein Auftragsverarbeiter?",
    "Was bedeutet Accountability im Datenschutz?",
    "Welche Fristen gelten bei Betroffenenanfragen?",
    "Ist ein Cookie-Banner nach DSGVO Pflicht?",
    "Wie lange darf man IP-Adressen speichern?",
]


def get_results(queries, mode_env):
    """Holt retrieve()-Ergebnisse für alle Queries in einem Modus."""
    for k, v in mode_env.items():
        os.environ[k] = v
    import app
    importlib.reload(app)

    results = {}
    for q in queries:
        t = time.time()
        try:
            r = app.retrieve(q)
            if isinstance(r, dict):
                results[q] = {"chunks": [], "ms": 0, "error": "clarification"}
                continue
            results[q] = {
                "chunks": [{"id": c.get("id", "?"), "source_type": c.get("meta", {}).get("source_type", "?")} for c in r[:10]],
                "ms": (time.time() - t) * 1000,
                "error": None,
            }
        except Exception as e:
            results[q] = {"chunks": [], "ms": 0, "error": str(e)}
    return results


def main():
    print("Lauf 1: Single-Call (Shadow-Mode)...")
    base = get_results(TEST_QUERIES, {
        "OPENLEX_PER_SOURCE_RETRIEVAL_ENABLED": "true",
        "OPENLEX_PER_SOURCE_BUDGET_ACTIVE": "false",
    })

    print("Lauf 2: Per-Source aktiv (Budget)...")
    active = get_results(TEST_QUERIES, {
        "OPENLEX_PER_SOURCE_RETRIEVAL_ENABLED": "true",
        "OPENLEX_PER_SOURCE_BUDGET_ACTIVE": "true",
    })

    # Analyse
    comparisons = []
    for q in TEST_QUERIES:
        b = base.get(q, {})
        a = active.get(q, {})
        b_ids = set(c["id"] for c in b.get("chunks", []))
        a_ids = set(c["id"] for c in a.get("chunks", []))
        added = a_ids - b_ids
        removed = b_ids - a_ids
        b_st = {}
        for c in b.get("chunks", []):
            st = c["source_type"]; b_st[st] = b_st.get(st, 0) + 1
        a_st = {}
        for c in a.get("chunks", []):
            st = c["source_type"]; a_st[st] = a_st.get(st, 0) + 1
        comparisons.append({
            "query": q,
            "baseline_ids": list(b_ids),
            "active_ids": list(a_ids),
            "added": list(added),
            "removed": list(removed),
            "n_overlap": len(b_ids & a_ids),
            "n_changed": len(added),
            "baseline_source_mix": b_st,
            "active_source_mix": a_st,
            "baseline_ms": round(b.get("ms", 0)),
            "active_ms": round(a.get("ms", 0)),
        })

    # Output JSON
    out_dir = Path("/opt/openlex-mvp/_private")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = out_dir / f"per_source_active_ab_compare_{ts}.json"
    out_path.write_text(json.dumps({"timestamp": ts, "queries": comparisons}, ensure_ascii=False, indent=2))

    # Konsolen-Summary
    n_changed = sum(1 for c in comparisons if c["n_changed"] > 0)
    avg_overlap = sum(c["n_overlap"] for c in comparisons) / len(comparisons)
    avg_changed = sum(c["n_changed"] for c in comparisons) / len(comparisons)
    avg_active_ms = sum(c["active_ms"] for c in comparisons) / len(comparisons)
    avg_base_ms = sum(c["baseline_ms"] for c in comparisons) / len(comparisons)

    print(f"\n{'='*70}")
    print(f"A/B: Single-Call vs. Per-Source-Aktiv — {len(TEST_QUERIES)} Queries")
    print(f"{'='*70}")
    print(f"Queries mit Änderungen: {n_changed}/{len(comparisons)}")
    print(f"Avg Overlap (Top-10):   {avg_overlap:.1f}/10")
    print(f"Avg neue Chunks:        {avg_changed:.1f}")
    print(f"Avg Latenz Baseline:    {avg_base_ms:.0f}ms")
    print(f"Avg Latenz Aktiv:       {avg_active_ms:.0f}ms")
    print()

    # Per-Query
    print(f"{'Query':<55} {'Overlap':>7} {'Geändert':>9} {'B-Mix':<35} {'A-Mix'}")
    print("-" * 140)
    for c in comparisons:
        b_mix = ",".join(f"{k[:3]}:{v}" for k, v in sorted(c["baseline_source_mix"].items()))
        a_mix = ",".join(f"{k[:3]}:{v}" for k, v in sorted(c["active_source_mix"].items()))
        print(f"{c['query'][:53]:<55} {c['n_overlap']:>6}/10 {c['n_changed']:>8} {b_mix:<35} {a_mix}")

    print(f"\nJSON: {out_path}")


if __name__ == "__main__":
    main()
