"""
Registry der bekannten Normen im Datenschutzrechts-Korpus.

Struktur: gesetz_name → set von gültigen Paragraphen/Artikeln (als Strings).
Vergleich erfolgt normalisiert (z.B. "Art. 6" == "art.6" == "Art 6").
"""
from dataclasses import dataclass
from typing import Optional


# === DSGVO: Art. 1-99 ===
DSGVO_ARTICLES = {str(i) for i in range(1, 100)}

# === BDSG (BDSG 2018, aktuell): §§ 1–85 ===
BDSG_SECTIONS = {str(i) for i in range(1, 86)}

# === TDDDG (seit Mai 2024, vormals TTDSG): §§ 1–34 ===
TDDDG_SECTIONS = {str(i) for i in range(1, 35)}

# === DDG (Digitale-Dienste-Gesetz, seit Mai 2024): §§ 1–28 ===
DDG_SECTIONS = {str(i) for i in range(1, 29)}

# === AEUV (für Verweise auf EU-Primärrecht): wichtige Artikel ===
AEUV_ARTICLES = {"16", "288", "267", "49", "56", "101", "102"}

# === GG (Grundgesetz): datenschutz-relevante Artikel ===
GG_ARTICLES = {"1", "2", "5", "10", "13", "14", "19", "20", "21"}

# === Zusätzliche Gesetze, die häufig zitiert werden ===
UWG_SECTIONS = {str(i) for i in range(1, 21)}  # Grob §§ 1-20
TMG_SECTIONS = {str(i) for i in range(1, 17)}  # Nur historisch relevant (bis Mai 2024)
GDPR_ARTICLES = DSGVO_ARTICLES  # englische Bezeichnung

# === Union-Mapping für Gesetze-Namensvarianten ===
GESETZ_ALIASES = {
    # Kanonische Form → Varianten
    "DSGVO": {"dsgvo", "ds-gvo", "ds-g-vo", "gdpr", "dsg-vo", "datenschutz-grundverordnung"},
    "BDSG": {"bdsg", "bdsg-neu", "bdsg 2018", "bundesdatenschutzgesetz"},
    "TDDDG": {"tdddg", "ttdsg", "ttdsg/tdddg", "telekommunikation-digitale-dienste-datenschutz-gesetz"},
    "DDG": {"ddg", "digitale-dienste-gesetz", "digitale dienste gesetz"},
    "AEUV": {"aeuv", "avü", "vertrag über die arbeitsweise der europäischen union"},
    "GG": {"gg", "grundgesetz"},
    "UWG": {"uwg", "gesetz gegen den unlauteren wettbewerb"},
    "TMG": {"tmg", "telemediengesetz"},
}


@dataclass
class NormCheck:
    """Ergebnis einer Normprüfung."""
    raw: str                    # Originalstring aus der Antwort
    gesetz: Optional[str]       # Kanonisierter Gesetzesname oder None
    paragraph: Optional[str]    # Paragraph/Artikel als String
    is_syntax_valid: bool       # Syntax erkannt?
    exists: bool                # Existiert laut Registry?
    in_retrieved_context: bool  # Im retrieved Kontext erwähnt?
    status: str                 # "ok" | "unknown_gesetz" | "unknown_norm" | "ungrounded" | "malformed"


def canonicalize_gesetz(name: str) -> Optional[str]:
    """Normalisiert Gesetzesnamen. Gibt kanonische Form zurück oder None."""
    name_lower = name.lower().strip().replace(" ", "").replace("-", "")
    for canonical, aliases in GESETZ_ALIASES.items():
        if name_lower in {a.lower().replace(" ", "").replace("-", "") for a in aliases}:
            return canonical
        if name_lower == canonical.lower():
            return canonical
    return None


def check_norm_exists(gesetz: str, paragraph: str) -> bool:
    """Prüft Existenz in Registry."""
    registry_map = {
        "DSGVO": DSGVO_ARTICLES,
        "GDPR": DSGVO_ARTICLES,
        "BDSG": BDSG_SECTIONS,
        "TDDDG": TDDDG_SECTIONS,
        "DDG": DDG_SECTIONS,
        "AEUV": AEUV_ARTICLES,
        "GG": GG_ARTICLES,
        "UWG": UWG_SECTIONS,
        "TMG": TMG_SECTIONS,
    }
    valid = registry_map.get(gesetz.upper())
    if valid is None:
        return False
    return paragraph in valid
