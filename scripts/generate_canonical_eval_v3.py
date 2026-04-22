#!/usr/bin/env python3
"""
Canonical-Eval-Generator v3 – Weiterentwicklung von v2.

Wichtigste Änderungen gegenüber v2:
- Neues LLM-Prompt-Template: LLM extrahiert 'main_norms' (2-4 zentrale Normen)
  statt allgemeiner 'expected_norms'
- Flipped Gold-Logik:
    must  = Gesetzes-Chunks aus LLM-extrahierten main_norms
    should = MW-Quell-Chunk (Traceability) + Erwägungsgründe aus normbezuege
- MW-Chunks explizit aus must gefiltert (nur in should)
- Warnung wenn must_ids leer (rein methodische Chunks)

Schema: eval_v3.py-kompatibel (gold_ids, should_ids, forbidden_ids auf Top-Level).

Verwendung:
  python scripts/generate_canonical_eval_v3.py --limit 5 --output eval_sets/canonical_v3.json --overwrite
  python scripts/generate_canonical_eval_v3.py --all --output eval_sets/canonical_v3.json --resume
  python scripts/generate_canonical_eval_v3.py --all --output eval_sets/canonical_v3.json --overwrite
"""
import os
import sys
import json
import re
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import chromadb
from dotenv import load_dotenv
import requests

load_dotenv("/opt/openlex-mvp/.env")

CHROMA_PATH = "/opt/openlex-mvp/chromadb"
COLLECTION_NAME = "openlex_datenschutz"

# ─────────────────────────────────────────────
# Globales Lookup-Mapping (ChromaDB-ID → normalized_id)
# wird einmalig beim Start gebaut
# ─────────────────────────────────────────────

_chroma_to_norm: Dict[str, str] = {}  # ChromaDB-ID → normalized_id
_norm_to_chroma: Dict[str, str] = {}  # normalized_id → ChromaDB-ID
_granular_by_gesetz: Dict[str, List[Tuple[str, str]]] = {}  # gesetz → [(chroma_id, norm_id)]


def _normalize_meta(meta: dict, doc: str) -> str:
    """Exakt wie eval_v3._normalize_id."""
    chunk_id = (
        meta.get("chunk_id", "")
        or meta.get("volladresse", "")
        or meta.get("thema", "")
        or doc[:60]
    )
    return chunk_id.strip()


def build_lookup_index(col) -> None:
    """Baut globale Lookup-Tabellen für alle gesetz_granular- und MW-Chunks."""
    global _chroma_to_norm, _norm_to_chroma, _granular_by_gesetz

    print("Baue Lookup-Index für Norm-Resolver...")

    # gesetz_granular (BDSG, DDG, TDDDG)
    r = col.get(
        where={"source_type": "gesetz_granular"},
        include=["metadatas", "documents"],
        limit=2000
    )
    for chroma_id, meta, doc in zip(r["ids"], r["metadatas"], r["documents"]):
        norm_id = _normalize_meta(meta, doc)
        _chroma_to_norm[chroma_id] = norm_id
        _norm_to_chroma[norm_id] = chroma_id
        gesetz = meta.get("gesetz", "?")
        if gesetz not in _granular_by_gesetz:
            _granular_by_gesetz[gesetz] = []
        _granular_by_gesetz[gesetz].append((chroma_id, norm_id))

    # methodenwissen
    mw = col.get(
        where={"source_type": "methodenwissen"},
        include=["metadatas", "documents"]
    )
    for chroma_id, meta, doc in zip(mw["ids"], mw["metadatas"], mw["documents"]):
        norm_id = _normalize_meta(meta, doc)
        _chroma_to_norm[chroma_id] = norm_id
        _norm_to_chroma[norm_id] = chroma_id

    print(f"  Index gebaut: {len(_chroma_to_norm)} ChromaDB-IDs, {len(_granular_by_gesetz)} Gesetze")
    for g, items in sorted(_granular_by_gesetz.items()):
        print(f"    {g}: {len(items)} chunks")


# ─────────────────────────────────────────────
# Norm-Resolver (identisch zu v2, plus MW-Filter)
# ─────────────────────────────────────────────

_resolve_cache: Dict[str, List[str]] = {}


def resolve_norm_to_chunk_ids(norm_text: str, col=None, all_ids=None) -> List[str]:
    """
    Hierarchische Auflösung: gibt rohe ChromaDB-IDs zurück.
    Wählt gröbste passende Ebene – keine Satz-Explosion.
    col und all_ids werden für Signatur-Kompatibilität akzeptiert, aber nicht benötigt.
    """
    norm = norm_text.strip()
    if norm in _resolve_cache:
        return _resolve_cache[norm]

    result = []

    # 1. Primärrecht (GRCh, AEUV, EUV, GG) – nicht im Korpus
    if re.search(r'\bGRCh\b|\bAEUV\b|\bEUV\b|\bGG\b', norm, re.IGNORECASE):
        print(f"  [INFO] Primärrecht: '{norm}' – übersprungen")
        _resolve_cache[norm] = []
        return []

    # 2. Andere externe Gesetze ohne Chunks
    if re.search(r'\bBGB\b|\bHGB\b|\bUWG\b|\bBetrVG\b|\bSGB\b|\bAO\b|\bTKG\b', norm, re.IGNORECASE):
        print(f"  [INFO] Externes Gesetz: '{norm}' – übersprungen")
        _resolve_cache[norm] = []
        return []

    # 3. DSGVO-Erwägungsgrund: "EG 47", "Erwägungsgrund 47", "ErwGr. 47"
    m = re.search(r'(?:Erw[äa]gungsgrund|ErwGr\.?|EG(?:\s+Nr\.?)?)\s*(\d+)', norm, re.IGNORECASE)
    if m:
        print(f"  [INFO] Erwägungsgrund: '{norm}' – kein stabiler chunk_id → übersprungen")
        _resolve_cache[norm] = []
        return []

    # 4. DSGVO-Artikel: "Art. 6 DSGVO", "Art. 6 Abs. 1 lit. f DSGVO"
    m = re.search(r'Art\.?\s*(\d+)(?:.*?)DSGVO', norm, re.IGNORECASE)
    if m:
        art_nr = m.group(1)
        dsgvo_chunks = _granular_by_gesetz.get("DSGVO", [])
        matching = [cid for cid, _ in dsgvo_chunks
                    if cid == f"dsgvo_art_{art_nr}" or
                    re.match(rf"^dsgvo_art_{art_nr}_part\d+$", cid)]
        if not matching:
            print(f"  [WARN] Kein DSGVO-Chunk fuer Art. {art_nr} gefunden (norm='{norm}')")
        else:
            print(f"  [INFO] DSGVO Art. {art_nr} -> {matching}")
        _resolve_cache[norm] = matching
        return matching

    # 5. BDSG: "§ 26 BDSG", "§ 26 Abs. 1 BDSG", "§ 26 Abs. 1 S. 1 BDSG"
    m = re.search(r'§\s*(\d+[a-z]?)(?:\s+Abs\.?\s*(\d+))?(?:\s+S(?:atz)?\.?\s*(\d+))?\s+BDSG', norm, re.IGNORECASE)
    if m:
        para, abs_nr, satz = m.group(1), m.group(2), m.group(3)
        chunks = _granular_by_gesetz.get("BDSG", [])
        if abs_nr and satz:
            target = f"gran_BDSG_§_{para}_Abs.{abs_nr}_S.{satz}"
            result = [cid for cid, _ in chunks if cid == target]
        elif abs_nr:
            target = f"gran_BDSG_§_{para}_Abs.{abs_nr}"
            result = [cid for cid, _ in chunks if cid == target]
            if not result:
                fallback = f"gran_BDSG_§_{para}_Abs.{abs_nr}_S.1"
                result = [cid for cid, _ in chunks if cid == fallback]
        else:
            target = f"gran_BDSG_§_{para}_Abs.1"
            result = [cid for cid, _ in chunks if cid == target]
            if not result:
                fallback = f"gran_BDSG_§_{para}_Abs.1_S.1"
                result = [cid for cid, _ in chunks if cid == fallback]
        _resolve_cache[norm] = result
        return result

    # 6. TDDDG/TTDSG: "§ 25 TDDDG", "§ 25 TTDSG"
    m = re.search(r'§\s*(\d+[a-z]?)(?:\s+Abs\.?\s*(\d+))?(?:\s+S(?:atz)?\.?\s*(\d+))?\s+(TDDDG|TTDSG)', norm, re.IGNORECASE)
    if m:
        para = m.group(1)
        chunks = _granular_by_gesetz.get("TDDDG", [])
        exact_chroma = f"gran_TDDDG_§_{para}"
        result = [cid for cid, _ in chunks
                  if cid == exact_chroma or cid.startswith(exact_chroma + "_part")]
        _resolve_cache[norm] = result
        return result

    # 7. DDG: "§ 1 DDG", "§ 1 Abs. 2 DDG"
    m = re.search(r'§\s*(\d+[a-z]?)(?:\s+Abs\.?\s*(\d+))?(?:\s+S(?:atz)?\.?\s*(\d+))?\s+DDG', norm, re.IGNORECASE)
    if m:
        para, abs_nr, satz = m.group(1), m.group(2), m.group(3)
        chunks = _granular_by_gesetz.get("DDG", [])
        if abs_nr and satz:
            target = f"gran_DDG_§_{para}_Abs.{abs_nr}_S.{satz}"
            result = [cid for cid, _ in chunks if cid == target]
        elif abs_nr:
            target = f"gran_DDG_§_{para}_Abs.{abs_nr}"
            result = [cid for cid, _ in chunks if cid == target]
            if not result:
                fallback = f"gran_DDG_§_{para}_Abs.{abs_nr}_S.1"
                result = [cid for cid, _ in chunks if cid == fallback]
        else:
            target = f"gran_DDG_§_{para}_Abs.1"
            result = [cid for cid, _ in chunks if cid == target]
            if not result:
                fallback = f"gran_DDG_§_{para}_Abs.1_S.1"
                result = [cid for cid, _ in chunks if cid == fallback]
        _resolve_cache[norm] = result
        return result

    # 8. Nicht erkannt
    print(f"  [WARN] Norm nicht erkannt: '{norm}' – übersprungen")
    _resolve_cache[norm] = []
    return []


def parse_normbezuege(normbezuege_str: str) -> List[str]:
    """Splittet den Freitext-normbezuege-String in einzelne Norm-Referenzen."""
    if not normbezuege_str:
        return []
    parts = re.split(r'\s*[,;]\s*', normbezuege_str)
    return [p.strip() for p in parts if p.strip()]


def parse_norm_reference(norm_ref: str) -> Optional[dict]:
    """Erkennt ob eine Norm-Referenz ein Erwägungsgrund ist."""
    m = re.search(r'(?:Erw[äa]gungsgrund|ErwGr\.?|EG(?:\s+Nr\.?)?)\s*(\d+)', norm_ref, re.IGNORECASE)
    if m:
        return {"gesetz": "DSGVO_EG", "nr": m.group(1)}
    return None


# ─────────────────────────────────────────────
# LLM-API
# ─────────────────────────────────────────────

MISTRAL_API_KEY = os.getenv("MISTRAL_KEY") or os.getenv("MISTRAL_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")


def call_llm(prompt: str, temperature: float = 0.2) -> Tuple[str, int, int]:
    """Ruft Mistral API auf. Fallback: OpenRouter. Gibt (response_text, in_tokens, out_tokens) zurück."""

    if MISTRAL_API_KEY:
        try:
            resp = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "mistral-medium-latest",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "response_format": {"type": "json_object"}
                },
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        except Exception as e:
            print(f"  [WARN] Mistral fehlgeschlagen: {e}, versuche OpenRouter...")

    # Fallback: OpenRouter
    if OPENROUTER_KEY:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://openlex.de",
                "X-Title": "OpenLex Eval Generator v3"
            },
            json={
                "model": "mistralai/mistral-small-3.1",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature
            },
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)

    raise RuntimeError("Weder MISTRAL_KEY noch OPENROUTER_KEY konfiguriert")


# ─────────────────────────────────────────────
# LLM-Prompt (v3: main_norms statt expected_norms)
# ─────────────────────────────────────────────

PROMPT_TEMPLATE = """Du bist ein juristischer Evaluations-Experte für deutsches Datenschutzrecht.

Du erhältst einen Methodenwissen-Chunk aus einem RAG-System.

Aufgabe:
1. Formuliere EINE realistische juristische Frage, deren Antwort in diesem Text steht.
   - Nicht als Ja/Nein-Frage
   - Wie ein Datenschutzbeauftragter, Unternehmer oder Jurist sie stellen würde
   - Nicht wörtlich die Überschrift wiederholen

2. main_norms: Die 2-4 wichtigsten Hauptnormen (nicht alle!), die in einer korrekten 
   Antwort ZWINGEND erwähnt werden müssen. Nur die zentralen Rechtsgrundlagen,
   keine Randnormen. Exakte Zitierform (z.B. "Art. 6 Abs. 1 lit. f DSGVO").
   
3. expected_keywords: 3-5 juristische Schlüsselbegriffe, die in einer guten Antwort vorkommen müssen.

Antworte NUR als reines JSON-Objekt (kein Markdown):
{{
  "question": "...",
  "main_norms": ["Art. X DSGVO", "§ Y BDSG"],
  "expected_keywords": ["Begriff1", "Begriff2", "Begriff3"]
}}

Thema: {thema}
Normbezüge im Chunk: {normbezuege}
Text:
{document}"""


# ─────────────────────────────────────────────
# Kategorie-Ableitung
# ─────────────────────────────────────────────

def derive_category(thema: str) -> str:
    """Leitet Kategorie aus MW-Thema ab."""
    t = thema.lower()
    if any(k in t for k in ["art. 5", "art. 6", "art. 7", "art. 9", "rechtsgrundlag", "erlaubnis", "verbot mit erlaubnis"]):
        return "rechtsgrundlagen"
    if any(k in t for k in ["art. 13", "art. 14", "informationspflicht", "transparenz"]):
        return "betroffenenrechte"
    if any(k in t for k in ["art. 15", "art. 17", "art. 18", "art. 20", "art. 21", "recht auf", "lösch", "auskunft", "portabilit"]):
        return "betroffenenrechte"
    if any(k in t for k in ["prüfungsschema", "prüfung", "schema"]):
        return "pruefungsschemata"
    if any(k in t for k in ["eugh", "bgh", "bag", "bverwg", "urteil", "entscheidung", "c-"]):
        return "rechtsprechung"
    if any(k in t for k in ["auslegung", "methode", "hierarchie", "normenhierarchie", "öffnungsklausel"]):
        return "methodenwissen"
    if any(k in t for k in ["drittland", "transfer", "scc", "bcr", "dpf", "angemessenheit", "standardvertrags"]):
        return "drittlandtransfer"
    if any(k in t for k in ["dsk", "behörde", "aufsicht", "edpb"]):
        return "behoerden"
    if any(k in t for k in ["beschäftigt", "arbeitnehmer", "§ 26 bdsg", "email"]):
        return "beschaeftigtendatenschutz"
    if any(k in t for k in ["auftragsverarb", "cloud"]):
        return "auftragsverarbeitung"
    if any(k in t for k in ["cookies", "tracking", "ttdsg", "tdddg", "eprivacy"]):
        return "cookies_tracking"
    return "allgemein"


# ─────────────────────────────────────────────
# Build Eval Entry (Flipped Gold-Logik)
# ─────────────────────────────────────────────

def build_eval_entry(mw_id: str, meta: dict, document: str, llm_data: dict,
                     col, all_ids, entry_index: int) -> dict:
    thema = meta.get("thema", mw_id)
    normbezuege_str = meta.get("normbezuege", "")

    # must_contain = Gesetzes-Chunks aus main_norms (LLM-Extraktion, die wichtigsten)
    main_norms = llm_data.get("main_norms", [])
    must_ids = []
    for norm in main_norms:
        resolved = resolve_norm_to_chunk_ids(norm)
        must_ids.extend(resolved)

    # Deduplizieren, Reihenfolge erhalten
    must_ids = list(dict.fromkeys(must_ids))

    # MW-Chunks explizit aus must entfernen (nur in should)
    must_ids = [cid for cid in must_ids if not cid.startswith("mw_")]
    # Auch den eigenen MW-Chunk herausfiltern (falls Resolver ihn reingebracht hat)
    must_ids = [cid for cid in must_ids if cid != mw_id]

    if not must_ids:
        print(f"  [WARN] Keine must-IDs für {mw_id} (main_norms: {main_norms}) – should-only Entry")

    # should_contain = MW-Chunk selbst (Traceability) + Erwägungsgründe aus normbezuege
    should_ids = [mw_id]  # Der MW-Quell-Chunk

    # Erwägungsgründe aus normbezuege auflösen und zu should hinzufügen
    norm_refs = parse_normbezuege(normbezuege_str)
    for norm_ref in norm_refs:
        parsed = parse_norm_reference(norm_ref)
        if parsed and parsed.get("gesetz") == "DSGVO_EG":
            # Nur Erwägungsgründe in should (resolve gibt [] zurück, aber wir loggen es)
            eg_ids = resolve_norm_to_chunk_ids(norm_ref)
            should_ids.extend(eg_ids)

    # should darf nicht mit must überlappen
    should_ids = [cid for cid in should_ids if cid not in must_ids]
    should_ids = list(dict.fromkeys(should_ids))

    # normalized IDs für Top-Level-Felder (eval_v3.py-Kompatibilität)
    must_norm_ids = [_chroma_to_norm.get(cid, cid) for cid in must_ids]
    should_norm_ids = [_chroma_to_norm.get(cid, cid) for cid in should_ids]

    entry = {
        "id": f"canonical_{entry_index:03d}",
        "level": "canonical",
        "question": llm_data.get("question", ""),

        "retrieval_gold": {
            "must_contain_chunk_ids": must_ids,
            "should_contain_chunk_ids": should_ids,
            "forbidden_chunk_ids": []
        },

        # Rückwärtskompatibel für eval_v3.py (liest gold_ids top-level)
        "gold_ids": must_norm_ids,
        "should_ids": should_norm_ids,
        "forbidden_ids": [],

        "answer_gold": {
            "expected_norms": main_norms,
            "expected_keywords": llm_data.get("expected_keywords", []),
            "expected_cases": [],
            "forbidden_norms": [],
            "min_sources": 2
        },

        # Rückwärtskompatibel
        "expected_norms": main_norms,
        "expected_keywords": llm_data.get("expected_keywords", []),
        "min_sources": 2,

        "category": derive_category(thema),
        "difficulty": "canonical",
        "source_mw_chunk": mw_id,
        "generated_by": "mistral-medium-latest"
    }
    return entry


# ─────────────────────────────────────────────
# Haupt-Generator-Logik
# ─────────────────────────────────────────────

def generate_canonical_set(
    limit: int,
    output_path: str,
    overwrite: bool = False,
    resume: bool = False
):
    # ChromaDB laden
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    col = client.get_collection(COLLECTION_NAME)

    # Lookup-Index bauen (einmalig)
    build_lookup_index(col)

    # Alle MW-Chunks holen
    mw = col.get(where={"source_type": "methodenwissen"}, include=["metadatas", "documents"])
    mw_chunks = list(zip(mw["ids"], mw["metadatas"], mw["documents"]))
    all_ids = mw["ids"]
    print(f"MW-Chunks geladen: {len(mw_chunks)}")

    # Output-Datei-Handling
    out_path = Path(output_path)
    if not out_path.is_absolute():
        out_path = Path("/opt/openlex-mvp") / out_path

    existing_entries = []
    existing_mw_ids = set()

    if out_path.exists():
        if overwrite:
            print(f"[INFO] --overwrite: {out_path} wird überschrieben")
        elif resume:
            with open(out_path) as f:
                existing_entries = json.load(f)
            existing_mw_ids = {e.get("source_mw_chunk", "") for e in existing_entries}
            print(f"[INFO] --resume: {len(existing_entries)} bestehende Einträge geladen")
        else:
            print(f"[ERROR] {out_path} existiert bereits. Nutze --overwrite oder --resume.")
            sys.exit(1)
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)

    # Chunks filtern (für Resume)
    chunks_to_process = [c for c in mw_chunks if c[0] not in existing_mw_ids]
    if limit > 0:
        chunks_to_process = chunks_to_process[:limit]

    print(f"Zu verarbeiten: {len(chunks_to_process)} Chunks")

    results = list(existing_entries)
    total_tokens_in = 0
    total_tokens_out = 0
    n_must_only = 0
    n_should_only = 0

    for i, (mw_id, meta, document) in enumerate(chunks_to_process, 1):
        thema = meta.get("thema", mw_id)
        normbezuege_str = meta.get("normbezuege", "")

        print(f"\n[{i}/{len(chunks_to_process)}] {mw_id}")
        print(f"  Thema: {thema[:60]}")
        print(f"  Normbezüge: {normbezuege_str[:80]}")

        # 1. LLM für Query + main_norms + Keywords
        prompt = PROMPT_TEMPLATE.format(
            thema=thema,
            normbezuege=normbezuege_str or "(keine)",
            document=document[:2000]
        )
        try:
            raw, tok_in, tok_out = call_llm(prompt)
            total_tokens_in += tok_in
            total_tokens_out += tok_out

            # JSON-Extraktion (robust gegen ```json ... ``` Wrapper)
            text = raw.strip()
            if "```" in text:
                for part in text.split("```"):
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        text = part
                        break
            llm_data = json.loads(text)
        except json.JSONDecodeError as e:
            print(f"  [ERROR] JSON-Parse-Fehler: {e} – übersprungen\n  Raw: {raw[:200]}")
            continue
        except Exception as e:
            print(f"  [ERROR] LLM-Fehler: {e} – übersprungen")
            continue

        # 2. Eval-Entry mit Flipped Gold-Logik bauen
        entry_index = len(results) + 1
        entry = build_eval_entry(mw_id, meta, document, llm_data, col, all_ids, entry_index)

        # Statistik
        must_count = len(entry["retrieval_gold"]["must_contain_chunk_ids"])
        should_count = len(entry["retrieval_gold"]["should_contain_chunk_ids"])
        if must_count > 0:
            n_must_only += 1
        else:
            n_should_only += 1

        print(f"  → must ({must_count}): {entry['retrieval_gold']['must_contain_chunk_ids']}")
        print(f"  → should ({should_count}): {entry['retrieval_gold']['should_contain_chunk_ids']}")
        print(f"  → main_norms: {entry['expected_norms']}")
        print(f"  → tokens: {tok_in} in, {tok_out} out")

        results.append(entry)

        # Zwischenspeichern nach jedem Chunk
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        time.sleep(0.5)  # Rate-Limiting

    # Abschlussbericht
    total_chunks = len(mw_chunks)
    n_new = len(results) - len(existing_entries)
    cost_estimate = (total_tokens_in / 1_000_000 * 2.7 + total_tokens_out / 1_000_000 * 8.1)
    avg_tok_in = total_tokens_in / max(n_new, 1)
    avg_tok_out = total_tokens_out / max(n_new, 1)
    remaining = total_chunks - len(results)
    cost_full = (remaining * avg_tok_in / 1_000_000 * 2.7 + remaining * avg_tok_out / 1_000_000 * 8.1)

    print(f"\n=== FERTIG ===")
    print(f"Generiert: {n_new} neue Queries ({len(results)} gesamt)")
    print(f"  must-Einträge (mind. 1 Gesetzes-Chunk): {n_must_only}")
    print(f"  should-only Einträge (must leer):        {n_should_only}")
    print(f"Tokens: {total_tokens_in} in / {total_tokens_out} out")
    print(f"Geschätzte Kosten dieser Session: ~{cost_estimate:.4f} EUR (Mistral Medium)")
    if remaining > 0:
        print(f"Für restliche {remaining} Chunks: ~{cost_full:.4f} EUR zusätzlich")
    print(f"Output: {out_path} ({len(results)} Einträge)")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Canonical-Eval-Generator v3")
    parser.add_argument("--limit", type=int, default=5, help="Anzahl MW-Chunks (default: 5)")
    parser.add_argument("--all", action="store_true", help="Alle MW-Chunks verarbeiten")
    parser.add_argument("--output", default="eval_sets/canonical_v3.json",
                        help="Ausgabedatei (relativ zum Projektverzeichnis)")
    parser.add_argument("--overwrite", action="store_true", help="Bestehende Datei überschreiben")
    parser.add_argument("--resume", action="store_true", help="Fehlende Chunks nachgenerieren")
    args = parser.parse_args()

    limit = 0 if args.all else args.limit
    generate_canonical_set(
        limit=limit,
        output_path=args.output,
        overwrite=args.overwrite,
        resume=args.resume
    )
