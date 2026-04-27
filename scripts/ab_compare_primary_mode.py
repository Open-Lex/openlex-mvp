#!/usr/bin/env python3
"""
A/B-Vergleich: Additive (1.3) vs. Primary (1.4) mode.
Gleiches Test-Set wie ab_compare_injection.py.
"""
import os, sys, json, importlib
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/opt/openlex-mvp")
from dotenv import load_dotenv
load_dotenv('/opt/openlex-mvp/.env')

TEST_QUERIES = [
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


def run_mode(primary: bool, queries: list) -> list:
    os.environ["OPENLEX_NORM_HYPOTHESIS_ENABLED"] = "true"
    os.environ["OPENLEX_NORM_HYPOTHESIS_INJECT_ENABLED"] = "true"
    os.environ["OPENLEX_NORM_HYPOTHESIS_PRIMARY"] = "true" if primary else "false"

    import app as _app
    importlib.reload(_app)
    from app import retrieve

    results = []
    for i, q in enumerate(queries, 1):
        label = "PRIMARY" if primary else "ADDITIVE"
        print(f"  [{label} {i:02d}/{len(queries)}] {q[:55]}", end="", flush=True)
        try:
            r = retrieve(q)
            hyp_n = sum(1 for c in r[:10] if c.get("source") == "hypothesis_pflicht")
            qu_n = sum(1 for c in r[:10] if c.get("source") == "qu_injection")
            print(f" → {len(r)} results (hyp={hyp_n}, qu={qu_n})")
            results.append({
                "query": q, "type": "ok",
                "chunks": [{"id": c.get("id"), "score": c.get("ce_score", c.get("score", 0)), "source": c.get("source", "")} for c in r[:10]],
            })
        except Exception as e:
            print(f" → ERROR: {e}")
            results.append({"query": q, "type": "error", "error": str(e), "chunks": []})
    return results


def main():
    print("=== A/B: Additive (1.3) vs. Primary (1.4) ===\n")
    print("Lauf 1/2: Additive Mode (1.3-Verhalten)")
    additive = run_mode(False, TEST_QUERIES)

    print("\nLauf 2/2: Primary Mode (1.4)")
    primary = run_mode(True, TEST_QUERIES)

    # Analyse
    identical = changed_top3 = changed_top10 = 0
    qu_lost = hyp_gained = 0
    diffs = []

    for a, p in zip(additive, primary):
        if a["type"] != "ok" or p["type"] != "ok":
            continue

        a_ids = [c["id"] for c in a["chunks"]]
        p_ids = [c["id"] for c in p["chunks"]]

        if a_ids == p_ids:
            identical += 1
            continue

        changed_top10 += 1
        if a_ids[:3] != p_ids[:3]:
            changed_top3 += 1

        removed = set(a_ids) - set(p_ids)
        added   = set(p_ids) - set(a_ids)

        # Welche QU-Chunks wurden verdrängt?
        qu_removed = [c["id"] for c in a["chunks"] if c["id"] in removed and c.get("source") == "qu_injection"]
        # Welche Hyp-Chunks sind neu drin?
        hyp_new = [c["id"] for c in p["chunks"] if c["id"] in added and c.get("source") == "hypothesis_pflicht"]

        qu_lost += len(qu_removed)
        hyp_gained += len(hyp_new)

        diffs.append({
            "query": a["query"][:65],
            "qu_removed": qu_removed,
            "hyp_new": hyp_new[:3],
            "other_removed": [x for x in list(removed)[:3] if x not in qu_removed],
        })

    n_valid = sum(1 for a in additive if a["type"] == "ok")
    print(f"\n=== Ergebnisse ({n_valid} valide Queries) ===")
    print(f"Identische Top-10:  {identical}/{n_valid}")
    print(f"Top-10 geändert:    {changed_top10}")
    print(f"Top-3 geändert:     {changed_top3}")
    print(f"QU-Chunks verdrängt (total): {qu_lost}")
    print(f"Hyp-Chunks neu (total):      {hyp_gained}")

    if diffs:
        print(f"\nTop-5 Diffs:")
        for d in diffs[:5]:
            print(f"  Q: {d['query']}")
            if d["qu_removed"]:
                print(f"     -QU: {d['qu_removed'][:2]}")
            if d["hyp_new"]:
                print(f"     +hyp: {d['hyp_new'][:2]}")
            if d["other_removed"]:
                print(f"     -other: {d['other_removed'][:2]}")

    out_dir = Path("/opt/openlex-mvp/_private")
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = out_dir / f"primary_mode_ab_compare_{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {"total": len(TEST_QUERIES), "valid": n_valid, "identical": identical,
                        "changed_top10": changed_top10, "changed_top3": changed_top3,
                        "qu_lost": qu_lost, "hyp_gained": hyp_gained},
            "additive": additive, "primary": primary, "diffs": diffs,
        }, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nDetail: {out_path}")


if __name__ == "__main__":
    main()
