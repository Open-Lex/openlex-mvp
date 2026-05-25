"""Regelbasierte Heuristiken: Sprachstil-Erkennung und AG-ID-Synthese."""
from __future__ import annotations

import re
from typing import Literal, Optional

PARAGRAPH_RE = re.compile(r"§\s?\d+|Art\.\s?\d+", re.IGNORECASE)

PROFI_PHRASES = (
    "als anwalt", "als jurist", "als rechtsanwält", "anspruchsgrundlage",
    "subsumtion", "tatbestand", "rechtsfolge", "i.v.m", "ivm", "analog",
    "mandant", "anspruchsteller", "anspruchsgegner", "aktivlegitim",
)
LAIE_PHRASES = (
    "ich verstehe nicht", "keine ahnung", "weiß nicht", "weiss nicht",
    "kenne mich nicht aus", "was kann ich tun", "bin verzweifelt", "hilfe",
)
# grobe Fachbegriff-Marker für die Dichte-Heuristik
FACHWORT_RE = re.compile(
    r"\b\w*(recht|anspruch|vertrag|klage|frist|verjährung|haftung|"
    r"schadensersatz|kündigung|widerruf)\w*\b|\b(BGB|StGB|StVG|DSGVO|HGB|VwGO|SGB)\b",
    re.IGNORECASE,
)


def detect_sprachstil(text: str) -> Literal["laie", "profi", "unklar"]:
    t = (text or "").lower()
    if PARAGRAPH_RE.search(text or "") or any(p in t for p in PROFI_PHRASES):
        return "profi"
    if any(p in t for p in LAIE_PHRASES):
        return "laie"
    woerter = max(1, len(t.split()))
    dichte = len(FACHWORT_RE.findall(text or "")) / woerter
    if dichte >= 0.18:
        return "profi"
    return "unklar"


_DEFLECT_RE = re.compile(
    r"\bwei(?:ss|ß)\b.{0,8}\bnicht\b"          # "weiß (es/ich) nicht"
    r"|\bw[üu]sste? .{0,8}\bnicht\b"
    r"|\bkeine?\s+(?:ahnung|plan|idee)\b"
    r"|\bkein\s+plan\b"
    r"|\bsag(?:s|en)?\s+du\b|\bdu\s+sagst\b|\bmusst\s+du\b"
    r"|\bwas\s+meinst\s+du\b|\bwie\s+soll\s+ich\s+das\s+wissen\b"
    r"|\bkann\s+ich\s+nicht\s+sagen\b|\bschwer\s+zu\s+sagen\b"
    r"|\bist\s+mir\s+egal\b|\bmir\s+egal\b|\begal\b"
    # Abschluss-/Erschöpfungs-Signale
    r"|\bdas\s+ist\s+(?:alles|alles\s+was)\b"   # "das ist alles"
    r"|\bist\s+alles\b"                          # "ist alles"
    r"|\bmehr\s+(?:wei(?:ss|ß)\s+ich\s+nicht|(?:hab(?:e)?\s+ich\s+)?nicht)\b"
    r"|\bmehr\s+(?:kann|weiß|weiss)\s+ich\s+(?:dazu\s+)?nicht\b"
    r"|\b(?:hab(?:e)?|habe\s+ich)\s+.{0,20}(?:alles|schon\s+alles)\s+(?:gesagt|erklärt|beschrieben)\b"
    r"|\bkeine\s+weiteren\s+(?:infos?|informationen|angaben|details?)\b"
    r"|\bnichts?\s+(?:mehr|weiteres?)\s+(?:dazu|zu\s+sagen|zu\s+berichten)\b"
    r"|\bdas\s+war(?:s)?\s+(?:auch\s+)?(?:alles|schon)\b"  # "das wars alles"
    r"|\bweiß?\s+(?:ich\s+)?(?:leider\s+)?(?:auch\s+)?nicht\s+mehr\b"
    # Imperativ-Verweigerungen: Nutzer will keine Fragen beantworten, sondern
    # dass das System selbst nachschlägt — ist faktisch Erschöpfung der Kooperation
    r"|\bsuch\s+(?:es|das|selbst|mal|doch|es\s+selbst|du)\b"   # "such es", "such selbst"
    r"|\bsuch(?:en\s+sie)?\s+(?:es|das)\b"
    r"|\bfind(?:e|en\s+sie)?\s+(?:es|das|selbst|raus|heraus)\b"  # "finde es", "finden Sie raus"
    r"|\braus(?:finden|suchen)?\b"                               # "raus", "rausfinden"
    r"|\bherausfinden\b"
    r"|\bdo\s+(?:it\s+)?yourself\b|\blook\s+it\s+up\b"         # EN fallback
    r"|\bkümmer\s+(?:dich|sich)\s+drum\b"
    r"|\bdas\s+ist\s+deine\s+aufgabe\b|\bdas\s+musst\s+du\b"
    r"|\bsollst\s+du\s+(?:mir\s+)?sagen\b|\bsag\s+du\s+mir\b",  # "sollst du mir sagen"
    re.IGNORECASE,
)


def is_deflection(text: str) -> bool:
    """Erkennt Ausweich-/Weiß-nicht-Antworten (robust gegen Wortstellung, z.B.
    'ich weiss es nicht'), damit ein Slot nicht endlos erfragt wird."""
    t = (text or "").strip().lower()
    if t in ("", "?", "??", "ka", "kp"):
        return True
    return bool(_DEFLECT_RE.search(t))


def resolve(text: str, llm_stil: str) -> Literal["laie", "profi"]:
    """Heuristik gewinnt bei klarem Signal; LLM nur als Tiebreaker; Default Laie."""
    h = detect_sprachstil(text)
    if h != "unklar":
        return h
    if llm_stil in ("laie", "profi"):
        return llm_stil  # type: ignore[return-value]
    return "laie"


_NOISE_TOKENS = {"Abs", "Alt", "Nr", "Halbs", "ff", "analog", "iVm", "Satz", "S", "Art"}


def synth_ag_id(norm: str) -> str:
    """Deterministische ID aus einem Norm-String.

    "§ 823 Abs. 1 BGB" → ag_bgb_823_1 · "§ 223 StGB" → ag_stgb_223 ·
    "Art. 6 DSGVO" → ag_dsgvo_art_6 · "§ 1004 BGB analog" → ag_bgb_1004 ·
    "GewSchG" → ag_gewschg
    """
    raw = norm or ""
    is_art = bool(re.search(r"\bArt\.?", raw))
    tokens = re.findall(r"[A-Za-zÄÖÜäöüß]{2,}", raw)
    cand = [t for t in tokens if any(c.isupper() for c in t) and t not in _NOISE_TOKENS]
    gesetz = cand[-1].lower() if cand else "norm"
    main = re.search(r"(?:§|Art\.?)\s*(\d+[a-z]?)", raw)
    abs_ = re.search(r"Abs\.?\s*(\d+)", raw)
    base = main.group(1) if main else (re.findall(r"\d+", raw)[:1] or [""])[0]
    pid = f"ag_{gesetz}"
    if is_art:
        pid += "_art"
    if base:
        pid += f"_{base}"
    if abs_:
        pid += f"_{abs_.group(1)}"
    return pid.lower()
