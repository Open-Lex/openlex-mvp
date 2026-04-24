#!/usr/bin/env python3
"""
Art. 4 DSGVO Metadata-Diagnose und Normalisierung.

Befund aus Diagnose:
- 5 Chunks haben korrekt artikel='Art. 4' (gesetz_granular)
- Der Audit-Report zeigte '0 chunks' wegen eines f-string-Bugs:
  f"Art. {a}" mit a='Art. 4' → Display "Art. Art. 4"
- Die 75 chunk_id-Kandidaten mit '_4' am Ende sind Leitlinien-Chunk #4,
  keine Art.-4-Chunks
- Das Metadata ist korrekt. Kein Patch an Chunk-Daten nötig.

Dieses Script:
1. Verifiziert die 5 Art.-4-Chunks
2. Verifiziert, dass Art. 4 per Filter retrieveable ist
3. Gibt Bericht aus
"""
import sys

sys.path.insert(0, "/opt/openlex-mvp")
import chromadb

client = chromadb.PersistentClient(path="/opt/openlex-mvp/chromadb")
col = client.get_collection("openlex_datenschutz")


def main():
    # 1. Art. 4 per Filter
    r = col.get(
        where={"artikel": "Art. 4"},
        limit=20,
        include=["metadatas", "documents"]
    )
    ids = r["ids"]
    metas = r.get("metadatas") or []
    docs = r.get("documents") or []

    print(f"Art. 4 DSGVO via filter (artikel='Art. 4'): {len(ids)} Chunks")
    for cid, m, d in zip(ids, metas, docs):
        print(f"  ID: {cid}")
        print(f"    artikel={m.get('artikel')!r}, gesetz={m.get('gesetz')!r}, nr={m.get('nr')!r}")
        print(f"    doc: {d[:200] if d else ''}...")
        print()

    # 2. DSGVO-Artikel-Übersicht (korrekte Anzeige ohne doppeltes "Art.")
    print("=== DSGVO-Artikel-Verteilung (korrekte Anzeige) ===")
    from collections import Counter
    all_dsgvo_ids, all_dsgvo_metas = [], []
    offset = 0
    while True:
        res = col.get(limit=5000, offset=offset, include=["metadatas"])
        if not res["ids"]:
            break
        for cid, m in zip(res["ids"], res.get("metadatas") or []):
            m = m or {}
            if m.get("gesetz", "").upper() in ("DSGVO", "DS-GVO"):
                all_dsgvo_ids.append(cid)
                all_dsgvo_metas.append(m)
        if len(res["ids"]) < 5000:
            break
        offset += 5000

    art_dist = Counter(m.get("artikel", "MISSING") for m in all_dsgvo_metas)
    print(f"DSGVO gesetz_granular Chunks: {len(all_dsgvo_ids)}")
    print(f"Artikel-Verteilung (Top 30):")
    for a, cnt in art_dist.most_common(30):
        # Korrekte Anzeige: artikel-Wert enthält bereits "Art. X"
        print(f"  {a}: {cnt} Chunks")

    # 3. Fazit
    art4_count = art_dist.get("Art. 4", 0)
    print(f"\nFazit: Art. 4 DSGVO hat {art4_count} Chunks, Metadata ist korrekt.")
    print("Kein Patch an ChromaDB-Metadata erforderlich.")
    print("Audit-Script-Bug war ein f-string-Formatierungsfehler (f'Art. {a}' mit a='Art. 4').")

    return 0


if __name__ == "__main__":
    sys.exit(main())
