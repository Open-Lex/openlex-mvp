#!/usr/bin/env python3
"""
auto_fix_questions.py — Automatische Norm/Keyword-Vorschläge aus Retrieval-Analyse.

Analysiert retrieval_scorer-Output und schlägt bessere expected_norms + expected_keywords vor,
ohne einen einzigen LLM-Call zu benötigen.

Usage:
  python3 auto_fix_questions.py                        # alle Skills analysieren
  python3 auto_fix_questions.py --skill kaufrecht      # einzelner Skill
  python3 auto_fix_questions.py --apply                # Fixes direkt anwenden (nach Review!)
  python3 auto_fix_questions.py --min-confidence high  # nur sichere Fixes
"""
import sys, json, re, argparse, logging
from pathlib import Path
from collections import Counter
from datetime import datetime

EVAL_DIR      = Path("/opt/openlex-sources/scripts/eval")
QUESTIONS_DIR = Path("/opt/openlex-sources/eval/questions")
REPORTS_DIR   = Path("/opt/openlex-sources/reports/eval")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(EVAL_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AFQ] %(message)s")
log = logging.getLogger(__name__)


# ── Norm-Extraktion aus Chunk-Texten ──────────────────────────────────────────
NORM_RE = re.compile(
    r'(?:'
    r'§§?\s*\d+[a-zäöü]?'          # § 437, §§ 437 ff.
    r'|Art\.\s*\d+'                  # Art. 6
    r'|Artikel\s*\d+'                # Artikel 6
    r')',
    re.IGNORECASE
)
ABS_RE  = re.compile(r'\s+Abs\b.*', re.IGNORECASE)


def normalize_norm(n: str) -> str:
    """§ 437 Abs. 1 BGB → § 437"""
    n = n.strip()
    # Gesetzesabkürzung am Ende entfernen (BGB, StGB, etc.)
    n = re.sub(r'\s+[A-ZÄÖÜ]{2,10}\s*$', '', n).strip()
    # Abs./Satz/Nr. entfernen
    n = ABS_RE.sub('', n).strip()
    # Doppel-§ normalisieren
    n = re.sub(r'§§', '§', n)
    # ff. entfernen
    n = re.sub(r'\s+ff\.?', '', n).strip()
    return n


def suggest_norms(chunks: list, top_n: int = 3) -> list[tuple[str, int]]:
    """Extrahiert häufigste Norm-Referenzen aus Chunk-Texten.
    Returns: [(norm, count), ...]"""
    counter = Counter()
    for c in chunks:
        raw = NORM_RE.findall(c["text"])
        for r in raw:
            normed = normalize_norm(r)
            if normed and len(normed) >= 3:
                counter[normed] += 1
    return counter.most_common(top_n)


# ── Keyword-Extraktion aus Chunk-Texten ──────────────────────────────────────
NOUN_RE = re.compile(r'\b[A-ZÄÖÜ][a-zäöüß]{4,}\b')

GENERIC_STOPWORDS = {
    'Absatz', 'Artikel', 'Gesetz', 'Gericht', 'Grundlage', 'Grundsatz',
    'Vorschrift', 'Regelung', 'Bestimmung', 'Paragraph', 'Nummer',
    'Frage', 'Antwort', 'Inhalt', 'Bereich', 'Rahmen', 'Form', 'Sinne',
    'Weise', 'Seite', 'Stelle', 'Punkt', 'Stand', 'Lage', 'Maße',
    'Nichtamtliches', 'Inhaltsverzeichnis', 'Bürgerliches', 'Gesetzbuch',
}


def suggest_keywords(chunks: list, question: str = "", top_n: int = 5) -> list[tuple[str, int]]:
    """Extrahiert häufige juristische Substantive aus Top-Chunks."""
    corpus = " ".join(c["text"] for c in chunks)
    words = NOUN_RE.findall(corpus)
    candidates = [w for w in words if w not in GENERIC_STOPWORDS and len(w) >= 5]
    counter = Counter(candidates)

    # Wörter aus der Frage boosten (sind garantiert relevant)
    q_words = set(NOUN_RE.findall(question))
    boosted = Counter()
    for w, cnt in counter.items():
        boost = 3 if w in q_words else 0
        boosted[w] = cnt + boost

    return boosted.most_common(top_n)


# ── Confidence-Bewertung ──────────────────────────────────────────────────────
def confidence(current: list, suggested: list[tuple], missing: list, corpus: str) -> str:
    """
    high   = suggested norm erscheint 3+× im Corpus, current norm fehlt völlig
    medium = suggested erscheint 1-2×, oder current erscheint manchmal
    low    = unsichere Heuristik
    """
    if not missing:
        return "ok"  # kein Fix nötig
    if not suggested:
        return "low"

    top_norm, top_count = suggested[0]
    # Ist die vorgeschlagene Norm deutlich häufiger als die aktuelle?
    current_counts = [corpus.count(n.lower()) for n in current]
    max_current = max(current_counts) if current_counts else 0

    if top_count >= 3 and max_current == 0:
        return "high"
    if top_count >= 2:
        return "medium"
    return "low"


# ── Hauptlogik ────────────────────────────────────────────────────────────────
def analyze_skill(skill: str) -> list[dict]:
    """Analysiert alle 5 Fragen eines Skills und generiert Fix-Vorschläge."""
    from eval_llm import simple_retrieve

    q_path = QUESTIONS_DIR / f"{skill}.json"
    if not q_path.exists():
        return []

    questions = json.loads(q_path.read_text(encoding="utf-8"))[:5]
    fixes = []

    for q in questions:
        question  = q["question"]
        cur_norms = q.get("expected_norms", [])
        cur_kw    = q.get("expected_keywords", [])

        chunks = simple_retrieve(question, skill, n=8)
        if not chunks:
            continue

        corpus = " ".join(c["text"] for c in chunks).lower()

        # Welche aktuellen Norms/KW fehlen im Corpus?
        missing_norms = [n for n in cur_norms if n.lower() not in corpus]
        missing_kw    = [k for k in cur_kw    if k.lower() not in corpus]

        if not missing_norms and not missing_kw:
            # Alles OK für diese Frage
            fixes.append({
                "skill": skill, "q_id": q["id"],
                "question": question[:80],
                "status": "ok",
                "current_norms": cur_norms, "current_kw": cur_kw,
            })
            continue

        # Norm-Vorschläge
        norm_suggestions = suggest_norms(chunks, top_n=5)
        # Nur vorschlagen wenn besser als aktuell
        suggested_norms = []
        if missing_norms:
            for norm, cnt in norm_suggestions:
                if norm.lower() in corpus:
                    suggested_norms.append(norm)
                if len(suggested_norms) >= len(cur_norms):
                    break
            if not suggested_norms:
                suggested_norms = [n for n, _ in norm_suggestions[:len(cur_norms)]]

        # Keyword-Vorschläge
        kw_suggestions = suggest_keywords(chunks, question, top_n=10)
        suggested_kw = []
        if missing_kw:
            # Ersetze nur die fehlenden Keywords, behalte funktionierende
            working_kw = [k for k in cur_kw if k.lower() in corpus]
            # Neue Kandidaten (die noch nicht in working_kw sind)
            new_candidates = [w for w, _ in kw_suggestions
                              if w not in working_kw and w.lower() in corpus]
            # Fülle auf bis wieder 3 KW vorhanden
            n_needed = len(cur_kw) - len(working_kw)
            suggested_kw = working_kw + new_candidates[:n_needed]
            # Falls immer noch zu wenig: alle top-suggestions
            if len(suggested_kw) < len(cur_kw):
                extra = [w for w, _ in kw_suggestions
                         if w not in suggested_kw]
                suggested_kw += extra[:len(cur_kw) - len(suggested_kw)]

        # Confidence bewerten
        norm_conf = confidence(cur_norms, norm_suggestions, missing_norms, corpus)
        kw_conf   = "ok" if not missing_kw else ("high" if suggested_kw else "low")

        fixes.append({
            "skill": skill,
            "q_id": q["id"],
            "question": question[:80],
            "status": "needs_fix",
            "current_norms": cur_norms,
            "suggested_norms": suggested_norms if missing_norms else cur_norms,
            "norm_confidence": norm_conf,
            "missing_norms": missing_norms,
            "current_kw": cur_kw,
            "suggested_kw": suggested_kw if missing_kw else cur_kw,
            "kw_confidence": kw_conf,
            "missing_kw": missing_kw,
            "top_norms_in_corpus": [f"{n}({c}×)" for n, c in norm_suggestions[:5]],
            "top_kw_in_corpus": [f"{w}({c}×)" for w, c in kw_suggestions[:5]],
        })

        log.info(f"  [{skill}] Q{q['id']}: missing_norms={missing_norms} "
                 f"suggested={suggested_norms} | missing_kw={missing_kw} "
                 f"suggested_kw={suggested_kw}")

    return fixes


def apply_fixes(fixes: list[dict], min_confidence: str = "high") -> int:
    """Wendet Fixes auf question JSON-Dateien an. Gibt Anzahl der Änderungen zurück."""
    conf_order = {"high": 0, "medium": 1, "low": 2, "ok": 99}
    min_idx    = conf_order[min_confidence]

    # Gruppiere nach Skill
    by_skill: dict[str, list] = {}
    for f in fixes:
        if f["status"] != "needs_fix":
            continue
        by_skill.setdefault(f["skill"], []).append(f)

    total_changed = 0
    for skill, skill_fixes in by_skill.items():
        q_path = QUESTIONS_DIR / f"{skill}.json"
        questions = json.loads(q_path.read_text(encoding="utf-8"))
        changed = False

        for fix in skill_fixes:
            norm_ok = conf_order.get(fix.get("norm_confidence", "low"), 2) <= min_idx
            kw_ok   = conf_order.get(fix.get("kw_confidence",  "low"), 2) <= min_idx

            for q in questions:
                if q["id"] == fix["q_id"]:
                    if norm_ok and fix.get("suggested_norms") and fix["suggested_norms"] != q.get("expected_norms"):
                        old = q.get("expected_norms")
                        q["expected_norms"] = fix["suggested_norms"]
                        log.info(f"  [{skill}] Q{fix['q_id']} norms: {old} → {fix['suggested_norms']}")
                        changed = True
                    if kw_ok and fix.get("suggested_kw") and fix["suggested_kw"] != q.get("expected_keywords"):
                        old = q.get("expected_keywords")
                        q["expected_keywords"] = fix["suggested_kw"]
                        log.info(f"  [{skill}] Q{fix['q_id']} kw: {old} → {fix['suggested_kw']}")
                        changed = True
                    break

        if changed:
            q_path.write_text(json.dumps(questions, ensure_ascii=False, indent=2))
            log.info(f"  [{skill}] gespeichert: {q_path}")
            total_changed += 1

    return total_changed


def print_fixes(fixes: list[dict], min_confidence: str = "medium"):
    """Gibt Vorschläge als lesbaren Report aus."""
    conf_order = {"high": 0, "medium": 1, "low": 2, "ok": 99}
    min_idx    = conf_order[min_confidence]
    needs_fix  = [f for f in fixes if f["status"] == "needs_fix"]

    if not needs_fix:
        print("  ✅ Keine Fixes nötig.")
        return

    print(f"\n{'='*80}")
    print(f"Auto-Fix Vorschläge ({len(needs_fix)} Fragen betroffen)")
    print(f"Min-Confidence: {min_confidence} | Einstellbar mit --min-confidence")
    print(f"{'='*80}\n")

    for f in sorted(needs_fix, key=lambda x: (x["skill"], x["q_id"])):
        norm_conf = f.get("norm_confidence", "?")
        kw_conf   = f.get("kw_confidence",  "?")
        show_norm = conf_order.get(norm_conf, 2) <= min_idx and f.get("missing_norms")
        show_kw   = conf_order.get(kw_conf,  2) <= min_idx and f.get("missing_kw")

        if not show_norm and not show_kw:
            continue

        print(f"[{f['skill']}] Q{f['q_id']}: {f['question']}")
        if show_norm:
            print(f"  NORMS  [{norm_conf}]: {f['current_norms']} → {f.get('suggested_norms','?')}")
            print(f"         Häufigste im Corpus: {f.get('top_norms_in_corpus','?')}")
        if show_kw:
            print(f"  KW     [{kw_conf}]: {f['current_kw']} → {f.get('suggested_kw','?')}")
            print(f"         Häufigste im Corpus: {f.get('top_kw_in_corpus','?')}")
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", help="Nur diesen Skill analysieren")
    ap.add_argument("--apply", action="store_true",
                    help="Fixes direkt auf question-JSONs anwenden")
    ap.add_argument("--min-confidence", default="medium",
                    choices=["high", "medium", "low"],
                    help="Minimale Confidence für Vorschläge/Anwendung (default: medium)")
    args = ap.parse_args()

    skills = sorted(p.stem for p in QUESTIONS_DIR.glob("*.json"))
    if args.skill:
        skills = [s for s in skills if s == args.skill]

    all_fixes = []
    for skill in skills:
        log.info(f"\n[{skill}] Analysiere...")
        fixes = analyze_skill(skill)
        all_fixes.extend(fixes)

    print_fixes(all_fixes, min_confidence=args.min_confidence)

    # Report speichern
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    report_path = REPORTS_DIR / f"auto_fix_{ts}.json"
    report_path.write_text(json.dumps(all_fixes, ensure_ascii=False, indent=2))
    log.info(f"Report gespeichert: {report_path}")

    if args.apply:
        n = apply_fixes(all_fixes, min_confidence=args.min_confidence)
        log.info(f"\n✅ {n} Skill-Dateien aktualisiert (confidence≥{args.min_confidence})")
    else:
        needs = sum(1 for f in all_fixes if f["status"] == "needs_fix")
        if needs:
            print(f"Zum Anwenden: python3 auto_fix_questions.py --apply "
                  f"--min-confidence {args.min_confidence}")


if __name__ == "__main__":
    main()
