#!/usr/bin/env python3
"""
Validiert eval_sets/v4/queries.json:
- Schema-Konsistenz
- Chunk-ID-Existenz in ChromaDB
- Stratifizierungs-Verteilung
"""
import sys
import json
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, "/opt/openlex-mvp")
import chromadb

PATH = Path("/opt/openlex-mvp/eval_sets/v4/queries.json")
CANDIDATES_PATH = Path("/opt/openlex-mvp/eval_sets/v4/queries_with_candidates.json")


def load_all_db_ids():
    col = chromadb.PersistentClient("/opt/openlex-mvp/chromadb").get_collection("openlex_datenschutz")
    ids_set = set()
    offset = 0
    while True:
        r = col.get(limit=5000, offset=offset, include=[])
        if not r["ids"]:
            break
        ids_set.update(r["ids"])
        if len(r["ids"]) < 5000:
            break
        offset += 5000
    return ids_set


def main():
    # Prüfe ob annotiertes Set vorhanden, sonst candidates
    if PATH.exists():
        with open(PATH) as f:
            queries = json.load(f)
        print(f"Lade: {PATH}")
    elif CANDIDATES_PATH.exists():
        with open(CANDIDATES_PATH) as f:
            queries = json.load(f)
        print(f"Lade (noch kein annotiertes Set): {CANDIDATES_PATH}")
    else:
        print("Kein Eval-Set gefunden. Query-Generator und Preselect zuerst ausführen.")
        return 1

    print(f"\nTotal Queries: {len(queries)}")
    by_source = Counter(q.get("query_source") for q in queries)
    print("Query-Sources:")
    for s, n in by_source.most_common():
        print(f"  {s}: {n}")

    annotated = [q for q in queries if q.get("must_contain_chunk_ids")]
    unannotated = [q for q in queries if not q.get("must_contain_chunk_ids")]
    templates = [q for q in queries if str(q.get("query", "")).startswith("[TO BE FILLED")]
    adversarial = [q for q in queries if q.get("is_adversarial")]

    print(f"\nAnnotiert (≥1 must_contain): {len(annotated)}")
    print(f"Noch offen: {len(unannotated)}")
    print(f"Templates (noch kein Query-Text): {len(templates)}")
    print(f"Adversarial: {len(adversarial)}")

    if not annotated:
        print("\n[Noch keine Annotationen vorhanden — Tool starten und annotieren]")
        return 0

    # DB-IDs laden
    print("\nLade ChromaDB-IDs...")
    all_ids_db = load_all_db_ids()
    print(f"DB-IDs: {len(all_ids_db)}")

    problems = []

    # must_contain-IDs Existenz
    missing_must = []
    for q in annotated:
        for cid in q.get("must_contain_chunk_ids", []):
            if cid not in all_ids_db:
                missing_must.append((q["query_id"], cid))
                problems.append(f"{q['query_id']}: must-ID nicht in DB: {cid}")

    # forbidden-IDs Existenz
    missing_forb = []
    for q in annotated:
        for cid in q.get("forbidden_contain_chunk_ids", []):
            if cid not in all_ids_db:
                missing_forb.append((q["query_id"], cid))

    # must_contain Anzahl 1-5
    out_of_range = [(q["query_id"], len(q["must_contain_chunk_ids"]))
                    for q in annotated
                    if not (1 <= len(q["must_contain_chunk_ids"]) <= 5)]

    # Tags-Vollständigkeit
    missing_tags = [q["query_id"] for q in annotated
                    if not q.get("tags", {}).get("rechtsgebiete")
                    or not q.get("tags", {}).get("anfrage_typen")]

    print(f"\n=== Probleme ===")
    print(f"must_contain-IDs nicht in DB: {len(missing_must)}")
    print(f"forbidden-IDs nicht in DB: {len(missing_forb)}")
    print(f"must_contain Anzahl außerhalb 1-5: {len(out_of_range)}")
    print(f"Tags unvollständig: {len(missing_tags)}")

    # Stratifizierung
    rechtsgebiete = Counter()
    anfrage_typen = Counter()
    cross_table = Counter()
    for q in annotated:
        tags = q.get("tags", {})
        for rg in tags.get("rechtsgebiete", []):
            rechtsgebiete[rg] += 1
        for at in tags.get("anfrage_typen", []):
            anfrage_typen[at] += 1
        for rg in tags.get("rechtsgebiete", []):
            for at in tags.get("anfrage_typen", []):
                cross_table[f"{rg}×{at}"] += 1

    print(f"\n=== Stratifizierung (aus {len(annotated)} annotierten Queries) ===")
    print("Rechtsgebiete:")
    for rg, n in rechtsgebiete.most_common():
        print(f"  {rg}: {n}")
    print("\nAnfrage-Typen:")
    for at, n in anfrage_typen.most_common():
        print(f"  {at}: {n}")

    low_cells = [(k, v) for k, v in cross_table.items() if v < 5]
    if low_cells:
        print(f"\nZellen mit <5 Queries (Unterrepräsentation):")
        for k, v in sorted(low_cells, key=lambda x: x[1]):
            print(f"  {k}: {v}")

    deep = sum(1 for q in annotated if q.get("is_deep_eval"))
    print(f"\nDeep-Eval-Queries: {deep} (Soll: 30-50)")
    print(f"Adversarial-Queries annotiert: {sum(1 for q in annotated if q.get('is_adversarial'))}")

    if problems:
        print(f"\n=== Erste 20 Probleme ===")
        for p in problems[:20]:
            print(f"  {p}")

    if not problems and not out_of_range:
        print("\n✅ Keine Probleme gefunden — Eval-Set ist valide.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
