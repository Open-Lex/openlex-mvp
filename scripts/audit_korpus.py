#!/usr/bin/env python3
"""
audit_korpus.py – 9-Sektionen ChromaDB-Audit für OpenLex-Korpus.
Liest direkt aus ChromaDB, schreibt Report nach _private/korpus_audit_YYYY-MM-DD.md
"""
import sys
import json
import re
import os
from pathlib import Path
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, "/opt/openlex-mvp")

CHROMA_PATH = "/opt/openlex-mvp/chromadb"
EVAL_SETS_DIR = Path("/opt/openlex-mvp/eval_sets")
REPORT_DIR = Path("/opt/openlex-mvp/_private")

TODAY = date.today().isoformat()
REPORT_PATH = REPORT_DIR / f"korpus_audit_{TODAY}.md"


def load_all_chunks(col):
    """Paginierter Bulk-Read aus ChromaDB."""
    chunks = []
    batch = 500
    offset = 0
    while True:
        res = col.get(
            limit=batch, offset=offset,
            include=["metadatas", "documents"]
        )
        ids = res["ids"]
        if not ids:
            break
        for i, cid in enumerate(ids):
            chunks.append({
                "id": cid,
                "meta": res["metadatas"][i],
                "doc": res["documents"][i],
            })
        if len(ids) < batch:
            break
        offset += batch
    return chunks


def section(title):
    return f"\n## {title}\n"


def main():
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    col = client.get_collection("openlex_datenschutz")

    print(f"Loading all chunks from ChromaDB ({CHROMA_PATH})…")
    chunks = load_all_chunks(col)
    print(f"  → {len(chunks)} chunks loaded")

    lines = [f"# Korpus-Audit {TODAY}", "", f"Chunks total: **{len(chunks)}**", ""]

    # ──────────────────────────────────────────────
    # 1. Source-Type + Gesetz-Inventar
    # ──────────────────────────────────────────────
    lines.append(section("1. Source-Type + Gesetz-Inventar"))

    source_types = Counter(c["meta"].get("source_type", "MISSING") for c in chunks)
    lines.append("### Source-Type-Verteilung")
    for st, cnt in source_types.most_common():
        lines.append(f"- `{st}`: {cnt}")

    gesetze = Counter(c["meta"].get("gesetz", "MISSING") for c in chunks)
    lines.append("\n### Gesetz-Verteilung (Top 30)")
    for g, cnt in gesetze.most_common(30):
        lines.append(f"- `{g}`: {cnt}")

    # ──────────────────────────────────────────────
    # 2. Gesetz-Naming-Inkonsistenzen
    # ──────────────────────────────────────────────
    lines.append(section("2. Gesetz-Naming-Inkonsistenzen"))

    known_gesetz_keys = list(gesetze.keys())

    # Suspected confusion pairs
    pairs = [
        ("TTDSG", "TDDDG"),
        ("TKG", "TDDDG"),
        ("TMG", "TDDDG"),
        ("UWG", "DSGVO"),
        ("DS-GVO", "DSGVO"),
        ("GVO", "DSGVO"),
        ("BDSG-neu", "BDSG"),
        ("BDSG2018", "BDSG"),
    ]
    found_issues = []
    for a, b in pairs:
        has_a = any(a.lower() in k.lower() for k in known_gesetz_keys)
        has_b = any(b.lower() in k.lower() for k in known_gesetz_keys)
        if has_a and has_b:
            found_issues.append(f"⚠️  Beide `{a}` und `{b}` vorhanden — mögliche Doppelbenennung")
        elif has_a and a in ("TTDSG", "TMG", "TKG"):
            found_issues.append(f"⚠️  Veraltete Bezeichnung `{a}` gefunden (sollte `{b}` sein?)")

    # Unknown gesetz names (not in known aliases)
    KNOWN_BASE = {"DSGVO", "BDSG", "TDDDG", "GG", "AEUV", "UrhG", "StGB", "BGB",
                  "ZPO", "HGB", "TKG", "TMG", "BetrVG", "SGB", "NIS2", "KI-VO",
                  "DDG", "DSGVO-Leitlinie", "Leitlinie", "Urteil", "Beschluss",
                  "Entscheidung", "Stellungnahme", "Orientierungshilfe", "Kurzpapier",
                  "FAQ", "Whitepaper", "Muster", "TTDSG", "AGG", "ArbGG", "EMRK",
                  "EUV", "GRCh", "NetzDG"}
    unknown_gesetz = [k for k in known_gesetz_keys
                      if k != "MISSING" and not any(b.lower() in k.lower() for b in KNOWN_BASE)]

    if found_issues:
        for fi in found_issues:
            lines.append(fi)
    else:
        lines.append("✅ Keine offensichtlichen Naming-Konflikte gefunden.")

    if unknown_gesetz:
        lines.append(f"\n**Unbekannte Gesetz-Werte** ({len(unknown_gesetz)}):")
        for uk in sorted(unknown_gesetz)[:20]:
            lines.append(f"- `{uk}`: {gesetze[uk]}")
    else:
        lines.append("✅ Alle Gesetz-Werte in Known-Liste.")

    # ──────────────────────────────────────────────
    # 3. DSGVO-Granularität (Artikel vs. Absatz)
    # ──────────────────────────────────────────────
    lines.append(section("3. DSGVO-Granularität"))

    dsgvo_chunks = [c for c in chunks if "dsgvo" in c["meta"].get("gesetz", "").lower()]
    lines.append(f"DSGVO-Chunks total: {len(dsgvo_chunks)}")

    # Gibt es artikel-Metadaten?
    has_artikel = sum(1 for c in dsgvo_chunks if c["meta"].get("artikel"))
    has_absatz = sum(1 for c in dsgvo_chunks if c["meta"].get("absatz"))
    lines.append(f"- Mit `artikel`-Meta: {has_artikel}")
    lines.append(f"- Mit `absatz`-Meta: {has_absatz}")

    # Artikel-Verteilung
    art_dist = Counter(c["meta"].get("artikel", "MISSING") for c in dsgvo_chunks)
    lines.append(f"\n**Artikel-Verteilung DSGVO** (Top 20):")
    for a, cnt in art_dist.most_common(20):
        lines.append(f"- Art. {a}: {cnt} Chunks")

    # Artikel mit besonders vielen Chunks (split-Problem?)
    overloaded = [(a, cnt) for a, cnt in art_dist.items() if cnt > 15 and a != "MISSING"]
    if overloaded:
        lines.append(f"\n⚠️ Artikel mit >15 Chunks (ggf. zu fein gesplittet): "
                     + ", ".join(f"Art.{a}({n})" for a, n in overloaded))

    # ──────────────────────────────────────────────
    # 4. BDSG-Granularität
    # ──────────────────────────────────────────────
    lines.append(section("4. BDSG-Granularität"))

    bdsg_chunks = [c for c in chunks if "bdsg" in c["meta"].get("gesetz", "").lower()]
    lines.append(f"BDSG-Chunks total: {len(bdsg_chunks)}")

    para_dist = Counter(c["meta"].get("paragraph", c["meta"].get("paragraf", "MISSING"))
                        for c in bdsg_chunks)
    lines.append(f"\n**§-Verteilung BDSG** (Top 20):")
    for p, cnt in para_dist.most_common(20):
        lines.append(f"- § {p}: {cnt} Chunks")

    # ──────────────────────────────────────────────
    # 5. Urteile-Audit
    # ──────────────────────────────────────────────
    lines.append(section("5. Urteile-Audit"))

    urteil_chunks = [c for c in chunks if c["meta"].get("source_type") == "urteil"]
    lines.append(f"Urteil-Chunks total: {len(urteil_chunks)}")

    # Segment-Typ-Verteilung
    seg_types = Counter(c["meta"].get("segment_type", "MISSING") for c in urteil_chunks)
    lines.append(f"\n**Segment-Type-Verteilung:**")
    for st, cnt in seg_types.most_common():
        lines.append(f"- `{st}`: {cnt}")

    # Chunk-Size-Verteilung
    sizes = [len(c["doc"]) for c in urteil_chunks]
    if sizes:
        avg_sz = sum(sizes) / len(sizes)
        lines.append(f"\n**Chunk-Größen:** avg={avg_sz:.0f}, min={min(sizes)}, max={max(sizes)}")
        too_small = sum(1 for s in sizes if s < 100)
        too_large = sum(1 for s in sizes if s > 4000)
        if too_small:
            lines.append(f"⚠️ {too_small} Chunks < 100 Zeichen (zu klein?)")
        if too_large:
            lines.append(f"⚠️ {too_large} Chunks > 4000 Zeichen (zu groß?)")

    # Bindestrich-Duplikate (gleiche Gesetz+AZ mehrfach)
    az_counter = Counter()
    for c in urteil_chunks:
        az = c["meta"].get("aktenzeichen", "")
        court = c["meta"].get("gericht", "")
        if az:
            az_counter[(court, az)] += 1
    dupes = [(k, v) for k, v in az_counter.items() if v > 8]
    if dupes:
        lines.append(f"\n**Urteile mit >8 Chunks (mögl. Duplikat-AZ):**")
        for (court, az), cnt in sorted(dupes, key=lambda x: -x[1])[:10]:
            lines.append(f"- {court} / {az}: {cnt} Chunks")

    # ──────────────────────────────────────────────
    # 6. Art. 4 DSGVO Parser-Check
    # ──────────────────────────────────────────────
    lines.append(section("6. Art. 4 DSGVO Parser-Check"))

    art4_chunks = [c for c in dsgvo_chunks
                   if str(c["meta"].get("artikel", "")) == "4"]
    lines.append(f"Art. 4 DSGVO Chunks: {len(art4_chunks)}")

    # Erwartete Definitionen
    EXPECTED_TERMS = [
        "personenbezogene Daten", "Verarbeitung", "Pseudonymisierung",
        "Verantwortlicher", "Auftragsverarbeiter", "Empfänger",
        "Einwilligung", "Verletzung"
    ]
    found_terms = {term: False for term in EXPECTED_TERMS}
    for c in art4_chunks:
        doc_lower = c["doc"].lower()
        for term in EXPECTED_TERMS:
            if term.lower() in doc_lower:
                found_terms[term] = True

    for term, found in found_terms.items():
        status = "✅" if found else "❌"
        lines.append(f"- {status} `{term}`")

    # ──────────────────────────────────────────────
    # 7. Coverage-Check für 6 Zero-MRR-Kategorien
    # ──────────────────────────────────────────────
    lines.append(section("7. Coverage-Check: Zero-MRR-Kategorien"))

    ZERO_MRR_CATS = [
        "verhaltensbasiertes_targeting",
        "beschaeftigtendatenschutz",
        "internationale_datentransfers",
        "cookie_tracking",
        "direktwerbung_widerspruch",
        "auftragsverarbeitung",
    ]

    # Check welche source_types / gesetz values abgedeckt sind
    lines.append("Coverage-Analyse der 6 Kategorien mit MRR=0 in eval_v3/messy:\n")

    # Map categories to keywords for rough coverage check
    CAT_KEYWORDS = {
        "verhaltensbasiertes_targeting": ["targeting", "profiling", "tracking", "werbung"],
        "beschaeftigtendatenschutz": ["beschäftig", "arbeitnehm", "§ 26 bdsg", "arbeits"],
        "internationale_datentransfers": ["drittland", "standard", "transfer", "schrems", "scc"],
        "cookie_tracking": ["cookie", "tracking", "einwillig", "telemedi"],
        "direktwerbung_widerspruch": ["direktwerbung", "widerspruch", "art. 21"],
        "auftragsverarbeitung": ["auftragsv", "art. 28", "avv"],
    }

    for cat in ZERO_MRR_CATS:
        keywords = CAT_KEYWORDS.get(cat, [])
        matching = []
        for c in chunks:
            doc_lower = c["doc"].lower()
            if any(kw in doc_lower for kw in keywords):
                matching.append(c["meta"].get("source_type", "?"))
        cnt = len(matching)
        st_dist = Counter(matching)
        lines.append(f"**{cat}**")
        lines.append(f"  Chunks mit Kategorie-Keyword: {cnt}")
        if st_dist:
            lines.append(f"  Source-Types: {dict(st_dist.most_common(5))}")
        else:
            lines.append(f"  ❌ KEINE CHUNKS — Korpus-Lücke!")
        lines.append("")

    # ──────────────────────────────────────────────
    # 8. Eval Gold-Chunk-Existenz-Check
    # ──────────────────────────────────────────────
    lines.append(section("8. Eval Gold-Chunk-Existenz"))

    existing_ids = {c["id"] for c in chunks}

    for set_name in ("canonical", "messy"):
        for suf in ("", "_v3"):
            p = EVAL_SETS_DIR / f"{set_name}{suf}.json"
            if not p.exists():
                continue
            with open(p) as f:
                eval_set = json.load(f)

            missing = []
            total_refs = 0
            for entry in eval_set:
                refs = entry.get("must_contain_chunk_ids") or entry.get("relevant_chunk_ids") or []
                for ref in refs:
                    total_refs += 1
                    if ref not in existing_ids:
                        missing.append((entry.get("query", entry.get("question", "?"))[:60], ref))

            lines.append(f"**{p.name}** ({len(eval_set)} Queries, {total_refs} Gold-Chunk-Refs):")
            if missing:
                lines.append(f"  ❌ {len(missing)} Gold-Chunks NICHT in ChromaDB!")
                for q, cid in missing[:10]:
                    lines.append(f"  - `{cid}` (Query: {q})")
                if len(missing) > 10:
                    lines.append(f"  … und {len(missing)-10} weitere")
            else:
                lines.append(f"  ✅ Alle Gold-Chunks in ChromaDB vorhanden")
            lines.append("")

    # ──────────────────────────────────────────────
    # 9. Gesamt-Statistik + Empfehlungen
    # ──────────────────────────────────────────────
    lines.append(section("9. Gesamt-Statistik + Empfehlungen"))

    lines.append(f"| Metrik | Wert |")
    lines.append(f"|--------|------|")
    lines.append(f"| Chunks gesamt | {len(chunks)} |")
    lines.append(f"| Source-Types | {len(source_types)} |")
    lines.append(f"| Unterschiedliche Gesetze | {len(gesetze)} |")
    lines.append(f"| DSGVO-Chunks | {len(dsgvo_chunks)} |")
    lines.append(f"| BDSG-Chunks | {len(bdsg_chunks)} |")
    lines.append(f"| Urteil-Chunks | {len(urteil_chunks)} |")

    lines.append("\n### Empfehlungen")
    # Dynamisch basierend auf Findings
    recs = []
    if unknown_gesetz:
        recs.append(f"1. **Gesetz-Normalisierung**: {len(unknown_gesetz)} unbekannte Gesetz-Werte bereinigen")
    if found_issues:
        recs.append(f"2. **Naming-Konflikte**: {'; '.join(found_issues[:2])}")

    # Check Gold-Chunk-Missing aus Abschnitt 8
    recs.append("3. **Eval-Set-Alignment**: Prüfe ob Gold-Chunk-IDs mit DB-IDs übereinstimmen (s. Sektion 8)")
    recs.append("4. **Zero-MRR-Kategorien**: Korpus gezielt mit fehlendem Content zu den 6 Kategorien anreichern")

    for r in recs:
        lines.append(r)

    # Write report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\n✅ Report geschrieben: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
