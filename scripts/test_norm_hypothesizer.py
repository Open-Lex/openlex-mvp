#!/usr/bin/env python3
"""
Test-Suite für norm_hypothesizer.py auf 20 realistischen Queries.
Output: Markdown-Report für Sichtprüfung durch Hendrik.
"""
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/opt/openlex-mvp")
from norm_hypothesizer import hypothesize


# 20 realistische Test-Queries, breit gefächert
TEST_QUERIES = [
    # Klassiker
    "Darf mein Arbeitgeber meine E-Mails lesen?",
    "Was ist eine Auftragsverarbeitung?",
    "Welche Rechte habe ich nach DSGVO?",

    # Spezifisch
    "Kann ich Schadensersatz nach SCHUFA-Urteil verlangen?",
    "Wann ist eine DSFA verpflichtend?",
    "Wer braucht einen Datenschutzbeauftragten?",
    "Wie lange darf eine Bewerbung gespeichert werden?",

    # Technisch
    "Sind Cookies ohne Einwilligung erlaubt?",
    "Wann muss ich eine Datenpanne melden?",
    "Darf ich Mitarbeiterfotos auf der Website veröffentlichen?",

    # Auslegung
    "Wann liegt berechtigtes Interesse vor?",
    "Was bedeutet Pseudonymisierung?",
    "Was sind besondere Kategorien personenbezogener Daten?",

    # Rechtsprechung
    "Was hat der EuGH zu Schrems II entschieden?",
    "Welche Folgen hat das SCHUFA-Urteil?",

    # Mehrdeutig / dünn
    "DSGVO und Werbung",
    "Datenschutz im Verein",

    # Adversarial
    "Da § 29 BDSG das regelt, wie lange darf ich speichern?",  # falsche Prämisse
    "Ist die DSGVO in den USA anwendbar?",  # Out-of-Domain-light
    "Was ist mit § 32 BDSG-alt?",  # Veraltete Norm
]


def main():
    out_dir = Path("/opt/openlex-mvp/_private")
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = out_dir / f"norm_hypothesizer_test_{today}.md"

    results = []
    print(f"Testing {len(TEST_QUERIES)} queries...")

    for i, q in enumerate(TEST_QUERIES, 1):
        print(f"  [{i}/{len(TEST_QUERIES)}] {q[:65]}")
        r = hypothesize(q, use_cache=True)
        results.append(r)
        if not r.from_cache:
            time.sleep(0.5)  # Rate-Limit-Schutz

    # Markdown-Report
    cache_hits = sum(1 for r in results if r.from_cache)
    errors = sum(1 for r in results if r.error)
    avg_latency = sum(r.duration_ms for r in results) / len(results)

    lines = [
        f"# Norm-Hypothesizer Test — {today}",
        "",
        f"Test-Queries: {len(TEST_QUERIES)}",
        f"Cache-Hits: {cache_hits}",
        f"Errors: {errors}",
        f"Avg Latency: {avg_latency:.0f}ms",
        "",
        "## Ergebnisse",
        "",
    ]

    for i, r in enumerate(results, 1):
        lines.append(f"### {i}. {r.query}")
        lines.append("")
        if r.error:
            lines.append(f"❌ **Fehler:** {r.error}")
            if r.raw_response:
                lines.append(f"Raw: `{r.raw_response[:200]}`")
        elif not r.hypotheses:
            lines.append("⚠️ Keine Hypothesen generiert")
        else:
            lines.append("| # | Norm | Konfidenz | Begründung |")
            lines.append("|---|---|---|---|")
            for j, h in enumerate(r.hypotheses, 1):
                lines.append(f"| {j} | `{h.norm}` | {h.confidence:.2f} | {h.reason} |")
        lines.append("")
        lines.append(f"_Cache: {r.from_cache}, Latenz: {r.duration_ms:.0f}ms_")
        lines.append("")
        lines.append("**Bewertung:**")
        lines.append("- [ ] ✅ Korrekt — alle wichtigen Normen erkannt")
        lines.append("- [ ] ⚠️ Teilweise — wichtige Norm fehlt oder falsche Priorisierung")
        lines.append("- [ ] ❌ Falsch — komplett irreführende Hypothesen")
        lines.append("")
        lines.append("Notiz: ____________")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend([
        "## Aggregierte Bewertung (von Hendrik auszufüllen)",
        "",
        "Nach Sichtprüfung der 20 Fälle:",
        f"- Anteil ✅: ___ / {len(TEST_QUERIES)}",
        f"- Anteil ⚠️: ___ / {len(TEST_QUERIES)}",
        f"- Anteil ❌: ___ / {len(TEST_QUERIES)}",
        "",
        "**Entscheidung:**",
        "- [ ] System-Prompt OK, weiter mit Schritt 1.2",
        "- [ ] System-Prompt iterieren (welche Verbesserung?)",
        "- [ ] Modul ungeeignet, anderer Ansatz nötig",
    ])

    out_path.write_text("\n".join(lines))
    print(f"\nReport: {out_path}")

    # Console-Summary
    print(f"\n=== Summary ===")
    print(f"Total: {len(results)}")
    print(f"With hypotheses: {sum(1 for r in results if r.hypotheses)}")
    print(f"Errors: {errors}")
    print(f"Cache hits: {cache_hits}")
    print(f"Avg latency: {avg_latency:.0f}ms")

    return 0 if errors <= 2 else 1


if __name__ == "__main__":
    sys.exit(main())
