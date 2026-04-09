#!/usr/bin/env python3
"""
add_edpb_guidelines.py – Lädt fehlende EDPB Guidelines herunter,
extrahiert Text, segmentiert und embeddet in ChromaDB.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time

import requests

BASE_DIR = os.path.expanduser("~/openlex-mvp")
LEITLINIEN_DIR = os.path.join(BASE_DIR, "data", "leitlinien")
CHROMADB_DIR = os.path.join(BASE_DIR, "chromadb")
COLLECTION_NAME = "openlex_datenschutz"
MODEL_NAME = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"

sys.path.insert(0, BASE_DIR)
from refine_behoerden import segment_document, extract_themen, sanitize, find_verweise

# 14 fehlende EDPB Guidelines (07/2020 und 04/2022 bereits vorhanden)
DOWNLOADS = [
    {
        "url": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_202005_consent_en.pdf",
        "titel": "Guidelines 05/2020 on Consent under Regulation 2016/679 (Version 1.1)",
        "datum": "2020-05-04",
        "json_name": "EDPB_Guidelines_05_2020_Consent.json",
    },
    {
        "url": "https://www.edpb.europa.eu/system/files/2023-04/edpb_guidelines_202201_data_subject_rights_access_v2_en.pdf",
        "titel": "Guidelines 01/2022 on Data Subject Rights - Right of Access (Version 2.0)",
        "datum": "2023-04-17",
        "json_name": "EDPB_Guidelines_01_2022_Right_of_Access.json",
    },
    {
        "url": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines-art_6-1-b-adopted_after_public_consultation_en.pdf",
        "titel": "Guidelines 2/2019 on the processing of personal data under Article 6(1)(b) GDPR",
        "datum": "2019-10-16",
        "json_name": "EDPB_Guidelines_02_2019_Art6_1_b.json",
    },
    {
        "url": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_201903_video_devices_en_0.pdf",
        "titel": "Guidelines 3/2019 on processing of personal data through video devices",
        "datum": "2020-01-30",
        "json_name": "EDPB_Guidelines_03_2019_Video_Devices.json",
    },
    {
        "url": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_201904_dataprotection_by_design_and_by_default_v2.0_en.pdf",
        "titel": "Guidelines 4/2019 on Article 25 Data Protection by Design and by Default (Version 2.0)",
        "datum": "2020-10-20",
        "json_name": "EDPB_Guidelines_04_2019_DPbD.json",
    },
    {
        "url": "https://www.edpb.europa.eu/system/files/2021-04/edpb_guidelines_082020_on_the_targeting_of_social_media_users_en.pdf",
        "titel": "Guidelines 8/2020 on the targeting of social media users",
        "datum": "2021-04-13",
        "json_name": "EDPB_Guidelines_08_2020_Social_Media.json",
    },
    {
        "url": "https://www.edpb.europa.eu/system/files/2023-02/edpb_guidelines_05-2021_interplay_between_the_application_of_art3-chapter_v_of_the_gdpr_v2_en_0.pdf",
        "titel": "Guidelines 05/2021 on the interplay between Article 3 and Chapter V GDPR (Version 2.0)",
        "datum": "2023-02-24",
        "json_name": "EDPB_Guidelines_05_2021_Art3_Transfer.json",
    },
    {
        "url": "https://www.edpb.europa.eu/system/files/2022-01/edpb_guidelines_012021_pdbnotification_adopted_en.pdf",
        "titel": "Guidelines 01/2021 on Examples regarding Personal Data Breach Notification",
        "datum": "2022-01-03",
        "json_name": "EDPB_Guidelines_01_2021_Data_Breach.json",
    },
    {
        "url": "https://www.edpb.europa.eu/system/files/2023-06/edpb_guidelines_202103_article65-1-a_v2_en.pdf",
        "titel": "Guidelines 03/2021 on the application of Article 65(1)(a) GDPR (Version 2.0)",
        "datum": "2023-06-14",
        "json_name": "EDPB_Guidelines_03_2021_Art65.json",
    },
    {
        "url": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_201901_v2.0_codesofconduct_en.pdf",
        "titel": "Guidelines 01/2019 on Codes of Conduct and Monitoring Bodies",
        "datum": "2019-06-04",
        "json_name": "EDPB_Guidelines_01_2019_Codes_of_Conduct.json",
    },
    {
        "url": "https://www.edpb.europa.eu/system/files/2023-02/edpb_guidelines_07-2022_on_certification_as_a_tool_for_transfers_v2_en_0.pdf",
        "titel": "Guidelines 07/2022 on certification as a tool for transfers (Version 2.0)",
        "datum": "2023-02-24",
        "json_name": "EDPB_Guidelines_07_2022_Certification_Transfers.json",
    },
    {
        "url": "https://www.edpb.europa.eu/system/files/2023-04/edpb_guidelines_202208_identifying_lsa_targeted_update_v2_en.pdf",
        "titel": "Guidelines 08/2022 on identifying a controller or processor's lead supervisory authority (Version 2.0)",
        "datum": "2023-04-17",
        "json_name": "EDPB_Guidelines_08_2022_Lead_SA.json",
    },
    {
        "url": "https://www.edpb.europa.eu/system/files/2021-07/edpb_guidelines_202102_on_vva_v2.0_adopted_en.pdf",
        "titel": "Guidelines 02/2021 on Virtual Voice Assistants (Version 2.0)",
        "datum": "2021-07-07",
        "json_name": "EDPB_Guidelines_02_2021_Voice_Assistants.json",
    },
    {
        "url": "https://www.edpb.europa.eu/system/files/2022-03/edpb_guidelines_codes_conduct_transfers_after_public_consultation_en_1.pdf",
        "titel": "Guidelines 04/2021 on Codes of Conduct as tools for transfers (Version 2.0)",
        "datum": "2022-02-22",
        "json_name": "EDPB_Guidelines_04_2021_CoC_Transfers.json",
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
    print("  EDPB Guidelines herunterladen & embedden")
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
                "quelle": "edpb",
                "typ": "leitlinie",
                "titel": dl["titel"],
                "datum": dl["datum"],
                "sprache": "en",
                "text": text,
                "normbezuege": verweise,
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            print(f"  JSON gespeichert: {dl['json_name']}")
            downloaded += 1

        # Segmentieren
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
                "quelle": "edpb",
                "typ": "leitlinie",
                "titel": dl["titel"][:200],
                "datum": dl["datum"],
                "abschnitt": sec_title[:200],
                "themen": themen_str,
                "normbezuege": ", ".join(verweise[:20]),
                "chunk_id": chunk_id,
                "sprache": "en",
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

    # ChromaDB
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
