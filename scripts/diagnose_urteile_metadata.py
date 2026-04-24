#!/usr/bin/env python3
"""Diagnose: Wie vollständig sind die Urteile-Metadaten?"""
import sys
import re
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, "/opt/openlex-mvp")
import chromadb

col = chromadb.PersistentClient("/opt/openlex-mvp/chromadb").get_collection("openlex_datenschutz")


def load_urteile():
    ids, metas, docs = [], [], []
    offset = 0
    while True:
        r = col.get(
            limit=5000, offset=offset,
            where={"source_type": "urteil"},
            include=["metadatas", "documents"],
        )
        if not r["ids"]:
            break
        ids.extend(r["ids"])
        metas.extend(r.get("metadatas") or [{}] * len(r["ids"]))
        docs.extend(r.get("documents") or [""] * len(r["ids"]))
        if len(r["ids"]) < 5000:
            break
        offset += 5000
    return ids, metas, docs


def main():
    ids, metas, docs = load_urteile()
    print(f"Urteile-Chunks total: {len(ids)}")

    # 1. Welche Metadaten-Felder gibt es überhaupt?
    all_keys = Counter()
    for m in metas:
        for k in (m or {}).keys():
            all_keys[k] += 1
    print("\n=== Alle Meta-Keys bei Urteilen ===")
    for k, n in all_keys.most_common():
        print(f"  {k}: {n}/{len(ids)}")

    # 2. Identifikations-Feld-Coverage
    print("\n=== Identifikations-Feld-Coverage ===")
    id_fields = ["gericht", "aktenzeichen", "az", "urteil_name",
                 "volladresse", "datum", "fundstelle"]
    for field in id_fields:
        set_count = sum(1 for m in metas if (m or {}).get(field))
        print(f"  {field}: {set_count}/{len(ids)} ({set_count/len(ids)*100:.1f} %)")

    # 3. Chunks ohne jegliche Identifikation
    no_id_chunks = []
    for cid, m, d in zip(ids, metas, docs):
        has_any_id = any((m or {}).get(f) for f in id_fields)
        if not has_any_id:
            no_id_chunks.append((cid, m or {}, d or ""))

    print(f"\n=== Chunks ohne jede Identifikation: {len(no_id_chunks)} ===")

    # 4. Chunk-ID-Muster analysieren
    id_patterns = Counter()
    for cid, m, d in zip(ids, metas, docs):
        if re.match(r"^[a-f0-9]{16}$", cid):
            id_patterns["hash_only_16"] += 1
        elif re.match(r"^[a-f0-9]{8,}$", cid):
            id_patterns["hash_only_other"] += 1
        elif cid.startswith("seg_eugh"):
            id_patterns["seg_eugh"] += 1
        elif cid.startswith("seg_bgh"):
            id_patterns["seg_bgh"] += 1
        elif cid.startswith("seg_"):
            id_patterns["seg_other"] += 1
        elif "eugh" in cid.lower() or "c-" in cid.lower():
            id_patterns["eugh_variant"] += 1
        else:
            id_patterns["other"] += 1
    print(f"\n=== Chunk-ID-Muster (bei allen Urteilen) ===")
    for p, n in id_patterns.most_common():
        print(f"  {p}: {n}")

    # 5. Für Chunks ohne ID: Kann man aus dem Volltext was extrahieren?
    print(f"\n=== Volltext-Extraktions-Potenzial (bis 50 Samples ohne Metadaten) ===")

    eugh_pattern = re.compile(r"C[-‑–]\s?(\d+)[/∕](\d+)")
    bgh_pattern  = re.compile(r"([IVX]+\s+Z[RB]\s+\d+/\d+)")
    vg_pattern   = re.compile(r"(VG|OVG|VGH|LG|OLG|AG|BAG|LAG|BFH|FG|BSG|LSG|BPatG)\s+\w+\s+\d+")
    datum_pattern = re.compile(r"(\d{1,2}\.\d{1,2}\.\d{4})")

    extractable = 0
    for cid, m, d in no_id_chunks[:50]:
        if not d:
            continue
        text = d[:3000]
        eugh_match  = eugh_pattern.search(text)
        bgh_match   = bgh_pattern.search(text)
        vg_match    = vg_pattern.search(text)
        datum_match = datum_pattern.search(text)

        if eugh_match or bgh_match or vg_match:
            extractable += 1
            preview = d[:200].replace("\n", " ")
            print(f"\n  {cid}:")
            if eugh_match:
                print(f"    → EuGH: C-{eugh_match.group(1)}/{eugh_match.group(2)}")
            if bgh_match:
                print(f"    → BGH-Style: {bgh_match.group(1)}")
            if vg_match:
                print(f"    → Gericht: {vg_match.group(0)}")
            if datum_match:
                print(f"    → Datum: {datum_match.group(1)}")
            print(f"    Preview: {preview[:150]}...")

    print(f"\n=== Fazit ===")
    print(f"Urteile total:                    {len(ids)}")
    print(f"Ohne Identifikations-Metadaten:   {len(no_id_chunks)} ({len(no_id_chunks)/len(ids)*100:.1f} %)")
    if no_id_chunks:
        sample_size = min(50, len(no_id_chunks))
        print(f"Davon Regex-heilbar (Sample {sample_size}):  {extractable}")
        if sample_size > 0:
            projected = int(extractable / sample_size * len(no_id_chunks))
            print(f"Extrapoliert auf alle:            ca. {projected} per Backfill heilbar")


if __name__ == "__main__":
    main()
