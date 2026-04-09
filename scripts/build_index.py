#!/usr/bin/env python3
"""
build_index.py – Drei-Schritt-Pipeline:
  1. Chunking aller gesammelten Dokumente → chunks.jsonl
  2. Embedding + ChromaDB-Indexierung
  3. Regelbasierter Knowledge Graph in Neo4j (optional)
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import time
from typing import Any

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
DATA_DIR = os.path.join(BASE_DIR, "data")
CHUNKS_FILE = os.path.join(DATA_DIR, "chunks.jsonl")
CHROMADB_DIR = os.path.join(BASE_DIR, "chromadb")
COLLECTION_NAME = "openlex_datenschutz"

EMBEDDING_MODEL = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"
EMBED_BATCH_SIZE = 100

# Chunking-Parameter (in Zeichen; ~1 Token ≈ 4 Zeichen im Deutschen)
CHUNK_TARGET_CHARS = 2400   # ~600 Token
CHUNK_MIN_CHARS = 2000      # ~500 Token
CHUNK_MAX_CHARS = 3200      # ~800 Token
OVERLAP_CHARS = 400         # ~100 Token

# Neo4j
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "openlex"

# Quellverzeichnisse
SOURCE_DIRS = {
    "gesetz":    os.path.join(DATA_DIR, "gesetze"),
    "urteil":    os.path.join(DATA_DIR, "urteile"),
    "leitlinie": os.path.join(DATA_DIR, "leitlinien"),
    "behoerde":  os.path.join(DATA_DIR, "behoerden"),
}

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

# Regex: Satzende = Punkt/Ausrufezeichen/Fragezeichen gefolgt von Leerzeichen
# oder Ende. Nicht nach typischen Abkürzungen (Art., Abs., Nr., Satz, vgl., etc.)
SATZ_ENDE_RE = re.compile(
    r"(?<!\bArt)(?<!\bAbs)(?<!\bNr)(?<!\bBsp)(?<!\bvgl)(?<!\bzB)"
    r"(?<!\bBGBl)(?<!\bBVerfG)(?<!\bBGH)(?<!\bBSG)(?<!\bBFH)"
    r"(?<!\bS)(?<!\blit)(?<!\bds)(?<!\bggf)(?<!\bzw)(?<!\bd\.h)"
    r"(?<!\bi\.S)(?<!\bi\.V)(?<!\bu\.a)(?<!\bDr)(?<!\bProf)"
    r"[.!?]\s",
    re.UNICODE,
)


def find_sentence_boundary(text: str, target_pos: int) -> int:
    """Findet das nächste Satzende ab target_pos."""
    search_start = max(0, target_pos - 50)
    search_window = text[search_start:target_pos + 300]

    best = None
    for m in SATZ_ENDE_RE.finditer(search_window):
        abs_pos = search_start + m.end()
        if abs_pos >= target_pos:
            if best is None or abs_pos < best:
                best = abs_pos
            break  # Erstes Satzende nach target_pos nehmen

    return best if best is not None else min(target_pos, len(text))


def chunk_text(text: str) -> list[str]:
    """Teilt Text in überlappende Chunks, ohne mitten im Satz abzuschneiden."""
    if not text or len(text) < CHUNK_MIN_CHARS:
        return [text] if text else []

    chunks = []
    pos = 0
    text_len = len(text)

    while pos < text_len:
        remaining = text_len - pos

        # Letzter Chunk: alles nehmen wenn kürzer als max
        if remaining <= CHUNK_MAX_CHARS:
            chunk = text[pos:].strip()
            if chunk:
                chunks.append(chunk)
            break

        # Satzende nahe target suchen
        boundary = find_sentence_boundary(text, pos + CHUNK_TARGET_CHARS)

        # Sicherstellen dass Chunk nicht zu kurz oder zu lang wird
        chunk_end = max(boundary, pos + CHUNK_MIN_CHARS)
        chunk_end = min(chunk_end, pos + CHUNK_MAX_CHARS)

        chunk = text[pos:chunk_end].strip()
        if chunk:
            chunks.append(chunk)

        # Nächster Chunk mit Overlap
        pos = chunk_end - OVERLAP_CHARS
        if pos <= (chunk_end - CHUNK_MIN_CHARS):
            pos = chunk_end  # Kein Overlap wenn Chunk zu kurz

    return chunks


def make_chunk_id(source_type: str, doc_id: str, chunk_index: int) -> str:
    """Erzeugt eine deterministische Chunk-ID."""
    raw = f"{source_type}:{doc_id}:{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def flatten_meta(doc: dict) -> dict[str, Any]:
    """Flacht Metadaten für ChromaDB ab (nur str/int/float/bool)."""
    flat = {}
    for k, v in doc.items():
        if k in ("text", "volltext"):
            continue
        if isinstance(v, list):
            flat[k] = ", ".join(str(x) for x in v[:50])
        elif isinstance(v, (str, int, float, bool)):
            flat[k] = v
        elif v is None:
            flat[k] = ""
        else:
            flat[k] = str(v)
    return flat


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 1 – Chunking
# ═══════════════════════════════════════════════════════════════════════════


def step1_chunking() -> list[dict]:
    """Liest alle JSON-Dateien und erzeugt Chunks."""
    print("=" * 60)
    print("SCHRITT 1 – Chunking")
    print("=" * 60)

    all_chunks: list[dict] = []
    counts: dict[str, int] = {}

    for source_type, src_dir in SOURCE_DIRS.items():
        if not os.path.isdir(src_dir):
            print(f"  {source_type}: Verzeichnis nicht gefunden. Überspringe.")
            continue

        json_files = sorted(glob.glob(os.path.join(src_dir, "*.json")))
        print(f"\n  {source_type}: {len(json_files)} Dateien")
        type_count = 0

        for fpath in json_files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    doc = json.load(f)
            except Exception:
                continue

            # Text-Feld bestimmen
            text = doc.get("text") or doc.get("volltext") or ""
            if not text or len(text.strip()) < 20:
                continue

            # Dokument-ID für Deduplizierung
            doc_id = (
                doc.get("aktenzeichen")
                or doc.get("paragraph")
                or doc.get("titel")
                or os.path.basename(fpath)
            )

            if source_type == "gesetz":
                # Gesetze: Jeder Paragraph = ein Chunk
                chunk_data = {
                    "chunk_id": make_chunk_id(source_type, doc_id, 0),
                    "chunk_index": 0,
                    "source_type": source_type,
                    "text": text.strip(),
                }
                # Metadaten übernehmen
                for k in ("gesetz", "paragraph", "ueberschrift", "verweise"):
                    if k in doc:
                        chunk_data[k] = doc[k]
                all_chunks.append(chunk_data)
                type_count += 1

            else:
                # Urteile, Leitlinien, Behördendokumente: Chunking
                text_chunks = chunk_text(text)
                meta_keys = [k for k in doc.keys() if k not in ("text", "volltext")]

                for idx, chunk_text_str in enumerate(text_chunks):
                    chunk_data = {
                        "chunk_id": make_chunk_id(source_type, doc_id, idx),
                        "chunk_index": idx,
                        "total_chunks": len(text_chunks),
                        "source_type": source_type,
                        "text": chunk_text_str,
                    }
                    for k in meta_keys:
                        chunk_data[k] = doc[k]
                    all_chunks.append(chunk_data)
                    type_count += 1

        counts[source_type] = type_count
        print(f"    → {type_count} Chunks erzeugt")

    # JSONL schreiben
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"\n  Gespeichert: {CHUNKS_FILE}")
    print(f"  Dateigröße:  {os.path.getsize(CHUNKS_FILE) / 1024 / 1024:.1f} MB")
    print(f"\n  {'Typ':<15} {'Chunks':>10}")
    print("  " + "-" * 27)
    total = 0
    for st, c in counts.items():
        print(f"  {st:<15} {c:>10}")
        total += c
    print("  " + "-" * 27)
    print(f"  {'GESAMT':<15} {total:>10}")

    return all_chunks


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 2 – Embedding + ChromaDB
# ═══════════════════════════════════════════════════════════════════════════


def step2_embedding(chunks: list[dict]) -> None:
    """Embeddet alle Chunks und speichert sie in ChromaDB."""
    print("\n" + "=" * 60)
    print("SCHRITT 2 – Embedding + ChromaDB")
    print("=" * 60)

    t_start = time.time()

    # Modell laden
    print(f"\n  Lade Embedding-Modell: {EMBEDDING_MODEL} ...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDING_MODEL)
    embed_dim = model.get_sentence_embedding_dimension()
    print(f"  Modell geladen. Dimension: {embed_dim}")

    # ChromaDB initialisieren
    print(f"\n  Initialisiere ChromaDB in {CHROMADB_DIR} ...")
    import chromadb
    client = chromadb.PersistentClient(path=CHROMADB_DIR)

    # Collection holen oder erstellen (Resume-fähig)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    existing_count = collection.count()
    print(f"  Collection '{COLLECTION_NAME}': {existing_count} Chunks vorhanden.")

    # Bereits vorhandene IDs ermitteln für Resume
    existing_ids: set[str] = set()
    if existing_count > 0:
        stored = collection.get(include=[])
        existing_ids = set(stored["ids"])
        print(f"  {len(existing_ids)} Chunks bereits indexiert – überspringe diese.")

    # Nur neue Chunks verarbeiten
    new_chunks = [c for c in chunks if c["chunk_id"] not in existing_ids]
    total_new = len(new_chunks)
    total_all = len(chunks)
    print(f"\n  Embedde und indexiere {total_new} neue Chunks "
          f"(von {total_all} gesamt) in Batches von {EMBED_BATCH_SIZE} ...")

    if total_new == 0:
        print("  Alle Chunks bereits indexiert. Überspringe Embedding.")
    else:
        for batch_start in range(0, total_new, EMBED_BATCH_SIZE):
            batch_end = min(batch_start + EMBED_BATCH_SIZE, total_new)
            batch = new_chunks[batch_start:batch_end]

            texts = [c["text"] for c in batch]
            ids = [c["chunk_id"] for c in batch]
            metadatas = [flatten_meta(c) for c in batch]

            # Embeddings berechnen
            embeddings = model.encode(texts, show_progress_bar=False).tolist()

            # In ChromaDB speichern
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )

            done = existing_count + batch_end
            pct = done / total_all * 100
            print(f"    {done:>6}/{total_all} ({pct:5.1f}%)", end="\r")

    t_elapsed = time.time() - t_start

    print(f"\n\n  ChromaDB-Collection: {collection.count()} Chunks gespeichert")
    print(f"  Dauer: {t_elapsed:.0f}s ({t_elapsed / 60:.1f} min)")
    print(f"  Verzeichnis: {CHROMADB_DIR}")

    # Schneller Testquery
    print("\n  Test-Query: 'Recht auf Löschung personenbezogener Daten'")
    test_emb = model.encode(["Recht auf Löschung personenbezogener Daten"]).tolist()
    results = collection.query(
        query_embeddings=test_emb,
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )
    for i, (doc_text, meta, dist) in enumerate(
        zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
    ):
        st = meta.get("source_type", "?")
        title = (meta.get("paragraph") or meta.get("aktenzeichen")
                 or meta.get("titel") or "")
        print(f"    {i+1}. [{st}] {title[:50]}  (dist={dist:.4f})")
        print(f"       {doc_text[:100]}...")


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 3 – Knowledge Graph (Neo4j)
# ═══════════════════════════════════════════════════════════════════════════

# Regex für Norm-Parsing
RE_GESETZ_PARA = re.compile(r"§§?\s*(\d+[a-z]?)\s+([A-Za-zÄÖÜäöüß]+)")
RE_ART_NORM = re.compile(r"Art\.?\s*(\d+)\s+([A-Za-zÄÖÜäöüß]+)")

# DSGVO → BDSG Konkretisierungen (vereinfacht)
KONKRETISIERUNGEN = [
    ("DSGVO", "BDSG"),
    ("BDSG", "LDSG"),  # Landesdatenschutzgesetze allgemein
]


def parse_normverweis(verweis: str) -> tuple[str, str] | None:
    """Parst einen Normverweis in (Gesetz, Paragraph/Artikel)."""
    m = RE_ART_NORM.match(verweis)
    if m:
        return (m.group(2), f"Art. {m.group(1)}")

    m = RE_GESETZ_PARA.match(verweis)
    if m:
        return (m.group(2), f"§ {m.group(1)}")

    return None


def step3_knowledge_graph(chunks: list[dict]) -> None:
    """Erstellt einen regelbasierten Knowledge Graph in Neo4j."""
    print("\n" + "=" * 60)
    print("SCHRITT 3 – Knowledge Graph (Neo4j)")
    print("=" * 60)

    # Neo4j importieren
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("\n  WARNUNG: neo4j-Paket nicht installiert.")
        print("  Installiere mit: pip install neo4j")
        return

    # Verbindung testen
    print(f"\n  Verbinde mit {NEO4J_URI} ...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("  Verbunden!")
    except Exception as e:
        print(f"\n  WARNUNG: Neo4j nicht erreichbar: {e}")
        print("\n  Um Neo4j per Docker zu starten:")
        print("  ┌─────────────────────────────────────────────────────────┐")
        print("  │ docker run -d --name neo4j \\                           │")
        print("  │   -p 7474:7474 -p 7687:7687 \\                         │")
        print("  │   -e NEO4J_AUTH=neo4j/openlex \\                        │")
        print("  │   neo4j:latest                                         │")
        print("  └─────────────────────────────────────────────────────────┘")
        print("\n  Nach dem Start: http://localhost:7474 im Browser öffnen.")
        print("  Schritt 3 wird übersprungen. Schritte 1+2 sind abgeschlossen.")
        return

    t_start = time.time()

    with driver.session() as session:
        # Datenbank leeren
        print("  Lösche bestehende Daten ...")
        session.run("MATCH (n) DETACH DELETE n")

        # Constraints erstellen
        print("  Erstelle Constraints ...")
        for label in ["Norm", "Entscheidung", "Gesetz"]:
            try:
                session.run(
                    f"CREATE CONSTRAINT IF NOT EXISTS "
                    f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                )
            except Exception:
                pass

        # ── Normen-Knoten aus Gesetzen ──
        print("\n  Erstelle Norm-Knoten ...")
        norm_count = 0
        gesetze_dir = SOURCE_DIRS["gesetz"]
        gesetze_set = set()

        for fpath in glob.glob(os.path.join(gesetze_dir, "*.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    doc = json.load(f)
            except Exception:
                continue

            gesetz = doc.get("gesetz", "")
            para = doc.get("paragraph", "")
            titel = doc.get("ueberschrift", "")
            if not gesetz or not para:
                continue

            norm_id = f"{gesetz}_{para}"
            gesetze_set.add(gesetz)

            session.run(
                """
                MERGE (n:Norm {id: $id})
                SET n.gesetz = $gesetz,
                    n.paragraph = $para,
                    n.titel = $titel
                """,
                id=norm_id, gesetz=gesetz, para=para, titel=titel,
            )
            norm_count += 1

        # Gesetz-Knoten
        for gesetz in gesetze_set:
            session.run(
                "MERGE (g:Gesetz {id: $id}) SET g.name = $id",
                id=gesetz,
            )
            # Norm → Gesetz Zugehörigkeit
            session.run(
                """
                MATCH (n:Norm), (g:Gesetz)
                WHERE n.gesetz = $gesetz AND g.id = $gesetz
                MERGE (n)-[:GEHOERT_ZU]->(g)
                """,
                gesetz=gesetz,
            )

        print(f"    {norm_count} Norm-Knoten, {len(gesetze_set)} Gesetz-Knoten")

        # ── Entscheidungs-Knoten ──
        print("  Erstelle Entscheidungs-Knoten ...")
        urteil_count = 0
        urteile_dir = SOURCE_DIRS["urteil"]

        for fpath in glob.glob(os.path.join(urteile_dir, "*.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    doc = json.load(f)
            except Exception:
                continue

            az = doc.get("aktenzeichen", "")
            if not az:
                continue

            session.run(
                """
                MERGE (e:Entscheidung {id: $id})
                SET e.gericht = $gericht,
                    e.datum = $datum,
                    e.quelle = $quelle
                """,
                id=az,
                gericht=doc.get("gericht", ""),
                datum=doc.get("datum", ""),
                quelle=doc.get("quelle", ""),
            )
            urteil_count += 1

            # ── Kanten: Urteil → WENDET_AN → Norm ──
            normbezuege = doc.get("normbezuege", [])
            for verweis in normbezuege:
                parsed = parse_normverweis(verweis)
                if not parsed:
                    continue
                gesetz_name, para_name = parsed
                norm_id = f"{gesetz_name}_{para_name}"

                session.run(
                    """
                    MATCH (e:Entscheidung {id: $az})
                    MERGE (n:Norm {id: $norm_id})
                    ON CREATE SET n.gesetz = $gesetz, n.paragraph = $para
                    MERGE (e)-[:WENDET_AN]->(n)
                    """,
                    az=az, norm_id=norm_id,
                    gesetz=gesetz_name, para=para_name,
                )

        print(f"    {urteil_count} Entscheidungs-Knoten")

        # ── Kanten: Norm → VERWEIST_AUF → Norm ──
        print("  Erstelle Norm-Verweiskanten ...")
        verweis_count = 0

        for fpath in glob.glob(os.path.join(gesetze_dir, "*.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    doc = json.load(f)
            except Exception:
                continue

            gesetz = doc.get("gesetz", "")
            para = doc.get("paragraph", "")
            if not gesetz or not para:
                continue
            source_id = f"{gesetz}_{para}"

            for verweis in doc.get("verweise", []):
                parsed = parse_normverweis(verweis)
                if not parsed:
                    continue
                target_gesetz, target_para = parsed
                target_id = f"{target_gesetz}_{target_para}"

                if target_id == source_id:
                    continue  # Kein Selbstverweis

                session.run(
                    """
                    MATCH (s:Norm {id: $src})
                    MERGE (t:Norm {id: $tgt})
                    ON CREATE SET t.gesetz = $gesetz, t.paragraph = $para
                    MERGE (s)-[:VERWEIST_AUF]->(t)
                    """,
                    src=source_id, tgt=target_id,
                    gesetz=target_gesetz, para=target_para,
                )
                verweis_count += 1

        print(f"    {verweis_count} VERWEIST_AUF-Kanten")

        # ── Hierarchie: DSGVO → KONKRETISIERT_DURCH → BDSG ──
        print("  Erstelle Hierarchie-Kanten ...")
        for parent, child in KONKRETISIERUNGEN:
            session.run(
                """
                MERGE (p:Gesetz {id: $parent})
                MERGE (c:Gesetz {id: $child})
                MERGE (p)-[:KONKRETISIERT_DURCH]->(c)
                """,
                parent=parent, child=child,
            )

        # ── Statistiken ──
        node_result = session.run("MATCH (n) RETURN count(n) AS cnt").single()
        edge_result = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()

        edge_types = session.run(
            "MATCH ()-[r]->() RETURN type(r) AS typ, count(r) AS cnt "
            "ORDER BY cnt DESC"
        ).data()

        t_elapsed = time.time() - t_start

        print(f"\n  Knoten gesamt:  {node_result['cnt']}")
        print(f"  Kanten gesamt:  {edge_result['cnt']}")
        print(f"\n  {'Kantentyp':<25} {'Anzahl':>10}")
        print("  " + "-" * 37)
        for row in edge_types:
            print(f"  {row['typ']:<25} {row['cnt']:>10}")
        print(f"\n  Dauer: {t_elapsed:.1f}s")

    driver.close()
    print("  Neo4j-Verbindung geschlossen.")


# ═══════════════════════════════════════════════════════════════════════════
# Hauptprogramm
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 60)
    print("OpenLex MVP – Index-Builder")
    print("=" * 60)

    # Schritt 1
    chunks = step1_chunking()

    # Schritt 2
    step2_embedding(chunks)

    # Schritt 3
    step3_knowledge_graph(chunks)

    print("\n" + "=" * 60)
    print("FERTIG – Alle Schritte abgeschlossen.")
    print("=" * 60)


if __name__ == "__main__":
    main()
