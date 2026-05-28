"""Regelbasierte Heuristiken: Sprachstil-Erkennung, Urteilsreferenz-Erkennung und AG-ID-Synthese."""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Literal, Optional

PARAGRAPH_RE = re.compile(r"§\s?\d+|Art\.\s?\d+", re.IGNORECASE)

# ── Urteilsanfrage-Erkennung ────────────────────────────────────────────────
# Phrasen, die auf eine Rechtsrecherche / Urteilsfrage hindeuten
_URTEILSANFRAGE_PHRASE_RE = re.compile(
    r"\b(was\s+sagt|was\s+wurde|was\s+hat\s+der|wie\s+lautet|wie\s+hat\s+der|"
    r"was\s+ist\s+der\s+inhalt|inhalt\s+des\s+urteils|leitsatz|"
    r"urteil\s+(im|in|von|zu|des|über)|entscheidung\s+(im|in|von|zu|des|über)|"
    r"rechtsprechung\s+(zu|in|von|des)|"
    r"was\s+hat\s+das\s+gericht|wie\s+hat\s+das\s+gericht|"
    r"grundsatzurteil|leitentscheidung|leitfall|landmark\s*case)\b",
    re.IGNORECASE,
)

# Gerichtskürzel — werden auch standalone als Signal gewertet wenn Fragekontext vorhanden
_COURT_RE = re.compile(
    r"\b(EuGH|EuG\b|EGMR|BVerfG|BGH|BAG|BSG|BFH|BVerwG|"
    r"OLG\b|LAG\b|VG\b|LSG\b|FG\b)\b"
)

# Lazy-Cache: wird beim ersten Aufruf aus SchemaLibrary befüllt
# Struktur: { lowercased_phrase: {"skills": [...], "gericht": str, "kurzinfo": str, "canonical": str} }
_URTEIL_INDEX: Optional[dict] = None
_COURT_INDEX: Optional[dict] = None   # kürzel → primary_skill
_BGH_AZ_MAP: Optional[dict] = None    # "I ZR" → [skill, ...]

# BGH-Aktenzeichen-Erkennung: z.B. "BGH I ZR 1/22", "BGH IX ZR 45/19"
_BGH_AZ_RE = re.compile(
    r"\b(?:BGH|Bundesgerichtshof)[,\s]+([IVXLC]+\s+(?:ZR|ZB|ZA|StR|StB|ARs?|ARZ|"
    r"NotZ|RiZ|AnwZ|ForstZ|VRG)\s+\d+[/\\]\d{2,4})\b",
    re.IGNORECASE,
)
# Nur Aktenzeichen-Präfix für Skill-Lookup: "I ZR" aus "I ZR 1/22"
_BGH_AZ_PREFIX_RE = re.compile(
    r"^([IVXLC]+\s+(?:ZR|ZB|ZA|StR|StB))\s+\d", re.IGNORECASE
)


def build_urteil_index(leitfaelle: list, court_aliases: list,
                       bgh_senat_skill_map: Optional[dict] = None) -> None:
    """Baut den Lookup-Index aus den geladenen YAML-Daten.
    Wird einmalig von SchemaLibrary beim Start aufgerufen (beide YAMLs zusammengeführt)."""
    global _URTEIL_INDEX, _COURT_INDEX, _BGH_AZ_MAP
    _URTEIL_INDEX = {}
    for entry in (leitfaelle or []):
        skills = entry.get("skills", [])
        gericht = entry.get("gericht", "")
        kurzinfo = entry.get("kurzinfo", "")
        namen = entry.get("namen", [])
        canonical = namen[0] if namen else ""
        for name in namen:
            key = name.lower().strip()
            if key and key not in _URTEIL_INDEX:
                _URTEIL_INDEX[key] = {
                    "canonical": canonical,
                    "skills": skills,
                    "gericht": gericht,
                    "kurzinfo": kurzinfo,
                }
    _COURT_INDEX = {}
    for ca in (court_aliases or []):
        kuerzel = ca.get("kürzel", "")
        if kuerzel:
            _COURT_INDEX[kuerzel] = ca.get("primary_skill")
    _BGH_AZ_MAP = {}
    for az_prefix, skills in (bgh_senat_skill_map or {}).items():
        _BGH_AZ_MAP[az_prefix.upper().strip()] = skills


def detect_urteilsanfrage(text: str) -> Optional[dict]:
    """Erkennt Urteilsanfragen — BEVOR das LLM aufgerufen wird.

    Gibt zurück:
      {"canonical": str, "skills": [str], "gericht": str, "kurzinfo": str,
       "match_type": "named_case" | "court_phrase"}
    oder None, wenn kein Treffer.

    Schicht 1: Bekannter Fallname im Index (exakter Substring-Match, case-insensitive).
    Schicht 2: Gerichtskürzel + Frageformulierung → primary_skill des Gerichts.
    """
    if not text:
        return None
    t = text.lower()

    # Schicht 1: Bekannter Fallname
    if _URTEIL_INDEX:
        # Längste Matches zuerst (verhindert Partial-Treffer wie "Costa" in "Costanza")
        for phrase in sorted(_URTEIL_INDEX, key=len, reverse=True):
            if phrase in t:
                entry = _URTEIL_INDEX[phrase]
                return {**entry, "match_type": "named_case"}

    # Schicht 2: BGH-Aktenzeichen (z.B. "BGH I ZR 1/22") → Senat → Skill
    az_match = _BGH_AZ_RE.search(text)
    if az_match and _BGH_AZ_MAP:
        full_az = az_match.group(1).strip()
        prefix_m = _BGH_AZ_PREFIX_RE.match(full_az)
        if prefix_m:
            prefix_key = prefix_m.group(1).upper()
            skills = _BGH_AZ_MAP.get(prefix_key, [])
            if skills:
                return {
                    "canonical": f"BGH {full_az}",
                    "skills": skills,
                    "gericht": "BGH",
                    "kurzinfo": f"BGH-Urteil {full_az}",
                    "match_type": "bgh_aktenzeichen",
                }

    # Schicht 3: Gericht-Kürzel + Frageformulierung
    has_phrase = bool(_URTEILSANFRAGE_PHRASE_RE.search(text))
    court_match = _COURT_RE.search(text)
    if has_phrase and court_match:
        kuerzel = court_match.group(1)
        primary_skill = (_COURT_INDEX or {}).get(kuerzel) if _COURT_INDEX else None
        skills = [primary_skill] if primary_skill else []
        return {
            "canonical": f"Urteil {kuerzel}",
            "skills": skills,
            "gericht": kuerzel,
            "kurzinfo": "",
            "match_type": "court_phrase",
        }

    return None


# ── Fuzzy-Urteilserkennung ───────────────────────────────────────────────────
# Stopwords die beim Token-Vergleich ignoriert werden
_FUZZY_STOPWORDS = frozenset({
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem",
    "von", "vom", "im", "in", "an", "am", "auf", "zu", "zum", "zur", "und",
    "oder", "vs", "v", "gegen", "the", "of", "and", "in", "a", "an", "v",
    "en", "et", "de", "le", "la", "les", "du", "des", "was", "sagt", "sagen",
    "wie", "lautet", "urteil", "entscheidung", "fall", "rechtsprechung",
    "erkläre", "erklärt", "erklären", "bitte", "mir", "ich", "mich",
})

_DIRECT_THRESHOLD = 0.88   # ab hier: direkt Handoff
_FUZZY_THRESHOLD  = 0.68   # ab hier: "Meinten Sie?"


def _normalize_fuzzy(text: str) -> str:
    """Lowercase, Akzente entfernen, Satzzeichen normalisieren."""
    nfkd = unicodedata.normalize("NFKD", (text or "").lower())
    s = "".join(c for c in nfkd if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _fuzzy_score(query_norm: str, phrase_norm: str) -> float:
    """Kombinierter Score aus SequenceMatcher + Token-Jaccard.
    Bevorzugt längere Phrasen-Matches um False-Positives (Kurzwörter) zu dämpfen."""
    # Sequenzähnlichkeit
    seq = SequenceMatcher(None, query_norm, phrase_norm).ratio()
    # Token-Jaccard (ohne Stopwords)
    q_tok = set(query_norm.split()) - _FUZZY_STOPWORDS
    p_tok = set(phrase_norm.split()) - _FUZZY_STOPWORDS
    if q_tok and p_tok:
        jaccard = len(q_tok & p_tok) / len(q_tok | p_tok)
        # Coverage: wie viel der Phrase-Tokens im Query gefunden?
        coverage = len(p_tok & q_tok) / len(p_tok)
    else:
        jaccard = coverage = 0.0
    # Gewichteter Max: SequenceMatcher dominiert, Jaccard/Coverage als Boost
    raw = max(seq, jaccard, coverage * 0.9)
    # Dämpfung für sehr kurze Phrasen (< 4 Zeichen nach Normierung) — vermeidet
    # False-Positives wie "AKZO" matchend auf "ich"
    if len(phrase_norm.replace(" ", "")) < 5:
        raw *= 0.7
    return raw


def detect_urteilsanfrage_fuzzy(text: str) -> Optional[dict]:
    """Fuzzy-Fallback: findet Urteilsnamen mit Tippfehlern/Auslassungen.

    Gibt zurück:
      {"canonical": str, "skills": [...], "gericht": str, "kurzinfo": str,
       "match_type": "fuzzy_direct" | "fuzzy_confirm",
       "fuzzy_score": float, "matched_key": str}
    oder None wenn kein Treffer ≥ _FUZZY_THRESHOLD.

    match_type="fuzzy_direct"  → Score ≥ _DIRECT_THRESHOLD, sofort Handoff
    match_type="fuzzy_confirm" → Score ≥ _FUZZY_THRESHOLD, "Meinten Sie?" fragen
    """
    if not text or not _URTEIL_INDEX:
        return None

    # Nur wenn Urteilskontext erkennbar: mindestens ein Non-Stopword-Token
    # muss im Query UND in mindestens einem Indexeintrag ähnlich vorkommen.
    q_norm = _normalize_fuzzy(text)
    q_tok = set(q_norm.split()) - _FUZZY_STOPWORDS
    if not q_tok:
        return None

    best_score = 0.0
    best_entry = None
    best_key   = None

    # Vorfilter: nur Phrasen, die mindestens 1 Token mit dem Query teilen
    # (oder sehr ähnlich sind) — vermeidet O(n) volle SequenceMatcher-Aufrufe
    for phrase, entry in _URTEIL_INDEX.items():
        p_norm = _normalize_fuzzy(phrase)
        p_tok  = set(p_norm.split()) - _FUZZY_STOPWORDS
        # Schneller Pre-Check: Tokenüberschneidung oder Substring der Normform
        if not (q_tok & p_tok) and p_norm not in q_norm and q_norm not in p_norm:
            continue
        score = _fuzzy_score(q_norm, p_norm)
        if score > best_score:
            best_score = score
            best_entry = entry
            best_key   = phrase

    if best_score < _FUZZY_THRESHOLD or best_entry is None:
        return None

    mtype = "fuzzy_direct" if best_score >= _DIRECT_THRESHOLD else "fuzzy_confirm"
    return {
        **best_entry,
        "match_type": mtype,
        "fuzzy_score": round(best_score, 3),
        "matched_key": best_key,
    }


_CONFIRM_YES_RE = re.compile(
    r"\b(ja\b|yes\b|genau\b|korrekt\b|richtig\b|stimmt\b|stimme\s+zu\b|"
    r"exakt\b|genau\s+das\b|das\s+ist\s+richtig\b|das\s+meinte\s+ich\b|"
    r"ja\s*,?\s*genau\b|passt\b)\b",
    re.IGNORECASE,
)
_CONFIRM_NO_RE = re.compile(
    r"\b(nein\b|no\b|nicht\b|falsch\b|anders\b|nope\b|"
    r"das\s+meinte\s+ich\s+nicht\b|nicht\s+gemeint\b)\b",
    re.IGNORECASE,
)


def is_confirm_yes(text: str) -> bool:
    """Erkennt Bestätigungsantworten auf 'Meinten Sie X?'."""
    return bool(_CONFIRM_YES_RE.search(text or ""))


def is_confirm_no(text: str) -> bool:
    """Erkennt Verneinungsantworten auf 'Meinten Sie X?'."""
    return bool(_CONFIRM_NO_RE.search(text or ""))


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
