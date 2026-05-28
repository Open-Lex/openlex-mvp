#!/usr/bin/env python3
"""
eval_retrieval.py — Layer 1: Retrieval-Diagnose für alle Skills.
Prüft Chunk-Typ-Coverage in ChromaDB und bei echten Queries.
"""
import json, sys, time, logging
from pathlib import Path
from datetime import datetime
import chromadb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [L1] %(message)s")
log = logging.getLogger(__name__)

CHROMADB_PATH = "/opt/openlex-mvp-v2/chromadb"
QUESTIONS_DIR = Path("/opt/openlex-sources/eval/questions")
RESULTS_DIR   = Path("/opt/openlex-sources/eval/results")
APP_PATH      = "/opt/openlex-mvp-v2"
MODEL_NAME    = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"

_embed_model = None

def get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        log.info(f"Lade Embedding-Modell: {MODEL_NAME}")
        _embed_model = SentenceTransformer(MODEL_NAME)
    return _embed_model


def embed_query(text: str) -> list[float]:
    model = get_embed_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def inventory_collection(col) -> dict:
    """Zählt Chunks pro source_type in der Collection."""
    total = col.count()
    if total == 0:
        return {}
    
    types = {}
    offset = 0
    batch_size = 5000
    while True:
        r = col.get(limit=batch_size, offset=offset, include=["metadatas"])
        if not r["ids"]:
            break
        for m in r["metadatas"]:
            st = m.get("source_type", "unknown")
            types[st] = types.get(st, 0) + 1
        offset += len(r["ids"])
        if len(r["ids"]) < batch_size:
            break
    return types


def query_coverage(col, questions: list[dict], available_types: set) -> dict:
    """Simuliert Queries mit Embedding und prüft Chunk-Typ-Coverage."""
    if not questions or not available_types:
        return {"coverage_rate": 0.0, "n_queries": 0, "details": []}
    
    # Erwarte die häufigsten Typen (top-3 nach Anzahl)
    # Wir prüfen ob bei einer Query mindestens 2 verschiedene Typen zurückkommen
    test_qs = questions[:5]
    details = []
    covered = 0
    
    for q in test_qs:
        question_text = q.get("question", "")
        if not question_text:
            continue
        
        try:
            emb = embed_query(question_text)
            n = min(10, col.count())
            results = col.query(
                query_embeddings=[emb],
                n_results=n,
                include=["metadatas"]
            )
            returned_types = set(
                m.get("source_type", "unknown")
                for m in results["metadatas"][0]
            )
            # Coverage: mindestens 2 verschiedene Typen in Top-10?
            is_covered = len(returned_types) >= 2
            if is_covered:
                covered += 1
            
            details.append({
                "question": question_text[:80],
                "returned_types": sorted(returned_types),
                "n_types": len(returned_types),
                "covered": is_covered,
            })
        except Exception as e:
            details.append({
                "question": question_text[:80],
                "error": str(e)[:100],
                "covered": False,
            })
    
    n = len(test_qs)
    return {
        "coverage_rate": round(covered / n * 100, 1) if n > 0 else 0.0,
        "n_queries": n,
        "n_covered": covered,
        "details": details,
    }


def eval_skill(client, skill: str) -> dict:
    """Vollständige Layer-1-Diagnose für einen Skill."""
    t0 = time.time()
    result = {
        "skill": skill,
        "timestamp": datetime.now().isoformat(),
        "collection_count": 0,
        "type_inventory": {},
        "n_distinct_types": 0,
        "query_coverage": {},
        "l1_score": 0.0,
        "issues": [],
    }
    
    try:
        col = client.get_collection(f"openlex_{skill}")
    except Exception as e:
        result["issues"].append(f"Collection nicht gefunden: {e}")
        return result
    
    # A) Inventory
    inv = inventory_collection(col)
    result["collection_count"] = col.count()
    result["type_inventory"] = inv
    result["n_distinct_types"] = len(inv)
    
    available = set(inv.keys())
    
    # Prüfe Mindest-Anforderungen
    if "gesetz_granular" not in available and "gesetz" not in available and "gesetz_norm" not in available:
        result["issues"].append("Keine Gesetzes-Chunks (gesetz_granular/gesetz) vorhanden!")
    
    urteil_types = {"urteil_segmentiert", "urteil", "eugh_urteil"}
    if not available.intersection(urteil_types) and result["collection_count"] > 200:
        result["issues"].append("Keine Urteils-Chunks vorhanden (urteil_segmentiert/urteil)")
    
    if result["collection_count"] < 50:
        result["issues"].append(f"Sehr wenige Chunks ({result['collection_count']}) — Datenbasis prüfen")
    
    # B) Query Coverage (nur wenn Fragen vorhanden und Embedding-Modell)
    qfile = QUESTIONS_DIR / f"{skill}.json"
    questions = []
    if qfile.exists():
        try:
            questions = json.loads(qfile.read_text())
        except Exception:
            pass
    
    if questions and result["collection_count"] > 0:
        cov = query_coverage(col, questions, available)
        result["query_coverage"] = cov
    else:
        result["query_coverage"] = {"coverage_rate": 0.0, "n_queries": 0, "note": "Keine Fragen vorhanden"}
    
    # C) L1-Score berechnen
    # 40% Typen-Vielfalt (≥3 Typen = 100%)
    type_score = min(100, result["n_distinct_types"] * 33)
    
    # 30% Keine kritischen Issues
    issue_score = max(0, 100 - len(result["issues"]) * 50)
    
    # 30% Query-Coverage-Rate
    coverage_rate = result["query_coverage"].get("coverage_rate", 0.0)
    
    result["l1_score"] = round(type_score * 0.4 + issue_score * 0.3 + coverage_rate * 0.3, 1)
    result["duration_s"] = round(time.time() - t0, 1)
    
    n_types = result["n_distinct_types"]
    log.info(f"  {skill}: L1={result['l1_score']}% | {n_types} Typen | Coverage: {coverage_rate}% | Issues: {len(result['issues'])}")
    return result


def run(skills: list[str] | None = None) -> dict:
    """Führt Layer-1-Eval für alle/ausgewählte Skills durch."""
    client = chromadb.PersistentClient(CHROMADB_PATH)
    
    if skills is None:
        skills = [col.name.replace("openlex_", "") for col in client.list_collections()]
    
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    all_results = []
    
    for skill in sorted(skills):
        log.info(f"Layer-1: {skill}")
        res = eval_skill(client, skill)
        all_results.append(res)
    
    # Speichern
    out_file = RESULTS_DIR / f"retrieval_{ts}.json"
    out_file.write_text(json.dumps(all_results, ensure_ascii=False, indent=2))
    log.info(f"Layer-1-Ergebnisse: {out_file}")
    
    avg_score = sum(r["l1_score"] for r in all_results) / len(all_results) if all_results else 0
    log.info(f"Ø L1-Score: {avg_score:.1f}%")
    
    return {"results": all_results, "output_file": str(out_file), "avg_score": avg_score}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", help="Nur diesen Skill evaluieren")
    args = parser.parse_args()
    skills = [args.skill] if args.skill else None
    run(skills)
