"""
Norm-Zitat-Validator. Prüft:
1. Syntaktische Gültigkeit (Extraktor)
2. Existenz in Norm-Registry
3. Grounding im retrieved Kontext

Output: pro Zitat ein NormCheck; plus Aggregat-Zahlen für die Antwort.
"""
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

from norm_extractor import extract_norms, NormCitation
from norm_registry import canonicalize_gesetz, check_norm_exists

logger = logging.getLogger(__name__)


@dataclass
class NormCheck:
    raw: str
    gesetz: str
    paragraph: str
    is_syntax_valid: bool
    exists: bool
    in_retrieved_context: bool
    status: str  # "ok" | "unknown_gesetz" | "unknown_norm" | "ungrounded" | "malformed"


@dataclass
class ValidationResult:
    total_citations: int
    ok_count: int
    unknown_norm_count: int
    ungrounded_count: int
    malformed_count: int
    checks: list = field(default_factory=list)
    summary: str = ""


def validate_answer(
    answer: str,
    retrieved_chunks: list,
    warn_on_ungrounded: bool = True,
) -> ValidationResult:
    """
    Validiert alle Normzitate in der Antwort.

    Args:
        answer: LLM-generierter Antworttext
        retrieved_chunks: Liste von Chunks (dict mit 'document' oder strings)
        warn_on_ungrounded: Ungrounded-Zitate als Fehler werten?

    Returns:
        ValidationResult mit Aggregat-Zahlen + Details.
    """
    # Normalize retrieved chunks to text
    chunk_texts = []
    for c in retrieved_chunks:
        if isinstance(c, dict):
            chunk_texts.append(c.get("document", ""))
        else:
            chunk_texts.append(str(c))
    combined_context = " ".join(chunk_texts).lower()

    citations = extract_norms(answer)
    checks = []

    for cit in citations:
        exists = check_norm_exists(cit.gesetz, cit.paragraph)

        # Grounding-Check: Erwähnt der retrieved Kontext dieselbe Norm?
        gesetz_lower = cit.gesetz.lower()
        in_context = False

        if chunk_texts:
            # Variante 1: "Art. X GESETZ" oder "§ X GESETZ" im Context
            pattern = re.compile(
                rf"(?:art\.?|artikel|§+)\s*{re.escape(cit.paragraph)}\b"
                rf"[^a-zA-Z]*[^.]*{re.escape(gesetz_lower)}",
                re.IGNORECASE,
            )
            if pattern.search(combined_context):
                in_context = True
            else:
                # Fallback: wenigstens Gesetz und Paragraph im selben Chunk?
                for chunk_text in chunk_texts:
                    chunk_lower = chunk_text.lower()
                    if gesetz_lower in chunk_lower and re.search(
                        rf"\b{re.escape(cit.paragraph)}\b", chunk_lower
                    ):
                        in_context = True
                        break
        else:
            # Keine Chunks mitgegeben → kein Grounding-Check möglich
            in_context = True  # Nicht als ungrounded flaggen ohne Context

        # Status bestimmen
        if not exists:
            status = "unknown_norm"
        elif not in_context:
            status = "ungrounded" if warn_on_ungrounded else "ok"
        else:
            status = "ok"

        checks.append(NormCheck(
            raw=cit.raw,
            gesetz=cit.gesetz,
            paragraph=cit.paragraph,
            is_syntax_valid=True,  # extrahiert = syntax OK
            exists=exists,
            in_retrieved_context=in_context,
            status=status,
        ))

    ok = sum(1 for c in checks if c.status == "ok")
    unknown = sum(1 for c in checks if c.status == "unknown_norm")
    ungrounded = sum(1 for c in checks if c.status == "ungrounded")
    malformed = sum(1 for c in checks if c.status == "malformed")

    # Summary
    parts = []
    if unknown:
        parts.append(f"{unknown} unbekannte Norm(en)")
    if ungrounded:
        parts.append(f"{ungrounded} nicht im Kontext belegbar")
    summary = "; ".join(parts) if parts else "alle Zitate OK"

    return ValidationResult(
        total_citations=len(checks),
        ok_count=ok,
        unknown_norm_count=unknown,
        ungrounded_count=ungrounded,
        malformed_count=malformed,
        checks=checks,
        summary=summary,
    )


def format_warning(result: ValidationResult) -> Optional[str]:
    """Generiert einen User-sichtbaren Warnhinweis oder None.
    Konservativ: nur unknown_norm → sichtbare Warnung; ungrounded nur im Log.
    """
    if result.unknown_norm_count == 0:
        return None

    bad = [c.raw for c in result.checks if c.status == "unknown_norm"]
    return f"⚠️ Unbekannte Normzitate: {', '.join(bad)}. Bitte manuell prüfen."
