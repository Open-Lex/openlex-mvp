#!/usr/bin/env python3
"""
Lädt 36 englische EuGH-Urteile in deutscher Fassung von CELLAR,
segmentiert sie und bettet sie in ChromaDB ein.
"""

import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

# Add project to path
os.chdir("/opt/openlex-mvp")
sys.path.insert(0, "/opt/openlex-mvp")

from parse_eugh import parse_and_chunk
from sentence_transformers import SentenceTransformer
import chromadb

# ── Config ──────────────────────────────────────────────────────────────────

EMBED_MODEL = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"
BATCH_SIZE = 100
URTEILE_DIR = "data/urteile"
SEG_DIR = "data/urteile_segmentiert"
NAMES_FILE = "data/urteilsnamen.json"

SEGMENT_PREFIX = {
    "header": "",
    "rechtsrahmen": "Rechtsrahmen: ",
    "sachverhalt": "Sachverhalt: ",
    "vorlagefragen": "Vorlagefragen: ",
    "wuerdigung": "Würdigung des Gerichtshofs: ",
    "tenor": "Tenor: ",
}


def get_prefix(seg_name: str) -> str:
    for key, prefix in SEGMENT_PREFIX.items():
        if seg_name.startswith(key):
            return prefix
    if seg_name.startswith("vf_"):
        return "Vorlagefrage: "
    return ""


def sanitize(s: str) -> str:
    s = s.replace("/", "_").replace(" ", "_").replace("-", "_")
    return re.sub(r"_+", "_", s).lower().strip("_")


# ── Text extraction ────────────────────────────────────────────────────────

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip = True
        if tag in ("p", "br", "div", "h1", "h2", "h3", "li", "tr", "td"):
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = False

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)


def extract_from_xml(data: bytes) -> str:
    """Extract text from CELLAR XML."""
    root = ET.fromstring(data)
    texts = []
    for elem in root.iter():
        if elem.text and elem.text.strip():
            texts.append(elem.text.strip())
        if elem.tail and elem.tail.strip():
            texts.append(elem.tail.strip())
    return "\n".join(texts)


def extract_from_html(data: bytes) -> str:
    """Extract text from XHTML/HTML."""
    e = TextExtractor()
    e.feed(data.decode("utf-8", errors="replace"))
    return "".join(e.text)


def extract_volltext(raw_text: str) -> str:
    """Extract from URTEIL DES GERICHTSHOFS to end, clean whitespace."""
    start = raw_text.find("URTEIL DES GERICHTSHOFS")
    if start < 0:
        start = raw_text.find("Urteil des Gerichtshofs")
    if start < 0:
        return ""
    text = raw_text[start:].strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def fetch_german_text(celex: str) -> str:
    """Fetch German judgment text from CELLAR API."""
    url = f"http://publications.europa.eu/resource/celex/{celex}"

    # Try XML first
    for accept in ["application/xml", "application/xhtml+xml", "text/html"]:
        req = urllib.request.Request(url, headers={
            "Accept": accept,
            "Accept-Language": "de",
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            if accept == "application/xml":
                raw = extract_from_xml(data)
            else:
                raw = extract_from_html(data)
            volltext = extract_volltext(raw)
            if volltext and len(volltext) > 2000:
                return volltext
        except Exception:
            continue

    return ""


# ── Find English cases ──────────────────────────────────────────────────────

def find_english_cases() -> list[dict]:
    """Find all EuGH cases with English volltext."""
    cases = []
    for fname in sorted(os.listdir(URTEILE_DIR)):
        if not fname.startswith("EuGH") or not fname.endswith(".json"):
            continue
        path = os.path.join(URTEILE_DIR, fname)
        with open(path) as f:
            d = json.load(f)
        vt = d.get("volltext", "")
        if len(vt) < 100:
            continue

        sample = vt[:500].lower()
        de_words = sum(1 for w in ["urteil", "gerichtshof", "richtlinie", "verarbeitung",
                                    "grundverordnung", "mitgliedstaat"] if w in sample)
        en_words = sum(1 for w in ["judgment", "court", "directive", "processing",
                                    "regulation", "member state"] if w in sample)
        if en_words <= de_words:
            continue

        cases.append({
            "file": fname,
            "path": path,
            "data": d,
            "az": d.get("aktenzeichen", ""),
            "az_clean": d.get("aktenzeichen", "").replace("Rechtssache ", ""),
            "celex": d.get("celex", ""),
            "datum": d.get("datum", ""),
            "gericht": d.get("gericht", "EuGH"),
            "quelle": d.get("quelle", "eugh_cellar"),
        })

    return cases


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("EuGH-Urteile: Englisch → Deutsch laden, segmentieren, einbetten")
    print("=" * 70)

    # Load urteilsnamen
    with open(NAMES_FILE) as f:
        namen = json.load(f)

    # Find English cases
    cases = find_english_cases()
    print(f"\n{len(cases)} englische Urteile gefunden.\n")

    # Load embedding model once
    print("Lade Embedding-Modell...")
    model = SentenceTransformer(EMBED_MODEL)

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path="chromadb")
    col = client.get_collection("openlex_datenschutz")
    initial_count = col.count()
    print(f"ChromaDB: {initial_count} Chunks vor Start\n")

    # Process each case
    stats = {"ok": 0, "fail_fetch": 0, "fail_parse": 0, "total_chunks": 0}

    all_batch_ids = []
    all_batch_docs = []
    all_batch_metas = []
    all_batch_embeds = []

    for i, case in enumerate(cases):
        az = case["az_clean"]
        celex = case["celex"]
        kurzname = namen.get(az, "")

        print(f"[{i+1:>2}/{len(cases)}] {az:<16} {kurzname or '-':<25} ", end="", flush=True)

        # Step 1: Fetch German text
        volltext = fetch_german_text(celex)
        if not volltext:
            print("FEHLER: Kein deutscher Text")
            stats["fail_fetch"] += 1
            continue

        # Step 2: Update raw file
        case["data"]["volltext"] = volltext
        case["data"]["segmentiert"] = True
        with open(case["path"], "w") as f:
            json.dump(case["data"], f, ensure_ascii=False, indent=2)

        # Step 3: Segment
        try:
            segments = parse_and_chunk(volltext, case["az"])
        except Exception as e:
            print(f"FEHLER beim Parsen: {e}")
            stats["fail_parse"] += 1
            continue

        if not segments:
            print("FEHLER: Keine Segmente")
            stats["fail_parse"] += 1
            continue

        has_vf = any(s.name.startswith("vf_") for s in segments)
        has_tenor = any("tenor" in s.name for s in segments)
        mode = "SEM" if has_vf else "FB"

        # Step 4: Save segmented chunks and prepare embedding
        base = case["file"].replace(".json", "")
        used_ids = set()

        for seg in segments:
            # Save segment file
            chunk_data = {
                "chunk_id": f"{base}_{seg.name}",
                "segment": seg.name,
                "text": seg.text,
                "gericht": case["gericht"],
                "aktenzeichen": case["az"],
                "datum": case["datum"],
                "quelle": case["quelle"],
            }
            seg_path = os.path.join(SEG_DIR, f"{base}_{seg.name}.json")
            with open(seg_path, "w") as f:
                json.dump(chunk_data, f, ensure_ascii=False, indent=2)

            # Prepare for ChromaDB
            chunk_id_base = sanitize(f"eugh_{az}_{seg.name}")
            if chunk_id_base in used_ids:
                suffix = 1
                while f"{chunk_id_base}_{suffix}" in used_ids:
                    suffix += 1
                chunk_id_base = f"{chunk_id_base}_{suffix}"
            used_ids.add(chunk_id_base)

            chroma_id = f"seg_{chunk_id_base}"
            prefix = get_prefix(seg.name)
            embed_text = f"{prefix}{seg.text}"

            meta = {
                "source_type": "urteil_segmentiert",
                "gericht": case["gericht"] or "EuGH",
                "aktenzeichen": az,
                "kurzname": kurzname,
                "datum": case["datum"] or "",
                "quelle": case["quelle"] or "",
                "segment": seg.name,
                "chunk_id": chunk_id_base,
            }

            all_batch_ids.append(chroma_id)
            all_batch_docs.append(seg.text)
            all_batch_metas.append(meta)
            all_batch_embeds.append(embed_text)

        stats["ok"] += 1
        stats["total_chunks"] += len(segments)
        print(f"{len(volltext):>6} chars  {len(segments):>2} seg  T={'Y' if has_tenor else 'N'}  [{mode}]")

    # Step 5: Batch embed all chunks
    print(f"\n{'='*70}")
    print(f"Embedding {len(all_batch_ids)} Chunks...")

    for batch_start in range(0, len(all_batch_ids), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(all_batch_ids))
        batch_texts = all_batch_embeds[batch_start:batch_end]
        embeddings = model.encode(batch_texts, show_progress_bar=False).tolist()

        col.upsert(
            ids=all_batch_ids[batch_start:batch_end],
            documents=all_batch_docs[batch_start:batch_end],
            metadatas=all_batch_metas[batch_start:batch_end],
            embeddings=embeddings,
        )
        print(f"  Batch {batch_start//BATCH_SIZE + 1}: {batch_end - batch_start} Chunks eingebettet")

    final_count = col.count()

    print(f"\n{'='*70}")
    print(f"ERGEBNIS:")
    print(f"  Erfolgreich: {stats['ok']}/{len(cases)}")
    print(f"  Fehler Fetch: {stats['fail_fetch']}")
    print(f"  Fehler Parse: {stats['fail_parse']}")
    print(f"  Neue Chunks: {stats['total_chunks']}")
    print(f"  ChromaDB: {initial_count} → {final_count} (+{final_count - initial_count})")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
