#!/usr/bin/env python3
"""
collect_gesetze.py – Lädt deutsche Gesetze (XML) und die DSGVO (HTML),
parst Paragraphen/Artikel und speichert sie als JSON in data/gesetze/.
"""

import io
import json
import os
import re
import zipfile

import warnings

import requests
from lxml import etree
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "gesetze")
os.makedirs(OUTPUT_DIR, exist_ok=True)

GESETZE = {
    "BDSG":      "bdsg_2018",
    "TTDSG":     "ttdsg",
    "DDG":       "ddg",       # Digitale-Dienste-Gesetz (ehem. TMG)
    "TKG":       "tkg_2021",
    "SGB_10":    "sgb_10",
    "PAuswG":    "pauswg",
    "AO":        "ao_1977",
    "GeschGehG": "geschgehg",
    "BetrVG":    "betrvg",
    "KUG":       "kunsturhg",
}

XML_URL = "https://www.gesetze-im-internet.de/{slug}/xml.zip"

# EUR-Lex Cellar API – deutsche HTML-Version der DSGVO (Sprachcode 0004 = DE)
DSGVO_URL = (
    "https://publications.europa.eu/resource/cellar/"
    "3e485e15-11bd-11e6-ba9a-01aa75ed71a1.0004.03/DOC_1"
)

VERWEIS_RE = re.compile(
    r"(?:§§?\s*\d+[a-z]?(?:\s*(?:Abs\.|Absatz|S\.|Satz|Nr\.|Nummer)\s*\d+)*"
    r"\s+[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*)"
    r"|(?:Art\.?\s*\d+\s+[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*)"
)

HEADERS = {
    "User-Agent": "OpenLex-MVP/1.0 (rechtswissenschaftliche Forschung)"
}

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def node_full_text(node) -> str:
    """Extrahiert rekursiv den gesamten Text eines lxml-Elements."""
    return " ".join((node.itertext())).strip()


def sanitize_filename(name: str) -> str:
    """Entfernt Zeichen, die in Dateinamen problematisch sind."""
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def find_verweise(text: str) -> list[str]:
    """Findet Normverweise im Text."""
    return list(set(VERWEIS_RE.findall(text)))


def save_json(data: dict, filename: str) -> None:
    """Speichert ein Dict als JSON-Datei."""
    path = os.path.join(OUTPUT_DIR, sanitize_filename(filename))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 1. Deutsche Gesetze (XML von gesetze-im-internet.de)
# ---------------------------------------------------------------------------


def download_and_parse_gesetz(name: str, slug: str) -> list[dict]:
    """Lädt ein Gesetz als ZIP herunter, entpackt die XML und parst §§."""
    url = XML_URL.format(slug=slug)
    print(f"  Lade {name} von {url} ...")

    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    paragraphen = []

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xml_files = [n for n in zf.namelist() if n.endswith(".xml")]
        if not xml_files:
            print(f"    WARNUNG: Keine XML-Datei in {slug}/xml.zip gefunden.")
            return paragraphen

        for xml_name in xml_files:
            tree = etree.parse(io.BytesIO(zf.read(xml_name)))
            root = tree.getroot()

            for norm in root.iter("norm"):
                metadaten = norm.find("metadaten")
                if metadaten is None:
                    continue

                enbez_el = metadaten.find("enbez")
                if enbez_el is None or enbez_el.text is None:
                    continue

                enbez = enbez_el.text.strip()
                # Nur echte Paragraphen (§) oder Artikel
                if not (enbez.startswith("§") or enbez.startswith("Art")):
                    continue

                titel_el = metadaten.find("titel")
                titel = titel_el.text.strip() if titel_el is not None and titel_el.text else ""

                # Volltext extrahieren
                text_parts = []
                for content_el in norm.iter("Content"):
                    text_parts.append(node_full_text(content_el))
                if not text_parts:
                    # Fallback: gesamten textdaten-Block nehmen
                    textdaten = norm.find("textdaten")
                    if textdaten is not None:
                        text_parts.append(node_full_text(textdaten))

                volltext = "\n".join(text_parts).strip()
                if not volltext:
                    continue

                verweise = find_verweise(volltext)

                eintrag = {
                    "gesetz": name,
                    "paragraph": enbez,
                    "ueberschrift": titel,
                    "text": volltext,
                    "verweise": verweise,
                }
                paragraphen.append(eintrag)

                # JSON speichern
                fname = f"{name}_{enbez}.json"
                save_json(eintrag, fname)

    print(f"    -> {len(paragraphen)} Paragraphen/Artikel geparst, "
          f"{sum(len(p['verweise']) for p in paragraphen)} Verweise gefunden.")
    return paragraphen


# ---------------------------------------------------------------------------
# 2. DSGVO (HTML von EUR-Lex)
# ---------------------------------------------------------------------------


def download_and_parse_dsgvo() -> list[dict]:
    """Lädt die DSGVO von EUR-Lex und parst Artikel + Erwägungsgründe."""
    print("  Lade DSGVO von EUR-Lex (Cellar API) ...")

    dsgvo_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Accept": "text/html, application/xhtml+xml",
    }
    resp = requests.get(DSGVO_URL, headers=dsgvo_headers, timeout=60)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    eintraege = []

    # --- Erwägungsgründe (Recitals) ---
    recitals = soup.select('div.eli-subdivision[id^="rct_"]')
    for div in recitals:
        rid = div.get("id", "")
        nummer_match = re.search(r"rct_(\d+)", rid)
        if not nummer_match:
            continue
        nummer = int(nummer_match.group(1))

        # Text aus der rechten Tabellenzelle oder aus p.oj-normal
        texte = []
        tds = div.find_all("td")
        if len(tds) >= 2:
            for p in tds[-1].find_all("p"):
                texte.append(p.get_text(strip=True))
        else:
            for p in div.find_all("p", class_="oj-normal"):
                texte.append(p.get_text(strip=True))

        # Erste Zelle enthält oft nur "(N)" – rausfiltern
        volltext = " ".join(t for t in texte if t and not re.match(r"^\(\d+\)$", t))
        if not volltext:
            continue

        verweise = find_verweise(volltext)
        eintrag = {
            "gesetz": "DSGVO",
            "paragraph": f"Erwägungsgrund {nummer}",
            "ueberschrift": f"Erwägungsgrund ({nummer})",
            "text": volltext,
            "verweise": verweise,
        }
        eintraege.append(eintrag)
        save_json(eintrag, f"DSGVO_EG_{nummer}.json")

    print(f"    -> {len(eintraege)} Erwägungsgründe geparst.")

    # --- Artikel ---
    artikel_count = 0
    articles = soup.select('div.eli-subdivision[id^="art_"]')
    for div in articles:
        aid = div.get("id", "")
        nummer_match = re.search(r"art_(\d+)", aid)
        if not nummer_match:
            continue
        nummer = int(nummer_match.group(1))

        # Titel
        titel_div = div.select_one("div.eli-title")
        titel = ""
        if titel_div:
            titel_p = titel_div.find("p")
            if titel_p:
                titel = titel_p.get_text(strip=True)

        # Text: alle p.oj-normal innerhalb des Artikels (aber nicht aus Unter-Artikeln)
        texte = []
        for p in div.find_all("p", class_="oj-normal"):
            t = p.get_text(strip=True)
            if t:
                texte.append(t)

        volltext = "\n".join(texte).strip()
        if not volltext:
            continue

        verweise = find_verweise(volltext)
        eintrag = {
            "gesetz": "DSGVO",
            "paragraph": f"Art. {nummer}",
            "ueberschrift": titel,
            "text": volltext,
            "verweise": verweise,
        }
        eintraege.append(eintrag)
        artikel_count += 1
        save_json(eintrag, f"DSGVO_Art_{nummer}.json")

    print(f"    -> {artikel_count} Artikel geparst.")
    return eintraege


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------


def main():
    print("=" * 60)
    print("OpenLex MVP – Gesetzessammler")
    print("=" * 60)

    alle_eintraege = []
    gesetze_ok = 0
    gesetze_fehler = []

    # Deutsche Gesetze
    for name, slug in GESETZE.items():
        try:
            ergebnis = download_and_parse_gesetz(name, slug)
            if ergebnis:
                alle_eintraege.extend(ergebnis)
                gesetze_ok += 1
            else:
                gesetze_fehler.append(name)
        except Exception as e:
            print(f"    FEHLER bei {name}: {e}")
            gesetze_fehler.append(name)

    # DSGVO
    try:
        dsgvo = download_and_parse_dsgvo()
        alle_eintraege.extend(dsgvo)
        gesetze_ok += 1
    except Exception as e:
        print(f"    FEHLER bei DSGVO: {e}")
        gesetze_fehler.append("DSGVO")

    # Zusammenfassung
    total_verweise = sum(len(e["verweise"]) for e in alle_eintraege)

    print()
    print("=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"  Gesetze erfolgreich geladen:  {gesetze_ok}")
    if gesetze_fehler:
        print(f"  Gesetze mit Fehler:           {', '.join(gesetze_fehler)}")
    print(f"  Paragraphen/Artikel gesamt:   {len(alle_eintraege)}")
    print(f"  Normverweise gesamt:          {total_verweise}")
    print(f"  Ausgabeverzeichnis:           {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
