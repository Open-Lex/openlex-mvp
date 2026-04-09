#!/usr/bin/env python3
"""
collect_eu_urteile_komplett.py – Erschöpfende Sammlung aller datenschutz-
relevanten EuGH/EuG-Entscheidungen aus Cellar (SPARQL) + GDPRhub.

Quellen:
  1. SPARQL + Cellar API (DSGVO + Datenschutzrichtlinie 95/46/EG)
  2. GDPRhub MediaWiki API (CJEU-Kategorie mit DSGVO-Artikel-Tags)

Deduplizierung über normalisierte Aktenzeichen. GDPRhub-Metadaten
(DSGVO-Artikel-Tags) werden auch bei Cellar-Urteilen ergänzt.
"""

from __future__ import annotations

import glob
import json
import os
import re
import time
import warnings

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "urteile")
os.makedirs(OUTPUT_DIR, exist_ok=True)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0")
HEADERS = {"User-Agent": UA}

RATE_LIMIT = 2.0

# Cellar-IDs der Schlüsselgesetzgebungen
CELLAR_DSGVO = ("http://publications.europa.eu/resource/cellar/"
                "3e485e15-11bd-11e6-ba9a-01aa75ed71a1")
CELLAR_DSRL = ("http://publications.europa.eu/resource/cellar/"
               "41f89a28-fc83-4be5-b094-aa8cee23c70e")

# SPARQL
SPARQL_ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"

# GDPRhub
GDPRHUB_API = "https://gdprhub.eu/api.php"

# CSS-Klassen für EUR-Lex Volltext-Extraktion
EURLEX_TEXT_CLASSES = {
    "normal", "pnormal", "sum-title-1", "index",
    "coj-normal", "coj-pnormal", "coj-sum-title-1", "coj-index", "coj-count",
    "oj-normal",
}

# Granulare Normverweis-Regex
VERWEIS_RE = re.compile(
    # Art. X Abs. Y lit. z DSGVO / GDPR
    r"Art\.?\s*\d+\s*"
    r"(?:Abs\.?\s*\d+\s*)?"
    r"(?:(?:lit\.?\s*[a-z]|Buchst(?:abe)?\.?\s*[a-z]|Nr\.?\s*\d+)\s*)?"
    r"(?:(?:UAbs\.?\s*\d+|S(?:atz)?\.?\s*\d+)\s*)?"
    r"(?:DSGVO|GDPR|DS-GVO|EUV\s*2016/679|VO\s*2016/679)"
    # Art. X Abs. Y lit. z + anderes Gesetz
    r"|Art\.?\s*\d+\s*"
    r"(?:Abs\.?\s*\d+\s*)?"
    r"(?:(?:lit\.?\s*[a-z]|Nr\.?\s*\d+)\s*)?"
    r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*"
    # § X Abs. Y S. Z BDSG etc
    r"|§§?\s*\d+[a-z]?\s*"
    r"(?:Abs\.?\s*\d+\s*)?"
    r"(?:(?:S(?:atz)?\.?\s*\d+|Nr\.?\s*\d+)\s*)?"
    r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*",
    re.UNICODE,
)

# ---------------------------------------------------------------------------
# Datenstrukturen
# ---------------------------------------------------------------------------

# Zentrale Registry: aktenzeichen_norm → dict
urteile_registry: dict[str, dict] = {}


def normalize_az(az: str) -> str:
    """Normalisiert Aktenzeichen."""
    if not az:
        return ""
    az = az.strip()
    az = az.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    az = az.replace("‑", "-").replace("–", "-")
    az = re.sub(r"\s+", " ", az)
    return az.lower()


def extract_case_number(text: str) -> str:
    """Extrahiert Rechtssache-Nummer (z.B. C-311/18) aus Text."""
    m = re.search(r"(C|T)[-‑]\d+/\d+", text)
    return m.group(0).replace("‑", "-") if m else ""


def find_verweise(text: str) -> list[str]:
    """Findet granulare Normverweise."""
    return list(set(VERWEIS_RE.findall(text)))


def sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\s]+', "_", name).strip("_")[:120]


def save_urteil(data: dict) -> None:
    """Speichert Urteil als JSON."""
    gericht = sanitize(data.get("gericht", "EuGH")[:20])
    az = sanitize(data.get("aktenzeichen", "unbekannt")[:60])
    fname = f"{gericht}_{az}.json"
    path = os.path.join(OUTPUT_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def celex_to_rechtssache(celex: str) -> str:
    """62018CJ0311 → C-311/18"""
    m = re.match(r"6(\d{4})(CJ|TJ)(\d+)", celex)
    if not m:
        return ""
    year = m.group(1)[2:]
    prefix = "C" if m.group(2) == "CJ" else "T"
    number = str(int(m.group(3)))
    return f"{prefix}-{number}/{year}"


# Statistik
stats = {"cellar": {"gefunden": 0, "neu": 0, "fehler": 0},
         "gdprhub": {"gefunden": 0, "neu": 0, "tags": 0, "fehler": 0}}

# ═══════════════════════════════════════════════════════════════════════════
# QUELLE 1 – SPARQL + Cellar (DSGVO + Richtlinie 95/46/EG)
# ═══════════════════════════════════════════════════════════════════════════


def sparql_find_caselaw() -> list[dict]:
    """SPARQL-Query für alle Entscheidungen, die DSGVO oder RL 95/46/EG zitieren."""
    query = f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>

SELECT DISTINCT ?celex ?date WHERE {{
  {{
    ?work cdm:work_cites_work <{CELLAR_DSGVO}> .
  }} UNION {{
    ?work cdm:work_cites_work <{CELLAR_DSRL}> .
  }}
  ?work cdm:resource_legal_id_celex ?celex .
  OPTIONAL {{ ?work cdm:work_date_document ?date }}
  FILTER(
    STRSTARTS(STR(?celex), '6') &&
    (CONTAINS(?celex, 'CJ') || CONTAINS(?celex, 'TJ'))
  )
}}
ORDER BY DESC(?date)
"""
    # Versuche zunächst eurlex-Package
    try:
        import eurlex
        print("  Nutze eurlex-Package für SPARQL ...")
        result = eurlex.run_query(query)
        bindings = result.get("results", {}).get("bindings", [])
        if bindings:
            return bindings
        print("  eurlex lieferte keine Ergebnisse, fallback auf requests.")
    except Exception as e:
        print(f"  eurlex-Package nicht nutzbar ({e}), nutze requests.")

    # Fallback: direkte SPARQL-Abfrage
    r = requests.get(
        SPARQL_ENDPOINT,
        params={"query": query, "format": "application/json"},
        headers={"Accept": "application/json", **HEADERS},
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("results", {}).get("bindings", [])


def cellar_fetch_volltext(celex: str) -> str | None:
    """Lädt den deutschen Volltext via Cellar API."""
    # Erst über eurlex versuchen
    try:
        import eurlex
        html = eurlex.get_html_by_celex_id(celex)
        if html and len(html) > 1000:
            soup = BeautifulSoup(html, "lxml")
            parts = [p.get_text(strip=True) for p in soup.find_all("p")
                     if set(p.get("class", [])) & EURLEX_TEXT_CLASSES]
            if parts:
                return "\n".join(parts)
    except Exception:
        pass

    # Fallback: direkte Cellar-URL (.DEU für Deutsch)
    url = f"https://publications.europa.eu/resource/celex/{celex}.DEU"
    try:
        r = requests.get(
            url,
            headers={"Accept": "application/xhtml+xml, text/html", **HEADERS},
            timeout=60, allow_redirects=True,
        )
        if r.status_code != 200 or len(r.text) < 1000:
            return None
        soup = BeautifulSoup(r.text, "lxml")
        parts = []
        for p in soup.find_all("p"):
            if set(p.get("class", [])) & EURLEX_TEXT_CLASSES:
                txt = p.get_text(strip=True)
                if txt:
                    parts.append(txt)
        return "\n".join(parts) if parts else None
    except Exception:
        return None


def collect_cellar() -> None:
    """Sammelt EuGH/EuG-Urteile via SPARQL + Cellar."""
    print("\n" + "=" * 60)
    print("QUELLE 1 – SPARQL + Cellar (DSGVO + RL 95/46/EG)")
    print("=" * 60)

    print("\n  SPARQL-Abfrage ...")
    bindings = sparql_find_caselaw()
    print(f"  {len(bindings)} Entscheidungen gefunden.")

    for i, row in enumerate(bindings, 1):
        celex = row.get("celex", {}).get("value", "")
        date = row.get("date", {}).get("value", "")
        if not celex:
            continue

        rechtssache = celex_to_rechtssache(celex)
        if not rechtssache:
            continue
        az = f"Rechtssache {rechtssache}"
        az_norm = normalize_az(az)

        stats["cellar"]["gefunden"] += 1

        # Bereits in Registry?
        if az_norm in urteile_registry:
            continue

        print(f"  [{i}/{len(bindings)}] {rechtssache} ...", end=" ")

        volltext = cellar_fetch_volltext(celex)
        if not volltext:
            print("Kein DE-Text.")
            stats["cellar"]["fehler"] += 1
            continue

        verweise = find_verweise(volltext)
        gericht = "EuGH" if "CJ" in celex else "EuG"

        eintrag = {
            "quelle": "cellar_eurlex",
            "gericht": gericht,
            "datum": date,
            "aktenzeichen": az,
            "rechtssache": rechtssache,
            "celex": celex,
            "dsgvo_artikel": [],  # wird ggf. von GDPRhub ergänzt
            "zusammenfassung": "",
            "leitsatz": "",
            "volltext": volltext,
            "normbezuege": verweise,
        }
        urteile_registry[az_norm] = eintrag
        stats["cellar"]["neu"] += 1
        print(f"{len(volltext)} Z, {len(verweise)} Verw.")
        time.sleep(RATE_LIMIT)

    print(f"\n  => {stats['cellar']['neu']} neue Cellar-Urteile.")


# ═══════════════════════════════════════════════════════════════════════════
# QUELLE 2 – GDPRhub
# ═══════════════════════════════════════════════════════════════════════════


def gdprhub_get_all_cjeu_pages() -> list[dict]:
    """Holt alle CJEU-Seiten aus der GDPRhub-Kategorie."""
    pages = []
    cmcontinue = None

    while True:
        params = {
            "action": "query", "list": "categorymembers",
            "cmtitle": "Category:CJEU", "format": "json", "cmlimit": "500",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue

        r = requests.get(GDPRHUB_API, params=params,
                         headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()

        members = data.get("query", {}).get("categorymembers", [])
        pages.extend(members)

        cont = data.get("continue", {})
        if "cmcontinue" in cont:
            cmcontinue = cont["cmcontinue"]
        else:
            break

    return pages


def gdprhub_parse_decision(title: str) -> dict | None:
    """Parst eine GDPRhub-Entscheidungsseite via MediaWiki API."""
    r = requests.get(GDPRHUB_API, params={
        "action": "parse", "page": title,
        "format": "json", "prop": "wikitext|categories",
        "redirects": "1",
    }, headers=HEADERS, timeout=15)

    if r.status_code != 200:
        return None

    data = r.json()
    parse = data.get("parse", {})
    wt = parse.get("wikitext", {}).get("*", "")
    cats = [c["*"] for c in parse.get("categories", [])]

    # Redirect prüfen
    if wt.startswith("#REDIRECT"):
        return None  # Wird durch die tatsächliche Seite abgedeckt

    # Template-Felder extrahieren
    def field(name: str) -> str:
        m = re.search(rf"\|{name}\s*=\s*(.+?)(?=\n\||\n\}})", wt, re.DOTALL)
        return m.group(1).strip() if m else ""

    case_number_name = field("Case_Number_Name")
    ecli = field("ECLI")
    date_decided = field("Date_Decided")

    # Rechtssache extrahieren
    case_nr = extract_case_number(case_number_name) or extract_case_number(title)
    if not case_nr:
        return None

    # DSGVO-Artikel aus Template-Feldern
    dsgvo_artikel = []
    for idx in range(1, 30):
        art_field = field(f"GDPR_Article_{idx}")
        if art_field:
            dsgvo_artikel.append(art_field)
        else:
            break

    # Zusätzlich aus Kategorien
    for cat in cats:
        m = re.match(r"Article_(\d+(?:\(\d+\))?)_GDPR", cat)
        if m:
            art = f"Article {m.group(1)} GDPR"
            if art not in dsgvo_artikel:
                dsgvo_artikel.append(art)

    # Zusammenfassung aus Wikitext extrahieren (nach "== Facts ==" etc.)
    zusammenfassung = ""
    for section in ["Facts", "Holding", "Summary", "Dispute"]:
        m = re.search(rf"==\s*{section}\s*==\s*\n(.*?)(?=\n==|\Z)", wt, re.DOTALL)
        if m:
            text = m.group(1).strip()
            # Wiki-Markup entfernen
            text = re.sub(r"\[\[(?:[^\]]*\|)?([^\]]*)\]\]", r"\1", text)
            text = re.sub(r"'{2,3}", "", text)
            zusammenfassung += f"\n\n{section}:\n{text}"

    # Gericht bestimmen
    gericht = "EuGH" if case_nr.startswith("C-") else "EuG"

    return {
        "case_nr": case_nr,
        "gericht": gericht,
        "ecli": ecli,
        "datum": date_decided,
        "dsgvo_artikel": dsgvo_artikel,
        "zusammenfassung": zusammenfassung.strip(),
        "title": title,
    }


def collect_gdprhub() -> None:
    """Sammelt CJEU-Metadaten von GDPRhub und ergänzt die Registry."""
    print("\n" + "=" * 60)
    print("QUELLE 2 – GDPRhub (CJEU-Kategorie)")
    print("=" * 60)

    print("\n  Lade CJEU-Kategorie ...")
    pages = gdprhub_get_all_cjeu_pages()
    # Nur CJEU-Seiten, keine AG-Opinions
    cjeu_pages = [p for p in pages if p["title"].startswith("CJEU")]
    print(f"  {len(cjeu_pages)} CJEU-Seiten gefunden.")

    for i, page in enumerate(cjeu_pages, 1):
        title = page["title"]
        print(f"  [{i}/{len(cjeu_pages)}] {title[:55]} ...", end=" ")

        try:
            result = gdprhub_parse_decision(title)
        except Exception as e:
            print(f"FEHLER: {e}")
            stats["gdprhub"]["fehler"] += 1
            time.sleep(RATE_LIMIT)
            continue

        if not result:
            print("Redirect/leer.")
            time.sleep(RATE_LIMIT)
            continue

        case_nr = result["case_nr"]
        az = f"Rechtssache {case_nr}"
        az_norm = normalize_az(az)
        stats["gdprhub"]["gefunden"] += 1

        dsgvo_art = result["dsgvo_artikel"]
        zusammenfassung = result["zusammenfassung"]

        if az_norm in urteile_registry:
            # Bereits aus Cellar vorhanden → Metadaten ergänzen
            existing = urteile_registry[az_norm]
            if dsgvo_art:
                existing["dsgvo_artikel"] = dsgvo_art
                stats["gdprhub"]["tags"] += 1
            if zusammenfassung and not existing.get("zusammenfassung"):
                existing["zusammenfassung"] = zusammenfassung
            print(f"Ergänzt ({len(dsgvo_art)} Tags).")
        else:
            # Neues Urteil nur von GDPRhub – versuche Volltext von Cellar
            volltext = ""
            # Versuche CELEX zu konstruieren
            m = re.match(r"(C|T)-(\d+)/(\d+)", case_nr)
            if m:
                prefix = "CJ" if m.group(1) == "C" else "TJ"
                year = m.group(3)
                if len(year) == 2:
                    year = "20" + year if int(year) < 50 else "19" + year
                number = m.group(2).zfill(4)
                celex = f"6{year}{prefix}{number}"

                volltext_result = cellar_fetch_volltext(celex)
                if volltext_result:
                    volltext = volltext_result

            verweise = find_verweise(volltext) if volltext else []

            eintrag = {
                "quelle": "gdprhub" if not volltext else "cellar_eurlex",
                "gericht": result["gericht"],
                "datum": result["datum"],
                "aktenzeichen": az,
                "rechtssache": case_nr,
                "celex": celex if m else "",
                "ecli": result.get("ecli", ""),
                "dsgvo_artikel": dsgvo_art,
                "zusammenfassung": zusammenfassung,
                "leitsatz": "",
                "volltext": volltext,
                "normbezuege": verweise,
            }
            urteile_registry[az_norm] = eintrag
            stats["gdprhub"]["neu"] += 1
            if dsgvo_art:
                stats["gdprhub"]["tags"] += 1
            print(f"Neu ({len(volltext)} Z, {len(dsgvo_art)} Tags).")

        time.sleep(RATE_LIMIT)

    print(f"\n  => {stats['gdprhub']['neu']} neue Urteile, "
          f"{stats['gdprhub']['tags']} mit DSGVO-Tags angereichert.")


# ═══════════════════════════════════════════════════════════════════════════
# Deduplizierung gegen vorhandene data/urteile/
# ═══════════════════════════════════════════════════════════════════════════


def load_existing_urteile() -> None:
    """Lädt vorhandene Urteile aus data/urteile/ in die Registry."""
    count = 0
    for fpath in glob.glob(os.path.join(OUTPUT_DIR, "*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception:
            continue

        az = doc.get("aktenzeichen", "")
        az_norm = normalize_az(az)
        if not az_norm:
            continue

        # Nur EU-Urteile berücksichtigen
        quelle = doc.get("quelle", "")
        if quelle not in ("eugh_cellar", "cellar_eurlex", "gdprhub"):
            continue

        urteile_registry[az_norm] = doc
        count += 1

    print(f"  {count} vorhandene EU-Urteile in Registry geladen.")


# ═══════════════════════════════════════════════════════════════════════════
# Hauptprogramm
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 60)
    print("OpenLex MVP – EU-Urteilssammler (komplett)")
    print("=" * 60)

    # Vorhandene Urteile laden
    print("\n  Lade vorhandene Urteile ...")
    load_existing_urteile()

    # Quelle 1
    collect_cellar()

    # Quelle 2
    collect_gdprhub()

    # Alle Urteile speichern (inkl. angereicherte)
    print("\n  Speichere alle Urteile ...")
    saved = 0
    for az_norm, eintrag in urteile_registry.items():
        save_urteil(eintrag)
        saved += 1

    # Zusammenfassung
    eugh_count = sum(1 for e in urteile_registry.values() if e.get("gericht") == "EuGH")
    eug_count = sum(1 for e in urteile_registry.values() if e.get("gericht") == "EuG")
    with_tags = sum(1 for e in urteile_registry.values() if e.get("dsgvo_artikel"))
    total_verweise = sum(len(e.get("normbezuege", [])) for e in urteile_registry.values())

    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"  EuGH-Urteile:               {eugh_count}")
    print(f"  EuG-Urteile:                {eug_count}")
    print(f"  Gesamt EU-Urteile:          {eugh_count + eug_count}")
    print(f"  Davon mit DSGVO-Artikel-Tags (GDPRhub): {with_tags}")
    print(f"  Normbezüge gesamt:          {total_verweise}")
    print(f"")
    print(f"  Cellar: {stats['cellar']['gefunden']} gefunden, "
          f"{stats['cellar']['neu']} neu, "
          f"{stats['cellar']['fehler']} Fehler")
    print(f"  GDPRhub: {stats['gdprhub']['gefunden']} gefunden, "
          f"{stats['gdprhub']['neu']} neu, "
          f"{stats['gdprhub']['tags']} Tags ergänzt, "
          f"{stats['gdprhub']['fehler']} Fehler")
    print(f"\n  Ausgabeverzeichnis: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
