#!/usr/bin/env python3
"""
collect_behoerden.py – Sammelt datenschutzrechtliche Behörden-Dokumente
aus vier Quellen: EDPB, DSK, BfDI, Landesbehörden.

PDF-Text-Extraktion via pymupdf (fitz).
"""

from __future__ import annotations

import io
import json
import os
import re
import time
import warnings

import fitz  # pymupdf
import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
DIR_LEITLINIEN = os.path.join(BASE_DIR, "data", "leitlinien")
DIR_BEHOERDEN = os.path.join(BASE_DIR, "data", "behoerden")
os.makedirs(DIR_LEITLINIEN, exist_ok=True)
os.makedirs(DIR_BEHOERDEN, exist_ok=True)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0")
HEADERS = {"User-Agent": UA}

RATE_LIMIT = 2.0  # Sekunden

VERWEIS_RE = re.compile(
    r"Art\.?\s*\d+\s+(?:Abs\.?\s*\d+\s+)?(?:(?:lit\.?\s*[a-z]\s+)?)"
    r"(?:UAbs\.?\s*\d+\s+)?(?:S\.?\s*\d+\s+)?DSGVO"
    r"|§§?\s*\d+[a-z]?(?:\s*(?:Abs\.|Absatz|S\.|Satz|Nr\.|Nummer)\s*\d+)*"
    r"\s+[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*"
    r"|Art\.?\s*\d+\s+[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*"
)

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

stats: dict[str, dict] = {}


def init_stats(quelle: str) -> None:
    stats[quelle] = {"dokumente": 0, "verweise": 0, "fehler": 0}


def find_verweise(text: str) -> list[str]:
    return list(set(VERWEIS_RE.findall(text)))


def sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\s]+', "_", name).strip("_")[:120]


def save_json(data: dict, out_dir: str, filename: str) -> None:
    path = os.path.join(out_dir, sanitize(filename) + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def pdf_to_text(content: bytes) -> str:
    """Extrahiert Text aus PDF-Bytes via pymupdf."""
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        parts = []
        for page in doc:
            parts.append(page.get_text())
        doc.close()
        return "\n".join(parts).strip()
    except Exception:
        return ""


def download_pdf(url: str, session: requests.Session | None = None) -> bytes | None:
    """Lädt eine PDF-Datei herunter."""
    try:
        requester = session or requests
        r = requester.get(url, headers=HEADERS, timeout=60, allow_redirects=True)
        if r.status_code == 200 and len(r.content) > 500:
            ct = r.headers.get("Content-Type", "")
            if "pdf" in ct or r.content[:5] == b"%PDF-":
                return r.content
        return None
    except Exception:
        return None


def titel_aus_url(url: str) -> str:
    """Extrahiert einen lesbaren Titel aus einer PDF-URL."""
    name = url.rstrip("/").split("/")[-1]
    name = name.rsplit(".", 1)[0]  # .pdf entfernen
    name = re.sub(r"[_-]+", " ", name)
    return name.strip()


# ═══════════════════════════════════════════════════════════════════════════
# QUELLE 1 – EDPB/EDSA-Leitlinien
# ═══════════════════════════════════════════════════════════════════════════

# Vordefinierte Liste bekannter EDPB Guidelines (Seite ist WAF-geschützt)
EDPB_GUIDELINES: list[dict] = [
    {"titel": "Guidelines 01/2024 on processing of personal data based on Art. 6(1)(f) GDPR",
     "pdf": "https://www.edpb.europa.eu/system/files/2025-02/edpb_guidelines_202401_article-6-1-f_v2_en.pdf",
     "datum": "2025-02"},
    {"titel": "Guidelines 02/2024 on Article 48 GDPR",
     "pdf": "https://www.edpb.europa.eu/system/files/2025-06/edpb_guidelines_202402_article48_v2_en.pdf",
     "datum": "2025-06"},
    {"titel": "Guidelines 01/2022 on Data Subject Rights - Right of Access",
     "pdf": "https://www.edpb.europa.eu/system/files/2024-04/edpb_guidelines_202201_data_subject_rights_access_v2_en_0.pdf",
     "datum": "2024-04"},
    {"titel": "Guidelines 04/2022 on the Calculation of Administrative Fines",
     "pdf": "https://www.edpb.europa.eu/system/files/2023-06/edpb_guidelines_042022_calculationofadministrativefines_en.pdf",
     "datum": "2023-06"},
    {"titel": "Guidelines 05/2022 on the use of facial recognition in law enforcement",
     "pdf": "https://www.edpb.europa.eu/system/files/2023-05/edpb_guidelines_202205_facialrecognition_v2_en.pdf",
     "datum": "2023-05"},
    {"titel": "Guidelines 03/2022 on Deceptive Design Patterns (Dark Patterns)",
     "pdf": "https://www.edpb.europa.eu/system/files/2023-02/edpb_03-2022_guidelines_on_deceptive_design_patterns_in_social_media_platform_interfaces_v2_en_0.pdf",
     "datum": "2023-02"},
    {"titel": "Guidelines 01/2021 on Examples regarding Personal Data Breach Notification",
     "pdf": "https://www.edpb.europa.eu/system/files/2022-09/edpb_guidelines_012021_pdbnotification_adopted_en.pdf",
     "datum": "2022-09"},
    {"titel": "Guidelines 02/2021 on Virtual Voice Assistants",
     "pdf": "https://www.edpb.europa.eu/system/files/2023-07/edpb_guidelines_202102_on_vva_v2.0_adopted_en.pdf",
     "datum": "2023-07"},
    {"titel": "Guidelines 04/2021 on Codes of Conduct as a tool for transfers",
     "pdf": "https://www.edpb.europa.eu/system/files/2022-05/edpb_guidelines_042021_on_codes_of_conduct_as_a_tool_for_transfers_v2_en.pdf",
     "datum": "2022-05"},
    {"titel": "Guidelines 05/2021 on the Interplay between Art. 3 and Chapter V GDPR",
     "pdf": "https://www.edpb.europa.eu/system/files/2023-02/edpb_guidelines_05-2021_interplay_between_the_application_of_article3_and_the_provisions_on_international_transfers_v2_en_0.pdf",
     "datum": "2023-02"},
    {"titel": "Guidelines 06/2021 on electronic health data processing",
     "pdf": "https://www.edpb.europa.eu/system/files/2023-01/edpb_guidelines_202106_healthdataelectronicprocessing_v2_en.pdf",
     "datum": "2023-01"},
    {"titel": "Guidelines 07/2020 on Controller and Processor",
     "pdf": "https://www.edpb.europa.eu/system/files/2021-07/eppb_guidelines_202007_controllerprocessor_final_en.pdf",
     "datum": "2021-07"},
    {"titel": "Guidelines 08/2020 on Targeting of Social Media Users",
     "pdf": "https://www.edpb.europa.eu/system/files/2021-04/edpb_guidelines_082020_on_the_targeting_of_social_media_users_en.pdf",
     "datum": "2021-04"},
    {"titel": "Guidelines 01/2020 on Processing personal data in the context of Connected Vehicles",
     "pdf": "https://www.edpb.europa.eu/system/files/2021-03/edpb_guidelines_202001_connected_vehicles_v2.0_adopted_en.pdf",
     "datum": "2021-03"},
    {"titel": "Guidelines 04/2020 on the use of location data and contact tracing tools (COVID-19)",
     "pdf": "https://www.edpb.europa.eu/system/files/2021-11/edpb_guidelines_20200420_contact_tracing_covid_with_annex_en.pdf",
     "datum": "2020-04"},
    {"titel": "Guidelines 05/2020 on Consent under the ePrivacy Directive",
     "pdf": "https://www.edpb.europa.eu/system/files/2021-11/edpb_guidelines_202005_consent_en.pdf",
     "datum": "2020-05"},
    {"titel": "Guidelines 06/2020 on the interplay between the ePrivacy Directive and GDPR",
     "pdf": "https://www.edpb.europa.eu/system/files/2021-11/edpb_guidelines_202006_interplay_eprivacydirective_and_gdpr_en.pdf",
     "datum": "2020-11"},
    {"titel": "Guidelines 07/2020 on Art. 49 GDPR - Derogations for specific situations",
     "pdf": "https://www.edpb.europa.eu/system/files/2021-11/edpb_guidelines_202007_article49derogations_en.pdf",
     "datum": "2020-11"},
    {"titel": "Guidelines 2/2019 on Processing personal data under Art. 6(1)(b) GDPR",
     "pdf": "https://www.edpb.europa.eu/system/files/2019-10/edpb_guidelines_201902_article6-1b_v1.1_en.pdf",
     "datum": "2019-10"},
    {"titel": "Guidelines 3/2019 on Processing personal data through Video Devices",
     "pdf": "https://www.edpb.europa.eu/system/files/2020-01/edpb_guidelines_201903_video_devices_en_0.pdf",
     "datum": "2020-01"},
    {"titel": "Guidelines 4/2019 on Art. 25 – Data Protection by Design and by Default",
     "pdf": "https://www.edpb.europa.eu/system/files/2021-04/edpb_guidelines_201904_dataprotection_by_design_and_by_default_v2.0_en.pdf",
     "datum": "2020-10"},
    {"titel": "Guidelines 1/2019 on Codes of Conduct and Monitoring Bodies",
     "pdf": "https://www.edpb.europa.eu/system/files/2019-06/edpb_guidelines_201901_v2.0_codesofconduct_en.pdf",
     "datum": "2019-06"},
    {"titel": "Guidelines 2/2018 on Derogations of Art. 49 under Regulation 2016/679",
     "pdf": "https://www.edpb.europa.eu/system/files/2019-02/edpb_guidelines_2_2018_derogations_en.pdf",
     "datum": "2018-05"},
    {"titel": "Guidelines 1/2018 on Certification",
     "pdf": "https://www.edpb.europa.eu/system/files/2019-05/edpb_guidelines_201801_v3.0_certificationcriteria_annex2_en.pdf",
     "datum": "2019-05"},
    {"titel": "Guidelines on Data Protection Impact Assessment (DPIA)",
     "pdf": "https://www.edpb.europa.eu/system/files/2019-06/edpb-wp248rev01_enpdf.pdf",
     "datum": "2017-10"},
    {"titel": "Guidelines on Data Protection Officers",
     "pdf": "https://www.edpb.europa.eu/system/files/2019-06/edpb-wp243rev01_enpdf.pdf",
     "datum": "2017-04"},
    {"titel": "Guidelines on the Right to Data Portability",
     "pdf": "https://www.edpb.europa.eu/system/files/2019-06/edpb-wp242rev01_enpdf.pdf",
     "datum": "2017-04"},
    {"titel": "Guidelines on Consent under Regulation 2016/679",
     "pdf": "https://www.edpb.europa.eu/system/files/2019-12/edpb_guidelines_202005_consent_en.pdf",
     "datum": "2020-05"},
    {"titel": "Guidelines on Transparency under Regulation 2016/679",
     "pdf": "https://www.edpb.europa.eu/system/files/2019-06/edpb-wp260rev01_enpdf.pdf",
     "datum": "2018-04"},
    {"titel": "Guidelines on Personal data breach notification",
     "pdf": "https://www.edpb.europa.eu/system/files/2019-06/edpb-wp250rev01_enpdf.pdf",
     "datum": "2018-02"},
    {"titel": "Guidelines on the Lead Supervisory Authority",
     "pdf": "https://www.edpb.europa.eu/system/files/2019-06/edpb-wp244rev01_enpdf.pdf",
     "datum": "2017-04"},
]


def collect_edpb() -> list[dict]:
    """Sammelt EDPB-Leitlinien."""
    quelle = "edpb"
    init_stats(quelle)
    print("\n" + "=" * 60)
    print("QUELLE 1 – EDPB/EDSA-Leitlinien")
    print("=" * 60)

    dokumente = []
    session = requests.Session()
    session.headers.update(HEADERS)

    # Schritt 1: Versuche die RSS-Feed-PDFs zu ergänzen
    print("  Prüfe RSS-Feed auf neue Leitlinien ...")
    try:
        r = session.get("https://www.edpb.europa.eu/rss.xml", timeout=15)
        if r.status_code == 200:
            soup_rss = BeautifulSoup(r.text, "xml")
            for item in soup_rss.find_all("item"):
                title_el = item.find("title")
                desc = item.find("description")
                if not title_el or not desc or not desc.string:
                    continue
                title = title_el.string or ""
                if "guideline" not in title.lower() and "leitlinie" not in title.lower():
                    continue
                pdfs = re.findall(
                    r"(https://www\.edpb\.europa\.eu/system/files/[^\"\s]+\.pdf)",
                    desc.string,
                )
                for pdf_url in pdfs:
                    if not any(g["pdf"] == pdf_url for g in EDPB_GUIDELINES):
                        pub_date = item.find("pubDate")
                        EDPB_GUIDELINES.append({
                            "titel": title,
                            "pdf": pdf_url,
                            "datum": pub_date.string[:16] if pub_date else "",
                        })
            print(f"    {len(EDPB_GUIDELINES)} Leitlinien in Liste.")
    except Exception as e:
        print(f"    RSS-Feed nicht verfügbar: {e}")

    # Schritt 2: PDFs herunterladen und verarbeiten
    for i, gl in enumerate(EDPB_GUIDELINES, 1):
        titel = gl["titel"]
        pdf_url = gl["pdf"]
        datum = gl.get("datum", "")

        print(f"  [{i}/{len(EDPB_GUIDELINES)}] {titel[:60]} ...", end=" ")

        content = download_pdf(pdf_url, session)
        if not content:
            print("FEHLER (Download).")
            stats[quelle]["fehler"] += 1
            continue

        text = pdf_to_text(content)
        if not text:
            print("FEHLER (Text-Extraktion).")
            stats[quelle]["fehler"] += 1
            continue

        verweise = find_verweise(text)
        eintrag = {
            "quelle": quelle,
            "typ": "leitlinie",
            "titel": titel,
            "datum": datum,
            "text": text[:100000],
            "normbezuege": verweise,
        }
        dokumente.append(eintrag)
        save_json(eintrag, DIR_LEITLINIEN, f"EDPB_{sanitize(titel[:60])}")
        stats[quelle]["dokumente"] += 1
        stats[quelle]["verweise"] += len(verweise)
        print(f"{len(text)} Z, {len(verweise)} Verw.")
        time.sleep(RATE_LIMIT)

    print(f"\n  => {stats[quelle]['dokumente']} EDPB-Leitlinien geladen.")
    return dokumente


# ═══════════════════════════════════════════════════════════════════════════
# QUELLE 2 – DSK (Datenschutzkonferenz)
# ═══════════════════════════════════════════════════════════════════════════

DSK_BASE = "https://www.datenschutzkonferenz-online.de"
DSK_PAGES = {
    "kurzpapiere": ("kurzpapiere.html", "kurzpapier"),
    "orientierungshilfen": ("orientierungshilfen.html", "orientierungshilfe"),
    "entschliessungen": ("entschliessungen.html", "entschliessung"),
    "anwendungshinweise": ("anwendungshinweise.html", "anwendungshinweis"),
    "stellungnahmen": ("stellungnahmen.html", "stellungnahme"),
}


def collect_dsk() -> list[dict]:
    """Sammelt DSK-Dokumente (Kurzpapiere, OH, Entschließungen, etc.)."""
    quelle = "dsk"
    init_stats(quelle)
    print("\n" + "=" * 60)
    print("QUELLE 2 – DSK (Datenschutzkonferenz)")
    print("=" * 60)

    dokumente = []
    session = requests.Session()
    session.headers.update(HEADERS)
    seen_urls = set()

    for kategorie, (page, typ) in DSK_PAGES.items():
        url = f"{DSK_BASE}/{page}"
        print(f"\n  Kategorie: {kategorie} ({url})")

        try:
            r = session.get(url, timeout=15)
            if r.status_code != 200:
                print(f"    HTTP {r.status_code}. Überspringe.")
                continue

            soup = BeautifulSoup(r.text, "lxml")
            pdf_links = []
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if ".pdf" not in href.lower():
                    continue
                # Relative URLs auflösen
                if href.startswith("../"):
                    href = DSK_BASE + "/" + href.lstrip("./")
                elif href.startswith("/"):
                    href = DSK_BASE + href
                elif not href.startswith("http"):
                    href = DSK_BASE + "/" + href

                if href in seen_urls:
                    continue
                seen_urls.add(href)

                link_text = a.get_text(strip=True) or titel_aus_url(href)
                pdf_links.append((href, link_text))

            print(f"    {len(pdf_links)} PDFs gefunden.")

            for j, (pdf_url, link_text) in enumerate(pdf_links, 1):
                print(f"    [{j}/{len(pdf_links)}] {link_text[:50]} ...", end=" ")

                content = download_pdf(pdf_url, session)
                if not content:
                    print("FEHLER.")
                    stats[quelle]["fehler"] += 1
                    continue

                text = pdf_to_text(content)
                if not text or len(text) < 50:
                    print("Kein Text.")
                    stats[quelle]["fehler"] += 1
                    continue

                titel = link_text or titel_aus_url(pdf_url)
                verweise = find_verweise(text)

                eintrag = {
                    "quelle": quelle,
                    "typ": typ,
                    "titel": titel,
                    "datum": "",
                    "text": text[:100000],
                    "normbezuege": verweise,
                }
                dokumente.append(eintrag)
                save_json(eintrag, DIR_LEITLINIEN, f"DSK_{sanitize(titel[:60])}")
                stats[quelle]["dokumente"] += 1
                stats[quelle]["verweise"] += len(verweise)
                print(f"{len(text)} Z, {len(verweise)} Verw.")
                time.sleep(RATE_LIMIT)

        except Exception as e:
            print(f"    FEHLER: {e}")
            stats[quelle]["fehler"] += 1

    print(f"\n  => {stats[quelle]['dokumente']} DSK-Dokumente geladen.")
    return dokumente


# ═══════════════════════════════════════════════════════════════════════════
# QUELLE 3 – BfDI (Bundesbeauftragter für den Datenschutz)
# ═══════════════════════════════════════════════════════════════════════════

BFDI_BASE = "https://www.bfdi.bund.de"
BFDI_PAGES = [
    ("Tätigkeitsberichte",
     "/DE/Service/Publikationen/Taetigkeitsberichte/taetigkeitsberichte_node.html"),
    ("Broschüren & Flyer",
     "/DE/Service/Publikationen/Broschueren/broschueren_node.html"),
    ("Rundschreiben",
     "/DE/BfDI/Dokumente/Rundschreiben/rundschreiben_node.html"),
    ("Stellungnahmen",
     "/DE/BfDI/Dokumente/Stellungnahmen/stellungnahmen_node.html"),
]


def collect_bfdi() -> list[dict]:
    """Sammelt BfDI-Dokumente."""
    quelle = "bfdi"
    init_stats(quelle)
    print("\n" + "=" * 60)
    print("QUELLE 3 – BfDI")
    print("=" * 60)

    dokumente = []
    session = requests.Session()
    session.headers.update(HEADERS)
    seen_urls = set()

    for kategorie, path in BFDI_PAGES:
        url = BFDI_BASE + path
        print(f"\n  Kategorie: {kategorie}")

        try:
            r = session.get(url, timeout=15)
            if r.status_code != 200:
                print(f"    HTTP {r.status_code}. Überspringe.")
                continue

            soup = BeautifulSoup(r.text, "lxml")

            # Finde PDF-Links (SharedDocs pattern)
            pdf_links = []
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if ".pdf" not in href.lower():
                    continue
                if href.startswith("/"):
                    href = BFDI_BASE + href
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                # Titel aus Link-Text extrahieren
                link_text = a.get_text(strip=True)
                # BfDI-Links enthalten oft "Herunterladen" am Ende
                link_text = re.sub(r"Herunterladen.*$", "", link_text).strip()
                if not link_text:
                    link_text = titel_aus_url(href)

                pdf_links.append((href, link_text))

            print(f"    {len(pdf_links)} PDFs gefunden.")

            for j, (pdf_url, link_text) in enumerate(pdf_links, 1):
                print(f"    [{j}/{len(pdf_links)}] {link_text[:50]} ...", end=" ")

                content = download_pdf(pdf_url, session)
                if not content:
                    print("FEHLER.")
                    stats[quelle]["fehler"] += 1
                    continue

                text = pdf_to_text(content)
                if not text or len(text) < 50:
                    print("Kein Text.")
                    stats[quelle]["fehler"] += 1
                    continue

                verweise = find_verweise(text)
                eintrag = {
                    "quelle": quelle,
                    "typ": kategorie.lower(),
                    "titel": link_text,
                    "datum": "",
                    "text": text[:100000],
                    "normbezuege": verweise,
                }
                dokumente.append(eintrag)
                save_json(eintrag, DIR_BEHOERDEN, f"BfDI_{sanitize(link_text[:60])}")
                stats[quelle]["dokumente"] += 1
                stats[quelle]["verweise"] += len(verweise)
                print(f"{len(text)} Z, {len(verweise)} Verw.")
                time.sleep(RATE_LIMIT)

        except Exception as e:
            print(f"    FEHLER: {e}")
            stats[quelle]["fehler"] += 1

    print(f"\n  => {stats[quelle]['dokumente']} BfDI-Dokumente geladen.")
    return dokumente


# ═══════════════════════════════════════════════════════════════════════════
# QUELLE 4 – Landesbehörden (Top 5)
# ═══════════════════════════════════════════════════════════════════════════

LANDESBEHOERDEN = [
    {
        "name": "BayLDA",
        "urls": [
            "https://www.lda.bayern.de/de/themen.html",
            "https://www.lda.bayern.de/de/datenschutzreform2018.html",
        ],
        "base": "https://www.lda.bayern.de",
    },
    {
        "name": "HmbBfDI",
        "urls": [
            "https://datenschutz-hamburg.de/service-information/handreichungen",
            "https://datenschutz-hamburg.de/service-information/taetigkeitsberichte",
        ],
        "base": "https://datenschutz-hamburg.de",
    },
    {
        "name": "LfDI_BaWue",
        "urls": [
            "https://www.baden-wuerttemberg.datenschutz.de/orientierungshilfen-und-handlungsempfehlungen/",
            "https://www.baden-wuerttemberg.datenschutz.de/faq/",
        ],
        "base": "https://www.baden-wuerttemberg.datenschutz.de",
    },
    {
        "name": "BlnBDI",
        "urls": [
            "https://www.datenschutz-berlin.de/infothek/publikationen-der-dsk/",
            "https://www.datenschutz-berlin.de/infothek/",
        ],
        "base": "https://www.datenschutz-berlin.de",
    },
    {
        "name": "LDI_NRW",
        "urls": [
            "https://www.ldi.nrw.de/berichte",
            "https://www.ldi.nrw.de/datenschutz/datenschutzrecht",
        ],
        "base": "https://www.ldi.nrw.de",
    },
]


def collect_landesbehoerden() -> list[dict]:
    """Sammelt Dokumente von den fünf größten Landesbehörden."""
    quelle = "landesbehoerden"
    init_stats(quelle)
    print("\n" + "=" * 60)
    print("QUELLE 4 – Landesbehörden (Top 5)")
    print("=" * 60)

    dokumente = []
    session = requests.Session()
    session.headers.update(HEADERS)
    seen_urls = set()

    for behörde in LANDESBEHOERDEN:
        name = behörde["name"]
        base = behörde["base"]
        print(f"\n  --- {name} ---")

        for page_url in behörde["urls"]:
            try:
                r = session.get(page_url, timeout=15)
                if r.status_code != 200:
                    print(f"    {page_url}: HTTP {r.status_code}. Überspringe.")
                    continue

                soup = BeautifulSoup(r.text, "lxml")

                # Sammle alle PDF-Links
                pdf_links = []
                for a in soup.find_all("a", href=True):
                    href = a.get("href", "")
                    if ".pdf" not in href.lower():
                        continue
                    if href.startswith("/"):
                        href = base + href
                    elif href.startswith(".."):
                        href = base + "/" + href.lstrip("./")
                    elif not href.startswith("http"):
                        href = base + "/" + href

                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    link_text = a.get_text(strip=True) or titel_aus_url(href)
                    pdf_links.append((href, link_text))

                if not pdf_links:
                    print(f"    {page_url}: Keine PDFs gefunden.")
                    continue

                print(f"    {len(pdf_links)} PDFs auf {page_url.split('/')[-1]}")

                for j, (pdf_url, link_text) in enumerate(pdf_links, 1):
                    print(f"      [{j}/{len(pdf_links)}] {link_text[:45]} ...", end=" ")

                    content = download_pdf(pdf_url, session)
                    if not content:
                        print("FEHLER.")
                        stats[quelle]["fehler"] += 1
                        continue

                    text = pdf_to_text(content)
                    if not text or len(text) < 50:
                        print("Kein Text.")
                        stats[quelle]["fehler"] += 1
                        continue

                    verweise = find_verweise(text)
                    eintrag = {
                        "quelle": f"landesbehoerde_{name.lower()}",
                        "typ": "veröffentlichung",
                        "titel": link_text,
                        "datum": "",
                        "behoerde": name,
                        "text": text[:100000],
                        "normbezuege": verweise,
                    }
                    dokumente.append(eintrag)
                    save_json(eintrag, DIR_BEHOERDEN,
                              f"{name}_{sanitize(link_text[:50])}")
                    stats[quelle]["dokumente"] += 1
                    stats[quelle]["verweise"] += len(verweise)
                    print(f"{len(text)} Z, {len(verweise)} Verw.")
                    time.sleep(RATE_LIMIT)

            except Exception as e:
                print(f"    FEHLER bei {page_url}: {e}")
                stats[quelle]["fehler"] += 1

    print(f"\n  => {stats[quelle]['dokumente']} Landes-Dokumente geladen.")
    return dokumente


# ═══════════════════════════════════════════════════════════════════════════
# Hauptprogramm
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 60)
    print("OpenLex MVP – Behörden-Dokumentensammler")
    print("=" * 60)

    collect_edpb()
    collect_dsk()
    collect_bfdi()
    collect_landesbehoerden()

    # Zusammenfassung
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"{'Quelle':<25} {'Dokumente':>10} {'Verweise':>10} {'Fehler':>8}")
    print("-" * 55)
    total_dok = 0
    total_verw = 0
    for quelle, s in stats.items():
        print(f"{quelle:<25} {s['dokumente']:>10} {s['verweise']:>10} "
              f"{s['fehler']:>8}")
        total_dok += s["dokumente"]
        total_verw += s["verweise"]
    print("-" * 55)
    print(f"{'GESAMT':<25} {total_dok:>10} {total_verw:>10}")
    print(f"\n  Leitlinien-Verzeichnis:  {DIR_LEITLINIEN}")
    print(f"  Behörden-Verzeichnis:    {DIR_BEHOERDEN}")
    print("=" * 60)


if __name__ == "__main__":
    main()
