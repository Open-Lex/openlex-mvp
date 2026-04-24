#!/usr/bin/env python3
"""
Generiert 200 Query-Kandidaten für eval_v4.
Output: eval_sets/v4/queries_raw.json
"""
import os
import sys
import json
import time
import logging
from pathlib import Path
from collections import Counter

sys.path.insert(0, "/opt/openlex-mvp")
import chromadb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CHROMADB_PATH = "/opt/openlex-mvp/chromadb"
COLLECTION_NAME = "openlex_datenschutz"
OUTPUT_PATH = Path("/opt/openlex-mvp/eval_sets/v4/queries_raw.json")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


_MW_QUERY_PROMPT = """Du bekommst einen juristischen Text-Chunk aus deutschem Datenschutzrecht.
Formuliere dazu EINE Nutzerfrage, die ein echter User (Laie oder Jurist) stellen würde.

Regeln:
1. Die Frage soll NATÜRLICH klingen, nicht wie aus einem Lehrbuch
2. Die Frage muss sich thematisch aus dem Chunk ergeben, nicht darüber hinaus
3. Variiere zwischen Fragetypen: "Was ist X?" / "Darf ich Y?" / "Wie mache ich Z?" / "Muss ich A?"
4. Maximal 20 Wörter
5. Verwende "ich", "mein", "meine" für direkte Bezüge
6. Gib NUR die Frage zurück, kein JSON, keine Erklärung

Beispiele:
Chunk: "Art. 82 DSGVO regelt Schadensersatzansprüche..."
Frage: Kann ich Schadensersatz verlangen, wenn meine Daten unrechtmäßig verarbeitet wurden?

Chunk: "§ 26 BDSG regelt den Beschäftigtendatenschutz..."
Frage: Darf mein Arbeitgeber meine Daten am Arbeitsplatz verarbeiten?

Chunk:
{chunk_text}

Frage:"""


_TAG_CLASSIFIER_PROMPT = """Klassifiziere die folgende juristische Nutzerfrage für ein Datenschutz-System.

Antworte NUR mit JSON, exakt diese Struktur:
{{
  "rechtsgebiete": ["DSGVO","BDSG","TDDDG","DDG","Rechtsprechung_EuGH","Rechtsprechung_BGH","Rechtsprechung_BVerfG","Leitlinien_EDPB","Leitlinien_DSK","Methodenwissen"],
  "anfrage_typen": ["definition","subsumtion","handlungsanweisung","rechtsprechung","prozedural","normauslegung"],
  "normbezug": []
}}

Wähle 1-3 rechtsgebiete, 1-2 anfrage_typen, 0-5 normbezug (Strings wie "Art. 6 DSGVO").

Frage: {query}

JSON:"""


def call_mistral(prompt: str, json_mode: bool = False, temperature: float = 0.7) -> str:
    import requests
    api_key = os.getenv("MISTRAL_KEY") or os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_KEY not set")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "mistral-medium-latest",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 300,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
        payload["temperature"] = 0.0
    backoff = 2.0
    for attempt in range(5):
        try:
            r = requests.post("https://api.mistral.ai/v1/chat/completions",
                              json=payload, headers=headers, timeout=30)
            if r.status_code == 429:
                logger.warning(f"Rate limit, sleeping {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt == 4:
                raise
            logger.warning(f"Mistral error attempt {attempt+1}: {e}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
    raise RuntimeError("Mistral call failed")


def generate_from_methodenwissen(n: int = 100) -> list:
    client = chromadb.PersistentClient(path=CHROMADB_PATH)
    col = client.get_collection(COLLECTION_NAME)

    ids_all, metas_all, docs_all = [], [], []
    offset = 0
    while True:
        r = col.get(limit=5000, offset=offset, include=["metadatas", "documents"],
                    where={"source_type": "methodenwissen"})
        if not r["ids"]:
            break
        ids_all.extend(r["ids"])
        metas_all.extend(r.get("metadatas") or [{}] * len(r["ids"]))
        docs_all.extend(r.get("documents") or [""] * len(r["ids"]))
        if len(r["ids"]) < 5000:
            break
        offset += 5000

    logger.info(f"Methodenwissen-Chunks: {len(ids_all)}")
    if len(ids_all) < n:
        logger.warning(f"Nur {len(ids_all)} MW-Chunks verfügbar")
        n = len(ids_all)

    import random
    random.seed(42)

    themen_buckets = {}
    for cid, m, d in zip(ids_all, metas_all, docs_all):
        thema = (m or {}).get("thema") or (m or {}).get("aspekt") or (m or {}).get("kategorie") or "mw_default"
        themen_buckets.setdefault(thema, []).append((cid, m, d))

    logger.info(f"Themen-Buckets: {len(themen_buckets)}")

    selected = []
    bucket_keys = list(themen_buckets.keys())
    random.shuffle(bucket_keys)
    bucket_iters = {k: iter(themen_buckets[k]) for k in bucket_keys}

    while len(selected) < n:
        any_found = False
        for k in bucket_keys:
            if len(selected) >= n:
                break
            try:
                selected.append(next(bucket_iters[k]))
                any_found = True
            except StopIteration:
                continue
        if not any_found:
            break

    logger.info(f"Ausgewählt: {len(selected)} MW-Chunks")

    queries = []
    for i, (cid, m, doc) in enumerate(selected, 1):
        if not doc or len(doc) < 100:
            continue
        try:
            query_text = call_mistral(_MW_QUERY_PROMPT.format(chunk_text=doc[:2000]))
            query_text = query_text.strip().strip('"').strip()
            if not query_text or "?" not in query_text:
                logger.warning(f"Bad query for {cid}: {query_text!r}")
                continue

            # Inter-call delay
            time.sleep(0.8)

            try:
                tags_json = call_mistral(_TAG_CLASSIFIER_PROMPT.format(query=query_text), json_mode=True)
                tags = json.loads(tags_json)
                # Validate structure
                if not isinstance(tags.get("rechtsgebiete"), list):
                    tags["rechtsgebiete"] = []
                if not isinstance(tags.get("anfrage_typen"), list):
                    tags["anfrage_typen"] = []
                if not isinstance(tags.get("normbezug"), list):
                    tags["normbezug"] = []
            except Exception as e:
                logger.warning(f"Tag classification failed for {cid}: {e}")
                tags = {"rechtsgebiete": [], "anfrage_typen": [], "normbezug": []}

            time.sleep(0.8)

            queries.append({
                "query_id": f"v4_mw_{len(queries)+1:03d}",
                "query": query_text,
                "query_source": "methodenwissen",
                "source_chunk_id": cid,
                "tags": tags,
                "must_contain_chunk_ids": [],
                "forbidden_contain_chunk_ids": [],
                "is_deep_eval": False,
                "legal_sufficiency_gold": None,
                "is_adversarial": False,
                "adversarial_type": None,
                "notes": "",
            })
            logger.info(f"[{len(queries)}/{n}] {query_text[:70]}")

            # Save progress every 10
            if len(queries) % 10 == 0:
                _save_intermediate(queries)

        except Exception as e:
            logger.error(f"Failed for chunk {cid}: {e}")
            continue

    return queries


def _save_intermediate(queries):
    tmp = OUTPUT_PATH.with_suffix(".tmp.json")
    with open(tmp, "w") as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)


def generate_real_templates(n: int = 75) -> list:
    quellen_plan = [
        ("real_lfdi", 20),
        ("real_dsk", 15),
        ("real_mandant", 20),
        ("real_forum", 20),
    ]
    queries = []
    idx = 0
    for quelle, count in quellen_plan:
        for _ in range(count):
            idx += 1
            queries.append({
                "query_id": f"v4_real_{idx:03d}",
                "query": f"[TO BE FILLED: reale Query aus Quelle {quelle}]",
                "query_source": quelle,
                "source_chunk_id": None,
                "tags": {"rechtsgebiete": [], "anfrage_typen": [], "normbezug": []},
                "must_contain_chunk_ids": [],
                "forbidden_contain_chunk_ids": [],
                "is_deep_eval": False,
                "legal_sufficiency_gold": None,
                "is_adversarial": False,
                "adversarial_type": None,
                "notes": "Query-Text durch Hendrik zu füllen",
            })
    return queries


def generate_adversarial(n: int = 25) -> list:
    adversarial_queries = [
        # negation (5)
        ("Darf mein Arbeitgeber meine Mails NICHT lesen, auch wenn er einen Verdacht hat?", "negation", ["DSGVO", "BDSG"], ["subsumtion"]),
        ("Wann muss ich keine Datenschutzerklärung auf meiner Website haben?", "negation", ["DSGVO"], ["subsumtion"]),
        ("In welchen Fällen ist eine Einwilligung nicht erforderlich?", "negation", ["DSGVO"], ["subsumtion"]),
        ("Ab wann ist ein Datenschutzbeauftragter nicht mehr nötig?", "negation", ["DSGVO", "BDSG"], ["subsumtion"]),
        ("Welche Daten dürfen ohne Einwilligung nicht verarbeitet werden?", "negation", ["DSGVO"], ["subsumtion"]),
        # false_premise (7)
        ("Da § 29 BDSG die Datenweitergabe regelt, wie lange darf ich Daten speichern?", "false_premise", ["BDSG"], ["subsumtion"]),
        ("Das TMG schreibt vor, dass Cookies ohne Einwilligung erlaubt sind – was heisst das konkret?", "false_premise", ["TDDDG"], ["subsumtion"]),
        ("Nach § 32 BDSG-alt darf der Arbeitgeber Mails lesen – was muss ich beachten?", "false_premise", ["BDSG"], ["subsumtion"]),
        ("Da die DSGVO nur für grosse Firmen gilt, welche Pflichten habe ich als Kleinunternehmer?", "false_premise", ["DSGVO"], ["subsumtion"]),
        ("Die DSK hat entschieden, dass Gesichtserkennung immer erlaubt ist – stimmt das?", "false_premise", ["Leitlinien_DSK"], ["rechtsprechung"]),
        ("Seit DSGVO brauche ich nie wieder eine Einwilligung – wie stelle ich das um?", "false_premise", ["DSGVO"], ["handlungsanweisung"]),
        ("Art. 6 Abs. 1 lit. f DSGVO erlaubt mir immer die Verarbeitung ohne Einwilligung.", "false_premise", ["DSGVO"], ["normauslegung"]),
        # out_of_domain (7)
        ("Wie funktioniert NSA-Überwachung bei US-Cloud-Anbietern?", "out_of_domain", ["DSGVO"], ["definition"]),
        ("Was sagt das kalifornische CCPA zu meinen Rechten?", "out_of_domain", ["DSGVO"], ["normauslegung"]),
        ("Wie umgehe ich den Datenschutz, ohne erwischt zu werden?", "out_of_domain", [], ["handlungsanweisung"]),
        ("Ist die DSGVO in der Schweiz anwendbar?", "out_of_domain", ["DSGVO"], ["subsumtion"]),
        ("Wie verschlüssele ich meine Festplatte am besten?", "out_of_domain", [], ["handlungsanweisung"]),
        ("Was ist besser – AWS oder Azure für meine Kundendaten?", "out_of_domain", ["DSGVO"], ["handlungsanweisung"]),
        ("Was passiert, wenn ich das chinesische Datenschutzgesetz nicht einhalte?", "out_of_domain", [], ["subsumtion"]),
        # ambiguous_context (6)
        ("Mein Chef liest meine Mails – ist das erlaubt?", "ambiguous_context", ["BDSG", "DSGVO"], ["subsumtion"]),
        ("Ich möchte Daten löschen – was muss ich tun?", "ambiguous_context", ["DSGVO"], ["handlungsanweisung"]),
        ("Darf ich das?", "ambiguous_context", [], ["subsumtion"]),
        ("Kann ich Fotos meiner Kunden veröffentlichen?", "ambiguous_context", ["DSGVO"], ["subsumtion"]),
        ("Brauche ich eine Einwilligung?", "ambiguous_context", ["DSGVO"], ["subsumtion"]),
        ("Ist das ein Datenleck?", "ambiguous_context", ["DSGVO"], ["subsumtion"]),
    ]

    queries = []
    for i, (q, typ, gebiete, anfrage) in enumerate(adversarial_queries[:n], 1):
        queries.append({
            "query_id": f"v4_adv_{i:03d}",
            "query": q,
            "query_source": "adversarial",
            "source_chunk_id": None,
            "tags": {"rechtsgebiete": gebiete, "anfrage_typen": anfrage, "normbezug": []},
            "must_contain_chunk_ids": [],
            "forbidden_contain_chunk_ids": [],
            "is_deep_eval": False,
            "legal_sufficiency_gold": None,
            "is_adversarial": True,
            "adversarial_type": typ,
            "notes": f"Adversarial: {typ}",
        })
    return queries


def main():
    all_queries = []

    logger.info("=== Phase 1: Methodenwissen-Queries (100) ===")
    mw = generate_from_methodenwissen(100)
    all_queries.extend(mw)
    logger.info(f"MW-Queries generiert: {len(mw)}")

    logger.info("=== Phase 2: Reale Quellen-Templates (75) ===")
    real = generate_real_templates(75)
    all_queries.extend(real)

    logger.info("=== Phase 3: Adversarial (25) ===")
    adv = generate_adversarial(25)
    all_queries.extend(adv)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(all_queries, f, indent=2, ensure_ascii=False)

    by_source = Counter(q["query_source"] for q in all_queries)
    logger.info(f"\n=== Zusammenfassung ===")
    logger.info(f"Total: {len(all_queries)}")
    for s, n in by_source.most_common():
        logger.info(f"  {s}: {n}")
    logger.info(f"Geschrieben: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
