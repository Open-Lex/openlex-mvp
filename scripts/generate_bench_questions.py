#!/usr/bin/env python3
"""
generate_bench_questions.py – Generiert Ground-Truth-Fragen aus ChromaDB-Chunks.

Einmalig ausführen (braucht LLM):
    python3 generate_bench_questions.py

Erzeugt: bench_questions.json
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

CHROMADB_DIR = str(BASE_DIR / "chromadb")
COLLECTION_NAME = "openlex_datenschutz"
OUTPUT_FILE = BASE_DIR / "bench_questions.json"
URTEILSNAMEN_FILE = BASE_DIR / "data" / "urteilsnamen.json"

# Wichtige DSGVO-Artikel für Benchmark
IMPORTANT_ARTICLES = (
    list(range(5, 10)) + list(range(12, 23)) + list(range(24, 29))
    + list(range(32, 40)) + list(range(44, 50)) + list(range(77, 85))
)


def _get_llm_response(prompt: str) -> str:
    """Ruft das LLM über stream_with_fallback auf."""
    from app import stream_with_fallback
    messages = [
        {"role": "system", "content": "Du generierst Testfragen für ein Datenschutz-Retrieval-System. "
                                       "Antworte ausschließlich im geforderten JSON-Format, ohne Erklärungen."},
        {"role": "user", "content": prompt},
    ]
    response = ""
    for token, _ in stream_with_fallback(messages):
        response += token
    return response.strip()


def _parse_json_from_response(text: str) -> list[dict]:
    """Extrahiert JSON-Array aus LLM-Antwort (tolerant)."""
    # Suche nach [...] Block
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    # Fallback: Versuche ganzen Text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return []


def generate_mw_questions(col) -> list[dict]:
    """Generiert Fragen für Methodenwissen-Chunks."""
    print("\n=== Methodenwissen-Chunks ===")
    r = col.get(include=["metadatas", "documents"], limit=5000,
                where={"source_type": "methodenwissen"})

    questions = []
    total = len(r["ids"])

    # Batch: 5 Chunks pro LLM-Aufruf
    batch_size = 5
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_chunks = []
        for i in range(batch_start, batch_end):
            thema = r["metadatas"][i].get("thema", "")
            text_preview = r["documents"][i][:300]
            cid = r["ids"][i]
            batch_chunks.append({"id": cid, "thema": thema, "text": text_preview})

        chunk_descriptions = "\n\n".join(
            f"Chunk {j+1} (ID: {c['id']}):\nThema: {c['thema']}\nText: {c['text']}..."
            for j, c in enumerate(batch_chunks)
        )

        prompt = f"""Für folgende {len(batch_chunks)} Methodenwissen-Chunks, generiere pro Chunk genau 2 Fragen:
- Frage 1: In Juristensprache (formal, mit Normbezügen)
- Frage 2: In Alltagssprache (wie ein Laie fragen würde)

{chunk_descriptions}

Antworte als JSON-Array:
[{{"chunk_id": "...", "question_jurist": "...", "question_alltag": "..."}}]"""

        print(f"  Batch {batch_start//batch_size + 1}/{(total + batch_size - 1)//batch_size} "
              f"({len(batch_chunks)} Chunks)...", end="", flush=True)

        try:
            resp = _get_llm_response(prompt)
            items = _parse_json_from_response(resp)
            for item in items:
                cid = item.get("chunk_id", "")
                if not cid:
                    continue
                # Juristenfrage
                if item.get("question_jurist"):
                    questions.append({
                        "question": item["question_jurist"],
                        "expected_chunk_ids": [cid],
                        "expected_source_types": ["methodenwissen"],
                        "style": "juristensprache",
                        "category": "methodenwissen",
                    })
                # Alltagsfrage
                if item.get("question_alltag"):
                    questions.append({
                        "question": item["question_alltag"],
                        "expected_chunk_ids": [cid],
                        "expected_source_types": ["methodenwissen"],
                        "style": "alltagssprache",
                        "category": "methodenwissen",
                    })
            print(f" {len(items)} Chunks → {len(items)*2} Fragen")
        except Exception as e:
            print(f" Fehler: {e}")

        time.sleep(1)  # Rate-Limiting

    print(f"  → {len(questions)} MW-Fragen generiert")
    return questions


def generate_dsgvo_questions(col) -> list[dict]:
    """Generiert Fragen für wichtige DSGVO-Artikel."""
    print("\n=== DSGVO-Artikel ===")

    questions = []
    # Sammle Chunks pro Artikel
    articles = {}
    r = col.get(include=["metadatas", "documents"], limit=5000,
                where={"source_type": "gesetz_granular"})

    for i, cid in enumerate(r["ids"]):
        if "DSGVO" not in cid:
            continue
        m = re.search(r"Art\._(\d+)", cid)
        if not m:
            continue
        art_nr = int(m.group(1))
        if art_nr not in IMPORTANT_ARTICLES:
            continue
        if art_nr not in articles:
            articles[art_nr] = {"ids": [], "texts": []}
        articles[art_nr]["ids"].append(cid)
        articles[art_nr]["texts"].append(r["documents"][i][:200])

    # Batch: 10 Artikel pro LLM-Aufruf
    art_list = sorted(articles.keys())
    batch_size = 10
    for batch_start in range(0, len(art_list), batch_size):
        batch_arts = art_list[batch_start:batch_start + batch_size]
        art_descriptions = "\n\n".join(
            f"Art. {a} DSGVO (Chunks: {', '.join(articles[a]['ids'][:3])}):\n"
            f"{articles[a]['texts'][0][:200]}..."
            for a in batch_arts
        )

        prompt = f"""Für folgende {len(batch_arts)} DSGVO-Artikel, generiere pro Artikel 1-2 Fragen:
- Mindestens 1 Frage in Alltagssprache
- Optional 1 Frage in Juristensprache (bei komplexen Artikeln)

{art_descriptions}

Antworte als JSON-Array:
[{{"article": 5, "questions": [{{"question": "...", "style": "alltagssprache"}}]}}]"""

        print(f"  Batch Art. {batch_arts[0]}-{batch_arts[-1]}...", end="", flush=True)

        try:
            resp = _get_llm_response(prompt)
            items = _parse_json_from_response(resp)
            for item in items:
                art_nr = item.get("article")
                if not art_nr or art_nr not in articles:
                    continue
                for q in item.get("questions", []):
                    questions.append({
                        "question": q["question"],
                        "expected_chunk_ids": articles[art_nr]["ids"][:3],
                        "expected_source_types": ["gesetz_granular"],
                        "style": q.get("style", "alltagssprache"),
                        "category": f"dsgvo_art_{art_nr}",
                    })
            print(f" {sum(len(i.get('questions',[])) for i in items)} Fragen")
        except Exception as e:
            print(f" Fehler: {e}")

        time.sleep(1)

    print(f"  → {len(questions)} DSGVO-Fragen generiert")
    return questions


def generate_urteil_questions(col) -> list[dict]:
    """Generiert Fragen für Schlüsselurteile mit bekannten Namen."""
    print("\n=== Schlüsselurteile ===")

    if not URTEILSNAMEN_FILE.exists():
        print("  Keine urteilsnamen.json gefunden – überspringe")
        return []

    with open(URTEILSNAMEN_FILE, "r", encoding="utf-8") as f:
        namen = json.load(f)

    # Nur Urteile mit Namen
    named = {az: name for az, name in namen.items() if name}
    print(f"  {len(named)} Urteile mit Namen")

    questions = []
    az_list = list(named.items())

    # Batch: 15 Urteile pro LLM-Aufruf
    batch_size = 15
    for batch_start in range(0, len(az_list), batch_size):
        batch = az_list[batch_start:batch_start + batch_size]
        urteil_descriptions = "\n".join(
            f"- {az} ({name})" for az, name in batch
        )

        prompt = f"""Für folgende {len(batch)} EuGH/BGH-Urteile, generiere pro Urteil genau 1 Frage die dieses Urteil als Antwort finden sollte. Die Frage soll sich auf das Thema des Urteils beziehen, NICHT einfach das Aktenzeichen nennen.

{urteil_descriptions}

Antworte als JSON-Array:
[{{"aktenzeichen": "C-131/12", "question": "Unter welchen Voraussetzungen..."}}]"""

        print(f"  Batch {batch_start//batch_size + 1}...", end="", flush=True)

        try:
            resp = _get_llm_response(prompt)
            items = _parse_json_from_response(resp)
            for item in items:
                az = item.get("aktenzeichen", "")
                q = item.get("question", "")
                if not az or not q:
                    continue
                # Finde passende Chunk-IDs in ChromaDB
                try:
                    search = col.get(
                        where_document={"$contains": az},
                        include=[], limit=3,
                    )
                    chunk_ids = search["ids"] if search["ids"] else [az]
                except Exception:
                    chunk_ids = [az]

                questions.append({
                    "question": q,
                    "expected_chunk_ids": chunk_ids,
                    "expected_source_types": ["urteil", "urteil_segmentiert"],
                    "style": "juristensprache",
                    "category": "urteil",
                })
            print(f" {len(items)} Fragen")
        except Exception as e:
            print(f" Fehler: {e}")

        time.sleep(1)

    print(f"  → {len(questions)} Urteils-Fragen generiert")
    return questions


def main():
    import chromadb
    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    col = client.get_collection(COLLECTION_NAME)

    print("=" * 60)
    print("  Ground-Truth-Fragen generieren")
    print("=" * 60)
    print(f"ChromaDB: {col.count()} Chunks")

    all_questions = []

    # 1) Methodenwissen
    mw_qs = generate_mw_questions(col)
    all_questions.extend(mw_qs)

    # 2) DSGVO-Artikel
    dsgvo_qs = generate_dsgvo_questions(col)
    all_questions.extend(dsgvo_qs)

    # 3) Schlüsselurteile
    urteil_qs = generate_urteil_questions(col)
    all_questions.extend(urteil_qs)

    # IDs vergeben
    for i, q in enumerate(all_questions, 1):
        q["id"] = i

    # Speichern
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_questions, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  {len(all_questions)} Fragen generiert")
    print(f"  - Methodenwissen: {len(mw_qs)}")
    print(f"  - DSGVO-Artikel:  {len(dsgvo_qs)}")
    print(f"  - Urteile:        {len(urteil_qs)}")
    print(f"\n  Gespeichert: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
