#!/usr/bin/env python3
"""
refine_behoerden.py – Verbessert die Durchsuchbarkeit von Behörden-Leitlinien
und DSK-Dokumenten durch thematische Segmentierung, Themen-Tagging und
angereicherte Embeddings.
"""

from __future__ import annotations

import glob
import json
import os
import re
import time

# ---------------------------------------------------------------------------
# Pfade & Konstanten
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
LEITLINIEN_DIR = os.path.join(BASE_DIR, "data", "leitlinien")
BEHOERDEN_DIR = os.path.join(BASE_DIR, "data", "behoerden")
MW_DIR = os.path.join(BASE_DIR, "data", "methodenwissen")
CHROMADB_DIR = os.path.join(BASE_DIR, "chromadb")
COLLECTION_NAME = "openlex_datenschutz"
MODEL_NAME = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"
BATCH_SIZE = 100

# Themen-Keywords
THEMEN_KEYWORDS: dict[str, list[str]] = {
    "Microsoft 365": ["microsoft 365", "microsoft365", "ms 365", "office 365", "m365", "ms365"],
    "Cloud": ["cloud", "saas", "iaas", "paas", "cloud computing"],
    "Videoüberwachung": ["videoüberwachung", "kameraüberwachung", "videokamera", "überwachungskamera"],
    "Beschäftigtendatenschutz": ["beschäftigtendatenschutz", "beschäftigten", "arbeitnehmer", "arbeitgeber",
                                   "betriebsvereinbarung", "betriebsrat"],
    "Einwilligung": ["einwilligung", "consent", "opt-in"],
    "Cookies/Tracking": ["cookie", "tracking", "tracker", "fingerprinting", "tracking-pixel"],
    "Scoring": ["scoring", "bonitätsbewertung", "schufa", "kreditscoring"],
    "KI": ["künstliche intelligenz", "ki-system", " ki ", "machine learning", "maschinelles lernen",
           "algorithmus", "automatisierte entscheidung", "chatgpt", "large language"],
    "Social Media": ["social media", "facebook", "instagram", "whatsapp", "tiktok", "twitter",
                      "linkedin", "fanpage", "soziale netzwerke"],
    "Google Analytics": ["google analytics", "google tag manager", "ga4"],
    "Auftragsverarbeitung": ["auftragsverarbeitung", "auftragsverarbeiter", "avv", "art. 28"],
    "Drittlandtransfer": ["drittland", "drittstaatentransfer", "usa", "standardvertragsklauseln",
                           "scc", "privacy shield", "data privacy framework", "dpf", "schrems"],
    "Löschkonzept": ["löschkonzept", "löschfrist", "löschpflicht", "aufbewahrungsfrist"],
    "DSFA": ["datenschutz-folgenabschätzung", "dsfa", "dpia", "folgenabschätzung"],
    "Datenpanne": ["datenpanne", "data breach", "datenschutzvorfall", "meldepflicht", "art. 33", "art. 34"],
    "Bußgeld": ["bußgeld", "sanktion", "art. 83", "ordnungswidrigkeit"],
    "Gesundheitsdaten": ["gesundheitsdaten", "patientendaten", "arzt", "krankenhaus", "medizin",
                          "elektronische patientenakte"],
    "Forschung": ["forschung", "wissenschaft", "statistik", "forschungszweck"],
    "Smart Home/IoT": ["smart home", "iot", "internet of things", "connected car", "smart tv",
                        "wearable", "fitness-tracker"],
    "Schule/Bildung": ["schule", "schulen", "bildung", "schüler", "lehrer", "unterricht",
                        "homeschooling", "lernplattform"],
    "E-Mail/Fax": ["fax", "e-mail-verschlüsselung", "transportverschlüsselung", "ende-zu-ende"],
    "Videokonferenz": ["videokonferenz", "zoom", "teams", "webex", "jitsi", "videokonferenzsystem"],
}

VERWEIS_RE = re.compile(
    r"Art\.?\s*\d+\s*(?:Abs\.?\s*\d+\s*)?(?:(?:lit\.?\s*[a-z]|Nr\.?\s*\d+)\s*)?"
    r"(?:DSGVO|DS-GVO|BDSG|TTDSG|UWG)"
    r"|§§?\s*\d+[a-z]?\s*(?:Abs\.?\s*\d+\s*)?[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*",
    re.UNICODE,
)

# Überschriften-Pattern
HEADING_RE = re.compile(
    r"(?:^|\n)"
    r"("
    # Nummerierte Abschnitte: 1. / 1.1 / I. / II. / a) etc.
    r"(?:\d+(?:\.\d+)*\.?\s+[A-ZÄÖÜ].{5,75})"
    r"|(?:[IVX]+\.\s+[A-ZÄÖÜ].{5,75})"
    r"|(?:[a-z]\)\s+[A-ZÄÖÜ].{5,75})"
    # GROSSBUCHSTABEN-Zeilen (mindestens 60% Großbuchstaben, 10-80 Zeichen)
    r"|(?:[A-ZÄÖÜ][A-ZÄÖÜ\s\-:,/]{8,78})"
    # Kurze Zeilen ohne Punkt am Ende (10-80 Zeichen)
    r"|(?:[A-ZÄÖÜ][^\n]{8,78}(?<![.;,]))"
    r")"
    r"\s*\n",
    re.MULTILINE,
)


def sanitize(n: str) -> str:
    return re.sub(r'[<>:"/\\|?*\s]+', "_", n).strip("_")[:120]


def find_verweise(text: str) -> list[str]:
    return list(set(VERWEIS_RE.findall(text)))


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 1 – Thematische Segmentierung
# ═══════════════════════════════════════════════════════════════════════════


def segment_document(text: str) -> list[dict]:
    """Segmentiert ein Dokument anhand von Überschriften."""
    if not text or len(text) < 100:
        return [{"title": "", "text": text}]

    # Finde alle Überschriften-Positionen
    headings: list[tuple[int, str]] = []
    for m in HEADING_RE.finditer(text):
        title = m.group(1).strip()
        # Filter: Überschrift muss sinnvoll sein
        if len(title) < 10:
            continue
        # Keine reinen Zahlen oder Datumstrings
        if re.match(r"^[\d\s./-]+$", title):
            continue
        # Nicht zu viele Sonderzeichen
        if sum(1 for c in title if c.isalpha()) < len(title) * 0.4:
            continue
        headings.append((m.start(), title))

    if not headings:
        # Keine Überschriften → Text in ~2500-Zeichen-Blöcke teilen
        chunks = []
        for i in range(0, len(text), 2500):
            block = text[i:i + 2500].strip()
            if block and len(block) > 50:
                chunks.append({"title": f"Abschnitt {len(chunks)+1}", "text": block})
        return chunks if chunks else [{"title": "", "text": text}]

    # Abschnitte zwischen Überschriften schneiden
    sections = []
    for i, (pos, title) in enumerate(headings):
        # Text bis zur nächsten Überschrift
        next_pos = headings[i + 1][0] if i + 1 < len(headings) else len(text)
        # Start: nach der Überschrifts-Zeile
        text_start = text.find("\n", pos)
        if text_start == -1 or text_start > pos + 200:
            text_start = pos + len(title)
        section_text = text[text_start:next_pos].strip()

        if not section_text or len(section_text) < 30:
            continue

        # Sehr lange Abschnitte aufteilen
        if len(section_text) > 5000:
            for j in range(0, len(section_text), 2500):
                part = section_text[j:j + 2500].strip()
                if part and len(part) > 50:
                    part_title = f"{title} (Teil {j // 2500 + 1})" if j > 0 else title
                    sections.append({"title": part_title, "text": part})
        else:
            sections.append({"title": title, "text": section_text})

    # Text vor der ersten Überschrift
    if headings[0][0] > 100:
        preamble = text[:headings[0][0]].strip()
        if len(preamble) > 50:
            sections.insert(0, {"title": "Einleitung", "text": preamble[:3000]})

    return sections if sections else [{"title": "", "text": text}]


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 2 – Themen-Extraktion
# ═══════════════════════════════════════════════════════════════════════════


def extract_themen(text: str) -> list[str]:
    """Findet bekannte Datenschutz-Themen im Text."""
    text_lower = text.lower()
    found = []
    for thema, keywords in THEMEN_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                found.append(thema)
                break
    return found


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 5 – Methodenwissen-Chunks
# ═══════════════════════════════════════════════════════════════════════════

BEHOERDEN_MW = [
    {
        "thema": "DSK zu Microsoft 365 – Bewertung und Hauptkritikpunkte",
        "text": (
            "Die Datenschutzkonferenz (DSK) hat am 24.11.2022 die 'Petersberger Erklärung' zu Microsoft 365 verabschiedet. "
            "Hauptkritikpunkte: 1. Mangelnde Transparenz: Microsoft informiert nicht hinreichend über alle Verarbeitungstätigkeiten, "
            "insbesondere bei Telemetrie- und Diagnosedaten. 2. Unzureichende Kontrolle: Der Verantwortliche kann nicht alle "
            "Datenflüsse steuern und überprüfen. 3. Drittlandtransfer: Datenübermittlung in die USA trotz Data Privacy Framework "
            "nicht vollständig geklärt für alle Verarbeitungen. 4. Telemetriedaten: Umfang und Zweck der Erfassung nicht transparent. "
            "EU Data Boundary: Microsoft hat zugesagt, EU-Daten in der EU zu speichern. Die DSK hat dies als positiven Schritt "
            "anerkannt, aber keinen Unbedenklichkeitsbeschluss gefasst. "
            "Ergebnis: Kein generelles Verbot, aber der Verantwortliche muss eigene Risikobewertung durchführen und "
            "geeignete Konfiguration sicherstellen. Eine DSFA nach Art. 35 DSGVO ist in der Regel erforderlich."
        ),
    },
    {
        "thema": "DSK zu Google Analytics – Drittlandtransfer-Problematik",
        "text": (
            "Die deutschen Datenschutzaufsichtsbehörden haben im Rahmen der Coordinated Enforcement nach Schrems II "
            "festgestellt, dass der Einsatz von Google Analytics in der Standardkonfiguration regelmäßig gegen die DSGVO verstößt. "
            "Grund: Übermittlung personenbezogener Daten (IP-Adressen, Cookies) in die USA ohne ausreichende Rechtsgrundlage. "
            "Auch die IP-Anonymisierung in Google Analytics 4 (GA4) löst das Problem nicht vollständig, da die Daten "
            "zunächst auf Google-Servern in den USA verarbeitet werden. "
            "Auch nach dem Angemessenheitsbeschluss zum Data Privacy Framework (DPF) vom 10.07.2023 bleiben Fragen offen: "
            "Der Verantwortliche muss prüfen, ob Google unter dem DPF zertifiziert ist und ob die spezifische Verarbeitung "
            "vom DPF gedeckt ist. Eine DSFA kann erforderlich sein. "
            "Alternativen: Matomo (selbstgehostet), Plausible, oder serverseitiges Tracking ohne Drittlandtransfer."
        ),
    },
    {
        "thema": "DSK zu Videoüberwachung – Orientierungshilfe",
        "text": (
            "Die DSK-Orientierungshilfe Videoüberwachung unterscheidet: "
            "Öffentliche Stellen: § 4 BDSG als spezielle Rechtsgrundlage für Videoüberwachung öffentlich zugänglicher Räume. "
            "Nicht-öffentliche Stellen: Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse) als Rechtsgrundlage. "
            "Prüfungsschritte: 1. Berechtigtes Interesse (Eigentumsschutz, Schutz von Personen), "
            "2. Erforderlichkeit (keine mildere Maßnahme wie Schlösser, Alarmanlagen), "
            "3. Interessenabwägung (Privatsphäre der Betroffenen, Erwartungshaltung, Art des überwachten Bereichs). "
            "Kennzeichnungspflicht: Art. 13 DSGVO – gut sichtbares Hinweisschild mit Angabe des Verantwortlichen. "
            "Speicherdauer: In der Regel maximal 48-72 Stunden, längere Speicherung nur mit besonderer Begründung. "
            "DSFA: Bei systematischer Videoüberwachung öffentlich zugänglicher Räume regelmäßig erforderlich (DSK-Blacklist). "
            "Audioaufzeichnung: Grundsätzlich unverhältnismäßig und unzulässig."
        ),
    },
    {
        "thema": "DSK zu Cookies und Tracking – Orientierungshilfe Telemedien 2021",
        "text": (
            "Die DSK-Orientierungshilfe Telemedienanbieter (2021, aktualisiert) regelt den Einsatz von Cookies und Tracking: "
            "Zweistufige Prüfung: Stufe 1: TTDSG § 25 – Zugriff auf das Endgerät. "
            "Grundsatz: Einwilligung erforderlich (Opt-in). "
            "Ausnahme: Technisch notwendige Cookies (Session-Cookies, Warenkorb, Spracheinstellung). "
            "Cookie-Banner: Muss informierte, freiwillige Einwilligung ermöglichen. Kein Nudging, kein Dark Pattern. "
            "Ablehnungs-Button muss gleich prominent sein wie Zustimmungs-Button (EuGH C-673/17 Planet49). "
            "Cookie-Wall: Grundsätzlich unzulässig, wenn kein echtes Alternativangebot besteht. "
            "Stufe 2: DSGVO Art. 6 – Für die anschließende Verarbeitung der über Cookies erhobenen Daten braucht es "
            "eine eigenständige DSGVO-Rechtsgrundlage. "
            "Consent Management Platforms (CMP): Müssen DSGVO-konform sein. IAB TCF Framework ist umstritten "
            "(EuGH C-604/22 IAB Europe: TCF-String ist personenbezogenes Datum)."
        ),
    },
    {
        "thema": "DSK zu KI und Datenschutz – Orientierungshilfe und Hambacher Erklärung",
        "text": (
            "Die DSK hat mehrere Dokumente zu KI und Datenschutz veröffentlicht: "
            "1. Hambacher Erklärung zur KI (03.04.2019): Sieben Anforderungen an KI-Systeme – "
            "Transparenz, Erklärbarkeit, Nicht-Diskriminierung, technische Sicherheit, Datenminimierung, "
            "Verantwortlichkeit und menschliche Kontrolle. "
            "2. Orientierungshilfe KI und Datenschutz (06.05.2024): Umfassende Prüfschritte für den Einsatz von KI-Systemen. "
            "Rechtsgrundlage: In der Regel Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse) oder Art. 6 Abs. 1 lit. a (Einwilligung). "
            "DSFA: In der Regel erforderlich bei KI-Systemen die personenbezogene Daten verarbeiten (DSK-Blacklist + WP 248). "
            "Training mit personenbezogenen Daten: Bedarf eigener Rechtsgrundlage. "
            "Art. 22 DSGVO: Automatisierte Einzelentscheidungen – bei KI-gestützten Entscheidungen mit Rechtswirkung "
            "muss menschliche Überprüfung gewährleistet sein. "
            "EuGH C-634/21 SCHUFA: Auch vorgelagerte automatisierte Bewertungen fallen unter Art. 22 DSGVO. "
            "AI Act: Zusätzliche Anforderungen bei Hochrisiko-KI-Systemen (Art. 6, Annex III AI Act)."
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# Hauptprogramm
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 60)
    print("OpenLex MVP – Behörden-Dokumente verfeinern")
    print("=" * 60)

    # ── Alle Quelldokumente laden ──
    all_docs = []
    for src_dir, default_type in [(LEITLINIEN_DIR, "leitlinie"), (BEHOERDEN_DIR, "behoerde")]:
        for fpath in sorted(glob.glob(os.path.join(src_dir, "*.json"))):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    doc = json.load(f)
                doc["_source_type"] = default_type
                doc["_fpath"] = fpath
                all_docs.append(doc)
            except Exception:
                pass
    print(f"\n  {len(all_docs)} Dokumente geladen ({LEITLINIEN_DIR}, {BEHOERDEN_DIR}).")

    # ── SCHRITT 1+2+3: Segmentieren, Themen extrahieren, Chunks vorbereiten ──
    print("\n" + "=" * 60)
    print("SCHRITT 1-3 – Segmentierung + Themen + Chunks vorbereiten")
    print("=" * 60)

    all_items = []
    themen_stats: dict[str, int] = {}
    tagged_count = 0

    for doc in all_docs:
        text = doc.get("text", "")
        if not text or len(text.strip()) < 50:
            continue

        doc_titel = doc.get("titel", "") or os.path.basename(doc["_fpath"])
        doc_datum = doc.get("datum", "")
        doc_quelle = doc.get("quelle", "")
        doc_typ = doc.get("typ", "")
        source_type = doc["_source_type"]
        behoerde = doc.get("behoerde", "")

        sections = segment_document(text)

        for sec_idx, section in enumerate(sections):
            sec_title = section["title"]
            sec_text = section["text"]

            # Themen extrahieren
            themen = extract_themen(sec_text + " " + doc_titel + " " + sec_title)
            if themen:
                tagged_count += 1
            for t in themen:
                themen_stats[t] = themen_stats.get(t, 0) + 1

            # Normverweise
            verweise = find_verweise(sec_text)

            # Chunk-ID
            doc_id = sanitize(doc_titel[:40])
            chunk_id = f"beh_{doc_id}_{sec_idx}"

            # Embedding-Text mit Anreicherung
            themen_str = ", ".join(themen) if themen else ""
            embed_parts = [doc_titel]
            if sec_title and sec_title != "Einleitung":
                embed_parts.append(sec_title)
            if themen_str:
                embed_parts.append(f"Themen: {themen_str}")
            embed_parts.append(sec_text[:4000])
            embed_text = " – ".join(embed_parts)

            meta = {
                "source_type": source_type,
                "quelle": doc_quelle,
                "typ": doc_typ,
                "titel": doc_titel[:200],
                "datum": doc_datum,
                "abschnitt": sec_title[:200],
                "themen": themen_str,
                "normbezuege": ", ".join(verweise[:20]),
                "chunk_id": chunk_id,
            }
            if behoerde:
                meta["behoerde"] = behoerde

            all_items.append({
                "id": chunk_id,
                "embed_text": embed_text,
                "document": sec_text,
                "meta": meta,
            })

    print(f"  {len(all_items)} thematische Chunks erstellt.")
    print(f"  {tagged_count} davon mit Themen-Tags.")
    print(f"\n  Themen-Verteilung (Top 15):")
    for thema, count in sorted(themen_stats.items(), key=lambda x: -x[1])[:15]:
        print(f"    {thema:<30} {count:>5}")

    # ── SCHRITT 5: Methodenwissen-Chunks ──
    print("\n" + "=" * 60)
    print("SCHRITT 5 – Methodenwissen-Chunks für Behörden-Themen")
    print("=" * 60)

    mw_items = []
    for mw in BEHOERDEN_MW:
        mw["source_type"] = "methodenwissen"
        mw["normbezuege"] = find_verweise(mw["text"])

        # Speichern
        fname = sanitize(mw["thema"][:80]) + ".json"
        with open(os.path.join(MW_DIR, fname), "w", encoding="utf-8") as f:
            json.dump(mw, f, ensure_ascii=False, indent=2)

        mw_id = f"mw_{sanitize(mw['thema'][:60]).lower()}"
        mw_items.append({
            "id": mw_id,
            "embed_text": f"{mw['thema']} – {mw['text']}",
            "document": mw["text"],
            "meta": {"source_type": "methodenwissen", "thema": mw["thema"],
                     "normbezuege": ", ".join(mw["normbezuege"][:15])},
        })

    print(f"  {len(mw_items)} Methodenwissen-Chunks erstellt.")

    # ── SCHRITT 4: ChromaDB aktualisieren ──
    print("\n" + "=" * 60)
    print("SCHRITT 4 – ChromaDB aktualisieren")
    print("=" * 60)

    import chromadb
    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"},
    )
    before_total = collection.count()

    # Alte leitlinie/behoerde Chunks finden und löschen
    print(f"  ChromaDB vorher: {before_total} Chunks.")
    print("  Lösche alte leitlinie/behoerde Chunks ...")

    old_ids_to_delete = []
    stored = collection.get(include=["metadatas"])
    for cid, meta in zip(stored["ids"], stored["metadatas"]):
        st = meta.get("source_type", "")
        if st in ("leitlinie", "behoerde"):
            old_ids_to_delete.append(cid)

    if old_ids_to_delete:
        # ChromaDB delete in Batches (max 5000 pro Aufruf)
        for i in range(0, len(old_ids_to_delete), 5000):
            batch = old_ids_to_delete[i:i + 5000]
            collection.delete(ids=batch)
        print(f"  {len(old_ids_to_delete)} alte Chunks gelöscht.")

    after_delete = collection.count()

    # Neue Chunks einfügen
    all_new = all_items + mw_items
    # Deduplizierung gegen bestehende IDs
    existing_ids = set(collection.get(include=[])["ids"])
    new_items = [it for it in all_new if it["id"] not in existing_ids]

    print(f"  {len(new_items)} neue Chunks zu embedden ...")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)

    for bs in range(0, len(new_items), BATCH_SIZE):
        be = min(bs + BATCH_SIZE, len(new_items))
        batch = new_items[bs:be]
        embeddings = model.encode(
            [it["embed_text"] for it in batch], show_progress_bar=False
        ).tolist()
        collection.add(
            ids=[it["id"] for it in batch],
            embeddings=embeddings,
            documents=[it["document"] for it in batch],
            metadatas=[it["meta"] for it in batch],
        )
        if be % 500 < BATCH_SIZE or be == len(new_items):
            print(f"    {be}/{len(new_items)}")

    after_total = collection.count()

    # ── Zusammenfassung ──
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"  Behörden-Chunks vorher:     {len(old_ids_to_delete)}")
    print(f"  Behörden-Chunks nachher:    {len(all_items)}")
    print(f"  Thematisch getaggt:         {tagged_count}")
    print(f"  Methodenwissen-Chunks:      {len(mw_items)}")
    print(f"  ChromaDB vorher:            {before_total}")
    print(f"  ChromaDB nach Löschung:     {after_delete}")
    print(f"  ChromaDB nachher:           {after_total}")
    print("=" * 60)


if __name__ == "__main__":
    main()
