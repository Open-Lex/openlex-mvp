#!/usr/bin/env python3
"""Findet Boilerplate-Chunks im Urteile-Bestand."""
import sys
import re
from collections import Counter

sys.path.insert(0, "/opt/openlex-mvp")
import chromadb

col = chromadb.PersistentClient("/opt/openlex-mvp/chromadb").get_collection("openlex_datenschutz")

BOILERPLATE_PATTERNS = [
    (re.compile(r"Startseite\s*[\n\s]*Entscheidungs", re.IGNORECASE), "nav_entscheidungssuche"),
    (re.compile(r"Benachrichtigungsdienst|Newsletter|RSS[-\s]?Feed", re.IGNORECASE), "nav_benachrichtigung"),
    (re.compile(r"Impressum|Datenschutzerkl[aä]rung|Cookie[-\s]?Einstellung", re.IGNORECASE), "footer"),
    (re.compile(r"Zur\s+Navigation|Zum\s+Inhalt|Skip\s+to"), "skiplinks"),
    (re.compile(r"Suche:\s*$|Suchbegriff"), "suchfeld"),
    (re.compile(r"Login|Anmelden|Passwort", re.IGNORECASE), "login_ui"),
    (re.compile(r"©\s*\d{4}"), "copyright"),
]

def load_urteile():
    ids, metas, docs = [], [], []
    offset = 0
    while True:
        r = col.get(limit=5000, offset=offset,
                    where={"source_type": "urteil"},
                    include=["metadatas", "documents"])
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
    print(f"Urteile-Chunks: {len(ids)}")

    # 1. Pattern-Match
    pattern_hits = Counter()
    hit_chunks = {}
    for cid, m, d in zip(ids, metas, docs):
        if not d:
            continue
        text_sample = d[:1500]
        for pat, label in BOILERPLATE_PATTERNS:
            if pat.search(text_sample):
                pattern_hits[label] += 1
                hit_chunks.setdefault(label, []).append(cid)

    print("\n=== Pattern-Matches ===")
    for label, n in pattern_hits.most_common():
        print(f"  {label}: {n}")

    # 2. Heuristik: wenig juristischer Inhalt
    legal_indicators = re.compile(
        r"\b(?:Rz\.|Randnummer|§\s*\d|Art\.\s*\d|Abs\.\s*\d|Urteil|Beschluss|Kläger|Beklagte|"
        r"Tenor|Tatbestand|Entscheidungsgründe|Leitsatz|Vorlagefrage)\b",
        re.IGNORECASE,
    )

    low_legal_content = []
    for cid, m, d in zip(ids, metas, docs):
        if not d or len(d) < 50:
            low_legal_content.append((cid, "empty_or_tiny", len(d)))
            continue
        sample = d[: len(d) // 3] if len(d) > 600 else d
        matches = len(legal_indicators.findall(sample))
        if matches == 0:
            low_legal_content.append((cid, "no_legal_indicators", len(d)))

    print(f"\n=== Chunks mit wenig juristischem Inhalt: {len(low_legal_content)} ===")
    reasons = Counter(r for _, r, _ in low_legal_content)
    for reason, n in reasons.most_common():
        print(f"  {reason}: {n}")

    # 3. Union verdächtiger Chunks
    suspicious_ids = set()
    for chunks in hit_chunks.values():
        suspicious_ids.update(chunks)
    for cid, _, _ in low_legal_content:
        suspicious_ids.add(cid)

    print(f"\n=== Verdächtige Chunks gesamt (Union): {len(suspicious_ids)} ===")
    print(f"Anteil am Urteile-Bestand: {len(suspicious_ids)/len(ids)*100:.1f} %")

    # 4. 10 Samples
    print("\n=== 10 Samples verdächtiger Chunks ===")
    for cid in list(suspicious_ids)[:10]:
        idx = ids.index(cid)
        m = metas[idx] or {}
        d = docs[idx] or ""
        print(f"\n  {cid} [{m.get('gericht', '?')} {m.get('aktenzeichen', '?')}]")
        print(f"    Länge: {len(d)}")
        print(f"    Preview: {d[:200]!r}")

    print("\n=== Entscheidungsregel ===")
    pct = len(suspicious_ids)/len(ids)*100
    if pct < 2:
        print(f"→ {pct:.1f} %: ignorieren, Einzelfälle")
    elif pct < 10:
        print(f"→ {pct:.1f} %: kleiner Backfill sinnvoll (Chunks löschen oder markieren)")
    else:
        print(f"→ {pct:.1f} %: systematisch, Ingest überarbeiten (Phase 3)")

if __name__ == "__main__":
    main()
