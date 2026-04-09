#!/usr/bin/env python3
"""
add_ki_docs.py – Lädt KI-Datenschutz-Dokumente herunter und embeddet sie in ChromaDB.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import requests

BASE_DIR = os.path.expanduser("~/openlex-mvp")
LEITLINIEN_DIR = os.path.join(BASE_DIR, "data", "leitlinien")
CHROMADB_DIR = os.path.join(BASE_DIR, "chromadb")
COLLECTION_NAME = "openlex_datenschutz"
MODEL_NAME = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"

sys.path.insert(0, BASE_DIR)
from refine_behoerden import segment_document, extract_themen, sanitize, find_verweise

DOWNLOADS = [
    {
        "url": "https://www.edpb.europa.eu/system/files/2024-12/edpb_opinion_202428_ai-models_en.pdf",
        "titel": "EDPB Opinion 28/2024 on certain data protection aspects related to AI models",
        "datum": "2024-12-17",
        "quelle": "edpb",
        "typ": "stellungnahme",
        "sprache": "en",
        "json_name": "EDPB_Opinion_28_2024_AI_Models.json",
    },
    {
        "url": "https://www.edpb.europa.eu/system/files/2024-05/edpb_20240523_report_chatgpt_taskforce_en.pdf",
        "titel": "EDPB Report of the work undertaken by the ChatGPT Taskforce",
        "datum": "2024-05-23",
        "quelle": "edpb",
        "typ": "bericht",
        "sprache": "en",
        "json_name": "EDPB_ChatGPT_Taskforce_Report.json",
    },
    {
        "url": "https://www.lda.bayern.de/media/ki_checkliste.pdf",
        "titel": "BayLDA Checkliste Datenschutzkonforme Künstliche Intelligenz",
        "datum": "2024",
        "quelle": "baylda",
        "typ": "checkliste",
        "sprache": "de",
        "json_name": "BayLDA_KI_Checkliste.json",
    },
    {
        "url": "https://www.baden-wuerttemberg.datenschutz.de/wp-content/uploads/2024/10/Rechtsgrundlagen-KI-v2.0.pdf",
        "titel": "LfDI BW Diskussionspapier Rechtsgrundlagen im Datenschutz beim Einsatz von KI (Version 2.0)",
        "datum": "2024-10",
        "quelle": "lfdi_bw",
        "typ": "diskussionspapier",
        "sprache": "de",
        "json_name": "LfDI_BW_Rechtsgrundlagen_KI_v2.json",
    },
    {
        "url": "https://www.datenschutzkonferenz-online.de/media/dskb/20240503_DSK_Positionspapier_Zustaendigkeiten_KI_VO.pdf",
        "titel": "DSK Positionspapier zu nationalen Zuständigkeiten für die KI-Verordnung",
        "datum": "2024-05-03",
        "quelle": "dsk",
        "typ": "positionspapier",
        "sprache": "de",
        "json_name": "DSK_Positionspapier_KI_VO.json",
    },
]


def download_pdf(url: str) -> bytes | None:
    print(f"  Lade {url.split('/')[-1][:60]} ...", end="", flush=True)
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent": "OpenLex/1.0"})
        r.raise_for_status()
        print(f" OK ({len(r.content) / 1024:.0f} KB)")
        return r.content
    except Exception as e:
        print(f" FEHLER: {e}")
        return None


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        if text.strip():
            return text.strip()
    except ImportError:
        pass
    try:
        import pdfplumber
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            tmp_path = f.name
        text = ""
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        os.unlink(tmp_path)
        if text.strip():
            return text.strip()
    except ImportError:
        pass
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        import io
        text = pdfminer_extract(io.BytesIO(pdf_bytes))
        if text.strip():
            return text.strip()
    except ImportError:
        pass
    return ""


def main():
    print("=" * 60)
    print("  KI-Datenschutz-Dokumente herunterladen & embedden")
    print("=" * 60)

    all_items = []
    downloaded = 0
    skipped = 0

    for dl in DOWNLOADS:
        print(f"\n--- {dl['titel'][:70]} ---")
        json_path = os.path.join(LEITLINIEN_DIR, dl["json_name"])

        if os.path.exists(json_path):
            print(f"  JSON existiert bereits → Lade aus Datei")
            with open(json_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
            text = doc.get("text", "")
            skipped += 1
        else:
            pdf_bytes = download_pdf(dl["url"])
            if not pdf_bytes:
                continue
            print("  Extrahiere Text...", end="", flush=True)
            text = extract_text_from_pdf(pdf_bytes)
            if not text:
                print(" FEHLER: Kein Text extrahiert")
                continue
            print(f" {len(text)} Zeichen")

            verweise = find_verweise(text)
            doc = {
                "quelle": dl["quelle"],
                "typ": dl["typ"],
                "titel": dl["titel"],
                "datum": dl["datum"],
                "sprache": dl["sprache"],
                "text": text,
                "normbezuege": verweise,
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            print(f"  JSON gespeichert: {dl['json_name']}")
            downloaded += 1

        sections = segment_document(text)
        print(f"  {len(sections)} Segmente")

        for sec_idx, section in enumerate(sections):
            sec_title = section["title"]
            sec_text = section["text"]
            themen = extract_themen(sec_text + " " + dl["titel"] + " " + sec_title)
            verweise = find_verweise(sec_text)
            doc_id = sanitize(dl["titel"][:40])
            chunk_id = f"beh_{doc_id}_{sec_idx}"
            themen_str = ", ".join(themen) if themen else ""
            embed_parts = [dl["titel"]]
            if sec_title and sec_title != "Einleitung":
                embed_parts.append(sec_title)
            if themen_str:
                embed_parts.append(f"Themen: {themen_str}")
            embed_parts.append(sec_text[:4000])
            embed_text = " – ".join(embed_parts)
            meta = {
                "source_type": "leitlinie",
                "quelle": dl["quelle"],
                "typ": dl["typ"],
                "titel": dl["titel"][:200],
                "datum": dl["datum"],
                "abschnitt": sec_title[:200],
                "themen": themen_str,
                "normbezuege": ", ".join(verweise[:20]),
                "chunk_id": chunk_id,
                "sprache": dl["sprache"],
            }
            all_items.append({
                "id": chunk_id,
                "embed_text": embed_text,
                "document": sec_text,
                "meta": meta,
            })

    print(f"\n{'='*60}")
    print(f"  {downloaded} PDFs heruntergeladen, {skipped} aus Cache")
    print(f"  {len(all_items)} Chunks erstellt")
    print(f"{'='*60}")

    if not all_items:
        print("Keine Chunks zu embedden.")
        return

    import chromadb
    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"},
    )
    before = collection.count()
    print(f"  ChromaDB vorher: {before} Chunks")

    existing_ids = set(collection.get(include=[])["ids"])
    new_items = [it for it in all_items if it["id"] not in existing_ids]
    dupes = len(all_items) - len(new_items)
    if dupes:
        print(f"  {dupes} Duplikate übersprungen")

    if not new_items:
        print("  Keine neuen Chunks.")
        return

    print(f"  {len(new_items)} neue Chunks embedden...")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)

    BATCH_SIZE = 50
    for bs in range(0, len(new_items), BATCH_SIZE):
        be = min(bs + BATCH_SIZE, len(new_items))
        batch = new_items[bs:be]
        embeddings = model.encode(
            [it["embed_text"] for it in batch], show_progress_bar=False
        ).tolist()
        collection.add(
            ids=[it["id"] for it in batch],
            documents=[it["document"] for it in batch],
            metadatas=[it["meta"] for it in batch],
            embeddings=embeddings,
        )
        print(f"  Batch {bs // BATCH_SIZE + 1}: {len(batch)} Chunks")

    after = collection.count()
    print(f"\n  ChromaDB nachher: {after} Chunks (+{after - before})")
    print("  Fertig!")


if __name__ == "__main__":
    main()
