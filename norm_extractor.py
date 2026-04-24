"""
Normzitate aus LLM-Text extrahieren.

Unterstützte Formen:
- "Art. 6 DSGVO", "Artikel 6 DSGVO", "Art. 6 Abs. 1 lit. f DSGVO"
- "§ 26 BDSG", "Paragraph 26 BDSG", "§§ 26, 27 BDSG"
- "Art. 82 DSGVO (EuGH C-300/21)"
"""
import re
from dataclasses import dataclass
from typing import Optional


# Regex-Komponenten
_ART_PATTERN = r"(?:Art\.?|Artikel|art\.?)\s*(\d+[a-z]?)"  # Art. 6, Artikel 6, Art. 6a
_PARA_PATTERN = r"§+\s*(\d+[a-z]?)"  # § 26, §§ 26, § 26a
_GESETZ_PATTERN = (
    r"(DSGVO|DS-GVO|GDPR|BDSG|TDDDG|TTDSG|DDG|AEUV|GG|UWG|TMG|"
    r"Datenschutz-Grundverordnung|Bundesdatenschutzgesetz|"
    r"Telemediengesetz|Grundgesetz)"
)

# Kombinierte Regex
_NORM_REGEX = re.compile(
    rf"(?:{_ART_PATTERN}|{_PARA_PATTERN})"                # Art. X oder § X
    rf"(?:\s+(?:Abs\.?\s*\d+))?"                          # optional "Abs. 1"
    rf"(?:\s+(?:lit\.?\s*[a-z]))?"                        # optional "lit. f"
    rf"(?:\s+(?:Satz\s*\d+))?"                            # optional "Satz 2"
    rf"\s+{_GESETZ_PATTERN}",                             # Gesetz zwingend
    re.IGNORECASE,
)


@dataclass
class NormCitation:
    raw: str           # Originalstring im Text
    paragraph: str     # "6" oder "26a"
    gesetz: str        # "DSGVO", "BDSG", etc. (kanonisiert)
    position: int      # Zeichenposition im Text


def extract_norms(text: str) -> list:
    """Extrahiert alle Normzitate aus einem Text."""
    from norm_registry import canonicalize_gesetz

    citations = []
    for match in _NORM_REGEX.finditer(text):
        art_num = match.group(1)   # Art.-Gruppe
        para_num = match.group(2)  # §-Gruppe
        gesetz_raw = match.group(3)

        paragraph = art_num or para_num
        if not paragraph:
            continue

        gesetz = canonicalize_gesetz(gesetz_raw)
        if gesetz is None:
            continue  # Unbekanntes Gesetz → skip (kein False Positive auslösen)

        citations.append(NormCitation(
            raw=match.group(0),
            paragraph=paragraph,
            gesetz=gesetz,
            position=match.start(),
        ))

    # Dedup: gleiche (gesetz, paragraph)-Kombi nur einmal
    seen = set()
    unique = []
    for c in citations:
        key = (c.gesetz, c.paragraph)
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    return unique
