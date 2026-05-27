#!/usr/bin/env python3
"""
build_bgb_at.py — Ergänzt openlex_bgb_at mit vollständigem Inhalt:
  1. BGB §§ 1–240 (Allgemeiner Teil) als gesetz_granular-Chunks
  2. BGH-Urteile zu BGB AT-Themen aus index.db
  3. Methodenwissen (BGB Allgemeiner Teil, ~700 Wörter)
  4. Eval-Fragen (5 Stück)

Steckbriefe sind bereits vorhanden — werden nur ergänzt, nicht überschrieben.
"""

import sys, os, re, hashlib, zipfile, io, time, urllib.request, ssl, sqlite3, json
from xml.etree import ElementTree as ET
from datetime import datetime
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "/opt/openlex-mvp-v2/chromadb"
INDEX_DB    = "/opt/openlex-sources/index.db"
LOG_FILE    = "/tmp/build_bgb_at.log"
EVAL_DIR    = Path("/opt/openlex-sources/eval/questions")

# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ── XML helpers ───────────────────────────────────────────────────────────────

def strip_tags(text):
    text = re.sub(r'<[^>]+>', ' ', text or '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fetch_gii_xml(gii_kuerzel):
    """Lädt XML-Zip von gesetze-im-internet.de und gibt Liste (enbez, text) zurück."""
    url = f"https://www.gesetze-im-internet.de/{gii_kuerzel}/xml.zip"
    log(f"  Lade GII: {url}")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 OpenLex-Bot/1.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        data = r.read()
    norms = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for fname in zf.namelist():
            if not fname.endswith('.xml'):
                continue
            xml_bytes = zf.read(fname)
            try:
                root = ET.fromstring(xml_bytes)
            except ET.ParseError:
                continue
            for norm in root.findall('.//norm'):
                meta = norm.find('metadaten')
                textd = norm.find('textdaten/text')
                if meta is None or textd is None:
                    continue
                enbez_el = meta.find('enbez')
                if enbez_el is None or not (enbez_el.text or '').strip():
                    continue
                enbez = enbez_el.text.strip()
                raw_xml = ET.tostring(textd, encoding='unicode')
                text = strip_tags(raw_xml)
                if len(text) < 30:
                    continue
                norms.append((enbez, text))
    return norms

def para_num(enbez):
    m = re.search(r'(\d+)', enbez)
    return int(m.group(1)) if m else None

def normalize_para(enbez):
    enbez = enbez.strip()
    if enbez.startswith('§'):
        parts = enbez.split()
        return ' '.join(parts[:2]) if len(parts) > 1 else enbez
    if re.match(r'^Art', enbez, re.I):
        return re.sub(r'^Art\.?\s*', 'Art. ', enbez)
    return enbez

def chunk_id_gii(skill, gesetz_abk, enbez):
    key = f"{skill}_{gesetz_abk}_{enbez}"
    return f"gii_{hashlib.sha256(key.encode()).hexdigest()[:14]}"

# ── Embedding + ChromaDB helpers ──────────────────────────────────────────────

def embed_batch(model, texts, prompt_name="passage", batch_size=16):
    all_embs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        embs = model.encode(batch, prompt_name=prompt_name, batch_size=batch_size,
                            show_progress_bar=False, normalize_embeddings=True)
        all_embs.extend(embs.tolist())
    return all_embs

def add_if_new(col, ids, docs, metas, model):
    """Dedup check then add. Returns number of added chunks."""
    new_ids, new_docs, new_metas = [], [], []
    for cid, doc, meta in zip(ids, docs, metas):
        existing = col.get(ids=[cid])
        if existing["ids"]:
            continue
        new_ids.append(cid)
        new_docs.append(doc)
        new_metas.append(meta)
    if not new_ids:
        return 0
    embs = embed_batch(model, new_docs)
    for i in range(0, len(new_ids), 64):
        col.add(
            ids=new_ids[i:i+64],
            documents=new_docs[i:i+64],
            metadatas=new_metas[i:i+64],
            embeddings=embs[i:i+64]
        )
    return len(new_ids)

# ── Content ───────────────────────────────────────────────────────────────────

SKILL = "bgb_at"
COL_NAME = f"openlex_{SKILL}"

# BGB §§ 1–240 als gesetz_granular
GII_KUERZEL = "bgb"
SECTION_FILTER = (1, 240)

# BGH-Keywords für BGB Allgemeiner Teil
URTEIL_KEYWORDS = [
    "§ 119 BGB",        # Anfechtung wegen Irrtums
    "§ 123 BGB",        # Anfechtung wegen Täuschung/Drohung
    "§ 138 BGB",        # Sittenwidrigkeit
    "§ 157 BGB",        # Auslegung
    "§ 164 BGB",        # Stellvertretung
    "§ 181 BGB",        # Insichgeschäft
    "§ 195 BGB",        # Regelverjährung
    "§ 199 BGB",        # Verjährungsbeginn
    "§ 242 BGB",        # Treu und Glauben
    "§ 307 BGB",        # AGB-Kontrolle
    "Willenserklärung",
    "Anfechtung Irrtum",
    "Geschäftsfähigkeit",
    "Stellvertretung Vollmacht",
    "Verjährung Hemmung",
    "Treu und Glauben Verwirkung",
    "AGB Inhaltskontrolle",
    "sittenwidrig nichtig",
    "Rechtsgeschäft Auslegung",
]

METHODENWISSEN = """BGB Allgemeiner Teil — Methodenwissen

Der Allgemeine Teil des Bürgerlichen Gesetzbuchs (BGB, §§ 1–240) bildet das dogmatische Fundament des gesamten Privatrechts. Er enthält allgemeine Vorschriften über Personen, Rechtsgeschäfte, Fristen, Verjährung und die Ausübung bürgerlicher Rechte. Die zentralen Institute sind:

Willenserklärung und Rechtsgeschäft (§§ 104–185 BGB):
Eine Willenserklärung ist eine Äußerung, die auf die Herbeiführung einer Rechtsfolge gerichtet ist. Sie besteht aus einem inneren Tatbestand (Handlungs-, Erklärungswille, Geschäftswille) und einem äußeren Tatbestand (Erklärungsakt). Das Rechtsgeschäft ist der Oberbegriff; es besteht aus einer oder mehreren Willenserklärungen, an die das Recht die gewollten Rechtsfolgen knüpft. Einseitige Rechtsgeschäfte (Kündigung, Anfechtung) wirken ohne Zustimmung des Empfängers; mehrseitige (Vertrag) erfordern übereinstimmende Willenserklärungen (Angebot + Annahme, §§ 145 ff.).

Geschäftsfähigkeit (§§ 104–113 BGB):
Volle Geschäftsfähigkeit ab 18 Jahren. Beschränkte Geschäftsfähigkeit (7–18 Jahre): Rechtsgeschäfte schwebend unwirksam, § 108 BGB; lediglich rechtlich vorteilhafte Geschäfte bedürfen keiner Zustimmung (§ 107 BGB). Geschäftsunfähigkeit bei Bewusstlosigkeit oder geistiger Störung (§ 104 Nr. 2 BGB) — Rechtsgeschäft nichtig.

Anfechtung (§§ 119–124 BGB):
Anfechtbar wegen Irrtums über Inhalt oder Erklärungsirrtum (§ 119 Abs. 1 BGB), Eigenschaftsirrtum (§ 119 Abs. 2 BGB), arglistiger Täuschung (§ 123 BGB) oder widerrechtlicher Drohung (§ 123 BGB). Anfechtungserklärung gegenüber dem Anfechtungsgegner (§ 143 BGB). Frist: unverzüglich (§ 121 BGB) bei Irrtum; 1 Jahr bei Täuschung/Drohung (§ 124 BGB). Wirkung: ex-tunc-Nichtigkeit (§ 142 Abs. 1 BGB); Schadensersatz des negativen Interesses (§ 122 BGB) beim Irrtum.

Stellvertretung (§§ 164–181 BGB):
Vertreter handelt im Namen des Vertretenen (offene Stellvertretung, § 164 BGB). Voraussetzungen: eigene Willenserklärung, Handeln in fremdem Namen, Vertretungsmacht (Vollmacht, gesetzliche Vertretung). Vollmacht (§ 166 BGB): Außenvollmacht durch Kundgabe gegenüber Dritten (§ 167 Abs. 2 BGB). Anscheinsvollmacht und Duldungsvollmacht als Schutztatbestände zugunsten gutgläubiger Dritter. Insichgeschäft grds. unzulässig (§ 181 BGB).

Sittenwidrigkeit und Nichtigkeitsgründe (§ 138 BGB):
Rechtsgeschäfte, die gegen die guten Sitten verstoßen, sind nichtig (§ 138 Abs. 1 BGB). Wuchertatbestand (§ 138 Abs. 2 BGB): auffälliges Missverhältnis von Leistung und Gegenleistung bei Ausbeutung einer Schwächesituation. BGH: Bürgschaft durch wirtschaftlich überforderten nahen Angehörigen → § 138 Abs. 1 BGB.

Treu und Glauben (§ 242 BGB):
Generalnorm für Verhaltens- und Ausübungsschranken. Fallgruppen: venire contra factum proprium, Verwirkung (Zeitablauf + Umstandsmoment), unzulässige Rechtsausübung, Schutzpflichten. § 242 BGB ist subsidiär zu speziellen Normen.

AGB-Recht (§§ 305–310 BGB):
Allgemeine Geschäftsbedingungen werden einbezogen durch ausdrücklichen Hinweis und Möglichkeit zur Kenntnisnahme (§ 305 Abs. 2 BGB). Überraschende Klauseln nicht einbezogen (§ 305c BGB). Inhaltskontrolle: § 307 BGB (Unangemessene Benachteiligung), §§ 308, 309 BGB (Klauselverbote). Keine Inhaltskontrolle bei kontrollfreien Individualabreden.

Verjährung (§§ 195–218 BGB):
Regelverjährung 3 Jahre (§ 195 BGB), Beginn mit Ende des Entstehungsjahres und Kenntnis (§ 199 Abs. 1 BGB). Sonderverjährungsfristen: 10 Jahre für Grundstücksrechte (§ 196 BGB), 30 Jahre für Herausgabeansprüche und titulierte Forderungen (§ 197 BGB). Hemmung (§§ 203–211 BGB) durch Verhandlungen, Klageerhebung, Mahnbescheid. Neubeginn (§ 212 BGB) durch Anerkenntnis oder Vollstreckungshandlung.
""".strip()

EVAL_QUESTIONS = [
    {
        "id": 1,
        "skill": SKILL,
        "question": "K kauft auf einer Weinversteigerung versehentlich eine Kiste Wein, weil er seinem Bekannten zugewinkt hat. Der Auktionator deutete das Winken als Gebot. Liegt eine wirksame Willenserklärung vor, und kann K das Rechtsgeschäft anfechten? Welche Anfechtungsfrist gilt?",
        "expected_norms": ["§ 119 Abs. 1 BGB", "§ 121 BGB"],
        "expected_keywords": ["Erklärungsirrtum", "Willenserklärung", "Anfechtung", "unverzüglich"],
        "category": "Anfechtung / Erklärungsirrtum"
    },
    {
        "id": 2,
        "skill": SKILL,
        "question": "V lässt sich beim Kauf eines Grundstücks von seinem Sohn S vertreten. S kauft das Grundstück gleichzeitig selbst als Käufer und als Vertreter seines Vaters als Verkäufer. Ist der Kaufvertrag wirksam? Welche Norm ist einschlägig, und gibt es Ausnahmen?",
        "expected_norms": ["§ 181 BGB"],
        "expected_keywords": ["Insichgeschäft", "Stellvertretung", "Vollmacht", "Ausnahme"],
        "category": "Stellvertretung / Insichgeschäft"
    },
    {
        "id": 3,
        "skill": SKILL,
        "question": "Eine 80-jährige demente Frau unterschreibt einen Kreditvertrag über 50.000 Euro, bei dem die Zinsen weit über dem Marktdurchschnitt liegen. Ihre Kinder möchten den Vertrag rückgängig machen. Welche Nichtigkeitsgründe kommen in Betracht, und welche Normen greifen ein?",
        "expected_norms": ["§ 104 Nr. 2 BGB", "§ 138 BGB"],
        "expected_keywords": ["Geschäftsunfähigkeit", "Sittenwidrigkeit", "Wucher", "Nichtigkeit"],
        "category": "Geschäftsunfähigkeit / Sittenwidrigkeit"
    },
    {
        "id": 4,
        "skill": SKILL,
        "question": "Gläubiger G wartet 4 Jahre lang, ohne seinen fälligen Kaufpreisanspruch gegen S geltend zu machen. S beruft sich auf Verjährung. Ist der Anspruch verjährt? Welche Verjährungsfrist gilt, wann beginnt sie, und welche Wirkung hat die Verjährungseinrede?",
        "expected_norms": ["§ 195 BGB", "§ 199 BGB", "§ 214 BGB"],
        "expected_keywords": ["Regelverjährung", "Verjährungsbeginn", "Kenntnis", "Einrede"],
        "category": "Verjährung"
    },
    {
        "id": 5,
        "skill": SKILL,
        "question": "Ein Mobilfunkanbieter verwendet in seinen AGB eine Klausel, die Kunden verpflichtet, Preiserhöhungen von bis zu 10% jährlich ohne Kündigungsrecht hinzunehmen. Ist diese Klausel wirksam? Welche AGB-rechtlichen Normen sind anwendbar?",
        "expected_norms": ["§ 305 BGB", "§ 307 BGB", "§ 308 Nr. 4 BGB"],
        "expected_keywords": ["AGB", "Inhaltskontrolle", "unangemessene Benachteiligung", "Klauselverbot"],
        "category": "AGB-Recht"
    },
]

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log("=" * 60)
    log("build_bgb_at.py — START")
    log("=" * 60)

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    log("ChromaDB verbunden.")

    log("Lade Embedding-Modell (mixedbread-ai/deepset-mxbai-embed-de-large-v1)...")
    model = SentenceTransformer('mixedbread-ai/deepset-mxbai-embed-de-large-v1')
    log("Modell geladen.")

    # Get or create collection
    existing_cols = {c.name for c in client.list_collections()}
    if COL_NAME in existing_cols:
        log(f"Collection {COL_NAME} existiert bereits, verwende bestehende")
        col = client.get_collection(COL_NAME)
    else:
        col = client.create_collection(COL_NAME, metadata={"hnsw:space": "cosine"})
        log(f"Collection {COL_NAME} neu erstellt")

    count_before = col.count()
    log(f"Aktueller Count: {count_before}")
    total_added = 0

    # ── Step 1: BGB §§ 1–240 (gesetz_granular) ────────────────────────────────
    log(f"\n--- GII: BGB ({GII_KUERZEL}), §§ {SECTION_FILTER[0]}–{SECTION_FILTER[1]} ---")
    try:
        norms = fetch_gii_xml(GII_KUERZEL)
        log(f"  {len(norms)} Normen geladen")
    except Exception as e:
        log(f"  FEHLER beim GII-Download: {e}")
        norms = []

    lo, hi = SECTION_FILTER
    filtered = [(e, t) for e, t in norms
                if (para_num(e) is not None and lo <= para_num(e) <= hi)]
    log(f"  Nach Filter §§ {lo}–{hi}: {len(filtered)} Normen")

    ids, docs, metas = [], [], []
    for enbez, text in filtered:
        para = normalize_para(enbez)
        cid = chunk_id_gii(SKILL, "BGB", enbez)
        ids.append(cid)
        docs.append(text[:2000])
        metas.append({
            "source_type":  "gesetz_granular",
            "gesetz_abk":   "BGB",
            "paragraph":    para,
            "gesetz_stand": "2024",
            "skill":        SKILL,
            "ueberschrift": f"BGB {para}",
            "gesetz":       "BGB",
        })

    n = add_if_new(col, ids, docs, metas, model)
    log(f"  BGB §§ {lo}–{hi}: {n} neue Chunks importiert")
    total_added += n

    # ── Step 2: BGH-Urteile zu BGB AT ─────────────────────────────────────────
    log(f"\n--- BGH-Urteile für BGB AT ({len(URTEIL_KEYWORDS)} Keywords) ---")
    try:
        db = sqlite3.connect(INDEX_DB)
        cur = db.cursor()

        all_ids, all_docs, all_metas = [], [], []
        per_kw = max(1, 200 // len(URTEIL_KEYWORDS))
        seen = set()

        for kw in URTEIL_KEYWORDS:
            cur.execute(f"""
                SELECT id, text, gericht, aktenzeichen, datum, normen_top5
                FROM items
                WHERE item_type = 'urteil'
                  AND text LIKE ?
                  AND text_length BETWEEN 500 AND 8000
                  AND is_duplicate = 0
                ORDER BY RANDOM()
                LIMIT {per_kw}
            """, (f'%{kw}%',))
            rows = cur.fetchall()
            for item_id, text, gericht, aktenzeichen, datum, normen_top5 in rows:
                if item_id in seen:
                    continue
                seen.add(item_id)
                cid = f"urteil_{item_id}_0"
                all_ids.append(cid)
                all_docs.append((text or '')[:2000])
                all_metas.append({
                    "source_type":  "urteil",
                    "gericht":      gericht or "",
                    "aktenzeichen": aktenzeichen or "",
                    "datum":        datum or "",
                    "normen_top5":  normen_top5 or "",
                    "skill":        SKILL,
                })
        db.close()

        log(f"  {len(all_ids)} Urteile geladen")
        n = add_if_new(col, all_ids, all_docs, all_metas, model)
        log(f"  BGH-Urteile: {n} neue Chunks importiert")
        total_added += n

    except Exception as e:
        log(f"  FEHLER bei Urteilen: {e}")
        import traceback; traceback.print_exc()

    # ── Step 3: Methodenwissen ─────────────────────────────────────────────────
    log(f"\n--- Methodenwissen ---")
    mw_id = f"methodenwissen_{SKILL}_0"
    existing = col.get(ids=[mw_id])
    if existing["ids"]:
        log("  Methodenwissen bereits vorhanden, überspringe")
    else:
        embs = embed_batch(model, [METHODENWISSEN])
        col.add(
            ids=[mw_id],
            documents=[METHODENWISSEN],
            metadatas=[{"source_type": "methodenwissen", "skill": SKILL}],
            embeddings=embs
        )
        log(f"  Methodenwissen importiert ({len(METHODENWISSEN)} Zeichen)")
        total_added += 1

    # ── Step 4: Eval-Fragen ────────────────────────────────────────────────────
    log(f"\n--- Eval-Fragen ---")
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    out = EVAL_DIR / f"{SKILL}.json"
    out.write_text(json.dumps(EVAL_QUESTIONS, ensure_ascii=False, indent=2))
    log(f"  Eval-Fragen geschrieben: {out}")

    # ── Zusammenfassung ────────────────────────────────────────────────────────
    count_after = col.count()
    log(f"\n{'='*60}")
    log(f"FERTIG: {total_added} neue Chunks importiert")
    log(f"Collection {COL_NAME}: {count_before} → {count_after} Dokumente")
    log(f"{'='*60}")

if __name__ == "__main__":
    main()
