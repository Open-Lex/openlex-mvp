#!/usr/bin/env python3
"""
eval_gen_questions.py — Generiert Testfragen für alle OpenLex Skills via LLM.
Überspringt Skills für die bereits Fragen-Dateien existieren.
"""
import json, os, sys, time, random, re, logging
from pathlib import Path
import requests
import chromadb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [GEN] %(message)s")
log = logging.getLogger(__name__)

CHROMADB_PATH = "/opt/openlex-mvp-v2/chromadb"
QUESTIONS_DIR = Path("/opt/openlex-sources/eval/questions")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
JUDGE_MODEL = "meta-llama/llama-3.3-70b-instruct"  # schnell + günstig für Generierung

# Skills mit bereits vorhandenen Fragen überspringen
SKIP_GEN = {"datenschutz"}  # hat eval_questions_v2.json

# Wie viele Fragen pro Skill?
def n_questions(chunk_count: int) -> int:
    return 5 if chunk_count < 500 else 10


def sample_chunks(col, n: int = 6) -> list[str]:
    """Sample diverse Chunks aus Collection."""
    total = col.count()
    if total == 0:
        return []
    
    texts = []
    # Versuche gesetz_granular
    try:
        r = col.get(where={"source_type": "gesetz_granular"}, limit=min(3, total), include=["documents"])
        texts.extend(r["documents"][:3])
    except Exception:
        pass
    
    # Versuche urteil_segmentiert
    try:
        r = col.get(where={"source_type": "urteil_segmentiert"}, limit=min(2, total), include=["documents"])
        texts.extend(r["documents"][:2])
    except Exception:
        pass
    
    # Fallback: random
    if len(texts) < 3:
        try:
            r = col.get(limit=min(6, total), include=["documents"])
            texts.extend(r["documents"])
        except Exception:
            pass
    
    # Kürze Texte auf 400 Zeichen
    return [t[:400] for t in texts[:n] if t and len(t) > 20]


def llm_generate_questions(skill: str, chunks: list[str], n: int) -> list[dict]:
    """Generiert n Testfragen via OpenRouter LLM."""
    if not OPENROUTER_KEY:
        log.error("OPENROUTER_KEY nicht gesetzt!")
        return []
    
    context = "\n\n---\n\n".join(chunks[:5])
    
    prompt = f"""Du bist ein Rechtsexperte. Generiere {n} realistische juristische Testfragen für das Rechtsgebiet "{skill}".

Nutze diese Quelltexte als Kontext:
{context}

Anforderungen:
- Fragen sollen typische Anwendungsfälle aus der Praxis abdecken
- Jede Frage soll mit expected_norms (Paragraphen/Artikel aus den Quellen), expected_keywords (3-5 Schlüsselwörter) und einer category (kurzer Themenname) beantwortet werden können
- Fragen auf Deutsch

Antworte NUR mit einem JSON-Array (kein Markdown, kein Erklärungstext):
[
  {{
    "id": 1,
    "skill": "{skill}",
    "question": "...",
    "expected_norms": ["§ X GesetzABK", "Art. Y EU-VO"],
    "expected_keywords": ["Begriff1", "Begriff2", "Begriff3"],
    "min_sources": 2,
    "category": "kurzthema"
  }},
  ...
]"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://openlex.de",
        "X-Title": "OpenLex Eval Generator",
    }
    payload = {
        "model": JUDGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 3000,
        "temperature": 0.7,
    }
    
    for attempt in range(3):
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            
            # JSON aus Antwort extrahieren
            # Manchmal wrapped in ```json ... ```
            m = re.search(r'\[.*\]', content, re.DOTALL)
            if not m:
                log.warning(f"  Kein JSON-Array in Antwort für {skill}")
                continue
            
            questions = json.loads(m.group(0))
            if isinstance(questions, list) and len(questions) > 0:
                # IDs normalisieren
                for i, q in enumerate(questions):
                    q["id"] = i + 1
                    q["skill"] = skill
                return questions
        except json.JSONDecodeError as e:
            log.warning(f"  JSON-Parse-Fehler für {skill} (attempt {attempt+1}): {e}")
        except Exception as e:
            log.warning(f"  LLM-Fehler für {skill} (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(5)
    
    return []


def run(skills: list[str] | None = None) -> dict:
    """Generiert Fragen für alle Skills. Gibt {skill: n_questions} zurück."""
    client = chromadb.PersistentClient(CHROMADB_PATH)
    
    if skills is None:
        all_cols = client.list_collections()
        skills = [col.name.replace("openlex_", "") for col in all_cols]
    
    results = {}
    for skill in sorted(skills):
        qfile = QUESTIONS_DIR / f"{skill}.json"
        
        if skill in SKIP_GEN and qfile.exists():
            log.info(f"  {skill}: übersprungen (bereits vorhanden, {len(json.load(open(qfile)))} Fragen)")
            results[skill] = len(json.load(open(qfile)))
            continue
        
        if qfile.exists():
            log.info(f"  {skill}: übersprungen (Datei existiert)")
            results[skill] = len(json.load(open(qfile)))
            continue
        
        try:
            col = client.get_collection(f"openlex_{skill}")
            count = col.count()
        except Exception as e:
            log.warning(f"  {skill}: Collection nicht gefunden: {e}")
            continue
        
        n = n_questions(count)
        log.info(f"  {skill}: {count} Chunks → {n} Fragen generieren...")
        
        chunks = sample_chunks(col)
        if not chunks:
            log.warning(f"  {skill}: Keine Chunks gefunden, überspringe")
            results[skill] = 0
            continue
        
        questions = llm_generate_questions(skill, chunks, n)
        if questions:
            qfile.write_text(json.dumps(questions, ensure_ascii=False, indent=2))
            log.info(f"  {skill}: {len(questions)} Fragen gespeichert → {qfile}")
            results[skill] = len(questions)
        else:
            log.error(f"  {skill}: Fragen-Generierung fehlgeschlagen")
            results[skill] = 0
        
        time.sleep(1)  # Rate-Limiting
    
    log.info(f"Fertig: {sum(results.values())} Fragen total für {len(results)} Skills")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", help="Nur diesen Skill generieren")
    parser.add_argument("--force", action="store_true", help="Überschreibe existierende Dateien")
    args = parser.parse_args()
    
    if args.force:
        # Entferne existierende Dateien (außer datenschutz)
        for f in QUESTIONS_DIR.glob("*.json"):
            if f.stem != "datenschutz":
                f.unlink()
    
    skills = [args.skill] if args.skill else None
    run(skills)
