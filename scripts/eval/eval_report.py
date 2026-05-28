#!/usr/bin/env python3
"""
eval_report.py — Generiert Markdown-Report aus Layer-1 und Layer-2 Ergebnissen.
"""
import json, sys
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path("/opt/openlex-sources/eval/results")
REPORTS_DIR = Path("/opt/openlex-sources/eval/reports")


def find_latest(prefix: str) -> Path | None:
    files = sorted(RESULTS_DIR.glob(f"{prefix}_*.json"), reverse=True)
    return files[0] if files else None


def gen_report(l1_file: Path | None = None, l2_file: Path | None = None) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if l1_file is None:
        l1_file = find_latest("retrieval")
    if l2_file is None:
        l2_file = find_latest("llm")
    
    l1_data = {}
    l2_data = {}
    
    if l1_file and l1_file.exists():
        for r in json.loads(l1_file.read_text()):
            l1_data[r["skill"]] = r
    
    if l2_file and l2_file.exists():
        for r in json.loads(l2_file.read_text()):
            l2_data[r["skill"]] = r
    
    all_skills = sorted(set(list(l1_data.keys()) + list(l2_data.keys())))
    
    lines = [
        f"# OpenLex Eval-Report — {ts}",
        "",
        f"**Layer 1 (Retrieval):** {l1_file.name if l1_file else 'nicht vorhanden'}  ",
        f"**Layer 2 (LLM):** {l2_file.name if l2_file else 'nicht vorhanden'}",
        "",
        "---",
        "",
        "## Zusammenfassung",
        "",
        "| Skill | Chunks | L1-Score | L2-Score | Halluz.-Rate | Issues |",
        "|-------|--------|----------|----------|--------------|--------|",
    ]
    
    # Sortiert nach L2-Score aufsteigend (schlechteste zuerst hervorheben)
    def sort_key(s):
        l2 = l2_data.get(s, {}).get("avg_score", 999)
        return l2
    
    for skill in sorted(all_skills, key=sort_key):
        l1 = l1_data.get(skill, {})
        l2 = l2_data.get(skill, {})
        chunks = l1.get("collection_count", "?")
        l1_score = f"{l1.get('l1_score', '?')}%" if l1 else "—"
        l2_score = f"{l2.get('avg_score', '?')}" if l2 else "—"
        hall = f"{l2.get('hallucination_rate', '?')}%" if l2 else "—"
        issues = "; ".join(l1.get("issues", []))[:60] if l1 else ""
        if l2.get("hallucination_rate", 0) > 30:
            issues += " ⚠️Hall"
        lines.append(f"| {skill} | {chunks} | {l1_score} | {l2_score} | {hall} | {issues} |")
    
    # Statistiken
    if l1_data:
        avg_l1 = sum(r.get("l1_score", 0) for r in l1_data.values()) / len(l1_data)
        lines += ["", f"**Ø L1-Score: {avg_l1:.1f}%** über {len(l1_data)} Skills"]
    if l2_data:
        avg_l2 = sum(r.get("avg_score", 0) for r in l2_data.values()) / len(l2_data)
        lines += [f"**Ø L2-Score: {avg_l2:.1f}/100** über {len(l2_data)} Skills"]
    
    # Layer 1 Details
    lines += ["", "---", "", "## Layer 1 — Retrieval-Diagnose", ""]
    
    for skill in sorted(all_skills):
        r = l1_data.get(skill)
        if not r:
            continue
        inv = r.get("type_inventory", {})
        missing = r.get("missing_expected_types", [])
        cov = r.get("query_coverage", {})
        
        status = "✅" if r.get("l1_score", 0) >= 80 else ("⚠️" if r.get("l1_score", 0) >= 50 else "❌")
        lines.append(f"### {status} {skill} (L1={r.get('l1_score')}%)")
        
        if inv:
            inv_str = ", ".join(f"{k}: {v}" for k, v in sorted(inv.items()))
            lines.append(f"- **Typen:** {inv_str}")
        if missing:
            lines.append(f"- **Fehlend:** {', '.join(missing)} ⚠️")
        if cov:
            lines.append(f"- **Query-Coverage:** {cov.get('n_covered', 0)}/{cov.get('n_queries', 0)} Queries alle Typen gefunden ({cov.get('coverage_rate', 0)}%)")
        for issue in r.get("issues", []):
            lines.append(f"- ⚠️ {issue}")
        lines.append("")
    
    # Layer 2 Details — nur schlechteste Skills
    lines += ["---", "", "## Layer 2 — LLM-Eval", ""]
    
    # Halluzinations-Hotspots
    hall_issues = []
    for skill, r in l2_data.items():
        for q in r.get("questions", []):
            judge = q.get("judge", {})
            if judge.get("hallucination") and judge.get("hallucination_examples"):
                for ex in judge["hallucination_examples"][:1]:
                    hall_issues.append(f"- **{skill}** Q{q['id']}: {str(ex)[:100]}")
    
    if hall_issues:
        lines += ["### ⚠️ Halluzinations-Hotspots", ""]
        lines.extend(hall_issues[:15])
        lines.append("")
    
    # Schlechteste Skills (L2 < 60)
    bad_skills = [(s, r) for s, r in l2_data.items() if r.get("avg_score", 100) < 60]
    if bad_skills:
        lines += ["### ❌ Skills mit L2-Score < 60", ""]
        for skill, r in sorted(bad_skills, key=lambda x: x[1].get("avg_score", 0)):
            lines.append(f"**{skill}** (Ø={r['avg_score']})")
            worst = sorted(r.get("questions", []), key=lambda q: q.get("score", 100))[:3]
            for q in worst:
                lines.append(f"  - Q{q['id']} ({q.get('score', 0)}): {q.get('question', '')[:70]}")
            lines.append("")
    
    # Empfehlungen
    lines += ["---", "", "## Empfehlungen", ""]
    
    recs = []
    for skill in all_skills:
        l1 = l1_data.get(skill, {})
        l2 = l2_data.get(skill, {})
        
        missing_types = l1.get("missing_expected_types", [])
        if "urteil_segmentiert" in missing_types:
            recs.append(f"- **{skill}**: Rechtsprechung nachladen (urteil_segmentiert fehlt, {l1.get('collection_count', 0)} Chunks total)")
        if l1.get("collection_count", 0) < 100:
            recs.append(f"- **{skill}**: Sehr wenige Chunks ({l1.get('collection_count', 0)}) — mehr Quellen nötig")
        if l2.get("hallucination_rate", 0) > 40:
            recs.append(f"- **{skill}**: Hohe Halluzinations-Rate ({l2.get('hallucination_rate')}%) — Systemp-Prompt prüfen")
        if l2.get("avg_score", 100) < 50:
            recs.append(f"- **{skill}**: L2-Score sehr niedrig ({l2.get('avg_score')}) — Datenbasis prüfen")
    
    if recs:
        lines.extend(recs[:20])
    else:
        lines.append("Keine kritischen Probleme gefunden.")
    
    return "\n".join(lines)


def run(l1_file=None, l2_file=None) -> Path:
    report = gen_report(
        Path(l1_file) if l1_file else None,
        Path(l2_file) if l2_file else None,
    )
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out = REPORTS_DIR / f"eval_report_{ts}.md"
    out.write_text(report)
    print(report[:500])
    print(f"\n... Report gespeichert: {out}")
    return out


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--l1", help="Layer-1-Ergebnis-Datei")
    parser.add_argument("--l2", help="Layer-2-Ergebnis-Datei")
    args = parser.parse_args()
    run(args.l1, args.l2)
