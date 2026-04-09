#!/usr/bin/env python3
"""
load_tdddg.py – Lädt alle 30 Paragraphen des TDDDG von dsgvo-gesetz.de,
chunked sie granular und embeddet sie in ChromaDB.
"""

import json, os, re, time, sys
import requests
from bs4 import BeautifulSoup
import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.expanduser("~/openlex-mvp")
EMBED_MODEL = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"

PARAGRAPHS = list(range(1, 31))  # § 1 bis § 30

def fetch_paragraph(par_num: int) -> dict:
    """Fetcht einen TDDDG-Paragraphen von dsgvo-gesetz.de."""
    url = f"https://dsgvo-gesetz.de/tdddg/{par_num}-tdddg/"
    resp = requests.get(url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (OpenLex-MVP Academic Research Bot)"
    })
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Titel extrahieren
    title_el = soup.find("h1") or soup.find("h2")
    title = title_el.get_text(strip=True) if title_el else f"§ {par_num} TDDDG"
    
    # Normtext extrahieren - suche nach dem Hauptinhalt
    # Auf dsgvo-gesetz.de ist der Gesetzestext typisch in einem entry-content oder ähnlichen div
    content_div = soup.find("div", class_="entry-content") or soup.find("article") or soup.find("main")
    
    if content_div:
        # Entferne Navigation, Footer, etc.
        for tag in content_div.find_all(["nav", "footer", "aside", "script", "style"]):
            tag.decompose()
        
        # Alle Absätze sammeln
        paragraphs = []
        for p in content_div.find_all(["p", "li"]):
            text = p.get_text(strip=True)
            if text and len(text) > 5:
                # Skip Navigation/Links
                if text.startswith("←") or text.startswith("→") or "Nächster Artikel" in text or "Vorheriger" in text:
                    continue
                if "dsgvo-gesetz.de" in text.lower():
                    continue
                paragraphs.append(text)
        
        volltext = "\n".join(paragraphs)
    else:
        volltext = ""
    
    # Cleanup: Entferne Werbetext/Footer
    # Typisch endet der Gesetzestext vor "Suitable" oder Werbeblöcken
    for cutoff in ["Suitable", "Passende", "← ", "→ ", "Copyright", "Datenschutzerklärung"]:
        idx = volltext.find(cutoff)
        if idx > 0:
            volltext = volltext[:idx].strip()
    
    return {
        "paragraph": f"§ {par_num}",
        "titel": title,
        "volltext": volltext,
        "url": url,
    }


def chunk_paragraph(par_data: dict) -> list[dict]:
    """Erstellt granulare Chunks aus einem Paragraphen.
    
    Für kurze Paragraphen: ein Chunk.
    Für lange: Split an Absatz-Grenzen.
    """
    par = par_data["paragraph"]
    titel = par_data["titel"]
    text = par_data["volltext"]
    
    if not text or len(text.strip()) < 20:
        return []
    
    # Absätze erkennen: (1), (2), (3) etc.
    abs_pattern = re.compile(r"^\((\d+)\)\s*", re.MULTILINE)
    
    chunks = []
    
    # Suche nach Absätzen
    matches = list(abs_pattern.finditer(text))
    
    if len(matches) > 1:
        # Mehrere Absätze → je ein Chunk pro Absatz
        for i, m in enumerate(matches):
            abs_num = m.group(1)
            start = m.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            abs_text = text[start:end].strip()
            
            if not abs_text or len(abs_text) < 10:
                continue
            
            chunk_id = f"gran_TDDDG_{par.replace(' ', '_')}_Abs.{abs_num}"
            chunks.append({
                "chunk_id": chunk_id,
                "text": abs_text,
                "volladresse": f"{par} Abs. {abs_num} TDDDG",
                "gesetz": "TDDDG",
                "source_type": "gesetz_granular",
            })
    else:
        # Ein Chunk für den ganzen Paragraphen
        chunk_id = f"gran_TDDDG_{par.replace(' ', '_')}"
        chunks.append({
            "chunk_id": chunk_id,
            "text": text.strip(),
            "volladresse": f"{par} TDDDG",
            "gesetz": "TDDDG",
            "source_type": "gesetz_granular",
        })
    
    return chunks


def main():
    print("=" * 60)
    print("TDDDG laden von dsgvo-gesetz.de")
    print("=" * 60)
    
    # 1. Alle Paragraphen fetchen
    all_pars = []
    for par_num in PARAGRAPHS:
        try:
            data = fetch_paragraph(par_num)
            text_len = len(data["volltext"])
            print(f"  § {par_num}: {data['titel'][:50]:<50} ({text_len} Zeichen)")
            all_pars.append(data)
            if par_num < PARAGRAPHS[-1]:
                time.sleep(1.0)
        except Exception as e:
            print(f"  § {par_num}: FEHLER – {e}")
    
    print(f"\n{len(all_pars)} Paragraphen geladen")
    
    # 2. Chunken
    all_chunks = []
    for par_data in all_pars:
        chunks = chunk_paragraph(par_data)
        all_chunks.extend(chunks)
    
    print(f"{len(all_chunks)} granulare Chunks erstellt")
    
    # Speichere Roh-JSONs
    out_dir = os.path.join(BASE_DIR, "data", "gesetze_tdddg")
    os.makedirs(out_dir, exist_ok=True)
    for par_data in all_pars:
        fname = f"TDDDG_{par_data['paragraph'].replace(' ', '_')}.json"
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            json.dump(par_data, f, ensure_ascii=False, indent=2)
    print(f"Roh-JSONs gespeichert in {out_dir}")
    
    # 3. Embedden
    print(f"\nLade Embedding-Model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)
    
    client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chromadb"))
    col = client.get_collection("openlex_datenschutz")
    
    existing = set(col.get(include=[])["ids"])
    
    ids_to_add = []
    docs_to_add = []
    metas_to_add = []
    embed_texts = []
    
    for chunk in all_chunks:
        chroma_id = chunk["chunk_id"]
        if chroma_id in existing:
            print(f"  SKIP (exists): {chroma_id}")
            continue
        
        embed_text = f"Gesetzestext TDDDG: {chunk['text']}"
        
        meta = {
            "source_type": chunk["source_type"],
            "gesetz": chunk["gesetz"],
            "chunk_id": chunk["chunk_id"],
            "volladresse": chunk["volladresse"],
        }
        
        ids_to_add.append(chroma_id)
        docs_to_add.append(chunk["text"])
        metas_to_add.append(meta)
        embed_texts.append(embed_text)
    
    if not ids_to_add:
        print("Alle Chunks bereits vorhanden!")
        return
    
    print(f"\nEmbedde {len(ids_to_add)} neue Chunks...")
    embeddings = model.encode(embed_texts, normalize_embeddings=True, show_progress_bar=True).tolist()
    
    batch_size = 500
    for i in range(0, len(ids_to_add), batch_size):
        end = min(i + batch_size, len(ids_to_add))
        col.add(
            ids=ids_to_add[i:end],
            documents=docs_to_add[i:end],
            metadatas=metas_to_add[i:end],
            embeddings=embeddings[i:end],
        )
    
    print(f"\n✓ {len(ids_to_add)} TDDDG-Chunks in ChromaDB eingebettet")
    print(f"ChromaDB gesamt: {col.count()}")
    
    # Verify
    r = col.get(where={"gesetz": "TDDDG"}, include=[], limit=1000)
    print(f"TDDDG-Chunks in DB: {len(r['ids'])}")


if __name__ == "__main__":
    main()
