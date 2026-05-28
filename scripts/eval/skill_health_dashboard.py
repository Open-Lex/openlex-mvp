#!/usr/bin/env python3
"""
skill_health_dashboard.py — Vollständiger Health-Report für alle 50 Skills.

Kombiniert:
- retrieval_scorer.py: deterministischer Predicted-Score
- Historische Eval-Ergebnisse: tatsächliche Scores + Q-by-Q Details
- ChromaDB-Metadaten: Chunk-Counts, Source-Type-Verteilung

Gibt einen Markdown-Report aus, der in reports/eval/skill_health_DATUM.md gespeichert wird.

Usage:
  python3 skill_health_dashboard.py
  python3 skill_health_dashboard.py --skill kaufrecht
  python3 skill_health_dashboard.py --no-predict   # nur historische Daten, kein Retrieval
"""
import sys, json, re, argparse, logging
from pathlib import Path
from collections import Counter
from datetime import datetime

EVAL_DIR      = Path("/opt/openlex-sources/scripts/eval")
QUESTIONS_DIR = Path("/opt/openlex-sources/eval/questions")
RESULTS_DIR   = Path("/opt/openlex-sources/eval/results")
REPORTS_DIR   = Path("/opt/openlex-sources/reports/eval")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
CHROMADB_PATH = "/opt/openlex-mvp-v2/chromadb"

sys.path.insert(0, str(EVAL_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SHD] %(message)s")
log = logging.getLogger(__name__)


def load_chromadb_stats(skill: str) -> dict:
    """Lädt Chunk-Count und Source-Type-Verteilung aus ChromaDB."""
    try:
        import chromadb
        client = chromadb.PersistentClient(CHROMADB_PATH)
        col    = client.get_collection(f"openlex_{skill}")
        total  = col.count()
        # Sample für source_type-Verteilung (max 500 für Performance)
        sample = min(total, 500)
        res    = col.get(limit=sample, include=["metadatas"])
        types  = Counter(m.get("source_type", "?") for m in res["metadatas"])
        return {"total_chunks": total, "source_types": dict(types)}
    except Exception as e:
        return {"total_chunks": 0, "source_types": {}, "error": str(e)}


def load_latest_actual_detail(skill: str) -> dict | None:
    """Lädt den letzten Eval-Run mit Q-by-Q Details."""
    files = sorted(RESULTS_DIR.glob("llm_*.json"), reverse=True)
    for f in files:
        try:
            data = json.loads(f.read_text())
            for item in data:
                if item.get("skill") == skill and item.get("avg_score", 0) > 0:
                    return item
        except Exception:
            pass
    return None


def structural_ceiling(source_types: dict) -> float:
    """Berechnet den strukturellen Score-Deckel basierend auf type_diversity."""
    n_types = len([t for t in source_types if t and t != "?"])
    type_score = min(100, n_types * 33)
    # Max bei perfekten anderen Scores (norm=100, kw=100, hall=100, complete=100)
    return type_score * 0.25 + 100 * 0.25 + 100 * 0.20 + 100 * 0.20 + 100 * 0.10


def build_skill_report(skill: str, with_predict: bool = True) -> dict:
    """Erstellt den vollständigen Health-Report für einen Skill."""
    log.info(f"  [{skill}]...")

    # ChromaDB-Stats
    chroma = load_chromadb_stats(skill)

    # Historischer Eval
    actual_data = load_latest_actual_detail(skill)
    actual_score = actual_data["avg_score"] if actual_data else None
    hall_rate    = actual_data.get("hallucination_rate", None) if actual_data else None

    # Q-by-Q Probleme aus letztem Eval
    q_problems = []
    if actual_data:
        for q in actual_data.get("questions", []):
            j = q.get("judge", {})
            probs = []
            if j.get("type_diversity", 0) <= 1: probs.append("type=1")
            if j.get("norm_presence", 1) < 1:   probs.append(f"norm={j['norm_presence']:.1f}")
            if j.get("keyword_coverage", 1) < 1: probs.append(f"kw={j['keyword_coverage']:.1f}")
            if j.get("hallucination"):            probs.append("HALL!")
            if j.get("completeness", 10) < 6:    probs.append(f"comp={j['completeness']}")
            if probs:
                q_problems.append(f"Q{q.get('id','?')}: {', '.join(probs)}")

    # Predicted Score (wenn gewünscht)
    predicted = None
    predicted_detail = None
    if with_predict:
        try:
            from retrieval_scorer import predict_skill
            pred_result = predict_skill(skill)
            predicted = pred_result.get("predicted_avg")
            predicted_detail = pred_result
        except Exception as e:
            log.warning(f"  [{skill}] Prediction fehlgeschlagen: {e}")

    # Struktureller Deckel
    ceiling = structural_ceiling(chroma.get("source_types", {}))

    # Hauptproblem identifizieren
    problems = []
    source_types = chroma.get("source_types", {})
    n_types = len([t for t in source_types if t and t != "?"])
    if chroma["total_chunks"] < 200:
        problems.append(f"Datenbasis klein ({chroma['total_chunks']} Chunks)")
    if n_types == 1:
        problems.append("type_diversity=1 (Deckel ~83%)")
    if n_types == 0:
        problems.append("KEINE Chunks!")
    if q_problems:
        problems.extend(q_problems[:2])

    return {
        "skill": skill,
        "actual": actual_score,
        "predicted": predicted,
        "delta": round(predicted - actual_score, 1) if predicted and actual_score else None,
        "hall_rate": hall_rate,
        "total_chunks": chroma["total_chunks"],
        "source_types": source_types,
        "n_types": n_types,
        "ceiling": round(ceiling, 1),
        "problems": problems,
        "q_problems": q_problems,
        "predicted_detail": predicted_detail,
    }


def render_markdown(reports: list[dict], ts: str) -> str:
    """Rendert den vollständigen Health-Report als Markdown."""
    lines = []
    lines.append(f"# OpenLex Skill Health Dashboard — {ts}")
    lines.append(f"\n**Generiert:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")

    # Zusammenfassung
    above80_pred   = sum(1 for r in reports if (r.get("predicted") or 0) >= 80)
    above80_actual = sum(1 for r in reports if (r.get("actual") or 0) >= 80)
    lines.append(f"| Metrik | Wert |")
    lines.append(f"|--------|------|")
    lines.append(f"| Skills ≥80% (actual)    | **{above80_actual}**/50 |")
    lines.append(f"| Skills ≥80% (predicted) | **{above80_pred}**/50 |")
    lines.append(f"| Skills mit type=1       | {sum(1 for r in reports if r['n_types']==1)} |")
    lines.append(f"| Skills <1000 Chunks     | {sum(1 for r in reports if r['total_chunks']<1000)} |")
    lines.append("")

    # Haupt-Tabelle
    lines.append("## Alle 50 Skills\n")
    lines.append("| Skill | Actual | Pred | Δ | Chunks | Types | Deckel | Probleme |")
    lines.append("|-------|--------|------|---|--------|-------|--------|----------|")

    for r in sorted(reports, key=lambda x: -(x.get("actual") or 0)):
        skill    = r["skill"]
        actual   = f"{r['actual']:.1f}" if r["actual"] else "—"
        pred     = f"{r['predicted']:.1f}" if r["predicted"] else "—"
        delta    = f"{r['delta']:+.1f}" if r["delta"] is not None else "—"
        chunks   = f"{r['total_chunks']:,}"
        types    = ", ".join(sorted(r["source_types"].keys())) or "—"
        ceiling  = f"{r['ceiling']:.0f}%"
        probs    = " · ".join(r["problems"][:2]) if r["problems"] else "✅"

        marker = "✅" if (r.get("actual") or 0) >= 80 else ("⚠️" if (r.get("actual") or 0) >= 70 else "❌")
        lines.append(f"| {marker} {skill} | {actual} | {pred} | {delta} | {chunks} | {types} | {ceiling} | {probs} |")

    # Problemskills detailliert
    problem_skills = [r for r in reports if r["q_problems"] or (r.get("actual") or 100) < 75]
    if problem_skills:
        lines.append("\n## Detailanalyse: Problem-Skills\n")
        for r in sorted(problem_skills, key=lambda x: x.get("actual") or 100):
            lines.append(f"### {r['skill']} (actual={r.get('actual','?')}, pred={r.get('predicted','?')})\n")
            lines.append(f"- **Chunks:** {r['total_chunks']:,} ({', '.join(f'{t}:{n}' for t,n in r['source_types'].items())})")
            lines.append(f"- **Struktureller Deckel:** {r['ceiling']:.0f}%")
            if r["q_problems"]:
                lines.append(f"- **Q-Probleme:** {'; '.join(r['q_problems'])}")
            if r["problems"]:
                lines.append(f"- **Hauptprobleme:** {'; '.join(r['problems'])}")
            lines.append("")

    # Empfehlungen
    type1_skills = [r["skill"] for r in reports if r["n_types"] == 1]
    small_skills = [r["skill"] for r in reports if r["total_chunks"] < 500]

    if type1_skills or small_skills:
        lines.append("## Empfehlungen\n")
        if type1_skills:
            lines.append(f"**Data-Import nötig (type_diversity=1, Deckel ~83%):**")
            lines.append(f"→ {', '.join(sorted(type1_skills))}\n")
        if small_skills:
            lines.append(f"**Datenbasis zu klein (<500 Chunks):**")
            lines.append(f"→ {', '.join(sorted(small_skills))}\n")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", help="Nur diesen Skill analysieren")
    ap.add_argument("--no-predict", action="store_true",
                    help="Kein Retrieval-Scoring — nur historische Daten")
    args = ap.parse_args()

    skills = sorted(p.stem for p in QUESTIONS_DIR.glob("*.json"))
    if args.skill:
        skills = [s for s in skills if s == args.skill]

    with_predict = not args.no_predict
    if with_predict:
        log.info("Lade Embedding-Modell (einmalig)...")
        from eval_llm import get_embed_model
        get_embed_model()  # Pre-load

    reports = []
    for skill in skills:
        r = build_skill_report(skill, with_predict=with_predict)
        reports.append(r)

    ts = datetime.now().strftime("%Y%m%d_%H%M")

    # Markdown-Report
    md = render_markdown(reports, ts)
    md_path = REPORTS_DIR / f"skill_health_{ts}.md"
    md_path.write_text(md, encoding="utf-8")

    # JSON-Report (für Weiterverarbeitung)
    json_path = REPORTS_DIR / f"skill_health_{ts}.json"
    clean = [{k: v for k, v in r.items() if k != "predicted_detail"} for r in reports]
    json_path.write_text(json.dumps(clean, ensure_ascii=False, indent=2))

    print(md)
    log.info(f"\nReports gespeichert:")
    log.info(f"  Markdown: {md_path}")
    log.info(f"  JSON:     {json_path}")


if __name__ == "__main__":
    main()
