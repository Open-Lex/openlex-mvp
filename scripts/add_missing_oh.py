#!/usr/bin/env python3
"""
add_missing_oh.py – Lädt fehlende Orientierungshilfen herunter, extrahiert Text,
segmentiert und embeddet in ChromaDB (gleiche Pipeline wie refine_behoerden.py).

Fehlende OH:
1. LfDI BW – Fotografieren und Datenschutz (Sept 2019)
2. LDI NRW – Datenschutz im Verein (Broschüre, 3. Überarbeitung)
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile

import requests

BASE_DIR = os.path.expanduser("~/openlex-mvp")
LEITLINIEN_DIR = os.path.join(BASE_DIR, "data", "leitlinien")
CHROMADB_DIR = os.path.join(BASE_DIR, "chromadb")
COLLECTION_NAME = "openlex_datenschutz"
MODEL_NAME = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"

# PDFs herunterladen
DOWNLOADS = [
    {
        "url": "https://www.baden-wuerttemberg.datenschutz.de/wp-content/uploads/2019/09/Fotografieren-und-Datenschutz-September-2019.pdf",
        "titel": "September 2019 - LfDI BW - Fotografieren und Datenschutz",
        "datum": "2019-09",
        "quelle": "lfdi_bw",
        "typ": "orientierungshilfe",
        "json_name": "LfDI_BW_Fotografieren_und_Datenschutz.json",
    },
    {
        "url": "https://www.baden-wuerttemberg.datenschutz.de/wp-content/uploads/2020/06/OH-Datenschutz-im-Verein-nach-der-DSGVO.pdf",
        "titel": "Juni 2020 - LfDI BW - Orientierungshilfe Datenschutz im Verein nach der DSGVO",
        "datum": "2020-06",
        "quelle": "lfdi_bw",
        "typ": "orientierungshilfe",
        "json_name": "LfDI_BW_Datenschutz_im_Verein.json",
    },
]


def download_pdf(url: str) -> bytes | None:
    """Lädt PDF herunter."""
    print(f"  Lade {url} ...", end="", flush=True)
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "OpenLex/1.0"})
        r.raise_for_status()
        print(f" OK ({len(r.content) / 1024:.0f} KB)")
        return r.content
    except Exception as e:
        print(f" FEHLER: {e}")
        return None


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrahiert Text aus PDF (pymupdf oder pdfplumber)."""
    # Versuche pymupdf (fitz)
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

    # Fallback: pdfplumber
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

    # Fallback: pdfminer
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        import io
        text = pdfminer_extract(io.BytesIO(pdf_bytes))
        if text.strip():
            return text.strip()
    except ImportError:
        pass

    print("  FEHLER: Kein PDF-Extractor verfügbar (pymupdf, pdfplumber, pdfminer)")
    return ""


def find_verweise(text: str) -> list[str]:
    """Extrahiert Normverweise aus Text."""
    pattern = re.compile(
        r"Art\.?\s*\d+\s*(?:Abs\.?\s*\d+\s*)?(?:(?:lit\.?\s*[a-z]|Nr\.?\s*\d+)\s*)?"
        r"(?:DSGVO|DS-GVO|BDSG|TTDSG|UWG|KUG)"
        r"|§§?\s*\d+[a-z]?\s*(?:Abs\.?\s*\d+\s*)?[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*",
        re.UNICODE,
    )
    return list(set(pattern.findall(text)))


# Import segmentation and theme extraction from refine_behoerden
sys.path.insert(0, BASE_DIR)
from refine_behoerden import segment_document, extract_themen, sanitize


def main():
    print("=" * 60)
    print("  Fehlende Orientierungshilfen herunterladen & embedden")
    print("=" * 60)

    all_items = []

    for dl in DOWNLOADS:
        print(f"\n--- {dl['titel']} ---")

        # 1. JSON schon vorhanden?
        json_path = os.path.join(LEITLINIEN_DIR, dl["json_name"])
        if os.path.exists(json_path):
            print(f"  JSON existiert bereits: {json_path}")
            with open(json_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
            text = doc.get("text", "")
        else:
            # 2. PDF herunterladen
            pdf_bytes = download_pdf(dl["url"])
            if not pdf_bytes:
                continue

            # 3. Text extrahieren
            print("  Extrahiere Text...", end="", flush=True)
            text = extract_text_from_pdf(pdf_bytes)
            if not text:
                print(" FEHLER: Kein Text extrahiert")
                continue
            print(f" {len(text)} Zeichen")

            # 4. JSON speichern
            verweise = find_verweise(text)
            doc = {
                "quelle": dl["quelle"],
                "typ": dl["typ"],
                "titel": dl["titel"],
                "datum": dl["datum"],
                "text": text,
                "normbezuege": verweise,
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            print(f"  JSON gespeichert: {json_path}")

        # 5. Segmentieren und Chunks erstellen
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
            }

            all_items.append({
                "id": chunk_id,
                "embed_text": embed_text,
                "document": sec_text,
                "meta": meta,
            })

    if not all_items:
        print("\nKeine neuen Chunks zu embedden.")
        return

    # 6. In ChromaDB einfügen
    print(f"\n{'='*60}")
    print(f"  {len(all_items)} Chunks in ChromaDB einfügen")
    print(f"{'='*60}")

    import chromadb
    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"},
    )
    before = collection.count()
    print(f"  ChromaDB vorher: {before} Chunks")

    # Deduplizierung
    existing_ids = set(collection.get(include=[])["ids"])
    new_items = [it for it in all_items if it["id"] not in existing_ids]
    dupes = len(all_items) - len(new_items)
    if dupes:
        print(f"  {dupes} Duplikate übersprungen")

    if not new_items:
        print("  Keine neuen Chunks (alle existieren bereits).")
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
        print(f"  Batch {bs//BATCH_SIZE + 1}: {len(batch)} Chunks eingefügt")

    after = collection.count()
    print(f"\n  ChromaDB nachher: {after} Chunks (+{after - before})")
    print("  Fertig!")


if __name__ == "__main__":
    main()
