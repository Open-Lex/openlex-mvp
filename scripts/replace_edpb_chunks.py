#!/usr/bin/env python3
"""
replace_edpb_chunks.py – Ersetzt englische EDPB-Chunks durch deutsche PDFs.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile

BASE_DIR = os.path.expanduser("~/openlex-mvp")
PDF_DIR = os.path.expanduser("~/Downloads/EDPB MANUELL")
LEITLINIEN_DIR = os.path.join(BASE_DIR, "data", "leitlinien")
CHROMADB_DIR = os.path.join(BASE_DIR, "chromadb")
COLLECTION_NAME = "openlex_datenschutz"
MODEL_NAME = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"

sys.path.insert(0, BASE_DIR)
from refine_behoerden import extract_themen, sanitize, find_verweise

# Heading pattern for segmentation
HEADING_RE = re.compile(
    r"(?:^|\n)"
    r"("
    r"(?:\d+(?:\.\d+)*\.?\s+[A-ZÄÖÜ].{5,75})"
    r"|(?:[IVX]+\.\s+[A-ZÄÖÜ].{5,75})"
    r"|(?:[a-z]\)\s+[A-ZÄÖÜ].{5,75})"
    r"|(?:ABSCHNITT\s+\d+.{3,60})"
    r"|(?:[A-ZÄÖÜ][A-ZÄÖÜ\s\-:,/]{8,78})"
    r")"
    r"\s*\n",
    re.MULTILINE,
)


def extract_text_from_pdf(path: str) -> str:
    try:
        import fitz
        doc = fitz.open(path)
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
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                pt = page.extract_text()
                if pt:
                    text += pt + "\n"
        if text.strip():
            return text.strip()
    except ImportError:
        pass
    return ""


def detect_language(text: str) -> str:
    """Erkennt Sprache anhand der ersten 500 Zeichen."""
    sample = text[:500].lower()
    de_words = ["die", "der", "das", "und", "ist", "für", "von", "mit", "auf", "den",
                "des", "eine", "wird", "nicht", "bei", "nach", "zur", "zum", "sich",
                "personenbezogene", "verarbeitung", "verantwortlicher", "dsgvo"]
    en_words = ["the", "and", "for", "with", "that", "this", "are", "from",
                "controller", "processor", "data subject", "pursuant", "regulation",
                "processing", "personal data", "gdpr"]
    de_hits = sum(1 for w in de_words if f" {w} " in f" {sample} " or sample.startswith(w))
    en_hits = sum(1 for w in en_words if f" {w} " in f" {sample} " or sample.startswith(w))
    return "de" if de_hits >= en_hits else "en"


def extract_titel(text: str, filename: str) -> str:
    """Extrahiert den Titel aus dem PDF-Text."""
    # Suche nach "Leitlinien XX/YYYY" oder "Guidelines XX/YYYY" in den ersten 2000 chars
    head = text[:2000]
    m = re.search(r"(Leitlinien\s+\d+/\d{4}\s+[^\n]{10,120})", head)
    if m:
        return m.group(1).strip()
    m = re.search(r"(Guidelines\s+\d+/\d{4}\s+[^\n]{10,120})", head)
    if m:
        return m.group(1).strip()
    m = re.search(r"(Stellungnahme\s+\d+/\d{4}\s+[^\n]{10,120})", head)
    if m:
        return m.group(1).strip()
    m = re.search(r"(Opinion\s+\d+/\d{4}\s+[^\n]{10,120})", head)
    if m:
        return m.group(1).strip()
    # Fallback: erste nicht-leere Zeile > 20 chars
    for line in head.split("\n"):
        line = line.strip()
        if len(line) > 20 and not line.startswith("Angenommen") and not line.startswith("Adopted"):
            return line[:200]
    return filename.replace(".pdf", "").replace("_", " ")[:200]


def segment_document(text: str, max_chunk: int = 2000) -> list[dict]:
    """Segmentiert nach Überschriften mit max Chunk-Größe."""
    if not text or len(text) < 100:
        return [{"title": "", "text": text}]

    headings = []
    for m in HEADING_RE.finditer(text):
        title = m.group(1).strip()
        if len(title) < 10:
            continue
        if re.match(r"^[\d\s./-]+$", title):
            continue
        if sum(1 for c in title if c.isalpha()) < len(title) * 0.4:
            continue
        headings.append((m.start(), title))

    if not headings:
        chunks = []
        for i in range(0, len(text), max_chunk):
            block = text[i:i + max_chunk].strip()
            if block and len(block) > 50:
                chunks.append({"title": f"Abschnitt {len(chunks)+1}", "text": block})
        return chunks if chunks else [{"title": "", "text": text}]

    sections = []
    for i, (pos, title) in enumerate(headings):
        next_pos = headings[i + 1][0] if i + 1 < len(headings) else len(text)
        text_start = text.find("\n", pos)
        if text_start == -1 or text_start > pos + 200:
            text_start = pos + len(title)
        section_text = text[text_start:next_pos].strip()

        if not section_text or len(section_text) < 30:
            continue

        if len(section_text) > max_chunk:
            # Teile an Absatzgrenzen
            paragraphs = re.split(r"\n\s*\n", section_text)
            current = ""
            part_num = 0
            for para in paragraphs:
                if len(current) + len(para) > max_chunk and current:
                    part_title = f"{title} (Teil {part_num+1})" if part_num > 0 else title
                    sections.append({"title": part_title, "text": current.strip()})
                    current = para
                    part_num += 1
                else:
                    current = current + "\n\n" + para if current else para
            if current.strip() and len(current.strip()) > 50:
                part_title = f"{title} (Teil {part_num+1})" if part_num > 0 else title
                sections.append({"title": part_title, "text": current.strip()})
        else:
            sections.append({"title": title, "text": section_text})

    # Preamble
    if headings and headings[0][0] > 100:
        preamble = text[:headings[0][0]].strip()
        if len(preamble) > 50:
            sections.insert(0, {"title": "Einleitung", "text": preamble[:max_chunk]})

    return sections if sections else [{"title": "", "text": text}]


def main():
    import chromadb
    print("=" * 60)
    print("  EDPB-Chunks ersetzen: EN → DE PDFs")
    print("=" * 60)

    # ── SCHRITT 1: PDFs analysieren ──
    print("\n--- SCHRITT 1: PDFs analysieren ---")
    pdfs = []
    for fname in sorted(os.listdir(PDF_DIR)):
        if not fname.endswith(".pdf"):
            continue
        fpath = os.path.join(PDF_DIR, fname)
        size = os.path.getsize(fpath)
        text = extract_text_from_pdf(fpath)
        lang = detect_language(text)
        titel = extract_titel(text, fname)
        pdfs.append({
            "filename": fname, "path": fpath, "size": size,
            "text": text, "lang": lang, "titel": titel,
        })
        lang_label = "DE" if lang == "de" else "EN"
        print(f"  [{lang_label}] {fname[:65]:<67} {size/1024:>7.0f} KB")

    de_pdfs = [p for p in pdfs if p["lang"] == "de"]
    en_pdfs = [p for p in pdfs if p["lang"] == "en"]
    print(f"\n  Gesamt: {len(pdfs)} PDFs ({len(de_pdfs)} DE, {len(en_pdfs)} EN)")

    # ── SCHRITT 2+3: Englische Chunks löschen ──
    print("\n--- SCHRITT 3: Englische Chunks löschen ---")
    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    col = client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"},
    )
    before = col.count()
    print(f"  ChromaDB vorher: {before} Chunks")

    # Alle Chunks mit quelle=edpb holen
    edpb_data = col.get(where={"quelle": "edpb"}, include=["documents", "metadatas"], limit=10000)

    ids_to_delete = []
    for cid, doc, meta in zip(edpb_data["ids"], edpb_data["documents"], edpb_data["metadatas"]):
        # a) sprache='en'
        if meta.get("sprache") == "en":
            ids_to_delete.append(cid)
            continue
        # b) Titel enthält 'Guidelines' und Text enthält engl. Keywords
        titel = meta.get("titel", "")
        doc_lower = (doc or "")[:500].lower()
        if "guidelines" in titel.lower():
            en_kw = ["controller", "processor", "data subject", "pursuant"]
            if sum(1 for w in en_kw if w in doc_lower) >= 2:
                ids_to_delete.append(cid)
                continue
        # c) Opinion 28/2024 englisch
        if "opinion 28/2024" in titel.lower() or "opinion" in titel.lower():
            if detect_language(doc[:500]) == "en":
                ids_to_delete.append(cid)
                continue
        # d) Taskforce/ChatGPT englisch
        if "taskforce" in titel.lower() or "chatgpt" in titel.lower():
            if detect_language(doc[:500]) == "en":
                ids_to_delete.append(cid)
                continue

    # Auch Chunks suchen die uebersetzt_aus='en' haben (von früherem Versuch)
    try:
        translated = col.get(where={"uebersetzt_aus": "en"}, include=["metadatas"], limit=5000)
        for cid in translated["ids"]:
            if cid not in ids_to_delete:
                ids_to_delete.append(cid)
    except Exception:
        pass

    if ids_to_delete:
        # Deduplizieren
        ids_to_delete = list(set(ids_to_delete))
        for i in range(0, len(ids_to_delete), 5000):
            batch = ids_to_delete[i:i + 5000]
            col.delete(ids=batch)
        print(f"  {len(ids_to_delete)} englische Chunks gelöscht")
    else:
        print("  Keine englischen Chunks gefunden")

    after_delete = col.count()
    print(f"  ChromaDB nach Löschung: {after_delete} Chunks")

    # ── SCHRITT 4: Deutsche PDFs laden ──
    print(f"\n--- SCHRITT 4: Deutsche PDFs laden ---")
    all_items = []

    for pdf in de_pdfs:
        sections = segment_document(pdf["text"])
        print(f"  {pdf['filename'][:55]:<57} → {len(sections):>3} Chunks  [{pdf['titel'][:50]}]")

        for sec_idx, section in enumerate(sections):
            sec_title = section["title"]
            sec_text = section["text"]
            themen = extract_themen(sec_text + " " + pdf["titel"] + " " + sec_title)
            verweise = find_verweise(sec_text)
            doc_id = sanitize(pdf["titel"][:40])
            chunk_id = f"beh_{doc_id}_{sec_idx}"
            themen_str = ", ".join(themen) if themen else ""

            embed_parts = [pdf["titel"]]
            if sec_title and sec_title != "Einleitung":
                embed_parts.append(sec_title)
            if themen_str:
                embed_parts.append(f"Themen: {themen_str}")
            embed_parts.append(sec_text[:4000])
            embed_text = " – ".join(embed_parts)

            meta = {
                "source_type": "leitlinie",
                "quelle": "edpb",
                "typ": "leitlinie",
                "titel": pdf["titel"][:200],
                "datum": "",
                "abschnitt": sec_title[:200],
                "themen": themen_str,
                "normbezuege": ", ".join(verweise[:20]),
                "chunk_id": chunk_id,
                "sprache": "de",
            }

            all_items.append({
                "id": chunk_id,
                "embed_text": embed_text,
                "document": sec_text,
                "meta": meta,
            })

    print(f"\n  {len(all_items)} Chunks aus {len(de_pdfs)} deutschen PDFs erstellt")

    if all_items:
        # Deduplizierung
        existing_ids = set(col.get(include=[])["ids"])
        new_items = [it for it in all_items if it["id"] not in existing_ids]
        dupes = len(all_items) - len(new_items)
        if dupes:
            print(f"  {dupes} Duplikate übersprungen")

        if new_items:
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
                col.add(
                    ids=[it["id"] for it in batch],
                    documents=[it["document"] for it in batch],
                    metadatas=[it["meta"] for it in batch],
                    embeddings=embeddings,
                )
                print(f"    Batch {bs // BATCH_SIZE + 1}: {len(batch)} Chunks")

    after = col.count()

    # ── SCHRITT 5: Englische PDFs auflisten ──
    print(f"\n--- SCHRITT 5: Nur auf Englisch verfügbar (müssen noch übersetzt werden) ---")
    for pdf in en_pdfs:
        print(f"  ⚠ {pdf['filename']}")

    # ── SCHRITT 6: Zusammenfassung ──
    print(f"\n{'='*60}")
    print(f"  ZUSAMMENFASSUNG")
    print(f"{'='*60}")
    print(f"  Englische Chunks gelöscht:  {len(ids_to_delete)}")
    print(f"  Deutsche PDFs geladen:      {len(de_pdfs)}")
    print(f"  Neue Chunks erstellt:       {len(all_items)}")
    print(f"  Nur englisch (TODO):        {len(en_pdfs)}")
    print(f"  ChromaDB vorher:            {before}")
    print(f"  ChromaDB nachher:           {after}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
