#!/usr/bin/env python3
"""
retrieval_scorer.py — Deterministischer L2-Score-Predictor (0 LLM-Calls).

Für alle 50 Skills × 5 Fragen: Retrieval aus ChromaDB, Scoring ohne LLM.
Proxy-Annahme: Wenn Norm/Keyword in den top-8 Chunks steht, wird der LLM sie zitieren.

Usage:
  python3 retrieval_scorer.py                    # alle Skills
  python3 retrieval_scorer.py --skill kaufrecht  # einzelner Skill
  python3 retrieval_scorer.py --calibrate        # Korrelation vs. historische Ergebnisse
"""
import sys, json, re, argparse, logging
from pathlib import Path
from collections import Counter

# ── Pfade ─────────────────────────────────────────────────────────────────────
EVAL_DIR     = Path("/opt/openlex-sources/scripts/eval")
QUESTIONS_DIR = Path("/opt/openlex-sources/eval/questions")
RESULTS_DIR   = Path("/opt/openlex-sources/eval/results")
REPORTS_DIR   = Path("/opt/openlex-sources/reports/eval")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(EVAL_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [RS] %(message)s")
log = logging.getLogger(__name__)

# ── Konstanten (aus historischen Eval-Daten kalibriert) ──────────────────────
ASSUMED_HALL_SCORE     = 100.0   # historisch 0-5% Halluzinations-Rate
ASSUMED_COMPLETE_SCORE = 70.0    # historisch ~7/10 im Schnitt


def load_questions(skill: str) -> list[dict]:
    path = QUESTIONS_DIR / f"{skill}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))[:5]  # erste 5


def predict_question(question: str, skill: str,
                     expected_norms: list, expected_keywords: list) -> dict:
    """Deterministischer Score-Predictor — kein LLM, nur ChromaDB-Retrieval."""
    from eval_llm import simple_retrieve

    chunks = simple_retrieve(question, skill, n=8)
    if not chunks:
        return {
            "predicted": 0.0, "type_score": 0, "norm_score": 0, "kw_score": 0,
            "types_found": [], "norms_missing": expected_norms[:],
            "kw_missing": expected_keywords[:], "chunks": [], "error": "no chunks"
        }

    # Kombinierter Text aller Chunks (lowercase für Substring-Matching)
    corpus = " ".join(c["text"] for c in chunks).lower()

    # 1. Type Diversity (100% deterministisch aus Metadaten)
    types = {c["meta"].get("source_type", "") for c in chunks
             if c["meta"].get("source_type")}
    type_score = min(100, len(types) * 33)

    # 2. Norm Presence — Dreistufiges Matching (kein LLM)
    # (a) Exakt: "§ 264 stgb" in corpus
    # (b) Kern:  "§ 264" (§-Nummer ohne Suffix) in corpus
    # (c) Konzept/Abkz. ohne § (HGB, InsO) → LLM-Trainingswissen → immer OK
    import re as _re
    _NORM_CORE = _re.compile(r"(§§?\s*\d+[a-z]?|Art\.\s*\d+)", _re.IGNORECASE)

    def _norm_in_corpus(n, corpus):
        if n.lower() in corpus:
            return True
        m = _NORM_CORE.match(n)
        if m:
            return m.group(1).lower() in corpus
        return True  # Abkz./Konzept: LLM kennt aus Training

    norms_missing = [n for n in expected_norms if not _norm_in_corpus(n, corpus)]
    norm_hits = len(expected_norms) - len(norms_missing)
    norm_score = norm_hits / max(1, len(expected_norms)) * 100

    # 3. Keyword Coverage — auch Compound-Keywords teilweise prüfen
    def _kw_in_corpus(k, corpus):
        if k.lower() in corpus:
            return True
        parts = k.lower().split()
        return len(parts) > 1 and any(p in corpus for p in parts if len(p) >= 5)

    kw_missing = [k for k in expected_keywords if not _kw_in_corpus(k, corpus)]
    kw_hits = len(expected_keywords) - len(kw_missing)
    kw_score = kw_hits / max(1, len(expected_keywords)) * 100


    # 4. Gesamtscore (Halluzination + Completeness = Konstanten)
    predicted = round(
        type_score    * 0.25 +
        norm_score    * 0.25 +
        kw_score      * 0.20 +
        ASSUMED_HALL_SCORE     * 0.20 +
        ASSUMED_COMPLETE_SCORE * 0.10,
        1
    )

    return {
        "predicted": predicted,
        "type_score": type_score,
        "norm_score": round(norm_score, 1),
        "kw_score": round(kw_score, 1),
        "types_found": sorted(types),
        "norms_missing": norms_missing,
        "kw_missing": kw_missing,
        "chunks": chunks,
    }


def predict_skill(skill: str) -> dict:
    """Predicted Score für alle 5 Fragen eines Skills."""
    questions = load_questions(skill)
    if not questions:
        return {"skill": skill, "error": "no questions", "predicted_avg": 0.0, "questions": []}

    results = []
    for q in questions:
        r = predict_question(
            q["question"], skill,
            q.get("expected_norms", []),
            q.get("expected_keywords", [])
        )
        r["q_id"] = q["id"]
        r["question"] = q["question"][:80]
        results.append(r)
        log.info(f"  [{skill}] Q{q['id']}: predicted={r['predicted']} "
                 f"type={r['type_score']} norm={r['norm_score']} kw={r['kw_score']} "
                 f"missing_norms={r['norms_missing']} missing_kw={r['kw_missing']}")

    avg = round(sum(r["predicted"] for r in results) / len(results), 1)
    return {"skill": skill, "predicted_avg": avg, "questions": results}


def load_latest_actual(skill: str) -> float | None:
    """Lädt den zuletzt gemessenen tatsächlichen Score aus Eval-Ergebnissen."""
    files = sorted(RESULTS_DIR.glob("llm_*.json"), reverse=True)
    for f in files:
        try:
            data = json.loads(f.read_text())
            for item in data:
                if item.get("skill") == skill and item.get("avg_score", 0) > 0:
                    return item["avg_score"]
        except Exception:
            pass
    return None


def run_all(skill_filter: str | None = None) -> list[dict]:
    """Führt Prediction für alle (oder einen) Skill(s) durch."""
    skills = sorted(p.stem for p in QUESTIONS_DIR.glob("*.json"))
    if skill_filter:
        skills = [s for s in skills if s == skill_filter]

    all_results = []
    for skill in skills:
        log.info(f"\n[{skill}] Starte Prediction...")
        result = predict_skill(skill)
        result["actual"] = load_latest_actual(skill)
        if result["actual"]:
            result["delta"] = round(result["predicted_avg"] - result["actual"], 1)
        all_results.append(result)

    return all_results


def print_summary(results: list[dict]):
    """Gibt eine kompakte Übersichtstabelle aus."""
    print("\n" + "="*90)
    print(f"{'Skill':<28} {'Pred':>6} {'Actual':>7} {'Δ':>6} {'Type':>5} {'Norm':>6} {'KW':>6}  Problem")
    print("-"*90)

    for r in sorted(results, key=lambda x: x.get("predicted_avg", 0)):
        if "error" in r:
            print(f"  {r['skill']:<26} {'ERROR':>6}")
            continue

        pred   = r["predicted_avg"]
        actual = r.get("actual")
        delta  = r.get("delta")
        act_s  = f"{actual:.1f}" if actual else "   —"
        dlt_s  = f"{delta:+.1f}" if delta is not None else "   —"

        # Typ-Score aus erstem Q
        qs = r.get("questions", [])
        type_s = qs[0]["type_score"] if qs else "?"
        norm_ok = all(q["norm_score"] == 100 for q in qs)
        kw_ok   = all(q["kw_score"]  == 100 for q in qs)

        problems = []
        if type_s == 33: problems.append("type=1")
        if not norm_ok:
            miss = [n for q in qs for n in q["norms_missing"]]
            if miss: problems.append(f"norm:{','.join(sorted(set(miss))[:2])}")
        if not kw_ok:
            miss = [k for q in qs for k in q["kw_missing"]]
            if miss: problems.append(f"kw:{','.join(sorted(set(miss))[:2])}")

        marker = "✅" if pred >= 80 else ("⚠️ " if pred >= 70 else "❌")
        print(f"  {marker} {r['skill']:<24} {pred:>6.1f} {act_s:>7} {dlt_s:>6} "
              f"{type_s:>5} {'✅' if norm_ok else '❌':>4} {'✅' if kw_ok else '❌':>4}  "
              f"{' | '.join(problems)}")

    above = sum(1 for r in results if r.get("predicted_avg", 0) >= 80)
    print("="*90)
    print(f"Predicted ≥80%: {above}/{len(results)}")


def calibrate(results: list[dict]):
    """Berechnet Pearson-Korrelation zwischen predicted und actual."""
    pairs = [(r["predicted_avg"], r["actual"])
             for r in results if r.get("actual") and r.get("predicted_avg")]
    if len(pairs) < 5:
        print("Zu wenig Daten für Kalibrierung.")
        return

    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    n  = len(pairs)
    mx, my = sum(xs)/n, sum(ys)/n
    cov = sum((x-mx)*(y-my) for x,y in pairs) / n
    sx  = (sum((x-mx)**2 for x in xs)/n)**0.5
    sy  = (sum((y-my)**2 for y in ys)/n)**0.5
    r   = cov / (sx * sy) if sx * sy > 0 else 0

    diffs = [abs(p[0]-p[1]) for p in pairs]
    mae   = sum(diffs)/n
    max_d = max(diffs)

    print(f"\nKalibrierung: n={n} Paare")
    print(f"  Pearson r     = {r:.3f}  (Ziel: >0.80)")
    print(f"  MAE           = {mae:.1f}  (mittl. abs. Fehler)")
    print(f"  Max-Abweichung= {max_d:.1f}")
    print(f"  Bias (pred-act)= {sum(p[0]-p[1] for p in pairs)/n:+.1f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", help="Nur diesen Skill testen")
    ap.add_argument("--calibrate", action="store_true", help="Korrelation vs. historische Ergebnisse")
    ap.add_argument("--json-out", help="Ergebnisse als JSON speichern")
    args = ap.parse_args()

    results = run_all(args.skill)
    print_summary(results)

    if args.calibrate or not args.skill:
        calibrate(results)

    if args.json_out:
        out = Path(args.json_out)
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print(f"\nJSON gespeichert: {out}")
    else:
        ts = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M")
        out = REPORTS_DIR / f"retrieval_score_{ts}.json"
        # chunks rauswerfen (zu groß für Report)
        clean = [{**r, "questions": [{k:v for k,v in q.items() if k!="chunks"}
                                      for q in r.get("questions",[])]}
                 for r in results]
        out.write_text(json.dumps(clean, ensure_ascii=False, indent=2))
        log.info(f"Report gespeichert: {out}")


if __name__ == "__main__":
    main()
