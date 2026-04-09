#!/usr/bin/env python3
"""
collect_urteile_komplett.py – Sammelt systematisch datenschutzrelevante
Urteile aus vier Quellen mit Deduplizierung über Aktenzeichen.

Quellen (in Prioritätsreihenfolge):
  1. NeuRIS-API (api.rechtsinformationsportal.de)
  2. EU SPARQL + Cellar API (EuGH/EuG)
  3. rechtsprechung-im-internet.de (BGH, BVerfG, BVerwG, …)
  4. OpenJur (openjur.de)
"""

from __future__ import annotations

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

SUCHBEGRIFFE = [
    "DSGVO",
    "Datenschutz-Grundverordnung",
    "BDSG",
    "Bundesdatenschutzgesetz",
]

RATE_LIMIT = 1.5  # Sekunden zwischen Requests (Standard)
RATE_LIMIT_OPENJUR = 2.0

# Verweis-Regex (erweitert für DSGVO-Referenzen)
VERWEIS_RE = re.compile(
    r"Art\.?\s*\d+\s+(?:Abs\.?\s*\d+\s+)?(?:(?:lit\.?\s*[a-z]\s+)?)"
    r"(?:UAbs\.?\s*\d+\s+)?(?:S\.?\s*\d+\s+)?DSGVO"
    r"|§§?\s*\d+[a-z]?(?:\s*(?:Abs\.|Absatz|S\.|Satz|Nr\.|Nummer)\s*\d+)*"
    r"\s+[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*"
    r"|Art\.?\s*\d+\s+[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*"
)

# ---------------------------------------------------------------------------
# Deduplizierung
# ---------------------------------------------------------------------------

gesehene_az: set[str] = set()


def normalize_az(az: str) -> str:
    """Normalisiert Aktenzeichen für Deduplizierungsvergleich."""
    if not az:
        return ""
    az = az.strip()
    az = az.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    az = az.replace("‑", "-").replace("–", "-")
    az = re.sub(r"\s+", " ", az)
    return az.lower()


def ist_neu(az: str) -> bool:
    """Prüft ob ein Aktenzeichen noch nicht gespeichert wurde."""
    norm = normalize_az(az)
    if not norm:
        return True  # Ohne AZ immer speichern
    if norm in gesehene_az:
        return False
    gesehene_az.add(norm)
    return True


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def find_verweise(text: str) -> list[str]:
    """Findet Normverweise im Text."""
    return list(set(VERWEIS_RE.findall(text)))


def sanitize_filename(name: str) -> str:
    """Entfernt Zeichen, die in Dateinamen problematisch sind."""
    return re.sub(r'[<>:"/\\|?*\s]', "_", name).strip("_")[:120]


def save_urteil(data: dict) -> None:
    """Speichert ein Urteil als JSON-Datei."""
    gericht = sanitize_filename(data.get("gericht", "Unbekannt")[:30])
    az = sanitize_filename(data.get("aktenzeichen", "ohne_az")[:60])
    fname = f"{gericht}_{az}.json"
    path = os.path.join(OUTPUT_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def strip_html(text: str) -> str:
    """Entfernt HTML-Tags aus Text."""
    if "<" in text and ">" in text:
        return BeautifulSoup(text, "lxml").get_text(separator="\n", strip=True)
    return text


# ---------------------------------------------------------------------------
# Statistik
# ---------------------------------------------------------------------------

stats: dict[str, dict] = {}


def init_stats(quelle: str) -> None:
    stats[quelle] = {"gefunden": 0, "neu": 0, "verweise": 0, "fehler": 0}


# ═══════════════════════════════════════════════════════════════════════════
# QUELLE 1 – NeuRIS-API
# ═══════════════════════════════════════════════════════════════════════════


def collect_neuris() -> list[dict]:
    """Versucht Urteile von der NeuRIS-API zu laden."""
    quelle = "neuris"
    init_stats(quelle)
    print("\n" + "=" * 60)
    print("QUELLE 1 – NeuRIS-API")
    print("=" * 60)

    urteile = []

    # Bekannte API-Endpunkte testen
    api_urls = [
        "https://api.rechtsinformationsportal.de/v1",
        "https://api.neuris.de/v1",
        "https://neuris.de/api",
    ]

    api_base = None
    for url in api_urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code in (200, 301, 302):
                api_base = url
                print(f"  API erreichbar: {url}")
                break
        except Exception:
            continue

    if not api_base:
        print("  WARNUNG: NeuRIS-API nicht erreichbar. Überspringe.")
        return urteile

    # Versuche Rechtsprechungs-Endpunkte
    search_endpoints = [
        f"{api_base}/cases",
        f"{api_base}/rechtsprechung",
        f"{api_base}/decisions",
        f"{api_base}/search",
    ]

    for endpoint in search_endpoints:
        for suchbegriff in SUCHBEGRIFFE:
            try:
                r = requests.get(
                    endpoint,
                    params={"q": suchbegriff, "search": suchbegriff,
                            "page_size": 100, "format": "json"},
                    headers={**HEADERS, "Accept": "application/json"},
                    timeout=15,
                )
                if r.status_code != 200:
                    continue

                data = r.json()
                results = data if isinstance(data, list) else data.get("results", [])

                for case in results:
                    az = (case.get("aktenzeichen") or case.get("file_number")
                          or case.get("ecli", ""))
                    if not ist_neu(az):
                        stats[quelle]["gefunden"] += 1
                        continue

                    volltext = strip_html(
                        case.get("content", "") or case.get("volltext", "") or ""
                    )
                    verweise = find_verweise(volltext)

                    eintrag = {
                        "quelle": quelle,
                        "gericht": case.get("court", {}).get("name", "")
                                   if isinstance(case.get("court"), dict)
                                   else str(case.get("court", "")),
                        "datum": case.get("date", "") or case.get("datum", ""),
                        "aktenzeichen": az,
                        "leitsatz": case.get("leitsatz", "") or "",
                        "volltext": volltext[:80000],
                        "normbezuege": verweise,
                    }
                    urteile.append(eintrag)
                    save_urteil(eintrag)
                    stats[quelle]["gefunden"] += 1
                    stats[quelle]["neu"] += 1
                    stats[quelle]["verweise"] += len(verweise)

                time.sleep(RATE_LIMIT)

            except Exception as e:
                stats[quelle]["fehler"] += 1
                continue

    print(f"  => {stats[quelle]['neu']} neue Urteile von NeuRIS.")
    return urteile


# ═══════════════════════════════════════════════════════════════════════════
# QUELLE 2 – EU SPARQL + Cellar API (EuGH/EuG)
# ═══════════════════════════════════════════════════════════════════════════


SPARQL_ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"
CELLAR_DSGVO = ("http://publications.europa.eu/resource/cellar/"
                "3e485e15-11bd-11e6-ba9a-01aa75ed71a1")

# CSS-Klassen für Volltext-Extraktion aus EUR-Lex HTML
EURLEX_TEXT_CLASSES = {
    "normal", "pnormal", "sum-title-1", "index",
    "coj-normal", "coj-pnormal", "coj-sum-title-1", "coj-index", "coj-count",
    "oj-normal",
}


def sparql_find_dsgvo_caselaw() -> list[dict]:
    """Findet via SPARQL alle EuGH/EuG-Entscheidungen, die die DSGVO zitieren."""
    query = f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>

SELECT DISTINCT ?celex ?date WHERE {{
  ?work cdm:work_cites_work <{CELLAR_DSGVO}> .
  ?work cdm:resource_legal_id_celex ?celex .
  OPTIONAL {{ ?work cdm:work_date_document ?date }}
  FILTER(
    STRSTARTS(STR(?celex), '6') &&
    (CONTAINS(?celex, 'CJ') || CONTAINS(?celex, 'TJ'))
  )
}}
ORDER BY DESC(?date)
"""
    try:
        r = requests.get(
            SPARQL_ENDPOINT,
            params={"query": query, "format": "application/json"},
            headers={"Accept": "application/json", **HEADERS},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("results", {}).get("bindings", [])
    except Exception as e:
        print(f"  FEHLER bei SPARQL-Abfrage: {e}")
        return []


def cellar_fetch_volltext(celex: str) -> str | None:
    """Lädt den deutschen Volltext über die EU Cellar API."""
    url = f"https://publications.europa.eu/resource/celex/{celex}.DEU"
    try:
        r = requests.get(
            url,
            headers={"Accept": "application/xhtml+xml, text/html", **HEADERS},
            timeout=60,
            allow_redirects=True,
        )
        if r.status_code != 200 or len(r.text) < 1000:
            return None

        soup = BeautifulSoup(r.text, "lxml")
        parts = []
        for p in soup.find_all("p"):
            cls = set(p.get("class", []))
            if cls & EURLEX_TEXT_CLASSES:
                txt = p.get_text(strip=True)
                if txt:
                    parts.append(txt)
        return "\n".join(parts) if parts else None
    except Exception:
        return None


def celex_to_rechtssache(celex: str) -> str:
    """Konvertiert CELEX-Nummer in Rechtssache-Format (z.B. 62018CJ0311 → C-311/18)."""
    m = re.match(r"6(\d{4})(CJ|TJ)(\d+)", celex)
    if not m:
        return celex
    year = m.group(1)[2:]  # letzte 2 Ziffern
    prefix = "C" if m.group(2) == "CJ" else "T"
    number = str(int(m.group(3)))  # führende Nullen entfernen
    return f"{prefix}-{number}/{year}"


def collect_eu_sparql() -> list[dict]:
    """Sammelt EuGH/EuG-Entscheidungen via SPARQL + Cellar."""
    quelle = "eugh_cellar"
    init_stats(quelle)
    print("\n" + "=" * 60)
    print("QUELLE 2 – EU SPARQL + Cellar API (EuGH/EuG)")
    print("=" * 60)

    urteile = []

    # Schritt 1: SPARQL-Abfrage
    print("  SPARQL-Abfrage: Suche Entscheidungen die DSGVO zitieren ...")
    bindings = sparql_find_dsgvo_caselaw()
    print(f"  => {len(bindings)} Entscheidungen gefunden.")

    if not bindings:
        print("  WARNUNG: Keine Ergebnisse. Überspringe.")
        return urteile

    # Schritt 2: Volltexte laden
    for i, row in enumerate(bindings, 1):
        celex = row.get("celex", {}).get("value", "")
        date = row.get("date", {}).get("value", "")
        if not celex:
            continue

        rechtssache = celex_to_rechtssache(celex)
        az = f"Rechtssache {rechtssache}"

        if not ist_neu(az):
            stats[quelle]["gefunden"] += 1
            continue

        print(f"  [{i}/{len(bindings)}] {rechtssache} ({celex}) ...", end=" ")

        volltext = cellar_fetch_volltext(celex)
        if not volltext:
            print("Kein DE-Text.")
            stats[quelle]["fehler"] += 1
            continue

        verweise = find_verweise(volltext)

        eintrag = {
            "quelle": quelle,
            "gericht": "EuGH" if "CJ" in celex else "EuG",
            "datum": date,
            "aktenzeichen": az,
            "rechtssache": rechtssache,
            "celex": celex,
            "leitsatz": "",
            "volltext": volltext,
            "normbezuege": verweise,
        }
        urteile.append(eintrag)
        save_urteil(eintrag)
        stats[quelle]["gefunden"] += 1
        stats[quelle]["neu"] += 1
        stats[quelle]["verweise"] += len(verweise)
        print(f"{len(volltext)} Zeichen, {len(verweise)} Verweise.")

        time.sleep(RATE_LIMIT)

    print(f"\n  => {stats[quelle]['neu']} neue EuGH/EuG-Urteile geladen.")
    return urteile


# ═══════════════════════════════════════════════════════════════════════════
# QUELLE 3 – rechtsprechung-im-internet.de
# ═══════════════════════════════════════════════════════════════════════════


BUND_BASE = "https://www.rechtsprechung-im-internet.de"
BUND_SEARCH = f"{BUND_BASE}/jportal/portal/page/bsjrsprod.psml/js_peid/Suchportlet1/media-type/html"
BUND_DOC = f"{BUND_BASE}/jportal/portal/page/bsjrsprod.psml"


def bund_search(session: requests.Session, query: str) -> list[dict]:
    """Durchsucht rechtsprechung-im-internet.de und gibt Ergebnisse zurück."""
    params = {
        "formhaschangedvalue": "yes",
        "eventSubmit_doSearch": "suchen",
        "action": "portlets.jw.MainAction",
        "deletemask": "no",
        "wt_form": "1",
        "form": "bsjrsFastSearch",
        "desc": "all",
        "query": query,
        "standardsuche": "suchen",
    }

    r = session.get(BUND_SEARCH, params=params, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    results = []
    seen_ids = set()
    for a in soup.find_all("a", href=re.compile(r"doc\.id=")):
        href = a.get("href", "")
        txt = a.get_text(strip=True)
        doc_id_m = re.search(r"doc\.id=([^&]+)", href)
        if not doc_id_m or not txt:
            continue
        doc_id = doc_id_m.group(1)
        if "Kurztext" in txt or "Langtext" in txt or doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)

        # Parse: "BGH 2. Zivilsenat| II ZB 2/25Beschluss|Leitsatz..."
        parts = txt.split("|", 2)
        gericht = parts[0].strip() if parts else ""
        az_raw = parts[1].strip() if len(parts) > 1 else ""
        leitsatz = parts[2].strip() if len(parts) > 2 else ""
        # Entferne Entscheidungstyp vom Ende des AZ
        az = re.sub(r"(Beschluss|Urteil|EuGH-Vorlage|Gerichtsbescheid|Vorlagebeschluss)$",
                     "", az_raw).strip()

        results.append({
            "doc_id": doc_id, "gericht": gericht,
            "aktenzeichen": az, "leitsatz": leitsatz,
        })

    return results


def bund_fetch_volltext(session: requests.Session, doc_id: str) -> tuple[str, str]:
    """Lädt den Volltext einer Entscheidung. Gibt (volltext, datum) zurück."""
    url = f"{BUND_DOC}?doc.id={doc_id}&doc.part=L&doc.price=0.0&showdoccase=1"
    r = session.get(url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # Volltext aus dem größten Textblock extrahieren
    best = ""
    for div in soup.find_all("div"):
        txt = div.get_text(separator="\n", strip=True)
        if len(txt) > len(best):
            best = txt

    # Datum extrahieren
    datum = ""
    datum_m = re.search(r"(\d{1,2}\.\s*\w+\s*\d{4})", best[:500])
    if datum_m:
        datum = datum_m.group(1)

    return best, datum


def collect_bund_rechtsprechung() -> list[dict]:
    """Sammelt Urteile von rechtsprechung-im-internet.de."""
    quelle = "bund_rechtsprechung"
    init_stats(quelle)
    print("\n" + "=" * 60)
    print("QUELLE 3 – rechtsprechung-im-internet.de")
    print("=" * 60)

    urteile = []
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    # Session initialisieren
    try:
        session.get(f"{BUND_BASE}/jportal/portal/page/bsjrsprod.psml", timeout=15)
    except Exception as e:
        print(f"  WARNUNG: Seite nicht erreichbar: {e}")
        return urteile

    alle_ergebnisse = []
    seen_doc_ids = set()

    for suchbegriff in SUCHBEGRIFFE:
        print(f"\n  Suche: '{suchbegriff}' ...")
        try:
            ergebnisse = bund_search(session, suchbegriff)
            neue = [e for e in ergebnisse if e["doc_id"] not in seen_doc_ids]
            for e in neue:
                seen_doc_ids.add(e["doc_id"])
            alle_ergebnisse.extend(neue)
            print(f"    {len(ergebnisse)} Treffer, {len(neue)} neue.")
            time.sleep(RATE_LIMIT)
        except Exception as e:
            print(f"    FEHLER: {e}")
            stats[quelle]["fehler"] += 1

    print(f"\n  Lade Volltexte für {len(alle_ergebnisse)} Entscheidungen ...")

    for i, erg in enumerate(alle_ergebnisse, 1):
        az = erg["aktenzeichen"]
        if not ist_neu(az):
            stats[quelle]["gefunden"] += 1
            continue

        print(f"  [{i}/{len(alle_ergebnisse)}] {erg['gericht']} {az} ...", end=" ")

        try:
            volltext, datum = bund_fetch_volltext(session, erg["doc_id"])
        except Exception as e:
            print(f"FEHLER: {e}")
            stats[quelle]["fehler"] += 1
            continue

        if not volltext or len(volltext) < 100:
            print("Kein Text.")
            continue

        verweise = find_verweise(volltext)

        eintrag = {
            "quelle": quelle,
            "gericht": erg["gericht"],
            "datum": datum or "",
            "aktenzeichen": az,
            "leitsatz": erg.get("leitsatz", ""),
            "volltext": volltext[:80000],
            "normbezuege": verweise,
        }
        urteile.append(eintrag)
        save_urteil(eintrag)
        stats[quelle]["gefunden"] += 1
        stats[quelle]["neu"] += 1
        stats[quelle]["verweise"] += len(verweise)
        print(f"{len(volltext)} Z, {len(verweise)} Verw.")

        time.sleep(RATE_LIMIT)

    print(f"\n  => {stats[quelle]['neu']} neue Bundesgerichts-Urteile geladen.")
    return urteile


# ═══════════════════════════════════════════════════════════════════════════
# QUELLE 4 – OpenJur (openjur.de)
# ═══════════════════════════════════════════════════════════════════════════


OPENJUR_SEARCH = "https://openjur.de/suche/"
OPENJUR_BASE = "https://openjur.de"


def openjur_search(session: requests.Session, query: str, max_pages: int = 5) -> list[dict]:
    """Durchsucht OpenJur und gibt Ergebnisliste zurück."""
    results = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        params = {"searchPhrase": query, "page": page}
        try:
            r = session.get(OPENJUR_SEARCH, params=params, timeout=20)
            if r.status_code != 200 or len(r.text) < 2000:
                break

            soup = BeautifulSoup(r.text, "lxml")

            # Prüfe auf CAPTCHA
            if "captcha" in r.text.lower() or "testImage" in r.text:
                print(f"    CAPTCHA auf Seite {page}. Stoppe.")
                break

            # Suche nach Ergebnis-Links: /u/{id}.html
            found = 0
            for a in soup.find_all("a", href=re.compile(r"/u/\d+\.html")):
                href = a.get("href", "")
                m = re.search(r"/u/(\d+)\.html", href)
                if not m:
                    continue
                oid = m.group(1)
                if oid in seen_ids:
                    continue
                seen_ids.add(oid)

                txt = a.get_text(strip=True)
                if not txt or len(txt) < 5:
                    continue

                results.append({"id": oid, "url": f"{OPENJUR_BASE}/u/{oid}.html",
                                "title": txt[:200]})
                found += 1

            if found == 0:
                break

            time.sleep(RATE_LIMIT_OPENJUR)

        except Exception as e:
            print(f"    FEHLER auf Seite {page}: {e}")
            break

    return results


def openjur_fetch(session: requests.Session, url: str) -> dict:
    """Lädt den Volltext eines OpenJur-Urteils."""
    r = session.get(url, timeout=20)
    r.raise_for_status()

    if "captcha" in r.text.lower() or "testImage" in r.text:
        return {}

    soup = BeautifulSoup(r.text, "lxml")

    # Metadaten
    gericht = ""
    datum = ""
    az = ""

    # OpenJur strukturiert Metadaten in <dl> oder Tabellen
    for dt in soup.find_all(["dt", "th", "strong"]):
        label = dt.get_text(strip=True).lower()
        dd = dt.find_next_sibling(["dd", "td"])
        if not dd:
            continue
        val = dd.get_text(strip=True)
        if "gericht" in label:
            gericht = val
        elif "datum" in label:
            datum = val
        elif "aktenzeichen" in label or "az" in label:
            az = val

    # Fallback: aus title oder h1
    if not az:
        h1 = soup.find("h1")
        if h1:
            az_m = re.search(r"(\d+\s*\w+\s*\d+/\d+)", h1.get_text())
            if az_m:
                az = az_m.group(1)

    # Volltext
    content = soup.find("div", class_="docBody") or soup.find("article")
    if not content:
        # Fallback: größter Textblock
        best = ""
        for div in soup.find_all("div"):
            txt = div.get_text(separator="\n", strip=True)
            if len(txt) > len(best):
                best = txt
        volltext = best
    else:
        volltext = content.get_text(separator="\n", strip=True)

    return {
        "gericht": gericht,
        "datum": datum,
        "aktenzeichen": az,
        "volltext": volltext,
    }


def collect_openjur() -> list[dict]:
    """Sammelt Urteile von OpenJur."""
    quelle = "openjur"
    init_stats(quelle)
    print("\n" + "=" * 60)
    print("QUELLE 4 – OpenJur (openjur.de)")
    print("=" * 60)

    urteile = []
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    alle_treffer = []
    seen_ids = set()

    for suchbegriff in ["DSGVO", "BDSG"]:
        print(f"\n  Suche: '{suchbegriff}' ...")
        try:
            treffer = openjur_search(session, suchbegriff)
            neue = [t for t in treffer if t["id"] not in seen_ids]
            for t in neue:
                seen_ids.add(t["id"])
            alle_treffer.extend(neue)
            print(f"    {len(treffer)} Treffer, {len(neue)} neue.")
        except Exception as e:
            print(f"    FEHLER: {e}")
            stats[quelle]["fehler"] += 1

    if not alle_treffer:
        print("  WARNUNG: Keine Treffer (möglicherweise CAPTCHA). Überspringe.")
        return urteile

    print(f"\n  Lade Volltexte für {len(alle_treffer)} Entscheidungen ...")

    for i, treffer in enumerate(alle_treffer, 1):
        print(f"  [{i}/{len(alle_treffer)}] {treffer['title'][:50]} ...", end=" ")

        try:
            data = openjur_fetch(session, treffer["url"])
        except Exception as e:
            print(f"FEHLER: {e}")
            stats[quelle]["fehler"] += 1
            continue

        if not data or not data.get("volltext") or len(data["volltext"]) < 100:
            print("Kein Text.")
            continue

        az = data.get("aktenzeichen", "")
        if not ist_neu(az):
            stats[quelle]["gefunden"] += 1
            print("Duplikat.")
            continue

        verweise = find_verweise(data["volltext"])

        eintrag = {
            "quelle": quelle,
            "gericht": data.get("gericht", ""),
            "datum": data.get("datum", ""),
            "aktenzeichen": az,
            "leitsatz": "",
            "volltext": data["volltext"][:80000],
            "normbezuege": verweise,
        }
        urteile.append(eintrag)
        save_urteil(eintrag)
        stats[quelle]["gefunden"] += 1
        stats[quelle]["neu"] += 1
        stats[quelle]["verweise"] += len(verweise)
        print(f"{len(data['volltext'])} Z, {len(verweise)} Verw.")

        time.sleep(RATE_LIMIT_OPENJUR)

    print(f"\n  => {stats[quelle]['neu']} neue OpenJur-Urteile geladen.")
    return urteile


# ═══════════════════════════════════════════════════════════════════════════
# Hauptprogramm
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 60)
    print("OpenLex MVP – Urteilssammler (komplett)")
    print("=" * 60)

    alle = []

    # Quelle 1
    alle.extend(collect_neuris())

    # Quelle 2
    alle.extend(collect_eu_sparql())

    # Quelle 3
    alle.extend(collect_bund_rechtsprechung())

    # Quelle 4
    alle.extend(collect_openjur())

    # ── Zusammenfassung ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"{'Quelle':<25} {'Gefunden':>10} {'Neu':>8} {'Verweise':>10} {'Fehler':>8}")
    print("-" * 63)
    total_neu = 0
    total_verw = 0
    for quelle, s in stats.items():
        print(f"{quelle:<25} {s['gefunden']:>10} {s['neu']:>8} "
              f"{s['verweise']:>10} {s['fehler']:>8}")
        total_neu += s["neu"]
        total_verw += s["verweise"]
    print("-" * 63)
    print(f"{'GESAMT':<25} {'':>10} {total_neu:>8} {total_verw:>10}")
    print(f"\n  Deduplizierte Aktenzeichen: {len(gesehene_az)}")
    print(f"  Ausgabeverzeichnis:         {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
