#!/usr/bin/env python3
"""Diagnostiziert, wie Art. 4 DSGVO in ChromaDB abgelegt ist."""
import sys
from collections import Counter

sys.path.insert(0, "/opt/openlex-mvp")
import chromadb

client = chromadb.PersistentClient(path="/opt/openlex-mvp/chromadb")
col = client.get_collection("openlex_datenschutz")


def load_all():
    ids, metas, docs = [], [], []
    offset = 0
    while True:
        r = col.get(limit=5000, offset=offset, include=["metadatas", "documents"])
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
    ids, metas, docs = load_all()
    print(f"Total: {len(ids)}")

    # Alle Chunks, die im ID oder in Metadaten "art" und "4" enthalten
    candidates = []
    for cid, m, d in zip(ids, metas, docs):
        cid_lower = cid.lower()
        has_4 = (
            "_4_" in cid_lower
            or cid_lower.endswith("_4")
            or "_art_4" in cid_lower
            or "_art._4" in cid_lower
            or "_art. 4" in cid_lower
        )
        is_dsgvo = (
            "dsgvo" in cid_lower or "ds-gvo" in cid_lower or "gdpr" in cid_lower
            or (m or {}).get("gesetz", "").upper() in ("DSGVO", "DS-GVO", "GDPR")
        )
        if has_4 and is_dsgvo:
            candidates.append((cid, m, d[:200] if d else ""))

    print(f"Art.-4-DSGVO-Kandidaten: {len(candidates)}")
    print()

    # Sample IDs für manuelles Regex-Verständnis
    print("=== Sample chunk_ids (erste 20) ===")
    for cid, m, _ in candidates[:20]:
        print(f"  {cid}")
    print()

    # Metadata-Felder sammeln
    all_meta_keys = Counter()
    artikel_values = Counter()
    paragraph_values = Counter()

    for cid, m, _ in candidates:
        for k in (m or {}).keys():
            all_meta_keys[k] += 1
        artikel_values[(m or {}).get("artikel", "NONE")] += 1
        paragraph_values[(m or {}).get("paragraph", "NONE")] += 1

    print(f"Meta-Keys (über alle Kandidaten):")
    for k, n in all_meta_keys.most_common():
        print(f"  {k}: {n}")

    print(f"\n`artikel`-Wert-Verteilung:")
    for v, n in artikel_values.most_common():
        print(f"  {v!r}: {n}")

    print(f"\n`paragraph`-Wert-Verteilung:")
    for v, n in paragraph_values.most_common():
        print(f"  {v!r}: {n}")

    print()
    print("Sample-Chunks (erste 10):")
    for cid, m, doc in candidates[:10]:
        print(f"  ID: {cid}")
        print(f"    artikel={m.get('artikel')!r}, paragraph={m.get('paragraph')!r}, "
              f"gesetz={m.get('gesetz')!r}")
        print(f"    doc: {doc[:150]}...")
        print()

    # Auch: DSGVO-Chunks die artikel='Art. 4' oder 'Art. Art. 4' haben
    print("=== Alle DSGVO-Chunks nach `artikel`-Wert (Top 30) ===")
    dsgvo_art_vals = Counter()
    for cid, m, _ in zip(ids, metas, docs):
        m = m or {}
        if m.get("gesetz", "").upper() in ("DSGVO", "DS-GVO"):
            dsgvo_art_vals[m.get("artikel", "NONE")] += 1
    for v, n in dsgvo_art_vals.most_common(30):
        print(f"  {v!r}: {n}")


if __name__ == "__main__":
    main()
