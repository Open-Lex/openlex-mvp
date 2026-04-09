#!/usr/bin/env python3
"""
update_index.py – Aktualisiert die ChromaDB-Collection 'openlex_datenschutz'
mit granularen Gesetzes-Chunks, segmentierten Urteils-Chunks, neuen
EU-Urteilen und angereicherten Erwägungsgründen.

OHNE Passauer-Chunks (werden separat auf dem Server embeddet).
Resume-fähig über chunk_id Deduplizierung.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import time

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
CHROMADB_DIR = os.path.join(BASE_DIR, "chromadb")
COLLECTION_NAME = "openlex_datenschutz"
MODEL_NAME = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"
BATCH_SIZE = 100

GRANULAR_DIR = os.path.join(BASE_DIR, "data", "gesetze_granular")
SEG_DIR = os.path.join(BASE_DIR, "data", "urteile_segmentiert")
URTEILE_DIR = os.path.join(BASE_DIR, "data", "urteile")
GESETZE_DIR = os.path.join(BASE_DIR, "data", "gesetze")

# Chunk-Parameter
CHUNK_TARGET = 2400
CHUNK_MIN = 2000
CHUNK_MAX = 3200
OVERLAP = 400
_SATZ_RE = re.compile(r"(\S+)\.\s+([A-ZÄÖÜ(])", re.UNICODE)

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\s]+', "_", name).strip("_")[:120]


def flatten_meta(doc: dict) -> dict:
    flat = {}
    for k, v in doc.items():
        if k in ("text", "volltext", "kontext_paragraph"):
            continue
        if isinstance(v, list):
            flat[k] = ", ".join(str(x) for x in v[:30])
        elif isinstance(v, (str, int, float, bool)):
            flat[k] = v
        elif v is None:
            flat[k] = ""
        else:
            flat[k] = str(v)
    return flat


def chunk_text(text: str) -> list[str]:
    if not text or len(text) < CHUNK_MIN:
        return [text] if text else []
    chunks, pos, tlen = [], 0, len(text)
    while pos < tlen:
        if tlen - pos <= CHUNK_MAX:
            c = text[pos:].strip()
            if c:
                chunks.append(c)
            break
        target = pos + CHUNK_TARGET
        best = target
        for m in _SATZ_RE.finditer(text, max(pos, target - 200)):
            end = m.start() + len(m.group(1)) + 1
            if end >= target:
                best = end
                break
            if end > target + 300:
                break
        best = max(best, pos + CHUNK_MIN)
        best = min(best, pos + CHUNK_MAX)
        c = text[pos:best].strip()
        if c:
            chunks.append(c)
        pos = best - OVERLAP
        if pos <= best - CHUNK_MIN:
            pos = best
    return chunks


def make_chunk_id(prefix: str, doc_id: str, idx: int) -> str:
    raw = f"{prefix}:{doc_id}:{idx}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def add_to_collection(collection, model, items: list[dict],
                      existing_ids: set, label: str) -> int:
    """Embeddet und fügt neue Items zur Collection hinzu. Gibt Anzahl eingefügter zurück."""
    new_items = [it for it in items if it["id"] not in existing_ids]
    total = len(new_items)
    if total == 0:
        print(f"    Alle {len(items)} {label} bereits vorhanden.")
        return 0

    print(f"    {total} neue {label} (von {len(items)} gesamt) ...")
    inserted = 0
    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)
        batch = new_items[batch_start:batch_end]

        texts = [it["embed_text"] for it in batch]
        ids = [it["id"] for it in batch]
        metadatas = [it["meta"] for it in batch]
        documents = [it["document"] for it in batch]

        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            ids=ids, embeddings=embeddings,
            documents=documents, metadatas=metadatas,
        )
        inserted += len(batch)
        existing_ids.update(ids)

        pct = batch_end / total * 100
        if batch_end % 1000 < BATCH_SIZE or batch_end == total:
            print(f"      {batch_end:>6}/{total} ({pct:5.1f}%)")

    return inserted


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 1 – Granulare Gesetzes-Chunks
# ═══════════════════════════════════════════════════════════════════════════


def prepare_granular_chunks() -> list[dict]:
    """Lädt granulare Gesetzes-Chunks und bereitet sie für Embedding vor."""
    items = []
    for fpath in glob.glob(os.path.join(GRANULAR_DIR, "*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception:
            continue

        chunk_id = doc.get("chunk_id", "")
        volladresse = doc.get("volladresse", "")
        text = doc.get("text", "")
        if not chunk_id or not text:
            continue

        # Embedding-Text: Volladresse + Text für besseres Retrieval
        embed_text = f"{volladresse} – {text}" if volladresse else text

        meta = flatten_meta(doc)
        meta["source_type"] = "gesetz_granular"

        items.append({
            "id": f"gran_{chunk_id}",
            "embed_text": embed_text,
            "document": text,
            "meta": meta,
        })

    return items


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 2 – Segmentierte Urteils-Chunks (ohne Passau)
# ═══════════════════════════════════════════════════════════════════════════


def prepare_segmented_chunks() -> list[dict]:
    """Lädt heuristisch segmentierte Urteils-Chunks (nicht Passau)."""
    items = []
    for fpath in glob.glob(os.path.join(SEG_DIR, "*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception:
            continue

        # Passauer Chunks überspringen
        if doc.get("quelle") == "passau_openlegaldata":
            continue

        chunk_id = doc.get("chunk_id", "")
        text = doc.get("text", "")
        if not chunk_id or not text:
            continue

        segment = doc.get("segment", "")
        meta = flatten_meta(doc)
        meta["source_type"] = "urteil_segmentiert"

        # Embedding-Text: Segment-Label voranstellen für Kontext
        prefix = {
            "leitsatz": "Leitsatz: ",
            "tenor": "Tenor: ",
            "tatbestand": "Tatbestand: ",
            "entscheidungsgruende": "Entscheidungsgründe: ",
            "wuerdigung": "Würdigung des Gerichtshofs: ",
            "sachverhalt": "Sachverhalt: ",
            "vorlagefragen": "Vorlagefragen: ",
        }.get(segment, "")

        items.append({
            "id": f"seg_{chunk_id}",
            "embed_text": f"{prefix}{text}",
            "document": text,
            "meta": meta,
        })

    return items


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 3 – Neue EU-Urteile (noch nicht in ChromaDB)
# ═══════════════════════════════════════════════════════════════════════════


def prepare_new_eu_chunks(existing_ids: set) -> list[dict]:
    """Chunked neue EU-Urteile die noch nicht in ChromaDB sind."""
    items = []
    eu_quellen = {"cellar_eurlex", "eugh_cellar", "gdprhub"}

    for fpath in glob.glob(os.path.join(URTEILE_DIR, "*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception:
            continue

        quelle = doc.get("quelle", "")
        if quelle not in eu_quellen:
            continue

        volltext = doc.get("volltext", "")
        if not volltext or len(volltext) < 200:
            continue

        az = doc.get("aktenzeichen", "")
        doc_id = az or os.path.basename(fpath)

        # Prüfe ob dieses Urteil schon Chunks in der DB hat
        test_id = make_chunk_id("urteil", doc_id, 0)
        if test_id in existing_ids:
            continue

        text_chunks = chunk_text(volltext)
        gericht = doc.get("gericht", "")
        datum = doc.get("datum", "")

        for idx, ct in enumerate(text_chunks):
            cid = make_chunk_id("urteil_eu_new", doc_id, idx)
            meta = {
                "source_type": "urteil",
                "quelle": quelle,
                "gericht": gericht,
                "aktenzeichen": az,
                "datum": datum,
                "chunk_index": idx,
                "total_chunks": len(text_chunks),
            }
            # DSGVO-Artikel-Tags ergänzen
            dsgvo_art = doc.get("dsgvo_artikel", [])
            if dsgvo_art:
                meta["dsgvo_artikel"] = ", ".join(dsgvo_art[:20])

            items.append({
                "id": cid,
                "embed_text": ct,
                "document": ct,
                "meta": meta,
            })

    return items


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 4 – Erwägungsgrund-Verknüpfungen aktualisieren
# ═══════════════════════════════════════════════════════════════════════════


def prepare_eg_updates(existing_ids: set) -> tuple[list[str], list[dict]]:
    """Bereitet angereicherte Erwägungsgrund-Chunks vor."""
    to_delete = []
    to_add = []

    for fpath in glob.glob(os.path.join(GESETZE_DIR, "DSGVO_EG_*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception:
            continue

        erlaeutert = doc.get("erlaeutert_artikel", [])
        if not erlaeutert:
            continue

        para = doc.get("paragraph", "")
        volltext = doc.get("volltext", "") or doc.get("text", "")
        if not volltext:
            continue

        eg_match = re.match(r"Erwägungsgrund\s+(\d+)", para)
        if not eg_match:
            continue
        eg_nr = int(eg_match.group(1))

        # Alten Chunk finden und zum Löschen vormerken
        old_id = make_chunk_id("gesetz", para, 0)
        if old_id in existing_ids:
            to_delete.append(old_id)

        # Neuen angereicherten Embedding-Text
        art_list = ", ".join(erlaeutert)
        embed_text = f"DSGVO Erwägungsgrund {eg_nr} (erläutert {art_list}) – {volltext}"

        meta = {
            "source_type": "gesetz",
            "gesetz": "DSGVO",
            "paragraph": para,
            "erlaeutert_artikel": art_list,
        }

        new_id = f"eg_enriched_{eg_nr}"
        to_add.append({
            "id": new_id,
            "embed_text": embed_text[:8000],  # Limit für Embedding
            "document": volltext,
            "meta": meta,
        })

    return to_delete, to_add


# ═══════════════════════════════════════════════════════════════════════════
# Hauptprogramm
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 60)
    print("OpenLex MVP – ChromaDB Index-Update")
    print("=" * 60)

    t_start = time.time()

    # Modell laden
    print(f"\n  Lade Embedding-Modell: {MODEL_NAME} ...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    print(f"  Modell geladen. Dimension: {model.get_sentence_embedding_dimension()}")

    # ChromaDB öffnen
    print(f"\n  Öffne ChromaDB: {CHROMADB_DIR}")
    import chromadb
    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    initial_count = collection.count()
    print(f"  Collection: {initial_count} Chunks vorhanden.")

    # Vorhandene IDs laden
    print("  Lade vorhandene IDs ...")
    existing_ids: set[str] = set()
    if initial_count > 0:
        stored = collection.get(include=[])
        existing_ids = set(stored["ids"])
    print(f"  {len(existing_ids)} IDs geladen.\n")

    results = {}

    # ── SCHRITT 1: Granulare Gesetzes-Chunks ──
    print("=" * 60)
    print("SCHRITT 1 – Granulare Gesetzes-Chunks")
    print("=" * 60)
    gran_items = prepare_granular_chunks()
    print(f"  {len(gran_items)} granulare Chunks vorbereitet.")
    results["granular"] = add_to_collection(
        collection, model, gran_items, existing_ids, "Granular-Chunks"
    )

    # ── SCHRITT 2: Segmentierte Urteils-Chunks (ohne Passau) ──
    print("\n" + "=" * 60)
    print("SCHRITT 2 – Segmentierte Urteils-Chunks (ohne Passau)")
    print("=" * 60)
    seg_items = prepare_segmented_chunks()
    print(f"  {len(seg_items)} segmentierte Chunks vorbereitet (ohne Passau).")
    results["segmentiert"] = add_to_collection(
        collection, model, seg_items, existing_ids, "Segment-Chunks"
    )

    # ── SCHRITT 3: Neue EU-Urteile ──
    print("\n" + "=" * 60)
    print("SCHRITT 3 – Neue EU-Urteile")
    print("=" * 60)
    eu_items = prepare_new_eu_chunks(existing_ids)
    print(f"  {len(eu_items)} neue EU-Chunks vorbereitet.")
    results["eu_neu"] = add_to_collection(
        collection, model, eu_items, existing_ids, "EU-Chunks"
    )

    # ── SCHRITT 4: Erwägungsgrund-Verknüpfungen ──
    print("\n" + "=" * 60)
    print("SCHRITT 4 – Erwägungsgrund-Verknüpfungen")
    print("=" * 60)
    to_delete, eg_items = prepare_eg_updates(existing_ids)
    print(f"  {len(eg_items)} Erwägungsgründe mit Artikel-Verknüpfung.")

    # Alte Chunks löschen
    if to_delete:
        valid_deletes = [d for d in to_delete if d in existing_ids]
        if valid_deletes:
            collection.delete(ids=valid_deletes)
            for d in valid_deletes:
                existing_ids.discard(d)
            print(f"    {len(valid_deletes)} alte EG-Chunks gelöscht.")

    results["eg_aktualisiert"] = add_to_collection(
        collection, model, eg_items, existing_ids, "EG-Chunks"
    )

    # ── Zusammenfassung ──
    t_elapsed = time.time() - t_start
    final_count = collection.count()

    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"  Granulare Gesetzes-Chunks:       +{results['granular']}")
    print(f"  Segmentierte Urteils-Chunks:     +{results['segmentiert']}")
    print(f"  Neue EU-Urteils-Chunks:          +{results['eu_neu']}")
    print(f"  Aktualisierte EG-Chunks:         +{results['eg_aktualisiert']}")
    print(f"")
    print(f"  ChromaDB vorher:  {initial_count}")
    print(f"  ChromaDB nachher: {final_count}")
    print(f"  Differenz:        +{final_count - initial_count}")
    print(f"  Dauer:            {t_elapsed:.0f}s ({t_elapsed / 60:.1f} min)")

    # Test-Queries
    print("\n  Test-Queries:")
    test_queries = [
        "Art. 6 Abs. 1 lit. f DSGVO berechtigtes Interesse",
        "Recht auf Löschung Erwägungsgrund",
        "Schrems II Standardvertragsklauseln",
    ]
    for q in test_queries:
        emb = model.encode([q]).tolist()
        res = collection.query(
            query_embeddings=emb, n_results=2,
            include=["metadatas", "distances"],
        )
        print(f"\n    Q: '{q}'")
        for i, (meta, dist) in enumerate(
            zip(res["metadatas"][0], res["distances"][0])
        ):
            st = meta.get("source_type", "?")
            label = (meta.get("volladresse") or meta.get("paragraph")
                     or meta.get("aktenzeichen") or meta.get("titel") or "")
            print(f"      {i+1}. [{st}] {label[:50]}  (dist={dist:.4f})")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
