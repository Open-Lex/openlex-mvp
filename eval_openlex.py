#!/usr/bin/env python3
"""
eval_openlex.py – Automatisiertes Evaluations-Framework für OpenLex MVP.

Verwendung:
    python3 eval_openlex.py                       # Alle 20 Fragen (Retrieval + LLM)
    python3 eval_openlex.py --category drittland   # Nur Drittland-Fragen
    python3 eval_openlex.py --quick                # Nur Retrieval, kein LLM
    python3 eval_openlex.py --compare              # Vergleich mit letztem Lauf
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_FILE = BASE_DIR / "eval_questions.json"
RESULTS_DIR = BASE_DIR / "eval_results"

# ── Veraltete Normen (für Aktualitäts-Check) ──
# ── Keyword-Synonyme (FIX 5) ──
_KEYWORD_SYNONYMS: dict[str, list[str]] = {
    "interessenabwägung": ["abwägung", "interessen abzuwägen", "interessen abwägen"],
    "profiling": ["profilbildung", "automatisierte bewertung"],
    "fernmeldegeheimnis": ["telekommunikationsgeheimnis", "tk-geheimnis"],
    "informationspflicht": ["informieren", "unterrichten", "informationspflichten"],
    "verantwortlicher": ["verantwortlichen", "verantwortliche stelle"],
    "beschäftigte": ["arbeitnehmer", "mitarbeiter", "beschäftigten"],
    "datenminimierung": ["erforderlichkeit", "auf das notwendige maß beschränkt", "erforderlichen umfang"],
    "benennung": ["bestellen", "bestellt"],
    "schranken": ["ausnahmen", "grenzen", "eingeschränkt"],
    "privatnutzung": ["private nutzung", "privat nutzen"],
    "verhältnismäßigkeit": ["verhältnismäßig", "angemessen"],
}

_OBSOLETE_NORMS = [
    "§ 4a BDSG", "§ 28 BDSG", "§ 28a BDSG", "§ 29 BDSG",
    "§ 4b BDSG", "§ 4c BDSG", "§ 6b BDSG", "§ 4f BDSG",
    "§ 4g BDSG", "§ 11 BDSG", "§ 13 TMG", "§ 15 TMG",
]

# ── Gewichtungen ──
WEIGHT_NORM = 0.30
WEIGHT_CASE = 0.20
WEIGHT_FORBIDDEN = 0.15
WEIGHT_KEYWORD = 0.15
WEIGHT_SOURCES = 0.10
WEIGHT_HALLUCINATION = 0.10


def load_questions(category: str | None = None,
                   file_path: Path | None = None) -> list[dict]:
    path = file_path or QUESTIONS_FILE
    with open(path, "r", encoding="utf-8") as f:
        questions = json.load(f)
    if category:
        questions = [q for q in questions if q["category"] == category]
    return questions


def _norm_in_text(norm: str, text: str) -> bool:
    """Prüft ob eine Norm im Text vorkommt (tolerant: Art. 44 matcht Art. 44 DSGVO)."""
    norm_lower = norm.lower().strip()
    text_lower = text.lower()
    if norm_lower in text_lower:
        return True
    # Ohne Gesetzeskürzel prüfen (z.B. "Art. 44" in "Art. 44 ff. DSGVO")
    base = re.sub(r"\s*(DSGVO|BDSG|UWG|TDDDG|TTDSG|TMG|GG|GRCh)\s*$", "", norm, flags=re.I).strip()
    if base.lower() in text_lower:
        return True
    return False


def _case_in_text(case: str, text: str) -> bool:
    """Prüft ob ein Aktenzeichen im Text vorkommt (Unicode-Bindestrich-tolerant)."""
    normalized = case.replace("\u2011", "-").replace("\u2010", "-").replace("\u2013", "-")
    text_norm = text.replace("\u2011", "-").replace("\u2010", "-").replace("\u2013", "-")
    return normalized.lower() in text_norm.lower()


def run_retrieval(question: str):
    """Ruft retrieve() aus app.py auf."""
    from app import retrieve
    return retrieve(question)


def run_llm(question: str, chunks: list[dict]) -> tuple[str, str]:
    """Ruft LLM via stream_with_fallback auf. Gibt (antwort, provider) zurück."""
    from app import format_context, _build_llm_messages, stream_with_fallback
    context = format_context(chunks)
    messages = _build_llm_messages(question, context, [])
    full_response = ""
    provider_display = ""
    for token, prov in stream_with_fallback(messages):
        provider_display = prov
        full_response += token
    return full_response, provider_display


def run_validator(response: str, chunks: list[dict]) -> list[dict]:
    """Ruft validate_response() aus app.py auf."""
    from app import validate_response
    return validate_response(response, chunks)


def evaluate_single(q: dict, chunks: list[dict], response: str,
                    validations: list[dict]) -> dict:
    """Bewertet eine einzelne Frage. Gibt Score-Dict zurück."""
    scores = {}
    details = {}

    # Kombinierten Text aus Antwort + Quellen bilden
    source_text = " ".join(c["text"] for c in chunks)
    combined = response + " " + source_text

    # a) Norm-Check (30%)
    expected_norms = q.get("expected_norms", [])
    if expected_norms:
        found = [n for n in expected_norms if _norm_in_text(n, response)]
        scores["norm"] = len(found) / len(expected_norms)
        details["norms_found"] = found
        details["norms_missing"] = [n for n in expected_norms if n not in found]
    else:
        scores["norm"] = 1.0
        details["norms_found"] = []
        details["norms_missing"] = []

    # b) Case-Check (20%) – in Antwort ODER Quellen
    expected_cases = q.get("expected_cases", [])
    if expected_cases:
        found = [c for c in expected_cases if _case_in_text(c, combined)]
        scores["case"] = len(found) / len(expected_cases)
        details["cases_found"] = found
        details["cases_missing"] = [c for c in expected_cases if c not in found]
    else:
        scores["case"] = 1.0
        details["cases_found"] = []
        details["cases_missing"] = []

    # c) Forbidden-Check (15% Abzug)
    forbidden = q.get("forbidden_norms", [])
    forbidden_found = [n for n in forbidden if _norm_in_text(n, response)]
    penalty = min(len(forbidden_found) * 10, 100)  # max 100% Abzug
    scores["forbidden"] = max(0, 100 - penalty) / 100
    details["forbidden_found"] = forbidden_found

    # d) Keyword-Check (15%) – mit Synonym-Matching
    expected_kw = q.get("expected_keywords", [])
    if expected_kw:
        resp_lower = response.lower()
        found = []
        for kw in expected_kw:
            # Exakter Match
            if kw.lower() in resp_lower:
                found.append(kw)
                continue
            # Synonym-Match
            synonyms = _KEYWORD_SYNONYMS.get(kw.lower(), [])
            if any(syn in resp_lower for syn in synonyms):
                found.append(kw)
        scores["keyword"] = len(found) / len(expected_kw)
        details["keywords_found"] = found
        details["keywords_missing"] = [kw for kw in expected_kw if kw not in found]
    else:
        scores["keyword"] = 1.0
        details["keywords_found"] = []
        details["keywords_missing"] = []

    # e) Source-Quality (10%)
    from app import group_chunks_to_docs
    n_docs = len(group_chunks_to_docs(chunks))
    min_src = q.get("min_sources", 3)
    scores["sources"] = min(n_docs / max(min_src, 1), 1.0)
    details["n_docs"] = n_docs
    details["min_sources"] = min_src

    # f) Halluzinations-Check (10% Abzug)
    n_missing = sum(1 for v in validations if v.get("level") == "missing")
    n_total = len(validations) if validations else 1
    scores["hallucination"] = max(0, 1.0 - (n_missing / n_total)) if validations else 1.0
    details["validations_missing"] = n_missing
    details["validations_total"] = n_total

    # g) Aktualitäts-Check (informativer Malus auf forbidden)
    obsolete_found = [n for n in _OBSOLETE_NORMS if _norm_in_text(n, response)]
    details["obsolete_norms"] = obsolete_found
    if obsolete_found:
        scores["forbidden"] = max(0, scores["forbidden"] - 0.1 * len(obsolete_found))

    # h) TDDDG-Check
    ttdsg_used = bool(re.search(r"\bTTDSG\b", response))
    tdddg_used = bool(re.search(r"\bTDDDG\b", response))
    details["ttdsg_instead_of_tdddg"] = ttdsg_used and not tdddg_used

    # Gesamtscore
    total = (
        scores["norm"] * WEIGHT_NORM
        + scores["case"] * WEIGHT_CASE
        + scores["forbidden"] * WEIGHT_FORBIDDEN
        + scores["keyword"] * WEIGHT_KEYWORD
        + scores["sources"] * WEIGHT_SOURCES
        + scores["hallucination"] * WEIGHT_HALLUCINATION
    ) * 100

    return {
        "question_id": q["id"],
        "question": q["question"],
        "category": q["category"],
        "total_score": round(total, 1),
        "scores": {k: round(v, 3) for k, v in scores.items()},
        "details": details,
    }


def print_report(results: list[dict], provider: str, duration: float,
                 compare_file: str | None = None):
    """Gibt den Evaluationsbericht aus."""
    print("\n" + "=" * 70)
    print("  OpenLex MVP – Evaluationsbericht")
    print("=" * 70)
    print(f"  Datum:    {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Provider: {provider}")
    print(f"  Fragen:   {len(results)}")
    print(f"  Dauer:    {duration:.0f}s")

    # Gesamtscore
    avg = sum(r["total_score"] for r in results) / max(len(results), 1)
    print(f"\n  GESAMTSCORE: {avg:.1f} / 100\n")

    # Score pro Kategorie
    cats = defaultdict(list)
    for r in results:
        cats[r["category"]].append(r["total_score"])

    print("  Score pro Kategorie:")
    for cat, cat_scores in sorted(cats.items(), key=lambda x: -sum(x[1]) / len(x[1])):
        cat_avg = sum(cat_scores) / len(cat_scores)
        bar = "█" * int(cat_avg / 5) + "░" * (20 - int(cat_avg / 5))
        print(f"    {cat:<25s} {bar} {cat_avg:5.1f}")

    # Einzelergebnisse
    print(f"\n  {'#':>3s}  {'Score':>5s}  {'N':>4s}  {'C':>4s}  {'K':>4s}  Frage")
    print("  " + "-" * 66)
    for r in sorted(results, key=lambda x: x["total_score"]):
        s = r["scores"]
        print(f"  {r['question_id']:3d}  {r['total_score']:5.1f}  "
              f"{s['norm']:.2f}  {s['case']:.2f}  {s['keyword']:.2f}  "
              f"{r['question'][:45]}")

    # Top-3 schlechteste
    worst = sorted(results, key=lambda x: x["total_score"])[:3]
    print("\n  Top-3 schlechteste Fragen:")
    for r in worst:
        d = r["details"]
        issues = []
        if d.get("norms_missing"):
            issues.append(f"Normen fehlen: {', '.join(d['norms_missing'])}")
        if d.get("cases_missing"):
            issues.append(f"AZ fehlen: {', '.join(d['cases_missing'])}")
        if d.get("forbidden_found"):
            issues.append(f"Verboten: {', '.join(d['forbidden_found'])}")
        if d.get("keywords_missing"):
            issues.append(f"Keywords fehlen: {', '.join(d['keywords_missing'])}")
        if d.get("obsolete_norms"):
            issues.append(f"Veraltet: {', '.join(d['obsolete_norms'])}")
        if d.get("ttdsg_instead_of_tdddg"):
            issues.append("TTDSG statt TDDDG")
        print(f"\n    #{r['question_id']} ({r['total_score']:.1f}): {r['question'][:50]}")
        for issue in issues:
            print(f"      - {issue}")

    # Systemische Muster
    all_missing_norms = Counter()
    all_missing_cases = Counter()
    all_hallucinations = 0
    all_obsolete = Counter()
    for r in results:
        d = r["details"]
        for n in d.get("norms_missing", []):
            all_missing_norms[n] += 1
        for c in d.get("cases_missing", []):
            all_missing_cases[c] += 1
        all_hallucinations += d.get("validations_missing", 0)
        for o in d.get("obsolete_norms", []):
            all_obsolete[o] += 1

    print("\n  Systemische Muster:")
    if all_missing_norms:
        print("    Häufig fehlende Normen:")
        for norm, cnt in all_missing_norms.most_common(5):
            print(f"      {norm}: {cnt}x")
    if all_missing_cases:
        print("    Häufig fehlende Aktenzeichen:")
        for case, cnt in all_missing_cases.most_common(5):
            print(f"      {case}: {cnt}x")
    if all_obsolete:
        print("    Veraltete Normen in Antworten:")
        for norm, cnt in all_obsolete.most_common(5):
            print(f"      {norm}: {cnt}x")
    print(f"    Halluzinationen gesamt: {all_hallucinations}")

    # Vergleich mit letztem Lauf
    if compare_file and os.path.exists(compare_file):
        with open(compare_file, "r", encoding="utf-8") as f:
            old = json.load(f)
        old_avg = old.get("average_score", 0)
        diff = avg - old_avg
        arrow = "↑" if diff > 0 else "↓" if diff < 0 else "→"
        print(f"\n  Vergleich mit {os.path.basename(compare_file)}:")
        print(f"    Vorher: {old_avg:.1f}  →  Jetzt: {avg:.1f}  ({arrow} {abs(diff):.1f})")

        # Vergleich pro Frage
        old_by_id = {r["question_id"]: r["total_score"] for r in old.get("results", [])}
        changed = []
        for r in results:
            old_score = old_by_id.get(r["question_id"])
            if old_score is not None:
                d = r["total_score"] - old_score
                if abs(d) >= 5:
                    changed.append((r["question_id"], r["question"][:40], old_score, r["total_score"], d))
        if changed:
            print("    Größte Veränderungen:")
            for qid, q, old_s, new_s, d in sorted(changed, key=lambda x: -abs(x[4])):
                arrow = "↑" if d > 0 else "↓"
                print(f"      #{qid} {q}: {old_s:.1f} → {new_s:.1f} ({arrow}{abs(d):.1f})")

    print("\n" + "=" * 70)


def find_last_result() -> str | None:
    """Findet die neueste Ergebnisdatei."""
    if not RESULTS_DIR.exists():
        return None
    files = sorted(RESULTS_DIR.glob("*.json"), reverse=True)
    return str(files[0]) if files else None


def main():
    parser = argparse.ArgumentParser(description="OpenLex Evaluation Framework")
    parser.add_argument("--file", type=str, help="Pfad zur Fragen-Datei (Default: eval_questions.json)")
    parser.add_argument("--category", type=str, help="Nur Fragen dieser Kategorie")
    parser.add_argument("--quick", action="store_true", help="Nur Retrieval, kein LLM")
    parser.add_argument("--compare", action="store_true", help="Vergleich mit letztem Lauf")
    args = parser.parse_args()

    # In das Projektverzeichnis wechseln (damit app.py importiert werden kann)
    os.chdir(BASE_DIR)
    sys.path.insert(0, str(BASE_DIR))

    q_file = Path(args.file) if args.file else None
    questions = load_questions(args.category, file_path=q_file)
    if not questions:
        print(f"Keine Fragen gefunden (Kategorie: {args.category})")
        return

    print(f"\nOpenLex Evaluation – {len(questions)} Fragen")
    if args.quick:
        print("  Modus: --quick (nur Retrieval, kein LLM)")
    print()

    compare_file = find_last_result() if args.compare else None

    results = []
    provider_name = "nur Retrieval" if args.quick else ""
    t_start = time.time()

    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] #{q['id']}: {q['question'][:50]}...", end="", flush=True)
        t0 = time.time()

        # a) Retrieval
        chunks = run_retrieval(q["question"])

        if args.quick:
            # Ohne LLM: Bewerte nur Quellen-Qualität
            # Erzeuge synthetische Antwort aus Quellentexten für Norm/Keyword-Prüfung
            response = " ".join(c["text"] for c in chunks)
            validations = []
        else:
            # b) LLM
            response, prov = run_llm(q["question"], chunks)
            if not provider_name:
                provider_name = prov

            # c) Validator
            validations = run_validator(response, chunks)

        dt = time.time() - t0

        # d) Bewertung
        result = evaluate_single(q, chunks, response, validations)
        result["duration_s"] = round(dt, 1)
        result["n_chunks"] = len(chunks)
        if not args.quick:
            result["response_length"] = len(response)
            result["validations"] = validations
        results.append(result)

        print(f"  {result['total_score']:5.1f}  ({dt:.1f}s)")

    duration = time.time() - t_start

    # Report
    print_report(results, provider_name, duration, compare_file)

    # Ergebnisse speichern
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_file = RESULTS_DIR / f"{timestamp}.json"
    avg = sum(r["total_score"] for r in results) / max(len(results), 1)
    output = {
        "timestamp": timestamp,
        "provider": provider_name,
        "mode": "quick" if args.quick else "full",
        "n_questions": len(results),
        "average_score": round(avg, 1),
        "duration_s": round(duration, 1),
        "results": results,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nErgebnisse gespeichert: {out_file}")


if __name__ == "__main__":
    main()
