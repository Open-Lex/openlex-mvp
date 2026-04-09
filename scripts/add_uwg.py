#!/usr/bin/env python3
"""
add_uwg.py – Lädt das UWG herunter, parst es, erzeugt granulare Chunks,
erstellt einen Methodenwissen-Chunk, und embeddet alles in ChromaDB.
"""

from __future__ import annotations

import glob
import hashlib
import io
import json
import os
import re
import zipfile

import requests
from lxml import etree

# ---------------------------------------------------------------------------
# Pfade
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
GESETZE_DIR = os.path.join(BASE_DIR, "data", "gesetze")
GRANULAR_DIR = os.path.join(BASE_DIR, "data", "gesetze_granular")
MW_DIR = os.path.join(BASE_DIR, "data", "methodenwissen")
CHROMADB_DIR = os.path.join(BASE_DIR, "chromadb")
COLLECTION_NAME = "openlex_datenschutz"
MODEL_NAME = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"

os.makedirs(GRANULAR_DIR, exist_ok=True)
os.makedirs(MW_DIR, exist_ok=True)

HEADERS = {"User-Agent": "OpenLex-MVP/1.0"}

VERWEIS_RE = re.compile(
    r"Art\.?\s*\d+\s*(?:Abs\.?\s*\d+\s*)?(?:(?:lit\.?\s*[a-z]|Nr\.?\s*\d+)\s*)?"
    r"(?:DSGVO|DS-GVO|GDPR|GRCh|AEUV|BDSG|TTDSG|TKG|SGB|AO|BetrVG|KUG|UWG|GG)"
    r"|§§?\s*\d+[a-z]?\s*(?:Abs\.?\s*\d+\s*)?(?:(?:S(?:atz)?\.?\s*\d+|Nr\.?\s*\d+)\s*)?"
    r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*",
    re.UNICODE,
)

_ABK = {"abs", "art", "nr", "lit", "buchst", "bzw", "gem", "vgl", "usw",
        "etc", "sog", "ggf", "bsp", "rn", "kap", "bgh", "bsg", "bfh",
        "bag", "dr", "prof"}
_SATZ_KANDID = re.compile(r"(\S+)\.\s+([A-ZÄÖÜ(])", re.UNICODE)


def find_verweise(text): return list(set(VERWEIS_RE.findall(text)))
def sanitize(n): return re.sub(r'[<>:"/\\|?*\s]+', "_", n).strip("_")[:150]


def split_saetze(text):
    text = text.strip()
    if not text: return []
    positions = []
    for m in _SATZ_KANDID.finditer(text):
        if m.group(1).lower().rstrip(".") not in _ABK:
            positions.append(m.start() + len(m.group(1)) + 1)
    if not positions: return [text]
    saetze, prev = [], 0
    for pos in positions:
        s = text[prev:pos].strip()
        if s: saetze.append(s)
        prev = pos + 1
    rest = text[prev:].strip()
    if rest: saetze.append(rest)
    return saetze or [text]


def parse_buchstaben(text):
    for pattern, typ in [(r"(?:^|\n)\s*([a-z])\)\s*\n?", "lit"),
                          (r"(?:^|\n)\s*(\d+)\.\s+", "nr")]:
        splits = re.split(pattern, text)
        if len(splits) >= 3:
            items = []
            for i in range(1, len(splits) - 1, 2):
                k = splits[i]
                t = splits[i + 1].strip() if i + 1 < len(splits) else ""
                if not t: continue
                kennung = f"lit. {k}" if typ == "lit" else f"Nr. {k}"
                items.append({"kennung": kennung, "text": t, "saetze": split_saetze(t)})
            if items: return items
    return []


def parse_absaetze(text):
    splits = re.split(r"(?:^|\n)\s*\((\d+)\)\s+", text)
    if len(splits) < 3:
        sub = parse_buchstaben(text)
        return [{"nummer": 1, "text": text.strip(),
                 "nummern_oder_buchstaben": sub,
                 "saetze": split_saetze(text) if not sub else []}]
    absaetze = []
    for i in range(1, len(splits) - 1, 2):
        nr = int(splits[i])
        t = splits[i + 1].strip()
        if not t: continue
        sub = parse_buchstaben(t)
        absaetze.append({"nummer": nr, "text": t,
                         "nummern_oder_buchstaben": sub,
                         "saetze": split_saetze(t) if not sub else []})
    return absaetze


def make_volladresse(gesetz, para, abs_nr=None, kennung=None, satz_nr=None):
    parts = [para]
    if abs_nr is not None: parts.append(f"Abs. {abs_nr}")
    if kennung is not None: parts.append(kennung)
    if satz_nr is not None: parts.append(f"S. {satz_nr}")
    parts.append(gesetz)
    return " ".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 1 – UWG herunterladen und parsen
# ═══════════════════════════════════════════════════════════════════════════


def download_uwg():
    print("=" * 60)
    print("SCHRITT 1 – UWG herunterladen")
    print("=" * 60)

    url = "https://www.gesetze-im-internet.de/uwg_2004/xml.zip"
    print(f"  Lade {url} ...")
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()

    paragraphen = []
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        for xml_name in [n for n in zf.namelist() if n.endswith(".xml")]:
            tree = etree.parse(io.BytesIO(zf.read(xml_name)))
            for norm in tree.getroot().iter("norm"):
                meta = norm.find("metadaten")
                if meta is None: continue
                enbez_el = meta.find("enbez")
                if enbez_el is None or not enbez_el.text: continue
                enbez = enbez_el.text.strip()
                if not (enbez.startswith("§") or enbez.startswith("Art")): continue

                titel_el = meta.find("titel")
                titel = titel_el.text.strip() if titel_el is not None and titel_el.text else ""

                text_parts = []
                for c in norm.iter("Content"):
                    text_parts.append(" ".join(c.itertext()).strip())
                if not text_parts:
                    td = norm.find("textdaten")
                    if td is not None:
                        text_parts.append(" ".join(td.itertext()).strip())

                volltext = "\n".join(text_parts).strip()
                if not volltext: continue

                verweise = find_verweise(volltext)
                eintrag = {
                    "gesetz": "UWG", "paragraph": enbez,
                    "ueberschrift": titel, "text": volltext, "verweise": verweise,
                }
                paragraphen.append(eintrag)

                fname = sanitize(f"UWG_{enbez}") + ".json"
                with open(os.path.join(GESETZE_DIR, fname), "w", encoding="utf-8") as f:
                    json.dump(eintrag, f, ensure_ascii=False, indent=2)

    print(f"  {len(paragraphen)} UWG-Paragraphen gespeichert.")
    return paragraphen


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 2 – Granulares Parsing + Chunks
# ═══════════════════════════════════════════════════════════════════════════


def refine_and_chunk_uwg():
    print("\n" + "=" * 60)
    print("SCHRITT 2 – Granulares Parsing + Chunks")
    print("=" * 60)

    uwg_files = sorted(glob.glob(os.path.join(GESETZE_DIR, "UWG_*.json")))
    print(f"  {len(uwg_files)} UWG-Dateien gefunden.")

    granular_count = 0
    for fpath in uwg_files:
        with open(fpath, "r", encoding="utf-8") as f:
            doc = json.load(f)

        text = doc.get("text", "")
        absaetze = parse_absaetze(text)

        # Erweiterte Struktur speichern
        refined = {
            "gesetz": doc["gesetz"], "paragraph": doc["paragraph"],
            "ueberschrift": doc.get("ueberschrift", ""), "volltext": text,
            "absaetze": absaetze, "verweise": doc.get("verweise", []),
        }
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(refined, f, ensure_ascii=False, indent=2)

        # Granulare Chunks
        for absatz in absaetze:
            abs_nr = absatz["nummer"]
            if absatz.get("nummern_oder_buchstaben"):
                for sub in absatz["nummern_oder_buchstaben"]:
                    addr = make_volladresse("UWG", doc["paragraph"], abs_nr, sub["kennung"])
                    cid = sanitize(f"UWG_{doc['paragraph']}_Abs.{abs_nr}_{sub['kennung']}")
                    chunk = {"chunk_id": cid, "gesetz": "UWG", "volladresse": addr,
                             "text": sub["text"], "kontext_paragraph": text[:5000],
                             "verweise": find_verweise(sub["text"])}
                    with open(os.path.join(GRANULAR_DIR, cid + ".json"), "w", encoding="utf-8") as f:
                        json.dump(chunk, f, ensure_ascii=False, indent=2)
                    granular_count += 1

                    if len(sub.get("saetze", [])) > 1:
                        for si, satz in enumerate(sub["saetze"], 1):
                            sa = make_volladresse("UWG", doc["paragraph"], abs_nr, sub["kennung"], si)
                            sid = sanitize(f"UWG_{doc['paragraph']}_Abs.{abs_nr}_{sub['kennung']}_S.{si}")
                            sc = {"chunk_id": sid, "gesetz": "UWG", "volladresse": sa,
                                  "text": satz, "kontext_paragraph": text[:5000],
                                  "verweise": find_verweise(satz)}
                            with open(os.path.join(GRANULAR_DIR, sid + ".json"), "w", encoding="utf-8") as f:
                                json.dump(sc, f, ensure_ascii=False, indent=2)
                            granular_count += 1
            else:
                addr = make_volladresse("UWG", doc["paragraph"], abs_nr)
                cid = sanitize(f"UWG_{doc['paragraph']}_Abs.{abs_nr}")
                chunk = {"chunk_id": cid, "gesetz": "UWG", "volladresse": addr,
                         "text": absatz["text"], "kontext_paragraph": text[:5000],
                         "verweise": find_verweise(absatz["text"])}
                with open(os.path.join(GRANULAR_DIR, cid + ".json"), "w", encoding="utf-8") as f:
                    json.dump(chunk, f, ensure_ascii=False, indent=2)
                granular_count += 1

                if len(absatz.get("saetze", [])) > 1:
                    for si, satz in enumerate(absatz["saetze"], 1):
                        sa = make_volladresse("UWG", doc["paragraph"], abs_nr, satz_nr=si)
                        sid = sanitize(f"UWG_{doc['paragraph']}_Abs.{abs_nr}_S.{si}")
                        sc = {"chunk_id": sid, "gesetz": "UWG", "volladresse": sa,
                              "text": satz, "kontext_paragraph": text[:5000],
                              "verweise": find_verweise(satz)}
                        with open(os.path.join(GRANULAR_DIR, sid + ".json"), "w", encoding="utf-8") as f:
                            json.dump(sc, f, ensure_ascii=False, indent=2)
                        granular_count += 1

    print(f"  {granular_count} granulare UWG-Chunks erstellt.")
    return granular_count


# ═══════════════════════════════════════════════════════════════════════════
# SCHRITT 3+4 – Methodenwissen-Chunk + Embedding
# ═══════════════════════════════════════════════════════════════════════════

MW_CHUNK = {
    "source_type": "methodenwissen",
    "thema": "Verhältnis DSGVO – TTDSG – § 7 UWG bei Werbung und Direktmarketing",
    "text": (
        "Bei Direktmarketing und Werbung greifen drei Regelungsebenen ineinander, "
        "die jeweils eigenständig geprüft werden müssen:\n\n"
        "1. § 7 UWG – Zulässigkeit der Kontaktaufnahme: § 7 Abs. 1 UWG verbietet "
        "geschäftliche Handlungen, durch die ein Marktteilnehmer in unzumutbarer Weise belästigt wird. "
        "§ 7 Abs. 2 Nr. 3 UWG: Werbung per E-Mail, Fax, SMS oder automatisierter Anruf ist grundsätzlich "
        "nur mit vorheriger ausdrücklicher Einwilligung des Empfängers zulässig. "
        "Bestandskundenausnahme (§ 7 Abs. 3 UWG): E-Mail-Werbung an Bestandskunden ist ohne Einwilligung zulässig, "
        "wenn: (a) die E-Mail-Adresse im Zusammenhang mit einem Kauf erlangt wurde, (b) für eigene ähnliche Waren/Dienstleistungen "
        "geworben wird, (c) der Kunde nicht widersprochen hat, (d) bei jeder Verwendung auf das Widerspruchsrecht hingewiesen wird. "
        "§ 7 Abs. 2 Nr. 1 UWG: Telefonwerbung gegenüber Verbrauchern nur mit vorheriger ausdrücklicher Einwilligung, "
        "gegenüber Gewerbetreibenden reicht mutmaßliche Einwilligung.\n\n"
        "2. TTDSG § 25 – Endgerätezugriff: Regelt den Zugriff auf das Endgerät des Nutzers (Cookies, Tracking-Pixel, "
        "Fingerprinting). Lex specialis zur DSGVO für den Zugriff selbst. "
        "Grundsatz: Einwilligung erforderlich (Opt-in). Ausnahme: Technisch notwendige Zugriffe. "
        "EuGH C-673/17 Planet49: Vorausgefüllte Checkbox genügt nicht.\n\n"
        "3. DSGVO Art. 6 – Rechtsgrundlage für die Datenverarbeitung: Für die Verarbeitung der beim "
        "Marketing erhobenen personenbezogenen Daten braucht es eine Rechtsgrundlage nach Art. 6 Abs. 1 DSGVO. "
        "Typischerweise Art. 6 Abs. 1 lit. a (Einwilligung) oder lit. f (berechtigtes Interesse). "
        "EG 47 DSGVO: Direktwerbung kann ein berechtigtes Interesse sein. "
        "Art. 21 Abs. 2 DSGVO: Jederzeitiges Widerspruchsrecht gegen Direktwerbung – kein Interessenabwägung nötig.\n\n"
        "Dreistufige Prüfung bei Direktmarketing:\n"
        "Stufe 1 – § 7 UWG: Ist die Kontaktaufnahme wettbewerbsrechtlich zulässig?\n"
        "Stufe 2 – TTDSG § 25: Ist der Zugriff auf das Endgerät (Cookies etc.) erlaubt?\n"
        "Stufe 3 – DSGVO Art. 6: Ist die Verarbeitung der personenbezogenen Daten rechtmäßig?\n\n"
        "Alle drei Stufen müssen kumulativ erfüllt sein. Eine UWG-Einwilligung deckt nicht automatisch "
        "die DSGVO-Einwilligung ab und umgekehrt – die Anforderungen unterscheiden sich."
    ),
}


def create_and_embed():
    print("\n" + "=" * 60)
    print("SCHRITT 3+4 – Methodenwissen + Embedding")
    print("=" * 60)

    # Methodenwissen-Chunk speichern
    MW_CHUNK["normbezuege"] = find_verweise(MW_CHUNK["text"])
    mw_path = os.path.join(MW_DIR, "Verhaeltnis_DSGVO_TTDSG_UWG_Werbung.json")
    with open(mw_path, "w", encoding="utf-8") as f:
        json.dump(MW_CHUNK, f, ensure_ascii=False, indent=2)
    print("  Methodenwissen-Chunk erstellt.")

    # Alle neuen UWG-Chunks + MW-Chunk sammeln
    items = []

    # UWG granulare Chunks
    for fpath in glob.glob(os.path.join(GRANULAR_DIR, "UWG_*.json")):
        with open(fpath, "r", encoding="utf-8") as f:
            doc = json.load(f)
        cid = doc.get("chunk_id", "")
        addr = doc.get("volladresse", "")
        text = doc.get("text", "")
        if not cid or not text: continue
        items.append({
            "id": f"gran_{cid}",
            "embed_text": f"{addr} – {text}" if addr else text,
            "document": text,
            "meta": {"source_type": "gesetz_granular", "gesetz": "UWG",
                     "volladresse": addr, "chunk_id": cid,
                     "verweise": ", ".join(doc.get("verweise", [])[:20])},
        })

    # Methodenwissen
    mw_id = "mw_verhaeltnis_dsgvo_ttdsg_uwg_werbung"
    items.append({
        "id": mw_id,
        "embed_text": f"{MW_CHUNK['thema']} – {MW_CHUNK['text']}",
        "document": MW_CHUNK["text"],
        "meta": {"source_type": "methodenwissen", "thema": MW_CHUNK["thema"],
                 "normbezuege": ", ".join(MW_CHUNK["normbezuege"][:20])},
    })

    print(f"  {len(items)} Chunks vorbereitet.")

    # ChromaDB öffnen und vorhandene IDs laden
    import chromadb
    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"},
    )
    before = collection.count()

    existing = set()
    if before > 0:
        stored = collection.get(include=[])
        existing = set(stored["ids"])

    new_items = [it for it in items if it["id"] not in existing]
    print(f"  {len(new_items)} neue Chunks (von {len(items)}, {before} vorher in DB).")

    if not new_items:
        print("  Alle Chunks bereits vorhanden.")
        return 0, before

    # Embedding
    print(f"  Lade Embedding-Modell ...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)

    BATCH = 100
    for bs in range(0, len(new_items), BATCH):
        be = min(bs + BATCH, len(new_items))
        batch = new_items[bs:be]
        embeddings = model.encode([it["embed_text"] for it in batch],
                                   show_progress_bar=False).tolist()
        collection.add(
            ids=[it["id"] for it in batch],
            embeddings=embeddings,
            documents=[it["document"] for it in batch],
            metadatas=[it["meta"] for it in batch],
        )
        print(f"    {be}/{len(new_items)}")

    after = collection.count()
    print(f"\n  ChromaDB vorher: {before}, nachher: {after}, +{after - before}")
    return len(new_items), after


# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("OpenLex MVP – UWG hinzufügen")
    print("=" * 60)

    paragraphen = download_uwg()
    granular_count = refine_and_chunk_uwg()
    new_embedded, total_db = create_and_embed()

    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"  UWG-Paragraphen:         {len(paragraphen)}")
    print(f"  Granulare UWG-Chunks:    {granular_count}")
    print(f"  Methodenwissen-Chunk:    1")
    print(f"  Neu in ChromaDB:         {new_embedded}")
    print(f"  ChromaDB gesamt:         {total_db}")
    print("=" * 60)


if __name__ == "__main__":
    main()
