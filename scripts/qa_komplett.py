#!/usr/bin/env python3
"""
qa_komplett.py – Umfassende Qualitätsprüfung der OpenLex-Datenbank.
"""

from __future__ import annotations

import glob
import json
import os
import random
import re
from collections import Counter, defaultdict

BASE_DIR = os.path.expanduser("~/openlex-mvp")
CHROMADB_DIR = os.path.join(BASE_DIR, "chromadb")
COLLECTION_NAME = "openlex_datenschutz"
MODEL_NAME = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"

DIRS = {
    "gesetze": os.path.join(BASE_DIR, "data", "gesetze"),
    "gesetze_granular": os.path.join(BASE_DIR, "data", "gesetze_granular"),
    "urteile": os.path.join(BASE_DIR, "data", "urteile"),
    "leitlinien": os.path.join(BASE_DIR, "data", "leitlinien"),
    "behoerden": os.path.join(BASE_DIR, "data", "behoerden"),
    "methodenwissen": os.path.join(BASE_DIR, "data", "methodenwissen"),
}

issues: list[str] = []
warnings_list: list[str] = []
score = 100  # Start bei 100, Abzüge für Probleme


def load_jsons(directory: str) -> list[dict]:
    docs = []
    for f in sorted(glob.glob(os.path.join(directory, "*.json"))):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                docs.append(json.load(fh))
        except Exception:
            pass
    return docs


def section(title: str):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ═══════════════════════════════════════════════════════════════════════════
# TEIL 1 – Bestandsaufnahme ChromaDB
# ═══════════════════════════════════════════════════════════════════════════

def teil1():
    global score
    section("TEIL 1 – Bestandsaufnahme ChromaDB")

    import chromadb
    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    col = client.get_collection(COLLECTION_NAME)
    total = col.count()
    print(f"\n  Gesamt: {total:,} Chunks")

    all_data = col.get(include=["metadatas"])
    type_counts = Counter()
    type_examples = {}
    type_unique = defaultdict(set)

    for cid, meta in zip(all_data["ids"], all_data["metadatas"]):
        st = meta.get("source_type", "unbekannt")
        type_counts[st] += 1
        if st not in type_examples:
            label = (meta.get("volladresse") or meta.get("thema")
                     or meta.get("titel") or meta.get("aktenzeichen") or cid)
            type_examples[st] = label[:60]
        unique_key = (meta.get("gesetz") or meta.get("gericht")
                      or meta.get("titel") or meta.get("quelle") or "")
        type_unique[st].add(unique_key)

    print(f"\n  {'Source Type':<25} {'Chunks':>8} {'Unique':>8}  Beispiel")
    print("  " + "-" * 75)
    for st, cnt in type_counts.most_common():
        ex = type_examples.get(st, "")
        uni = len(type_unique[st])
        print(f"  {st:<25} {cnt:>8} {uni:>8}  {ex}")

    if total < 20000:
        issues.append(f"Nur {total} Chunks – erwartet >25.000")
        score -= 10

    return all_data


# ═══════════════════════════════════════════════════════════════════════════
# TEIL 2 – Gesetze prüfen
# ═══════════════════════════════════════════════════════════════════════════

def teil2():
    global score
    section("TEIL 2 – Gesetze prüfen")

    docs = load_jsons(DIRS["gesetze"])
    print(f"\n  {len(docs)} Gesetze-Dateien geladen.")

    # a) Gesetze-Übersicht
    gesetz_paras = defaultdict(list)
    for d in docs:
        gesetz_paras[d.get("gesetz", "?")].append(d.get("paragraph", ""))

    print(f"\n  {'Gesetz':<12} {'Paragraphen':>12}")
    print("  " + "-" * 26)
    for g in sorted(gesetz_paras.keys()):
        print(f"  {g:<12} {len(gesetz_paras[g]):>12}")

    # b) DSGVO Vollständigkeit
    dsgvo_arts = set()
    dsgvo_egs = set()
    for d in docs:
        if d.get("gesetz") != "DSGVO":
            continue
        p = d.get("paragraph", "")
        am = re.match(r"Art\.\s*(\d+)", p)
        if am:
            dsgvo_arts.add(int(am.group(1)))
        em = re.match(r"Erwägungsgrund\s+(\d+)", p)
        if em:
            dsgvo_egs.add(int(em.group(1)))

    missing_arts = set(range(1, 100)) - dsgvo_arts
    missing_egs = set(range(1, 174)) - dsgvo_egs
    print(f"\n  DSGVO Artikel: {len(dsgvo_arts)}/99", end="")
    if missing_arts:
        print(f" – FEHLEN: {sorted(missing_arts)}")
        issues.append(f"DSGVO: {len(missing_arts)} Artikel fehlen")
        score -= 5
    else:
        print(" ✅")
    print(f"  DSGVO Erwägungsgründe: {len(dsgvo_egs)}/173", end="")
    if missing_egs:
        print(f" – FEHLEN: {sorted(missing_egs)[:10]}...")
        score -= 3
    else:
        print(" ✅")

    # c) BDSG Vollständigkeit
    bdsg_paras = set()
    for d in docs:
        if d.get("gesetz") != "BDSG":
            continue
        pm = re.match(r"§\s*(\d+)", d.get("paragraph", ""))
        if pm:
            bdsg_paras.add(int(pm.group(1)))
    print(f"  BDSG Paragraphen: {len(bdsg_paras)}")

    # d) Granulare Chunks Art. 6 DSGVO
    gran = load_jsons(DIRS["gesetze_granular"])
    art6 = [d for d in gran if d.get("gesetz") == "DSGVO"
            and d.get("volladresse", "").startswith("Art. 6")]
    print(f"\n  Art. 6 DSGVO granulare Chunks: {len(art6)}")
    for c in sorted(art6, key=lambda x: x.get("volladresse", ""))[:10]:
        print(f"    {c['volladresse']}: {c['text'][:50]}...")
    if len(art6) < 10:
        warnings_list.append("Art. 6 DSGVO hat weniger als 10 granulare Chunks")

    # e) Art. 5 DSGVO
    art5 = [d for d in gran if d.get("gesetz") == "DSGVO"
            and d.get("volladresse", "").startswith("Art. 5")]
    print(f"\n  Art. 5 DSGVO granulare Chunks: {len(art5)}")
    for c in sorted(art5, key=lambda x: x.get("volladresse", ""))[:8]:
        print(f"    {c['volladresse']}")

    # f) EG-Artikel-Verknüpfungen
    eg_linked = [(d.get("paragraph"), d.get("erlaeutert_artikel"))
                 for d in docs if d.get("erlaeutert_artikel")]
    print(f"\n  Erwägungsgründe mit Artikel-Verknüpfung: {len(eg_linked)}")
    for p, arts in eg_linked[:5]:
        print(f"    {p} → {arts}")


# ═══════════════════════════════════════════════════════════════════════════
# TEIL 3 – Urteile prüfen
# ═══════════════════════════════════════════════════════════════════════════

def teil3():
    global score
    section("TEIL 3 – Urteile prüfen")

    docs = load_jsons(DIRS["urteile"])
    print(f"\n  {len(docs)} Urteile geladen.")

    # a) Nach Gericht
    gericht_counts = Counter()
    for d in docs:
        g = d.get("gericht", "Unbekannt")
        # Normalisiere
        if "EuGH" in g or g == "EuGH":
            g = "EuGH"
        elif "EuG" in g and "EuGH" not in g:
            g = "EuG"
        elif any(x in g for x in ["BGH", "Zivilsenat", "Strafsenat"]):
            g = "BGH"
        elif "BVerfG" in g:
            g = "BVerfG"
        elif "BAG" in g:
            g = "BAG"
        elif "BFH" in g:
            g = "BFH"
        elif "BSG" in g:
            g = "BSG"
        elif "BVerwG" in g:
            g = "BVerwG"
        elif "OLG" in g or "Oberlandesgericht" in g:
            g = "OLG"
        elif "LG" in g or "Landgericht" in g:
            g = "LG"
        elif "VG" in g or "Verwaltungsgericht" in g:
            g = "VG"
        elif "AG" in g or "Amtsgericht" in g:
            g = "AG"
        elif "LAG" in g or "Landesarbeitsgericht" in g:
            g = "LAG"
        elif "SG" in g or "Sozialgericht" in g:
            g = "SG"
        gericht_counts[g] += 1

    print(f"\n  {'Gericht':<20} {'Anzahl':>8}")
    print("  " + "-" * 30)
    for g, cnt in gericht_counts.most_common():
        print(f"  {g:<20} {cnt:>8}")

    # b) Schlüsselurteile
    key_cases = {
        "C-311/18": "Schrems II",
        "C-131/12": "Google Spain",
        "C-252/21": "Meta",
        "C-673/17": "Planet49",
        "C-807/21": "Deutsche Wohnen",
        "C-34/21": "Beschäftigtendatenschutz",
        "C-621/22": "KNLTB",
        "C-634/21": "SCHUFA Scoring",
        "C-300/21": "Österreichische Post",
        "C-582/14": "Breyer",
        "C-40/17": "Fashion ID",
        "C-210/16": "Wirtschaftsakademie",
    }

    print(f"\n  Schlüsselurteile-Check:")
    found_key = 0
    for az, name in key_cases.items():
        found = None
        for d in docs:
            d_az = d.get("aktenzeichen", "") + " " + d.get("rechtssache", "")
            if az in d_az:
                found = d
                break
        if found:
            found_key += 1
            seg = "segm." if found.get("segmentiert") else "nicht segm."
            datum = found.get("datum", "?")
            print(f"    ✅ {az} ({name}): {datum}, {seg}")
        else:
            print(f"    ❌ {az} ({name}): NICHT GEFUNDEN")
            issues.append(f"Schlüsselurteil {az} ({name}) fehlt")
            score -= 2

    # c) Segmentierungsstatus
    seg_count = sum(1 for d in docs if d.get("segmentiert"))
    print(f"\n  Segmentiert: {seg_count}/{len(docs)} ({seg_count/len(docs)*100:.0f}%)")

    # d) GDPRhub-Tags
    gdpr_tagged = sum(1 for d in docs if d.get("dsgvo_artikel"))
    print(f"  Mit DSGVO-Artikel-Tags (GDPRhub): {gdpr_tagged}")

    # e) Stichprobe
    eugh = [d for d in docs if d.get("gericht") == "EuGH" and d.get("volltext")]
    if eugh:
        print(f"\n  Stichprobe (3 zufällige EuGH-Urteile):")
        for d in random.sample(eugh, min(3, len(eugh))):
            az = d.get("aktenzeichen", "?")
            vt = d.get("volltext", "")[:200].replace("\n", " ")
            print(f"    {az}: {vt}...")


# ═══════════════════════════════════════════════════════════════════════════
# TEIL 4 – Behörden-Dokumente prüfen
# ═══════════════════════════════════════════════════════════════════════════

def teil4():
    global score
    section("TEIL 4 – Behörden-Dokumente prüfen")

    leit = load_jsons(DIRS["leitlinien"])
    beh = load_jsons(DIRS["behoerden"])
    all_docs = leit + beh
    print(f"\n  Leitlinien: {len(leit)}, Behörden: {len(beh)}, Gesamt: {len(all_docs)}")

    # a) Nach Quelle
    quelle_counts = Counter(d.get("quelle", "?") for d in all_docs)
    print(f"\n  {'Quelle':<30} {'Anzahl':>8}")
    print("  " + "-" * 40)
    for q, cnt in quelle_counts.most_common():
        print(f"  {q:<30} {cnt:>8}")

    # b) DSK-Kurzpapiere
    kp = [d for d in all_docs if "kurzpapier" in d.get("typ", "").lower()
          or "kurzpapier" in d.get("titel", "").lower()]
    print(f"\n  DSK-Kurzpapiere: {len(kp)}/20")
    if len(kp) < 20:
        warnings_list.append(f"Nur {len(kp)} von 20 DSK-Kurzpapieren")
    for k in kp[:5]:
        print(f"    {k.get('titel', '?')[:60]}")

    # c+d) Stichprobe + Umlaute-Check
    kaputte_umlaute = re.compile(r"Ã¤|Ã¶|Ã¼|ÃŸ|Ã\x84|Ã\x96|Ã\x9c|Â")
    umlaut_count = 0
    for d in all_docs:
        text = d.get("text", "")
        if kaputte_umlaute.search(text):
            umlaut_count += 1

    print(f"\n  Dokumente mit kaputten Umlauten: {umlaut_count}/{len(all_docs)}")
    if umlaut_count > len(all_docs) * 0.3:
        issues.append(f"{umlaut_count} Dokumente mit kaputten Umlauten (>30%)")
        score -= 5

    print(f"\n  Stichprobe (5 zufällige Dokumente):")
    for d in random.sample(all_docs, min(5, len(all_docs))):
        t = d.get("titel", "?")[:50]
        txt = d.get("text", "")[:200].replace("\n", " ")
        print(f"    [{d.get('quelle','?')}] {t}")
        print(f"      {txt}...")


# ═══════════════════════════════════════════════════════════════════════════
# TEIL 5 – Methodenwissen prüfen
# ═══════════════════════════════════════════════════════════════════════════

def teil5():
    global score
    section("TEIL 5 – Methodenwissen prüfen")

    docs = load_jsons(DIRS["methodenwissen"])
    print(f"\n  {len(docs)} Methodenwissen-Chunks:")
    for d in docs:
        print(f"    {d.get('thema', '?')[:70]}")

    # DSK-spezifische Chunks prüfen
    expected = ["Microsoft 365", "Google Analytics", "Videoüberwachung", "Cookies", "KI"]
    print(f"\n  DSK-Behörden-Chunks:")
    for topic in expected:
        found = any(topic.lower() in d.get("thema", "").lower() for d in docs)
        status = "✅" if found else "❌"
        print(f"    {status} {topic}")
        if not found:
            warnings_list.append(f"Methodenwissen '{topic}' fehlt")
            score -= 1


# ═══════════════════════════════════════════════════════════════════════════
# TEIL 6 – ChromaDB-Konsistenz
# ═══════════════════════════════════════════════════════════════════════════

def teil6():
    section("TEIL 6 – ChromaDB-Konsistenz")

    import chromadb
    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    col = client.get_collection(COLLECTION_NAME)
    db_count = col.count()

    # Dateien auf der Festplatte zählen
    file_counts = {}
    for name, d in DIRS.items():
        if os.path.isdir(d):
            file_counts[name] = len(glob.glob(os.path.join(d, "*.json")))

    total_files = sum(file_counts.values())
    print(f"\n  ChromaDB Chunks: {db_count:,}")
    print(f"  Dateien gesamt:  {total_files:,}")
    print(f"\n  {'Verzeichnis':<25} {'Dateien':>8}")
    print("  " + "-" * 35)
    for name, cnt in file_counts.items():
        print(f"  {name:<25} {cnt:>8}")

    print(f"\n  Hinweis: ChromaDB enthält mehr Chunks als Dateien,")
    print(f"  da ein Dokument in mehrere Chunks aufgeteilt wird.")


# ═══════════════════════════════════════════════════════════════════════════
# TEIL 7 – Retrieval-Qualitätstest
# ═══════════════════════════════════════════════════════════════════════════

def teil7():
    global score
    section("TEIL 7 – Retrieval-Qualitätstest (volle Pipeline aus app.py)")

    import sys
    sys.path.insert(0, BASE_DIR)
    from app import retrieve

    tests = [
        {
            "query": "Art. 6 Abs. 1 lit. f DSGVO berechtigtes Interesse",
            "expect": ["Art. 6", "EG 47", "berechtigtes Interesse", "Methodenwissen"],
        },
        {
            "query": "Schrems II Drittlandtransfer USA",
            "expect": ["C-311/18", "Schrems", "Drittland", "DPF", "Privacy"],
        },
        {
            "query": "Einwilligung Cookie Banner",
            "expect": ["Planet49", "C-673/17", "TTDSG", "§ 25", "Cookie", "Einwilligung"],
        },
        {
            "query": "Videoüberwachung Arbeitsplatz",
            "expect": ["Videoüberwachung", "§ 4", "Kamera", "Art. 6"],
        },
        {
            "query": "Schadensersatz DSGVO immaterieller Schaden",
            "expect": ["Art. 82", "C-300/21", "Schaden", "Schadensersatz"],
        },
        {
            "query": "Microsoft 365 Datenschutz",
            "expect": ["Microsoft", "365", "DSK", "Telemetrie", "Cloud"],
        },
        {
            "query": "Scoring SCHUFA automatisierte Entscheidung",
            "expect": ["C-634/21", "SCHUFA", "Scoring", "Art. 22", "automatisiert"],
        },
        {
            "query": "Auftragsverarbeitung Cloud",
            "expect": ["Art. 28", "Auftragsverarbeitung", "Cloud", "Auftragsverarbeiter"],
        },
        {
            "query": "Recht auf Löschung Vergessenwerden",
            "expect": ["Art. 17", "Löschung", "Vergessen", "EG 65", "EG 66"],
        },
        {
            "query": "Beschäftigtendatenschutz § 26 BDSG",
            "expect": ["§ 26", "C-34/21", "Beschäftigte", "Art. 88"],
        },
    ]

    total_relevant = 0
    total_checks = 0

    for test in tests:
        q = test["query"]
        expects = test["expect"]

        chunks = retrieve(q)

        print(f"\n  Q: '{q}'")
        for i, chunk in enumerate(chunks[:3]):
            meta = chunk["meta"]
            st = meta.get("source_type", "?")
            label = (meta.get("volladresse") or meta.get("thema")
                     or meta.get("titel") or meta.get("aktenzeichen") or "")[:50]
            ce = chunk.get("ce_score", 0)
            src = chunk.get("source", "?")

            combined = (label + " " + chunk["text"][:200]).lower()
            relevant = any(e.lower() in combined for e in expects)
            icon = "✅" if relevant else "❌"
            total_checks += 1
            if relevant:
                total_relevant += 1

            print(f"    {icon} {i+1}. [{st}|{src}] {label} (CE={ce:.2f})")

    retrieval_score = total_relevant / total_checks * 100 if total_checks else 0
    print(f"\n  Retrieval-Relevanz: {total_relevant}/{total_checks} ({retrieval_score:.0f}%)")

    if retrieval_score < 50:
        issues.append(f"Retrieval-Qualität nur {retrieval_score:.0f}%")
        score -= 15
    elif retrieval_score < 70:
        warnings_list.append(f"Retrieval-Qualität {retrieval_score:.0f}% (verbesserungswürdig)")
        score -= 5


# ═══════════════════════════════════════════════════════════════════════════
# Zusammenfassung
# ═══════════════════════════════════════════════════════════════════════════

def zusammenfassung():
    global score
    section("ZUSAMMENFASSUNG")

    score = max(0, min(100, score))
    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    else:
        grade = "D"

    print(f"\n  Gesamtnote: {grade} ({score}/100)")

    if issues:
        print(f"\n  ❌ Kritische Probleme ({len(issues)}):")
        for i in issues:
            print(f"    - {i}")

    if warnings_list:
        print(f"\n  ⚠️ Warnungen ({len(warnings_list)}):")
        for w in warnings_list:
            print(f"    - {w}")

    if not issues and not warnings_list:
        print("\n  ✅ Keine Probleme gefunden!")

    print(f"\n  Handlungsempfehlungen:")
    if any("Umlaut" in i for i in issues):
        print("    1. PDF-Extraktion mit OCR-Nachverarbeitung für Umlaute wiederholen")
    if any("Retrieval" in i or "Retrieval" in w for i in issues for w in warnings_list):
        print("    2. Embedding-Texte mit mehr Kontext anreichern (Titel + Themen)")
    if any("fehlt" in i.lower() for i in issues):
        print("    3. Fehlende Schlüsselurteile/Gesetze manuell nachlagen")
    if not issues:
        print("    Keine kritischen Handlungsempfehlungen.")

    print("\n" + "=" * 60)


# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("OpenLex MVP – Qualitätsprüfung (QA)")
    print("=" * 60)

    teil1()
    teil2()
    teil3()
    teil4()
    teil5()
    teil6()
    teil7()
    zusammenfassung()


if __name__ == "__main__":
    main()
