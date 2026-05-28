#!/usr/bin/env python3
"""
eval_llm.py — Layer 2: LLM-Qualitäts-Eval für alle Skills.
Eigene Retrieval-Logik (kein app.py-Import wegen Gradio-Dependency).
"""
import json, os, re, sys, time, logging
from pathlib import Path
from datetime import datetime

import chromadb
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [L2] %(message)s")
log = logging.getLogger(__name__)

CHROMADB_PATH   = "/opt/openlex-mvp-v2/chromadb"
QUESTIONS_DIR   = Path("/opt/openlex-sources/eval/questions")
RESULTS_DIR     = Path("/opt/openlex-sources/eval/results")
MODEL_NAME      = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"

OPENROUTER_KEY  = os.environ.get("OPENROUTER_KEY", "")
ANTHROPIC_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL   = "https://api.anthropic.com/v1/messages"
OPENROUTER_URL  = "https://openrouter.ai/api/v1/chat/completions"
ANSWER_MODEL    = "claude-haiku-4-5"
JUDGE_MODEL     = "claude-haiku-4-5"

_embed_model = None
_chroma_client = None


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        log.info(f"Lade Embedding-Modell: {MODEL_NAME}")
        _embed_model = SentenceTransformer(MODEL_NAME)
    return _embed_model


def get_chroma():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(CHROMADB_PATH)
    return _chroma_client


def simple_retrieve(question: str, skill: str, n: int = 12) -> list[dict]:
    """Einfache semantische Suche in ChromaDB für einen Skill.
    
    Two-pass retrieval: wenn gesetz_granular/norm-Chunks im Primary-Result fehlen,
    wird ein zweiter Query mit Filter auf Gesetzes-Typen gemacht (garantiert min. 2 Gesetz-Chunks).
    """
    try:
        col = get_chroma().get_collection(f"openlex_{skill}")
    except Exception as e:
        log.warning(f"  Collection nicht gefunden für {skill}: {e}")
        return []
    
    model = get_embed_model()
    emb = model.encode(question, normalize_embeddings=True).tolist()
    
    GESETZ_TYPES = {"gesetz_granular", "gesetz_norm", "voelkerrecht_vertrag"}
    
    def _query(where_filter=None, n_results=n):
        count = col.count()
        kwargs = dict(
            query_embeddings=[emb],
            n_results=min(n_results, count),
            include=["metadatas", "documents", "distances"],
        )
        if where_filter:
            kwargs["where"] = where_filter
        try:
            return col.query(**kwargs)
        except Exception as e:
            log.warning(f"  ChromaDB Query fehlgeschlagen: {e}")
            return None
    
    def _parse(results) -> list[dict]:
        if not results:
            return []
        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({"text": doc or "", "meta": meta or {}, "distance": dist})
        return chunks
    
    try:
        # Pass 1: Standard retrieval
        primary = _query()
        chunks = _parse(primary)
        
        # Pass 2: Wenn keine Gesetzes-Chunks in Top-N, erzwinge mind. 2
        GESETZ_SRC_KEYS = ("source_type", "chunk_type")
        has_gesetz = any(
            meta.get(k, "") in GESETZ_TYPES
            for meta in (primary["metadatas"][0] if primary else [])
            for k in GESETZ_SRC_KEYS
        )
        if not has_gesetz:
            gesetz_filter = {"$or": [
                {"source_type": {"$in": list(GESETZ_TYPES)}},
                {"chunk_type": {"$in": list(GESETZ_TYPES)}},
            ]}
            gesetz_results = _query(where_filter=gesetz_filter, n_results=3)
            gesetz_chunks = _parse(gesetz_results)
            if gesetz_chunks:
                log.debug(f"  Two-pass: +{len(gesetz_chunks)} Gesetz-Chunks für {skill}")
                # Merge: Top (n-len(gesetz)) from primary + gesetz chunks
                seen_texts = {c["text"] for c in gesetz_chunks}
                merged = [c for c in chunks if c["text"] not in seen_texts]
                merged = merged[: max(0, n - len(gesetz_chunks))] + gesetz_chunks
                chunks = sorted(merged, key=lambda x: x["distance"])
        
        return chunks
    except Exception as e:
        log.warning(f"  Retrieval fehlgeschlagen: {e}")
        return []



def _anthropic_call(messages: list[dict], model: str = "claude-sonnet-4-5", max_tokens: int = 500) -> str | None:
    """Direct Anthropic API call (fallback when OpenRouter is unavailable).
    Handles system messages correctly (Anthropic requires separate system param)."""
    if not ANTHROPIC_KEY:
        return None
    headers = {
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    # Anthropic API: system als separater Parameter, nicht in messages
    system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
    user_msgs = [m for m in messages if m["role"] != "system"]
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": user_msgs,
    }
    if system_msg:
        payload["system"] = system_msg
    try:
        r = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=90)
        r.raise_for_status()
        data = r.json()
        return data.get("content", [{}])[0].get("text", "")
    except Exception as e:
        log.warning(f"Anthropic call failed: {e}")
        return None

def _llm_call(messages: list[dict], model: str, max_tokens: int = 1500) -> str | None:
    """LLM Call — direkt via Anthropic (OpenRouter deaktiviert)."""
    # Use passed model (strip openrouter prefix if present)
    _model = model.replace("anthropic/", "") if model.startswith("anthropic/") else model
    return _anthropic_call(messages, _model, max_tokens)


def generate_answer(question: str, skill: str) -> tuple[str, list[dict]]:
    """Retrieval + LLM-Antwort für eine Frage."""
    chunks = simple_retrieve(question, skill, n=12)
    if not chunks:
        import logging as _logging
        _logging.getLogger("eval_llm").warning("No chunks retrieved for skill=%s q=%s", skill, question[:60])
        return "", []
    
    context_parts = []
    for i, ch in enumerate(chunks):
        text = ch["text"][:500]
        meta = ch["meta"]
        src_type = meta.get("source_type", "unbekannt")
        quelle = (
            meta.get("volladresse")
            or meta.get("gesetz")
            or meta.get("aktenzeichen")
            or meta.get("titel", "?")
        )
        context_parts.append(f"[Quelle {i+1}] ({src_type}) {quelle}:\n{text}")
    
    context = "\n\n".join(context_parts)
    
    messages = [
        {
            "role": "system",
            "content": (
                "Du bist ein deutschsprachiger Rechtsexperte. "
                "Beantworte die Frage NUR auf Basis der bereitgestellten Quellen. "
                "Zitiere Quellen mit [Quelle X]. "
                "Nenne relevante Paragraphen/Artikel. "
                "Antwort max. 300 Wörter."
            ),
        },
        {
            "role": "user",
            "content": f"Frage: {question}\n\nQuellen:\n{context}",
        },
    ]
    
    answer = _llm_call(messages, ANSWER_MODEL, max_tokens=600)
    return answer or "", chunks


def judge_answer(question: str, chunks: list[dict], answer: str,
                 expected_norms: list[str], expected_keywords: list[str]) -> dict:
    """Bewertet Antwort mit Judge-LLM + einfachen Regex-Checks."""
    if not answer:
        return {
            "hallucination": True,
            "hallucination_examples": ["Keine Antwort generiert"],
            "completeness": 0,
            "norm_presence": 0.0,
            "keyword_coverage": 0.0,
            "type_diversity": 0,
            "types_in_retrieval": [],
            "uses_all_types": False,
        }
    
    answer_lower = answer.lower()
    
    # 1. Norm-Präsenz (Regex, case-insensitive)
    norm_hits = sum(1 for n in expected_norms if n.lower() in answer_lower)
    norm_presence = norm_hits / max(1, len(expected_norms))
    
    # 2. Keyword-Coverage
    kw_hits = sum(1 for k in expected_keywords if k.lower() in answer_lower)
    keyword_coverage = kw_hits / max(1, len(expected_keywords))
    
    # 3. Chunk-Typ-Diversität
    types_used = set()
    for ch in chunks:
        st = ch.get("meta", {}).get("source_type", "")
        if st:
            types_used.add(st)
    type_diversity = len(types_used)
    
    # 4. Judge-LLM (Halluzination + Vollständigkeit)
    chunk_texts = "\n".join(
        f"[Quelle {i+1}]: {ch['text'][:800]}"
        for i, ch in enumerate(chunks)
    )
    
    judge_prompt = (
        f"Frage: {question}\n\n"
        f"Quellen:\n{chunk_texts}\n\n"
        f"Antwort:\n{answer[:1200]}\n\n"
        "Prüfe: Enthält die Antwort sachlich FALSCHE Behauptungen die den Quellen widersprechen? Eine Antwort ist KEINE Halluzination wenn sie nur unvollständig ist oder Infos fehlen. "
        "Ist die Antwort vollständig?\n"
        'Antworte NUR JSON: {"hallucination": false, "hallucination_examples": [], "completeness": 7}'
    )
    
    judge_resp = _llm_call(
        [{"role": "user", "content": judge_prompt}],
        JUDGE_MODEL, max_tokens=250
    )
    
    judge_data = {"hallucination": False, "hallucination_examples": [], "completeness": 5}
    if judge_resp:
        try:
            m = re.search(r'\{[^}]+\}', judge_resp, re.DOTALL)
            if m:
                parsed = json.loads(m.group(0))
                judge_data.update(parsed)
        except Exception:
            pass
    
    return {
        "hallucination": bool(judge_data.get("hallucination", False)),
        "hallucination_examples": judge_data.get("hallucination_examples", [])[:3],
        "completeness": int(judge_data.get("completeness", 5)),
        "norm_presence": round(norm_presence, 2),
        "keyword_coverage": round(keyword_coverage, 2),
        "type_diversity": type_diversity,
        "types_in_retrieval": sorted(types_used),
        "uses_all_types": type_diversity >= 2,
    }


def score_question(judge: dict) -> float:
    """Gesamt-Score 0-100."""
    type_score    = min(100.0, judge["type_diversity"] * 33)
    norm_score    = judge["norm_presence"] * 100
    kw_score      = judge["keyword_coverage"] * 100
    hall_score    = 0.0 if judge["hallucination"] else 100.0
    complete_score= judge["completeness"] * 10
    
    return round(
        type_score    * 0.25 +
        norm_score    * 0.25 +
        kw_score      * 0.20 +
        hall_score    * 0.20 +
        complete_score* 0.10,
        1
    )


def eval_skill(skill: str, questions: list[dict]) -> dict:
    """Layer-2-Eval für einen Skill."""
    t0 = time.time()
    q_results = []
    
    for q in questions:
        qt0 = time.time()
        question_text = q.get("question", "")
        if not question_text:
            continue
        
        log.info(f"    [{skill}] Q{q.get('id', '?')}: {question_text[:65]}...")
        
        answer, chunks = generate_answer(question_text, skill)
        
        if not answer:
            q_results.append({
                "id": q.get("id"), "question": question_text,
                "category": q.get("category", ""), "score": 0.0,
                "error": "Keine Antwort", "duration_s": round(time.time()-qt0, 1),
            })
            continue
        
        judge = judge_answer(
            question_text, chunks, answer,
            q.get("expected_norms", []), q.get("expected_keywords", []),
        )
        score = score_question(judge)
        
        q_results.append({
            "id": q.get("id"),
            "question": question_text,
            "category": q.get("category", ""),
            "score": score,
            "answer_excerpt": answer[:200],
            "n_chunks": len(chunks),
            "judge": judge,
            "duration_s": round(time.time()-qt0, 1),
        })
        
        time.sleep(0.3)
    
    scores = [r["score"] for r in q_results if "error" not in r]
    avg_score = round(sum(scores)/len(scores), 1) if scores else 0.0
    hall_count = sum(1 for r in q_results if r.get("judge", {}).get("hallucination", False))
    
    return {
        "skill": skill,
        "n_questions": len(q_results),
        "avg_score": avg_score,
        "hallucination_rate": round(hall_count/max(1,len(q_results))*100, 1),
        "worst_score": min(scores) if scores else 0,
        "best_score": max(scores) if scores else 0,
        "questions": q_results,
        "duration_s": round(time.time()-t0, 1),
    }


def run(skills: list[str] | None = None, ntfy_fn=None, questions_dir: Path | None = None) -> dict:
    qdir = questions_dir or QUESTIONS_DIR
    if skills is None:
        skills = sorted([f.stem for f in QUESTIONS_DIR.glob("*.json")])
    
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    all_results = []
    total = len(skills)
    
    for i, skill in enumerate(skills, 1):
        qfile = QUESTIONS_DIR / f"{skill}.json"
        if not qfile.exists():
            log.warning(f"  {skill}: Keine Fragen-Datei, überspringe")
            continue
        try:
            questions = json.loads(qfile.read_text())  # alle Fragen (kein Limit)
        except Exception as e:
            log.warning(f"  {skill}: Laden fehlgeschlagen: {e}")
            continue
        
        log.info(f"Layer-2: {skill} ({i}/{total}, {len(questions)} Fragen)")
        res = eval_skill(skill, questions)
        all_results.append(res)
        
        log.info(f"  ✓ {skill}: Ø={res['avg_score']} | Hall={res['hallucination_rate']}% | {res['duration_s']}s")
        if ntfy_fn:
            ntfy_fn(f"✅ L2 {skill}: {res['avg_score']} Pkt | {i}/{total} Skills")
    
    out_file = RESULTS_DIR / f"llm_{ts}.json"
    out_file.write_text(json.dumps(all_results, ensure_ascii=False, indent=2))
    log.info(f"Layer-2-Ergebnisse: {out_file}")
    
    avg = round(sum(r["avg_score"] for r in all_results)/max(1,len(all_results)), 1)
    log.info(f"Ø L2-Score: {avg}")
    return {"results": all_results, "output_file": str(out_file), "avg_score": avg}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", help="Nur diesen Skill evaluieren")
    parser.add_argument("--questions-dir", help="Alternatives Fragen-Verzeichnis", default=None)
    args = parser.parse_args()
    qdir = Path(args.questions_dir) if args.questions_dir else None
    run([args.skill] if args.skill else None, questions_dir=qdir)
