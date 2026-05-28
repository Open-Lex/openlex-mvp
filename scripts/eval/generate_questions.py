#!/usr/bin/env python3
"""
generate_questions.py
Generiert 5 neue Eval-Fragen pro Skill, geerdet in tatsächlichen ChromaDB-Chunks.
Verwendet requests direkt (wie eval_llm.py) — kein anthropic-Paket nötig.

Usage:
    ANTHROPIC_API_KEY=sk-... python3 generate_questions.py [--skill NAME] [--dry-run]
"""
import argparse, json, os, re, sys, time
from collections import Counter
from pathlib import Path
import requests, chromadb

CHROMA_PATH    = "/opt/openlex-mvp-v2/chromadb"
QUESTIONS_DIR  = Path("/opt/openlex-sources/eval/questions")
ANTHROPIC_URL  = "https://api.anthropic.com/v1/messages"
MODEL          = "claude-haiku-4-5"

SKILLS = [
    "agrarrecht","arbeitsrecht","bank_kapitalmarktrecht","baurecht","bildungsrecht",
    "datenschutz","energierecht","erbrecht","familienrecht","gesellschaftsrecht",
    "gewerblicher_rechtsschutz","grundrechte","handelsrecht","insolvenzrecht",
    "it_recht","jugendrecht","kartellrecht","kaufrecht","ki_recht","kirchenrecht",
    "medizinrecht","mietrecht","migrationsrecht","nachbarrecht","reiserecht",
    "sachenrecht","sanktionsrecht","sozialrecht","sportrecht","staatsorganisationsrecht",
    "steuerrecht","strafrecht","strafverfahrensrecht","transportrecht","umweltrecht",
    "urheberrecht","verbraucherrecht","verbraucherschutzrecht","verfassungsprozessrecht",
    "vergaberecht","verkehrsrecht","versicherungsrecht","verwaltungsprozessrecht",
    "verwaltungsrecht","voelkerrecht","voelkerstrafrecht","waffenrecht","weltraumrecht",
    "wirtschaftsstrafrecht","zivilverfahrensrecht",
]

NORM_RE = re.compile(
    r'(?:§§?\s*\d+[a-z]?(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß]+)?)'
    r'|(?:Art\.\s*\d+(?:\s*Abs\.\s*\d+)?(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß]+)?)',
    re.UNICODE)
NOUN_RE = re.compile(r'\b([A-ZÄÖÜ][a-zäöüß]{3,})\b')
STOPWORDS = {
    "Absatz","Satz","Nach","Dieser","Diese","Dieses","Wenn","Durch","Eine","Einen",
    "Einer","Eines","Jedoch","Auch","Aber","Kann","Wird","Sind","Haben","Werden",
    "Soll","Muss","Darf","Dass","Dann","Damit","Soweit","Gemäß","Sofern","Wobei",
    "Daher","Deshalb","Zudem","Ferner","Indem","Hierbei","Insbesondere",
}


def get_chunks(skill: str, n: int = 20) -> list[str]:
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    col = client.get_collection(f"openlex_{skill}")
    total = col.count()
    res = col.get(limit=min(n, total), include=["documents"])
    return [d for d in res.get("documents", []) if d and d.strip()]


def extract_norms(texts: list[str]) -> list[str]:
    cnt: Counter = Counter()
    for t in texts:
        for m in NORM_RE.finditer(t):
            n = re.sub(r'\s+', ' ', m.group(0).strip())
            if len(n) >= 3:
                cnt[n] += 1
    return [n for n, _ in cnt.most_common(10)]


def extract_keywords(texts: list[str]) -> list[str]:
    cnt: Counter = Counter()
    for t in texts:
        for m in NOUN_RE.finditer(t):
            w = m.group(1)
            if w not in STOPWORDS and len(w) >= 5:
                cnt[w] += 1
    return [w for w, c in cnt.most_common(20) if c >= 2]


def haiku_call(api_key: str, prompt: str) -> str:
    r = requests.post(
        ANTHROPIC_URL,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": MODEL, "max_tokens": 2048,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=60
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"].strip()


def build_prompt(skill: str, chunks: list[str], norms: list[str], kws: list[str]) -> str:
    chunk_block = "\n---\n".join(chunks[:20])
    norms_str = ", ".join(norms) if norms else "(keine)"
    kws_str   = ", ".join(kws[:15]) if kws else "(keine)"
    return (
        f'Du bist ein juristischer Experte. Erstelle 5 unterschiedliche Praxisfragen für das Rechtsgebiet "{skill}".\n\n'
        f'REGEL 1: Jede Frage muss anhand der unten stehenden Textauszüge vollständig beantwortbar sein.\n'
        f'REGEL 2: expected_norms: Nur Normen die WORTGLEICH in den Texten vorkommen (§-Angaben oder Art.-Angaben).\n'
        f'REGEL 3: expected_keywords: Genau 3 Begriffe die WORTGLEICH in den Texten vorkommen.\n'
        f'REGEL 4: Die 5 Fragen sollen verschiedene Aspekte abdecken.\n'
        f'REGEL 5: Formuliere wie echte Nutzer fragen — konkret, szenariobasiert.\n\n'
        f'In den Texten gefundene Normen: {norms_str}\n'
        f'In den Texten häufige Begriffe: {kws_str}\n\n'
        f'AUSGABE: Nur gültiges JSON-Array mit genau 5 Objekten. Kein Markdown, keine Erklärungen.\n'
        f'Schema: [{{"id":1,"skill":"{skill}","question":"...","expected_norms":["..."],'
        f'"expected_keywords":["Begriff1","Begriff2","Begriff3"],"category":"..."}}]\n\n'
        f'TEXTE AUS DER WISSENSDATENBANK:\n{chunk_block}\n\nJSON-Array:'
    )


def generate(api_key: str, skill: str, chunks: list[str], dry_run: bool) -> list[dict]:
    norms = extract_norms(chunks)
    kws   = extract_keywords(chunks)
    
    if dry_run:
        print(f"  [dry] norms={norms[:3]} kws={kws[:3]}", flush=True)
        return [{"id": i+1, "skill": skill, "question": f"DRY Q{i+1}",
                 "expected_norms": norms[:1], "expected_keywords": kws[:3], "category": "test"}
                for i in range(5)]
    
    raw = haiku_call(api_key, build_prompt(skill, chunks, norms, kws))
    # Strip markdown fences
    raw = re.sub(r'^```[a-z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw).strip()
    
    qs = json.loads(raw)
    for i, q in enumerate(qs[:5]):
        q["id"] = i + 1
        q["skill"] = skill
        q.setdefault("expected_norms", norms[:2])
        q.setdefault("expected_keywords", kws[:3])
        q.setdefault("category", "allgemein")
    return qs[:5]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key and not args.dry_run:
        sys.exit("ERROR: ANTHROPIC_API_KEY not set")

    targets = [args.skill] if args.skill else SKILLS
    ok, failed = 0, []

    for i, skill in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {skill}", flush=True)
        try:
            chunks = get_chunks(skill)
            print(f"  {len(chunks)} chunks retrieved", flush=True)
            qs = generate(key, skill, chunks, args.dry_run)
            if not args.dry_run:
                QUESTIONS_DIR.mkdir(parents=True, exist_ok=True)
                (QUESTIONS_DIR / f"{skill}.json").write_text(
                    json.dumps(qs, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  ✓", flush=True)
            ok += 1
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON: {e}", flush=True)
            failed.append((skill, "json"))
        except Exception as e:
            print(f"  ✗ {type(e).__name__}: {str(e)[:80]}", flush=True)
            failed.append((skill, str(e)[:60]))
        
        if i < len(targets) and not args.dry_run:
            time.sleep(args.delay)

    print(f"\n✓ {ok}/{len(targets)} OK")
    for sk, r in failed:
        print(f"  ✗ {sk}: {r}")


if __name__ == "__main__":
    main()
