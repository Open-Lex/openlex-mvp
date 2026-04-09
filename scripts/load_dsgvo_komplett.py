#!/usr/bin/env python3
"""
load_dsgvo_komplett.py – Erstellt Chunks aus den gecrawlten DSGVO-Artikeln
und Erwägungsgründen und lädt sie in ChromaDB.

Schritte 3-5 des DSGVO-Reload-Plans.
"""

from __future__ import annotations

import json
import os
import re
import sys

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.expanduser("~/openlex-mvp")
ART_DIR = os.path.join(BASE_DIR, "data", "dsgvo_komplett", "artikel")
EG_DIR = os.path.join(BASE_DIR, "data", "dsgvo_komplett", "erwaegungsgruende")
EMBED_MODEL = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"
PROGRESS_FILE = os.path.join(BASE_DIR, "dsgvo_reload_progress.json")


def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_progress(data: dict):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_querverweise_text(eg_list: list, bdsg_list: list) -> str:
    """Baut den Querverweise-Anhang für Artikel-Chunks."""
    parts = []
    if eg_list:
        eg_str = ", ".join(f"EG {e['nr']} ({e['titel']})" for e in eg_list)
        parts.append(f"Passende Erwägungsgründe: {eg_str}")
    if bdsg_list:
        bdsg_str = ", ".join(
            f"{b['paragraph']} BDSG ({b['titel']})" if b.get("titel")
            else f"{b['paragraph']} BDSG"
            for b in bdsg_list
        )
        parts.append(f"Passende BDSG-Normen: {bdsg_str}")
    if parts:
        return "\n--- Querverweise ---\n" + "\n".join(parts)
    return ""


def split_article_at_absaetze(text: str, max_size: int = 4000) -> list[str]:
    """Teilt Artikeltext an Absatz-Grenzen (1), (2), (3) etc."""
    if len(text) <= max_size:
        return [text]

    # Finde Absätze: Zeilen die mit (N) beginnen
    abs_pattern = re.compile(r"^(\(\d+\))", re.MULTILINE)
    matches = list(abs_pattern.finditer(text))

    if len(matches) < 2:
        # Kein sinnvoller Split möglich – an Satzgrenzen splitten
        return split_at_sentences(text, max_size)

    chunks = []
    current_start = 0

    for i, m in enumerate(matches):
        # Prüfe ob der aktuelle Block zu groß wird
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        current_block = text[current_start:next_start]

        if len(current_block) > max_size and current_start < m.start():
            # Speichere bisherigen Block und starte neuen
            chunk = text[current_start:m.start()].strip()
            if chunk:
                chunks.append(chunk)
            current_start = m.start()

    # Letzten Block hinzufügen
    last = text[current_start:].strip()
    if last:
        chunks.append(last)

    # Falls einzelne Chunks immer noch zu groß, nochmal splitten
    result = []
    for c in chunks:
        if len(c) > max_size:
            result.extend(split_at_sentences(c, max_size))
        else:
            result.append(c)

    return result


def split_at_sentences(text: str, max_size: int = 4000) -> list[str]:
    """Fallback: Splittet an Satzgrenzen."""
    if len(text) <= max_size:
        return [text]

    chunks = []
    pos = 0
    while pos < len(text):
        if len(text) - pos <= max_size:
            chunks.append(text[pos:].strip())
            break

        # Suche Satzende in der Nähe von max_size
        target = pos + max_size - 200
        best = pos + max_size
        for m in re.finditer(r"\.\s+", text[target:pos + max_size]):
            best = target + m.end()
            break

        chunks.append(text[pos:best].strip())
        pos = best

    return [c for c in chunks if c]


def create_article_chunks() -> list[dict]:
    """Erstellt Chunks aus allen DSGVO-Artikeln."""
    all_chunks = []

    for art_nr in range(1, 100):
        art_file = os.path.join(ART_DIR, f"art_{art_nr}.json")
        if not os.path.exists(art_file):
            continue

        with open(art_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        artikel = data["artikel"]
        titel = data.get("titel", "")
        kapitel = data.get("kapitel", "")
        text = data.get("text", "")
        eg_list = data.get("passende_erwaegungsgruende", [])
        bdsg_list = data.get("passende_bdsg", [])

        if not text or len(text) < 20:
            print(f"  SKIP Art. {art_nr}: kein Text")
            continue

        # Art. 4: Nicht splitten – MW-Chunk existiert bereits separat
        if art_nr == 4:
            # Trotzdem einen gesetz_granular Chunk erstellen mit Querverweisen
            querverweise = build_querverweise_text(eg_list, bdsg_list)
            header = f"Art. 4 DSGVO – {titel}\n\n"
            chunk_text = header + text + querverweise

            all_chunks.append({
                "chroma_id": "dsgvo_art_4",
                "text": chunk_text,
                "meta": {
                    "source_type": "gesetz_granular",
                    "gesetz": "DSGVO",
                    "artikel": "Art. 4",
                    "titel": titel,
                    "kapitel": kapitel,
                    "volladresse": "Art. 4 DSGVO",
                    "erwaegungsgruende": ",".join(str(e["nr"]) for e in eg_list),
                    "bdsg_verweise": ", ".join(f"{b['paragraph']} BDSG" for b in bdsg_list),
                },
            })
            continue

        # Header + Querverweise
        header = f"{artikel} DSGVO – {titel}\n\n"
        querverweise = build_querverweise_text(eg_list, bdsg_list)

        # Splitten wenn nötig
        text_parts = split_article_at_absaetze(text, max_size=4000)

        if len(text_parts) == 1:
            chunk_text = header + text_parts[0] + querverweise
            chroma_id = f"dsgvo_art_{art_nr}"

            all_chunks.append({
                "chroma_id": chroma_id,
                "text": chunk_text,
                "meta": {
                    "source_type": "gesetz_granular",
                    "gesetz": "DSGVO",
                    "artikel": artikel,
                    "titel": titel,
                    "kapitel": kapitel,
                    "volladresse": f"{artikel} DSGVO",
                    "erwaegungsgruende": ",".join(str(e["nr"]) for e in eg_list),
                    "bdsg_verweise": ", ".join(f"{b['paragraph']} BDSG" for b in bdsg_list),
                },
            })
        else:
            for idx, part in enumerate(text_parts):
                chunk_text = header + part + querverweise
                chroma_id = f"dsgvo_art_{art_nr}_part{idx}"

                all_chunks.append({
                    "chroma_id": chroma_id,
                    "text": chunk_text,
                    "meta": {
                        "source_type": "gesetz_granular",
                        "gesetz": "DSGVO",
                        "artikel": artikel,
                        "titel": titel,
                        "kapitel": kapitel,
                        "volladresse": f"{artikel} DSGVO (Teil {idx + 1})",
                        "erwaegungsgruende": ",".join(str(e["nr"]) for e in eg_list),
                        "bdsg_verweise": ", ".join(f"{b['paragraph']} BDSG" for b in bdsg_list),
                    },
                })

    return all_chunks


def create_eg_chunks() -> list[dict]:
    """Erstellt Chunks aus allen Erwägungsgründen."""
    # Baue Reverse-Mapping: EG-Nr → passende Artikel (aus den Artikel-Daten)
    eg_to_articles: dict[int, list[str]] = {}
    for art_nr in range(1, 100):
        art_file = os.path.join(ART_DIR, f"art_{art_nr}.json")
        if not os.path.exists(art_file):
            continue
        with open(art_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for eg in data.get("passende_erwaegungsgruende", []):
            eg_nr = eg["nr"]
            if eg_nr not in eg_to_articles:
                eg_to_articles[eg_nr] = []
            art_ref = f"Art. {art_nr}"
            if art_ref not in eg_to_articles[eg_nr]:
                eg_to_articles[eg_nr].append(art_ref)

    all_chunks = []

    for eg_nr in range(1, 174):
        eg_file = os.path.join(EG_DIR, f"eg_{eg_nr}.json")
        if not os.path.exists(eg_file):
            continue

        with open(eg_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        titel = data.get("titel", "")
        text = data.get("text", "")
        # Use reverse-mapped articles (more complete) or from EG file
        passende = data.get("passende_artikel", [])
        if eg_nr in eg_to_articles:
            passende = eg_to_articles[eg_nr]

        if not text or len(text) < 20:
            print(f"  SKIP EG {eg_nr}: kein Text")
            continue

        header = f"Erwägungsgrund {eg_nr} DSGVO – {titel}\n\n"
        qv = ""
        if passende:
            qv = f"\n--- Querverweise ---\nPassende DSGVO-Artikel: {', '.join(passende)}"

        # Splitten wenn >4000
        if len(header + text + qv) <= 4000:
            chunk_text = header + text + qv
            chroma_id = f"dsgvo_eg_{eg_nr}"

            all_chunks.append({
                "chroma_id": chroma_id,
                "text": chunk_text,
                "meta": {
                    "source_type": "erwaegungsgrund",
                    "gesetz": "DSGVO",
                    "eg_nr": eg_nr,
                    "titel": titel,
                    "passende_artikel": ", ".join(passende) if passende else "",
                },
            })
        else:
            parts = split_at_sentences(text, max_size=3500)
            for idx, part in enumerate(parts):
                chunk_text = header + part + qv
                chroma_id = f"dsgvo_eg_{eg_nr}_{idx}"

                all_chunks.append({
                    "chroma_id": chroma_id,
                    "text": chunk_text,
                    "meta": {
                        "source_type": "erwaegungsgrund",
                        "gesetz": "DSGVO",
                        "eg_nr": eg_nr,
                        "titel": titel,
                        "passende_artikel": ", ".join(passende) if passende else "",
                    },
                })

    return all_chunks


def main():
    progress = load_progress()

    # SCHRITT 3: Artikel-Chunks
    print("=" * 60)
    print("SCHRITT 3: DSGVO-Artikel-Chunks erstellen")
    print("=" * 60)

    art_chunks = create_article_chunks()
    print(f"  {len(art_chunks)} Artikel-Chunks erstellt")

    # SCHRITT 4: EG-Chunks
    print("\n" + "=" * 60)
    print("SCHRITT 4: Erwägungsgrund-Chunks erstellen")
    print("=" * 60)

    eg_chunks = create_eg_chunks()
    print(f"  {len(eg_chunks)} Erwägungsgrund-Chunks erstellt")

    all_chunks = art_chunks + eg_chunks
    print(f"\n  GESAMT: {len(all_chunks)} Chunks")

    # SCHRITT 5: Embedden
    print("\n" + "=" * 60)
    print("SCHRITT 5: Embedden und in ChromaDB laden")
    print("=" * 60)

    print(f"  Lade Model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)

    client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chromadb"))
    col = client.get_collection("openlex_datenschutz")

    existing = set(col.get(include=[])["ids"])

    ids_to_add = []
    docs_to_add = []
    metas_to_add = []
    embed_texts = []

    for chunk in all_chunks:
        cid = chunk["chroma_id"]
        if cid in existing:
            continue

        # Embedding prefix
        st = chunk["meta"]["source_type"]
        if st == "erwaegungsgrund":
            prefix = "Erwägungsgrund DSGVO: "
        else:
            prefix = "Gesetzestext DSGVO: "

        ids_to_add.append(cid)
        docs_to_add.append(chunk["text"])
        metas_to_add.append(chunk["meta"])
        embed_texts.append(prefix + chunk["text"])

    print(f"  Neue Chunks: {len(ids_to_add)} (von {len(all_chunks)} gesamt)")

    if not ids_to_add:
        print("  Keine neuen Chunks!")
        return

    print(f"  Embedde {len(ids_to_add)} Chunks...")
    BATCH = 64
    all_embeddings = []
    for i in range(0, len(embed_texts), BATCH):
        batch = embed_texts[i:i + BATCH]
        embs = model.encode(batch, normalize_embeddings=True).tolist()
        all_embeddings.extend(embs)
        done = min(i + BATCH, len(embed_texts))
        print(f"    {done}/{len(embed_texts)} embedded", end="\r")
    print()

    # Add to ChromaDB in batches
    ADD_BATCH = 500
    for i in range(0, len(ids_to_add), ADD_BATCH):
        end = min(i + ADD_BATCH, len(ids_to_add))
        col.add(
            ids=ids_to_add[i:end],
            documents=docs_to_add[i:end],
            metadatas=metas_to_add[i:end],
            embeddings=all_embeddings[i:end],
        )

    print(f"\n  ✓ {len(ids_to_add)} Chunks in ChromaDB geladen")
    print(f"  ChromaDB gesamt: {col.count()}")

    # Verify
    for st in ["gesetz_granular", "erwaegungsgrund"]:
        r = col.get(where={"source_type": st}, include=["metadatas"], limit=50000)
        dsgvo = sum(1 for m in r["metadatas"] if m.get("gesetz") == "DSGVO")
        print(f"  DSGVO {st}: {dsgvo}")

    # Save progress
    progress["schritt_3"] = {"status": "done", "artikel_chunks": len(art_chunks)}
    progress["schritt_4"] = {"status": "done", "eg_chunks": len(eg_chunks)}
    progress["schritt_5"] = {
        "status": "done",
        "total_embedded": len(ids_to_add),
        "chromadb_total": col.count(),
    }
    save_progress(progress)


if __name__ == "__main__":
    main()
