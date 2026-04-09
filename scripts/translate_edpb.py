#!/usr/bin/env python3
"""
translate_edpb.py – Übersetzt englische EDPB-Chunks in ChromaDB ins Deutsche
via Anthropic API (Claude Sonnet), dann re-embeddet sie.

Batch-Verarbeitung: 5 Chunks pro API-Call.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CHROMADB_DIR = str(BASE_DIR / "chromadb")
COLLECTION_NAME = "openlex_datenschutz"
MODEL_NAME = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"
TRANSLATE_MODEL = "claude-sonnet-4-20250514"
BATCH_SIZE = 5  # Chunks pro API-Call
EMBED_BATCH = 50
PROGRESS_FILE = BASE_DIR / "translate_progress.json"

SYSTEM_PROMPT = """Du bist ein juristischer Fachübersetzer für EU-Datenschutzrecht. Übersetze den folgenden englischen Text ins Deutsche. Verwende die offizielle DSGVO-Terminologie:
- controller = Verantwortlicher
- processor = Auftragsverarbeiter
- data subject = betroffene Person
- personal data = personenbezogene Daten
- processing = Verarbeitung
- consent = Einwilligung
- legitimate interest = berechtigtes Interesse
- data protection impact assessment / DPIA = Datenschutz-Folgenabschätzung (DSFA)
- supervisory authority = Aufsichtsbehörde
- data protection officer / DPO = Datenschutzbeauftragter (DSB)
- data breach = Datenpanne / Verletzung des Schutzes personenbezogener Daten
- right of access = Auskunftsrecht
- right to erasure = Recht auf Löschung
- right to rectification = Recht auf Berichtigung
- data portability = Datenübertragbarkeit
- profiling = Profiling
- automated decision-making = automatisierte Einzelentscheidung
- joint controllers = gemeinsam Verantwortliche
- lead supervisory authority = federführende Aufsichtsbehörde
- binding corporate rules = verbindliche interne Datenschutzvorschriften
- standard contractual clauses = Standardvertragsklauseln
- third country = Drittland
- adequacy decision = Angemessenheitsbeschluss
- certification = Zertifizierung
- code of conduct = Verhaltensregeln
- purpose limitation = Zweckbindung
- data minimisation = Datenminimierung
- storage limitation = Speicherbegrenzung
- integrity and confidentiality = Integrität und Vertraulichkeit
- accountability = Rechenschaftspflicht
- transparency = Transparenz
- lawfulness = Rechtmäßigkeit
- fairness = Verarbeitung nach Treu und Glauben
- recipient = Empfänger
- representative = Vertreter
- main establishment = Hauptniederlassung
- filing system = Dateisystem
- restriction of processing = Einschränkung der Verarbeitung
- pseudonymisation = Pseudonymisierung
- anonymisation = Anonymisierung

Behalte Artikelverweise im Originalformat (z.B. Art. 6(1)(f) → Art. 6 Abs. 1 lit. f). Übersetze GDPR zu DSGVO. Übersetze keine Eigennamen, Aktenzeichen oder Zitate. Gib nur die Übersetzung zurück, keinen Kommentar.

Du bekommst nummerierte Texte. Gib die Übersetzungen im gleichen nummerierten Format zurück:
[1]
Übersetzung 1

[2]
Übersetzung 2

usw."""


def _is_english(text: str, meta: dict) -> bool:
    """Prüft ob ein Chunk englisch ist."""
    if meta.get("sprache") == "en":
        return True
    if meta.get("quelle") != "edpb":
        return False
    # Heuristik: englische Schlüsselwörter
    t = text[:500].lower()
    en_words = ["controller", "processor", "data subject", "pursuant to",
                "regulation", "the board", "guidelines", "supervisory authority"]
    hits = sum(1 for w in en_words if w in t)
    return hits >= 2


def _load_progress() -> set:
    """Lädt bereits übersetzte Chunk-IDs."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def _save_progress(done: set):
    """Speichert Fortschritt."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(list(done), f)


def translate_batch(client, texts: list[str]) -> list[str]:
    """Übersetzt einen Batch von Texten via Anthropic API."""
    # Nummerierte Liste erstellen
    prompt_parts = []
    for i, text in enumerate(texts, 1):
        # Kürze sehr lange Texte
        t = text[:3000] if len(text) > 3000 else text
        prompt_parts.append(f"[{i}]\n{t}")

    prompt = "\n\n".join(prompt_parts)

    for attempt in range(8):
        try:
            resp = client.messages.create(
                model=TRANSLATE_MODEL,
                max_tokens=4096 * len(texts),
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = resp.content[0].text

            # Parse nummerierte Antworten
            translations = []
            # Split by [N] markers
            parts = re.split(r"\[(\d+)\]\s*\n?", response_text)
            # parts: ['', '1', 'text1', '2', 'text2', ...]
            parsed = {}
            for j in range(1, len(parts) - 1, 2):
                num = int(parts[j])
                parsed[num] = parts[j + 1].strip()

            for i in range(1, len(texts) + 1):
                if i in parsed:
                    translations.append(parsed[i])
                else:
                    # Fallback: Original behalten
                    translations.append(texts[i - 1])

            return translations

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate_limit" in error_str or "overloaded" in error_str:
                wait = min(60 * (2 ** attempt), 600)
                print(f" RL({attempt+1}), warte {wait}s...", end="", flush=True)
                time.sleep(wait)
            else:
                print(f" Fehler: {e}")
                if attempt >= 3:
                    return texts  # Original zurückgeben
                time.sleep(10)

    return texts  # Fallback


def main():
    import anthropic
    import chromadb

    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
    if not token:
        print("FEHLER: Kein API-Key gefunden (ANTHROPIC_API_KEY oder CLAUDE_CODE_OAUTH_TOKEN)")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=token)
    db_client = chromadb.PersistentClient(path=CHROMADB_DIR)
    col = db_client.get_collection(COLLECTION_NAME)

    print("=" * 60)
    print("  EDPB-Chunks übersetzen (EN → DE)")
    print("=" * 60)

    # Finde alle englischen Chunks
    print("  Suche englische Chunks...", flush=True)
    all_data = col.get(where={"quelle": "edpb"}, include=["documents", "metadatas"], limit=5000)

    en_chunks = []
    for cid, doc, meta in zip(all_data["ids"], all_data["documents"], all_data["metadatas"]):
        if _is_english(doc, meta):
            en_chunks.append({"id": cid, "text": doc, "meta": meta})

    print(f"  {len(en_chunks)} englische Chunks gefunden")

    # Fortschritt laden
    done = _load_progress()
    remaining = [c for c in en_chunks if c["id"] not in done]
    print(f"  {len(done)} bereits übersetzt, {len(remaining)} verbleibend")

    if not remaining:
        print("  Alle bereits übersetzt!")
    else:
        # Übersetzen in Batches
        total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE
        translated_items = []

        for batch_idx in range(0, len(remaining), BATCH_SIZE):
            batch = remaining[batch_idx:batch_idx + BATCH_SIZE]
            batch_num = batch_idx // BATCH_SIZE + 1

            print(f"\n  Batch {batch_num}/{total_batches} ({len(batch)} Chunks)...",
                  end="", flush=True)

            texts = [c["text"] for c in batch]
            translations = translate_batch(client, texts)

            for chunk, translation in zip(batch, translations):
                chunk["translated"] = translation
                translated_items.append(chunk)
                done.add(chunk["id"])

            print(f" OK", flush=True)

            # Fortschritt speichern alle 10 Batches
            if batch_num % 10 == 0:
                _save_progress(done)
                print(f"  [Fortschritt gespeichert: {len(done)}/{len(en_chunks)}]")

            # Rate-Limiting: 3s Pause zwischen Batches
            time.sleep(3)

        _save_progress(done)

        # ChromaDB aktualisieren
        print(f"\n{'='*60}")
        print(f"  ChromaDB aktualisieren ({len(translated_items)} Chunks)")
        print(f"{'='*60}")

        update_batch = 500
        for bs in range(0, len(translated_items), update_batch):
            be = min(bs + update_batch, len(translated_items))
            batch = translated_items[bs:be]

            ids = [c["id"] for c in batch]
            docs = [c["translated"] for c in batch]
            metas = []
            for c in batch:
                m = dict(c["meta"])
                m["sprache"] = "de"
                m["uebersetzt_aus"] = "en"
                metas.append(m)

            col.update(ids=ids, documents=docs, metadatas=metas)
            print(f"  Metadaten+Text aktualisiert: {bs+1}-{be}")

    # Re-Embedding
    print(f"\n{'='*60}")
    print(f"  Re-Embedding aller übersetzten Chunks")
    print(f"{'='*60}")

    # Hole aktuelle Daten (nach Übersetzung)
    all_translated = col.get(
        where={"quelle": "edpb"},
        include=["documents", "metadatas"],
        limit=5000
    )

    # Filtere auf übersetzte Chunks
    to_embed = []
    for cid, doc, meta in zip(all_translated["ids"], all_translated["documents"], all_translated["metadatas"]):
        if meta.get("uebersetzt_aus") == "en" or meta.get("sprache") == "de":
            to_embed.append({"id": cid, "text": doc, "meta": meta})

    if not to_embed:
        # Alle EDPB Chunks re-embedden
        to_embed = [{"id": cid, "text": doc, "meta": meta}
                    for cid, doc, meta in zip(all_translated["ids"], all_translated["documents"], all_translated["metadatas"])]

    print(f"  {len(to_embed)} Chunks re-embedden...")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)

    for bs in range(0, len(to_embed), EMBED_BATCH):
        be = min(bs + EMBED_BATCH, len(to_embed))
        batch = to_embed[bs:be]

        # Enriched embedding text (wie in refine_behoerden.py)
        embed_texts = []
        for c in batch:
            parts = [c["meta"].get("titel", "")]
            abschnitt = c["meta"].get("abschnitt", "")
            if abschnitt and abschnitt != "Einleitung":
                parts.append(abschnitt)
            themen = c["meta"].get("themen", "")
            if themen:
                parts.append(f"Themen: {themen}")
            parts.append(c["text"][:4000])
            embed_texts.append(" – ".join(parts))

        embeddings = model.encode(embed_texts, show_progress_bar=False).tolist()

        col.update(
            ids=[c["id"] for c in batch],
            embeddings=embeddings,
        )
        print(f"  Re-embedded: {bs+1}-{be}")

    print(f"\n  Fertig! {len(to_embed)} Chunks übersetzt und re-embedded.")

    # Cleanup
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()


if __name__ == "__main__":
    main()
