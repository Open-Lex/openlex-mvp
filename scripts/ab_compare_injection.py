#!/usr/bin/env python3
"""
A/B-Vergleich: Hypothese-Injektion ON vs. OFF.
Misst, wie sich Top-10-Treffer pro Query ändern.
"""
import os
import sys
import json
import importlib
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/opt/openlex-mvp")

from dotenv import load_dotenv
load_dotenv('/opt/openlex-mvp/.env')

TEST_QUERIES = [
    # Kern-Queries
    "Darf mein Arbeitgeber meine E-Mails lesen?",
    "Was ist eine Auftragsverarbeitung?",
    "Welche Rechte habe ich nach DSGVO?",
    "Kann ich Schadensersatz nach SCHUFA-Urteil verlangen?",
    "Wann ist eine DSFA verpflichtend?",
    "Wer braucht einen Datenschutzbeauftragten?",
    "Wie lange darf eine Bewerbung gespeichert werden?",
    "Sind Cookies ohne Einwilligung erlaubt?",
    "Wann muss ich eine Datenpanne melden?",
    "Datenschutz im Verein",
    # Technisch
    "Welche Rechtsgrundlagen sind für die Anonymisierung relevant?",
    "Welche Kriterien müssen bei der Prüfung der Verhältnismäßigkeit gelten?",
    "Unter welchen Voraussetzungen stellt eine dynamische IP-Adresse personenbezogene Daten dar?",
    "Welche rechtlichen Voraussetzungen müssen für E-Mail-Werbung erfüllt sein?",
    "Welche Länder haben derzeit einen gültigen Angemessenheitsbeschluss?",
    "Welche rechtlichen Anforderungen müssen bei der Verarbeitung biometrischer Daten erfüllt sein?",
    "Welche rechtlichen Grundlagen und Grenzen sind beim Einsatz von Kamera-Systemen am Arbeitsplatz zu beachten?",
    "Welche spezifischen Angaben müssen in einer Datenschutzerklärung enthalten sein?",
    "Welche Rechtsgrundlagen sind bei der Videoüberwachung im öffentlichen Raum zu beachten?",
    "Welche rechtlichen Schritte sind erforderlich, um Daten in ein Drittland zu übermitteln?",
    # Adversarial / Edge
    "Mein Chef liest meine Mails",
    "DSGVO und Werbung",
    "Was ist mit § 32 BDSG-alt?",
    "Da § 29 BDSG das regelt, wie lange darf ich speichern?",
    "Was hat der EuGH zu Schrems II entschieden?",
    "Darf ich Mitarbeiterfotos auf der Website veröffentlichen?",
    "Wann liegt berechtigtes Interesse vor?",
    "Was bedeutet Pseudonymisierung?",
    "Was sind besondere Kategorien personenbezogener Daten?",
    "Welche Folgen hat das SCHUFA-Urteil?",
]


def run_with_flag(flag_value: bool, queries: list) -> list:
    os.environ["OPENLEX_NORM_HYPOTHESIS_ENABLED"] = "true"
    os.environ["OPENLEX_NORM_HYPOTHESIS_INJECT_ENABLED"] = "true" if flag_value else "false"

    import app as _app
    importlib.reload(_app)
    from app import retrieve

    results = []
    for i, q in enumerate(queries, 1):
        print(f"  [{i}/{len(queries)}] {q[:55]}", end="", flush=True)
        try:
            r = retrieve(q)
            results.append({
                "query": q,
                "type": "ok",
                "chunks": [
                    {
                        "id": c.get("id"),
                        "score": c.get("ce_score", c.get("score", 0)),
                        "source": c.get("source", ""),
                    }
                    for c in r[:10]
                ],
            })
            n_hyp = sum(1 for c in r[:10] if c.get("source") == "hypothesis_pflicht")
            print(f" → {len(r)} results, {n_hyp} hyp-injected")
        except Exception as e:
            print(f" → ERROR: {e}")
            results.append({"query": q, "type": "error", "error": str(e), "chunks": []})
    return results


def main():
    print("=== A/B-Vergleich: Hypothesis Injection ===\n")

    print("Lauf 1/2: Inject OFF (baseline)")
    baseline = run_with_flag(False, TEST_QUERIES)

    print("\nLauf 2/2: Inject ON")
    treatment = run_with_flag(True, TEST_QUERIES)

    # Vergleich
    identical = changed_top3 = changed_top10 = 0
    total_new_hyp_chunks = 0
    diffs = []

    for b, t in zip(baseline, treatment):
        if b["type"] != "ok" or t["type"] != "ok":
            continue

        b_ids = [c["id"] for c in b["chunks"]]
        t_ids = [c["id"] for c in t["chunks"]]
        b3 = b_ids[:3]
        t3 = t_ids[:3]

        new_in_t = [c for c in t["chunks"] if c.get("source") == "hypothesis_pflicht"]
        total_new_hyp_chunks += len(new_in_t)

        if b_ids == t_ids:
            identical += 1
        else:
            changed_top10 += 1
            if b3 != t3:
                changed_top3 += 1
            diffs.append({
                "query": b["query"][:65],
                "new_hyp_chunks": [c["id"] for c in new_in_t],
                "removed_from_top10": list(set(b_ids) - set(t_ids)),
            })

    n_valid = sum(1 for b in baseline if b["type"] == "ok")
    print(f"\n=== Ergebnisse ({n_valid} valide Queries) ===")
    print(f"Identische Top-10-Listen:   {identical}/{n_valid}")
    print(f"Top-10 geändert:            {changed_top10}")
    print(f"Top-3 geändert:             {changed_top3}")
    print(f"Avg neue Hyp-Chunks (bei Änderung): {total_new_hyp_chunks/max(1, changed_top10):.1f}")

    if diffs:
        print(f"\nTop-5 Diffs (Auszug):")
        for d in diffs[:5]:
            print(f"  Q: {d['query']}")
            print(f"     +hyp: {d['new_hyp_chunks'][:3]}")
            if d['removed_from_top10']:
                print(f"     -rem: {d['removed_from_top10'][:2]}")

    # Speichern
    out_dir = Path("/opt/openlex-mvp/_private")
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = out_dir / f"injection_ab_compare_{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total": len(TEST_QUERIES),
                "valid": n_valid,
                "identical": identical,
                "changed_top10": changed_top10,
                "changed_top3": changed_top3,
                "avg_new_hyp_per_changed": round(total_new_hyp_chunks / max(1, changed_top10), 1),
            },
            "baseline": baseline,
            "treatment": treatment,
            "diffs": diffs,
        }, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nDetail-Output: {out_path}")


if __name__ == "__main__":
    main()
