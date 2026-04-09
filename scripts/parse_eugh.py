#!/usr/bin/env python3
"""
parse_eugh.py – Semantischer Parser für EuGH-Vorabentscheidungen.

Zerlegt den Volltext in semantische Segmente:
  header, rechtsrahmen, sachverhalt, vorlagefragen,
  vf_1, vf_2, ... vf_N  (individuelle Vorlagefrage-Antworten),
  tenor

Fallback für Urteile ohne Vorlagefrage-Marker:
  wuerdigung (an Randnummern-Grenzen geteilt)
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.expanduser("~/openlex-mvp")
URTEILE_DIR = os.path.join(BASE_DIR, "data", "urteile")
NAMES_FILE = os.path.join(BASE_DIR, "data", "urteilsnamen.json")

# Chunk-Limits
CHUNK_MIN = 500
CHUNK_MAX = 4000
CHUNK_SPLIT_TARGET = 2800

# Abkürzungen für Satz-Split
_ABK = {
    "abs", "art", "nr", "lit", "buchst", "bzw", "gem", "vgl", "usw",
    "etc", "sog", "ggf", "bsp", "var", "ziff", "rn", "kap", "anh",
    "bgh", "bsg", "bfh", "bag", "bverwg", "bverfg", "eugh", "dr", "prof",
    "eur", "eg", "eu", "ewg",
}


# ---------------------------------------------------------------------------
# Hilfs-Patterns
# ---------------------------------------------------------------------------

def normalize_az(az: str) -> str:
    """Normalisiert Aktenzeichen (Unicode-Hyphens → ASCII)."""
    return az.replace("\u2011", "-").replace("\u2013", "-").replace("\u2012", "-")


# ── Abschnitts-Marker ────────────────────────────────────────────────────

# Rechtsrahmen: Beginn
_RE_RECHTSRAHMEN = re.compile(
    r'^[ \t]*(?:Recht(?:s|licher)\s*(?:rahmen|Rahmen)|'
    r'I\s*[–—-]\s*Recht(?:s|licher)\s*(?:rahmen|Rahmen))',
    re.MULTILINE,
)

# Rechtsrahmen: Alternativ-Erkennung wenn kein expliziter Header
_RE_UNIONSRECHT = re.compile(
    r'^[ \t]*(?:(?:A\s*[–—-]\s*)?Unionsrecht|'
    r'(?:A\s*[–—-]\s*)?(?:Das\s+)?[Nn]ationales?\s+Recht)',
    re.MULTILINE,
)

# Sachverhalt / Ausgangsverfahren
_RE_SACHVERHALT = re.compile(
    r'^[ \t]*(?:(?:II\s*[–—-]\s*)?'
    r'Ausgangsverfahren(?:\s+und\s+Vorlagefragen)?|'
    r'Ausgangsrechtsstreit(?:\s+und\s+Vorlagefragen)?|'
    r'Sachverhalt(?:\s+und\s+Vorlagefragen)?|'
    r'Vorgeschichte(?:\s+des\s+Rechtsstreits)?)',
    re.MULTILINE,
)

# Vorlagefragen (eigenständiger Abschnitt, OHNE "Zu den")
_RE_VORLAGEFRAGEN_EIGEN = re.compile(
    r'^[ \t]*(?:Vorlagefragen|Die\s+Vorlagefragen)\s*$',
    re.MULTILINE,
)

# "Zu den Vorlagefragen" – Beginn des Analyse-Teils
_RE_ZU_DEN_VORLAGEFRAGEN = re.compile(
    r'^[ \t]*(?:(?:III\s*[–—-]\s*)?Zu\s+den\s+Vorlagefragen)',
    re.MULTILINE,
)

# Individuelle Vorlagefrage-Antwort
# Variante A: "Mit seiner/ihrer/seinen/ihren [Ordinal] Frage"
# Variante B: "Zur [Ordinal] Frage/Vorlagefrage"
# Variante C: "Zu den Vorlagefragen [1] und [2]"

_ORDINALS = (
    r'(?:ersten|zweiten|dritten|vierten|fünften|sechsten|siebten|'
    r'achten|neunten|zehnten|elften|zwölften)'
)
_ORDINALS_COMBO = (
    rf'(?:{_ORDINALS}(?:\s+(?:und|bis)\s+(?:(?:zu[rm]\s+)?(?:seiner\s+)?)?{_ORDINALS})?)'
)

_RE_FRAGE_MIT = re.compile(
    rf'(?:Mit\s+(?:seiner|seinen|ihrer|ihren|der)\s+{_ORDINALS_COMBO}'
    rf'\s+(?:Frage|Vorlagefrage|Teilfrage))',
    re.IGNORECASE,
)

_RE_FRAGE_ZUR = re.compile(
    rf'(?:Zur?\s+(?:der\s+)?{_ORDINALS_COMBO}\s+(?:Frage|Vorlagefrage|Teilfrage))',
    re.IGNORECASE,
)

_RE_FRAGE_NUMMER = re.compile(
    r'(?:Zu\s+den?\s+Vorlagefragen?\s+(\d+)\s*(?:und|bis)\s*(\d+))',
    re.IGNORECASE,
)

# Tenor
_RE_TENOR = re.compile(
    r'(?:Aus\s+diesen\s+Gründen\s+hat\s+(?:der\s+Gerichtshof|das\s+Gericht))',
    re.IGNORECASE,
)

# Kosten (direkt vor Tenor)
_RE_KOSTEN = re.compile(
    r'^[ \t]*Kosten\s',
    re.MULTILINE,
)

# Randnummern-Pattern: Zahl am Zeilenanfang gefolgt von Leerzeichen
_RE_RANDNUMMER = re.compile(r'^(\d{1,3})\s{2,}', re.MULTILINE)


# ---------------------------------------------------------------------------
# Ordinal → Nummer Mapping
# ---------------------------------------------------------------------------

_ORD_MAP = {
    "ersten": 1, "zweiten": 2, "dritten": 3, "vierten": 4,
    "fünften": 5, "sechsten": 6, "siebten": 7, "achten": 8,
    "neunten": 9, "zehnten": 10, "elften": 11, "zwölften": 12,
}


def _extract_frage_nummern(text: str) -> list[int]:
    """Extrahiert Frage-Nummern aus einem Marker-Text."""
    nummern = []
    text_lower = text.lower()
    for word, num in _ORD_MAP.items():
        if word in text_lower:
            nummern.append(num)
    if not nummern:
        # Try digit patterns
        digits = re.findall(r'(\d+)', text)
        nummern = [int(d) for d in digits]
    return sorted(set(nummern))


# ---------------------------------------------------------------------------
# Segment-Datenklasse
# ---------------------------------------------------------------------------

@dataclass
class Segment:
    name: str          # z.B. "vf_1", "vf_2_3", "tenor"
    text: str
    start_pos: int
    end_pos: int
    frage_nummern: list[int] = field(default_factory=list)

    @property
    def length(self) -> int:
        return len(self.text)


# ---------------------------------------------------------------------------
# Hauptparser
# ---------------------------------------------------------------------------

def parse_eugh_urteil(volltext: str, aktenzeichen: str = "") -> list[Segment]:
    """
    Parst ein EuGH-Urteil in semantische Segmente.

    Returns:
        Liste von Segment-Objekten in Dokumentreihenfolge.
    """
    text = volltext
    tlen = len(text)
    segments: list[Segment] = []

    # ── Phase 1: Finde Haupt-Sektionsgrenzen ─────────────────────────────

    # Tenor (muss als erstes gefunden werden – definiert das Ende der Analyse)
    tenor_pos = tlen
    m_tenor = _RE_TENOR.search(text)
    if m_tenor:
        tenor_pos = m_tenor.start()

    # Kosten (direkt vor Tenor)
    kosten_pos = tenor_pos
    for m_k in _RE_KOSTEN.finditer(text):
        if m_k.start() > tenor_pos * 0.7 and m_k.start() < tenor_pos:
            kosten_pos = m_k.start()
            break

    # Rechtsrahmen
    rechtsrahmen_pos = None
    m_rr = _RE_RECHTSRAHMEN.search(text)
    if m_rr and m_rr.start() < tlen * 0.3:
        rechtsrahmen_pos = m_rr.start()
    else:
        m_ur = _RE_UNIONSRECHT.search(text)
        if m_ur and m_ur.start() < tlen * 0.3:
            rechtsrahmen_pos = m_ur.start()

    # Sachverhalt / Ausgangsverfahren
    sachverhalt_pos = None
    for m_sv in _RE_SACHVERHALT.finditer(text):
        if m_sv.start() < tlen * 0.5:
            sachverhalt_pos = m_sv.start()
            break

    # "Zu den Vorlagefragen" (Beginn Analyse)
    analyse_pos = None
    m_zdv = _RE_ZU_DEN_VORLAGEFRAGEN.search(text)
    if m_zdv and m_zdv.start() < kosten_pos:
        analyse_pos = m_zdv.start()

    # ── Phase 2: Finde individuelle Vorlagefrage-Marker ──────────────────

    frage_markers: list[tuple[int, str, list[int]]] = []  # (pos, raw_text, nummern)

    # Durchsuche den Analyseteil (nach "Zu den Vorlagefragen" bis Kosten)
    search_start = analyse_pos or (sachverhalt_pos or 0)
    search_end = kosten_pos

    for pat in [_RE_FRAGE_MIT, _RE_FRAGE_ZUR, _RE_FRAGE_NUMMER]:
        for m in pat.finditer(text, search_start, search_end):
            raw = m.group(0)
            nummern = _extract_frage_nummern(raw)
            frage_markers.append((m.start(), raw, nummern))

    # Deduplizieren und sortieren
    frage_markers.sort(key=lambda x: x[0])
    deduped: list[tuple[int, str, list[int]]] = []
    for pos, raw, nums in frage_markers:
        if deduped and abs(pos - deduped[-1][0]) < 20:
            # Behalte den mit mehr Nummern
            if len(nums) >= len(deduped[-1][2]):
                deduped[-1] = (pos, raw, nums)
            continue
        deduped.append((pos, raw, nums))
    frage_markers = deduped

    # ── Phase 3: Segmente aufbauen ───────────────────────────────────────

    # Header
    header_end = rechtsrahmen_pos or sachverhalt_pos or analyse_pos or tenor_pos
    if header_end and header_end > 200:
        segments.append(Segment(
            name="header",
            text=text[:header_end].strip(),
            start_pos=0,
            end_pos=header_end,
        ))

    # Rechtsrahmen
    if rechtsrahmen_pos is not None:
        rr_end = sachverhalt_pos or analyse_pos or tenor_pos
        if rr_end > rechtsrahmen_pos:
            segments.append(Segment(
                name="rechtsrahmen",
                text=text[rechtsrahmen_pos:rr_end].strip(),
                start_pos=rechtsrahmen_pos,
                end_pos=rr_end,
            ))

    # Sachverhalt
    if sachverhalt_pos is not None:
        sv_end = analyse_pos or (frage_markers[0][0] if frage_markers else kosten_pos)
        if sv_end > sachverhalt_pos:
            segments.append(Segment(
                name="sachverhalt",
                text=text[sachverhalt_pos:sv_end].strip(),
                start_pos=sachverhalt_pos,
                end_pos=sv_end,
            ))

    # Vorlagefragen-Einleitung (zwischen "Zu den Vorlagefragen" und erstem Frage-Marker)
    if analyse_pos is not None and frage_markers:
        first_frage = frage_markers[0][0]
        if first_frage > analyse_pos + 100:
            segments.append(Segment(
                name="vorlagefragen",
                text=text[analyse_pos:first_frage].strip(),
                start_pos=analyse_pos,
                end_pos=first_frage,
            ))

    # Individuelle Vorlagefrage-Antworten
    if frage_markers:
        used_names: dict[str, int] = {}  # FIX 2: Duplikat-Erkennung
        for i, (pos, raw, nums) in enumerate(frage_markers):
            # Ende = nächster Marker oder Kosten
            if i + 1 < len(frage_markers):
                end = frage_markers[i + 1][0]
            else:
                end = kosten_pos

            # Segment-Name: vf_N oder vf_N+M bei kombinierten Fragen
            if nums:
                seg_name = "vf_" + "_".join(str(n) for n in nums)
            else:
                seg_name = f"vf_{i + 1}"

            # FIX 2: Bei Duplikaten Suffix anhängen (vf_2 → vf_2a, vf_2b)
            if seg_name in used_names:
                count = used_names[seg_name]
                suffix = chr(ord('a') + count)
                seg_name = f"{seg_name}{suffix}"
                used_names[seg_name.rstrip('abcdefgh')] = count + 1
            else:
                used_names[seg_name] = 1

            seg_text = text[pos:end].strip()
            if seg_text:
                segments.append(Segment(
                    name=seg_name,
                    text=seg_text,
                    start_pos=pos,
                    end_pos=end,
                    frage_nummern=nums,
                ))
    elif analyse_pos is not None:
        # Fallback: Keine individuellen Marker → ein "wuerdigung"-Block
        wuerdigung_text = text[analyse_pos:kosten_pos].strip()
        if wuerdigung_text:
            segments.append(Segment(
                name="wuerdigung",
                text=wuerdigung_text,
                start_pos=analyse_pos,
                end_pos=kosten_pos,
            ))
    elif sachverhalt_pos is not None:
        # Kein "Zu den Vorlagefragen" und keine Marker gefunden
        # Alles zwischen Sachverhalt-Ende und Tenor ist Würdigung
        sv_end = segments[-1].end_pos if segments else 0
        wuerdigung_text = text[sv_end:kosten_pos].strip()
        if wuerdigung_text and len(wuerdigung_text) > 200:
            segments.append(Segment(
                name="wuerdigung",
                text=wuerdigung_text,
                start_pos=sv_end,
                end_pos=kosten_pos,
            ))

    # Tenor
    if m_tenor:
        tenor_text = text[tenor_pos:].strip()
        if tenor_text:
            segments.append(Segment(
                name="tenor",
                text=tenor_text,
                start_pos=tenor_pos,
                end_pos=tlen,
            ))

    # ── Phase 4: Post-Processing ─────────────────────────────────────────

    # Sonderfall: Kein Rechtsrahmen und kein Sachverhalt erkannt (z.B. C-131/12)
    if not rechtsrahmen_pos and not sachverhalt_pos and not analyse_pos:
        # Versuche, den Text grob zu teilen: Header + Wuerdigung + Tenor
        if m_tenor:
            # Alles vor Tenor ist eine große Wuerdigung
            pre_tenor = text[:tenor_pos].strip()
            if pre_tenor and len(pre_tenor) > 500:
                segments = [
                    Segment("wuerdigung", pre_tenor, 0, tenor_pos),
                    Segment("tenor", text[tenor_pos:].strip(), tenor_pos, tlen),
                ]

    return segments


# ---------------------------------------------------------------------------
# Chunk-Splitting für große Segmente
# ---------------------------------------------------------------------------

def split_segment(segment: Segment) -> list[Segment]:
    """
    Teilt ein zu großes Segment an Randnummern-Grenzen.

    - Segmente ≤ CHUNK_MAX bleiben unverändert
    - Segmente > CHUNK_MAX werden an Randnummern-Grenzen geteilt
    - Bei vf_X: Erster Teil enthält Fragestellung, letzter Teil das Ergebnis
    - Teil-Chunks: vf_1 → vf_1_0, vf_1_1, ...
    """
    if segment.length <= CHUNK_MAX:
        return [segment]

    text = segment.text

    # Finde Randnummern-Positionen
    rn_positions = []
    for m in _RE_RANDNUMMER.finditer(text):
        rn_positions.append(m.start())

    if not rn_positions:
        # Fallback: An Satzgrenzen teilen
        rn_positions = _find_sentence_boundaries(text)

    if not rn_positions:
        return [segment]

    # Teile an Randnummern-Grenzen nahe CHUNK_SPLIT_TARGET
    chunks_text: list[str] = []
    pos = 0

    while pos < len(text):
        remaining = len(text) - pos
        if remaining <= CHUNK_MAX:
            chunks_text.append(text[pos:].strip())
            break

        # Finde die beste Split-Position nahe Target
        target = pos + CHUNK_SPLIT_TARGET
        best = None
        best_dist = float("inf")

        for rn_pos in rn_positions:
            if rn_pos <= pos + CHUNK_MIN:
                continue
            if rn_pos > pos + CHUNK_MAX:
                break
            dist = abs(rn_pos - target)
            if dist < best_dist:
                best_dist = dist
                best = rn_pos

        if best is None:
            # Kein Randnummer-Split möglich – nehme CHUNK_MAX
            best = pos + CHUNK_MAX

        chunk = text[pos:best].strip()
        if chunk:
            chunks_text.append(chunk)
        pos = best

    # Erstelle Segment-Objekte
    result = []
    for idx, ct in enumerate(chunks_text):
        if len(chunks_text) == 1:
            sub_name = segment.name
        else:
            sub_name = f"{segment.name}_{idx}"

        result.append(Segment(
            name=sub_name,
            text=ct,
            start_pos=segment.start_pos,
            end_pos=segment.end_pos,
            frage_nummern=segment.frage_nummern,
        ))

    return result


def _find_sentence_boundaries(text: str) -> list[int]:
    """Fallback: Satzgrenzen finden."""
    _satz_pat = re.compile(r"(\S+)\.\s+([A-ZÄÖÜ(])", re.UNICODE)
    positions = []
    for m in _satz_pat.finditer(text):
        word = m.group(1).lower().rstrip(".")
        if word not in _ABK:
            positions.append(m.start() + len(m.group(1)) + 1)
    return positions


# ---------------------------------------------------------------------------
# Merge-Logik für zu kleine Segmente
# ---------------------------------------------------------------------------

def merge_small_segments(segments: list[Segment]) -> list[Segment]:
    """Fasst Segmente < CHUNK_MIN mit Nachbarn zusammen."""
    if not segments:
        return segments

    result = []
    for seg in segments:
        if seg.length < CHUNK_MIN and result:
            # Mit vorherigem zusammenfassen
            prev = result[-1]
            merged = Segment(
                name=prev.name,
                text=prev.text + "\n\n" + seg.text,
                start_pos=prev.start_pos,
                end_pos=seg.end_pos,
                frage_nummern=prev.frage_nummern + seg.frage_nummern,
            )
            result[-1] = merged
        else:
            result.append(seg)

    # Prüfe ob der letzte Segment zu klein ist
    if len(result) > 1 and result[-1].length < CHUNK_MIN:
        last = result.pop()
        prev = result[-1]
        result[-1] = Segment(
            name=prev.name,
            text=prev.text + "\n\n" + last.text,
            start_pos=prev.start_pos,
            end_pos=last.end_pos,
            frage_nummern=prev.frage_nummern + last.frage_nummern,
        )

    return result


# ---------------------------------------------------------------------------
# Vollständige Parse-Pipeline
# ---------------------------------------------------------------------------

def parse_and_chunk(volltext: str, aktenzeichen: str = "") -> list[Segment]:
    """
    Vollständige Pipeline: Parse → Split große Segmente → Merge kleine.
    """
    # 1. Parse
    segments = parse_eugh_urteil(volltext, aktenzeichen)

    # 2. Split große Segmente
    split_segments = []
    for seg in segments:
        split_segments.extend(split_segment(seg))

    # 3. Merge kleine Segmente
    final = merge_small_segments(split_segments)

    return final


# ---------------------------------------------------------------------------
# Testlauf
# ---------------------------------------------------------------------------

def load_urteilsnamen() -> dict[str, str | None]:
    try:
        with open(NAMES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def test_cases():
    """Teste den Parser auf 10 Schlüsselurteilen."""
    test_config = [
        ("C-131/12", "Google Spain"),
        ("C-311/18", "Schrems II"),
        ("C-252/21", "Meta/Bundeskartellamt"),
        ("C-687/21", "MediaMarktSaturn"),
        ("C-634/21", "SCHUFA Scoring"),
        ("C-673/17", "Planet49"),
        ("C-40/17", "Fashion ID"),
        ("C-210/16", "Wirtschaftsakademie"),
        ("C-460/20", "TU München/Google"),
        ("C-807/21", "Deutsche Wohnen"),
    ]

    names = load_urteilsnamen()
    all_files = os.listdir(URTEILE_DIR)
    results = {}

    for az, label in test_config:
        print(f"\n{'═' * 60}")
        print(f"  {az} ({label})")
        print(f"{'═' * 60}")

        # Finde JSON-Datei
        num_parts = az.replace("C-", "").split("/")
        patterns = [
            f"EuGH_C-{num_parts[0]}_{num_parts[1]}.json",
            f"EuGH_Rechtssache_C-{num_parts[0]}_{num_parts[1]}.json",
            f"EuGH_Rechtssache_C_{num_parts[0]}_{num_parts[1]}.json",
        ]
        json_file = None
        for p in patterns:
            if p in all_files:
                json_file = p
                break
        if not json_file:
            # Fuzzy match
            for f in all_files:
                if f"_{num_parts[0]}_{num_parts[1]}" in f and f.startswith("EuGH"):
                    json_file = f
                    break

        if not json_file:
            print(f"  ✗ JSON nicht gefunden")
            results[az] = {"status": "not_found"}
            continue

        with open(os.path.join(URTEILE_DIR, json_file), "r", encoding="utf-8") as f:
            doc = json.load(f)

        volltext = doc.get("volltext", "")
        if not volltext:
            print(f"  ✗ Kein Volltext")
            results[az] = {"status": "no_text"}
            continue

        print(f"  Volltext: {len(volltext)} Zeichen")

        # Parse
        segments = parse_and_chunk(volltext, az)

        # Report
        has_tenor = any(s.name == "tenor" or s.name.startswith("tenor") for s in segments)
        vf_count = sum(1 for s in segments if s.name.startswith("vf_") and "_" not in s.name[3:])
        # Auch Teil-Chunks zählen
        vf_unique = set()
        for s in segments:
            if s.name.startswith("vf_"):
                # vf_1_0 → vf_1
                base = s.name.rsplit("_", 1)[0] if re.match(r'vf_\d+_\d+', s.name) else s.name
                vf_unique.add(base)

        total_chars = sum(s.length for s in segments)
        coverage = total_chars / len(volltext) * 100 if volltext else 0

        print(f"  Segmente: {len(segments)}")
        print(f"  Tenor: {'✓' if has_tenor else '✗'}")
        print(f"  Vorlagefragen: {len(vf_unique)}")
        print(f"  Textabdeckung: {coverage:.1f}%")
        print()

        for s in segments:
            size_bar = "█" * min(40, s.length // 100)
            print(f"    {s.name:<20} {s.length:>6} Z  {size_bar}")

        results[az] = {
            "status": "ok",
            "label": label,
            "volltext_len": len(volltext),
            "segment_count": len(segments),
            "has_tenor": has_tenor,
            "vf_count": len(vf_unique),
            "coverage_pct": round(coverage, 1),
            "segments": [
                {"name": s.name, "length": s.length}
                for s in segments
            ],
        }

    # Zusammenfassung
    print(f"\n\n{'═' * 60}")
    print("  ZUSAMMENFASSUNG")
    print(f"{'═' * 60}")
    print(f"  {'AZ':<12} {'Segmente':>8} {'VF':>4} {'Tenor':>6} {'Abdeckung':>10}")
    print(f"  {'─'*12} {'─'*8} {'─'*4} {'─'*6} {'─'*10}")
    for az, r in results.items():
        if r["status"] != "ok":
            print(f"  {az:<12} {'—':>8} {'—':>4} {'—':>6} {'N/A':>10}")
        else:
            print(f"  {az:<12} {r['segment_count']:>8} {r['vf_count']:>4} "
                  f"{'✓' if r['has_tenor'] else '✗':>6} {r['coverage_pct']:>9.1f}%")

    # Progress speichern
    progress = {
        "step": "parser_test",
        "status": "completed",
        "results": results,
    }
    with open(os.path.join(BASE_DIR, "rechunk_progress.json"), "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)
    print(f"\n  Progress gespeichert: rechunk_progress.json")

    return results


if __name__ == "__main__":
    test_cases()
