"""
query_understanding.py – Query Understanding Light für OpenLex.

Deterministisches Mapping von Alltagsbegriffen auf DSGVO-Artikel und §§
für gezielte Chunk-Injection in die Retrieval-Pipeline.

Kein LLM-Call. Nur Regex-basiertes Pattern-Matching.
Deterministisch, idempotent, null Latenz.

Usage:
    from query_understanding import expand_query_to_norms, analyze_query

    query = "Unser Online-Shop will Newsletter an Kunden schicken"
    norms = expand_query_to_norms(query)
    # → ["Art. 6 DSGVO", "Art. 7 DSGVO"]

    result = analyze_query(query)
    # → {"query": ..., "matched_clusters": [...], "all_norms": [...]}
"""

import re
from typing import List, Dict

# ─────────────────────────────────────────────────────────
# Mapping: Norm-String → ChromaDB-IDs (deterministisch)
# ─────────────────────────────────────────────────────────
# Verifiziert gegen live-ChromaDB (2026-04-23, 17.897 Chunks).
# Mehrteilige Artikel (part0/part1) werden vollständig injiziert.
# Nicht vorhanden: dsgvo_art_49 (fehlt in ChromaDB).

QU_NORM_TO_CHROMA_IDS: Dict[str, List[str]] = {
    "Art. 5 DSGVO":  ["dsgvo_art_5"],
    "Art. 6 DSGVO":  ["dsgvo_art_6_part0", "dsgvo_art_6_part1"],
    "Art. 7 DSGVO":  ["dsgvo_art_7"],
    "Art. 8 DSGVO":  ["dsgvo_art_8"],
    "Art. 12 DSGVO": ["dsgvo_art_12_part0", "dsgvo_art_12_part1"],
    "Art. 13 DSGVO": ["dsgvo_art_13"],
    "Art. 14 DSGVO": ["dsgvo_art_14_part0", "dsgvo_art_14_part1"],
    "Art. 15 DSGVO": ["dsgvo_art_15"],
    "Art. 16 DSGVO": ["dsgvo_art_16"],
    "Art. 17 DSGVO": ["dsgvo_art_17"],
    "Art. 18 DSGVO": ["dsgvo_art_18"],
    "Art. 19 DSGVO": ["dsgvo_art_19"],
    "Art. 20 DSGVO": ["dsgvo_art_20"],
    "Art. 21 DSGVO": ["dsgvo_art_21"],
    "Art. 22 DSGVO": ["dsgvo_art_22"],
    "Art. 25 DSGVO": ["dsgvo_art_25"],
    "Art. 26 DSGVO": ["dsgvo_art_26"],
    "Art. 28 DSGVO": ["dsgvo_art_28_part0", "dsgvo_art_28_part1"],
    "Art. 33 DSGVO": ["dsgvo_art_33"],
    "Art. 34 DSGVO": ["dsgvo_art_34"],
    "Art. 35 DSGVO": ["dsgvo_art_35_part0", "dsgvo_art_35_part1"],
    "Art. 36 DSGVO": ["dsgvo_art_36"],
    "Art. 44 DSGVO": ["dsgvo_art_44"],
    "Art. 45 DSGVO": ["dsgvo_art_45_part0", "dsgvo_art_45_part1"],
    "Art. 46 DSGVO": ["dsgvo_art_46"],
    "Art. 47 DSGVO": ["dsgvo_art_47_part0", "dsgvo_art_47_part1"],
    "Art. 82 DSGVO": ["dsgvo_art_82"],
    "Art. 83 DSGVO": ["dsgvo_art_83_part0", "dsgvo_art_83_part1"],
    "Art. 85 DSGVO": ["dsgvo_art_85"],
    "Art. 88 DSGVO": ["dsgvo_art_88"],
    "Art. 89 DSGVO": ["dsgvo_art_89"],
    "Art. 95 DSGVO": ["dsgvo_art_95"],
    "§ 25 TDDDG":    ["gran_TDDDG_§_25"],
    "§ 26 BDSG":     ["gran_BDSG_§_26_Abs.1"],
    "§ 4 BDSG":      ["gran_BDSG_§_4_Abs.1"],
    "§ 31 BDSG":     ["gran_BDSG_§_31_Abs.1"],
}


def get_chroma_ids_for_norms(norms: List[str]) -> List[str]:
    """
    Gibt die ChromaDB-IDs für eine Liste von Norm-Strings zurück.
    Duplikate werden entfernt. Unbekannte Normen werden ignoriert.

    Args:
        norms: Liste von Norm-Strings wie ["Art. 6 DSGVO", "Art. 33 DSGVO"]

    Returns:
        Flache Liste von ChromaDB-IDs, dedupliziert.
    """
    seen: set = set()
    result: List[str] = []
    for norm in norms:
        for cid in QU_NORM_TO_CHROMA_IDS.get(norm, []):
            if cid not in seen:
                seen.add(cid)
                result.append(cid)
    return result


# ─────────────────────────────────────────────────────────
# 12 Cluster mit Trigger-Patterns und Ziel-Normen
# ─────────────────────────────────────────────────────────
# Norm-Strings müssen Schlüssel in QU_NORM_TO_CHROMA_IDS sein.

CLUSTERS = [
    {
        "name": "werbung_marketing",
        "triggers": [
            r"\b(newsletter|werbe(mail|brief)?|marketing|werbung|beworben)\b",
            r"\b(direktwerbung|kundeninformation|angebote?\s+schicken)\b",
            r"\b(e[- ]?mail[- ]?(kampagne|versand)|bestandskunden)\b",
            r"\b(e[- ]?mail[- ]?werbung|spam|opt[- ]?in|opt[- ]?out)\b",
        ],
        "norms": [
            "Art. 6 DSGVO",
            "Art. 7 DSGVO",
            "Art. 21 DSGVO",
        ],
    },
    {
        "name": "beschaeftigte",
        "triggers": [
            r"\b(mitarbeiter|beschäftigt|personal|arbeitnehmer|angestellt)\b",
            r"\b(personalakte|dienstplan|arbeitszeit|bewerber(in)?)\b",
            r"\b(bewerbung(sdaten|sunterlagen|smappe|sphase)?)\b",
            r"\b(lohn|gehalt|lohnbuchhalt|hr[- ]?software)\b",
            r"\b(homeoffice|home[- ]?office|mobiles?\s+arbeiten)\b",
        ],
        "norms": [
            "§ 26 BDSG",
            "Art. 88 DSGVO",
            "Art. 6 DSGVO",
            "Art. 5 DSGVO",
        ],
    },
    {
        "name": "cookies_tracking",
        "triggers": [
            r"\b(cookie|cookies|tracking|tracker)\b",
            r"\b(consent[- ]?banner|einwilligungs[- ]?popup|pixel)\b",
            r"\b(website[- ]?analyse|analytics|fingerprint)\b",
            r"\b(google\s+(analytics|tag|ads)|matomo|hotjar)\b",
        ],
        "norms": [
            "§ 25 TDDDG",
            "Art. 6 DSGVO",
            "Art. 7 DSGVO",
        ],
    },
    {
        "name": "betroffenenrechte",
        "triggers": [
            r"\b(auskunft|auskunfts[- ]?(anspruch|recht))\b",
            r"\b(lösch(ung|en|t)|löschen|weg(machen|löschen)|recht\s+auf\s+vergessen)\b",
            r"\b(berichtig(ung|en)|korrigier(en|ung))\b",
            r"\b(datenübertragbarkeit|portier(ung|en)|daten\s+mitnehmen)\b",
            r"\b(widerspruch|widersprecht?|widersprechen)\b",
            r"\b(was\s+habt\s+ihr|welche\s+daten\s+habt|daten\s+herausgeben)\b",
            r"\b(alle\s+(meine|seine|ihre)\s+daten|daten\s+(zurück|raus|löschen))\b",
        ],
        "norms": [
            "Art. 15 DSGVO",
            "Art. 16 DSGVO",
            "Art. 17 DSGVO",
            "Art. 18 DSGVO",
            "Art. 20 DSGVO",
            "Art. 21 DSGVO",
            "Art. 12 DSGVO",
        ],
    },
    {
        "name": "drittlandtransfer",
        "triggers": [
            r"\b(usa|vereinigte\s+staaten|amerika(nisch)?)\b",
            r"\b(drittland|drittstaat|ausland(s)?)\b",
            r"\b(cloud[- ]?anbieter|aws|azure|microsoft\s+365|office\s+365|google\s+cloud)\b",
            r"\b(standardvertragsklausel|scc|sccn?|angemessenheitsbeschluss)\b",
            r"\b(data\s+privacy\s+framework|dpf|safe\s+harbor|privacy\s+shield)\b",
            r"\b(server\s+(in\s+)?(usa|usa|america|uk|schweiz)|datentransfer)\b",
        ],
        "norms": [
            "Art. 44 DSGVO",
            "Art. 45 DSGVO",
            "Art. 46 DSGVO",
        ],
    },
    {
        "name": "schadensersatz",
        "triggers": [
            r"\b(schaden[- ]?ersatz|schadens[- ]?ersatz|entschädigung)\b",
            r"\b(schmerzensgeld|geld(forderung|fordernd)?|entschädigt)\b",
            r"\b(verklag(en|t|bar)|klag(en|t)|gericht(lich)?|kläger)\b",
            r"\b(haftung|haftbar|haftet|verantwortlich\s+machen)\b",
        ],
        "norms": [
            "Art. 82 DSGVO",
        ],
    },
    {
        "name": "standort_bewegung",
        "triggers": [
            r"\b(gps|standort|bewegungsdaten|location|ortung)\b",
            r"\b(aufenthalt(sort)?|geodaten|geolokal)\b",
            r"\b(fahrer(in)?|lieferdienst|tracker?\s+(im\s+)?auto|flottenmanagement)\b",
        ],
        "norms": [
            "Art. 6 DSGVO",
            "Art. 5 DSGVO",
        ],
    },
    {
        "name": "auftragsverarbeitung",
        "triggers": [
            r"\b(dienstleister|auftragsverarbeit(er|ung)|avv)\b",
            r"\b(hosting|cloud[- ]?dienst|saas|software[- ]?as[- ]?a[- ]?service)\b",
            r"\b(agentur|lohnbuchhalt|newsletter[- ]?anbieter|crm[- ]?system)\b",
            r"\b(extern(er|e)?\s+(anbieter|dienstleister|partner|it))\b",
        ],
        "norms": [
            "Art. 28 DSGVO",
            "Art. 6 DSGVO",
        ],
    },
    {
        "name": "datenpanne",
        "triggers": [
            r"\b(datenpanne|data\s+breach|datenleck|leak(ed)?)\b",
            r"\b(gehackt?|hacker[- ]?angriff|cyber[- ]?angriff|ransomware)\b",
            r"\b(daten[- ]?(verlust|verloren|weg|gestohlen)|fremdzugriff)\b",
            r"\b(unbefugt(er)?\s+zugriff|kompromittiert|eingedrungen)\b",
            r"\b(meldepflicht|behörde\s+melden|72[- ]?stunden)\b",
        ],
        "norms": [
            "Art. 33 DSGVO",
            "Art. 34 DSGVO",
        ],
    },
    {
        "name": "videoueberwachung",
        "triggers": [
            r"\b(video[- ]?(überwachung|kamera|anlage)|überwachungs[- ]?kamera)\b",
            r"\b(kamera(s)?|cctv|aufnahme(n)?\s+(im|von|am))\b",
            r"\b(kamera\s+(in|am|vor|im)\s+\w+)\b",
            r"\b(eingangs[- ]?bereich|parkplatz[- ]?überwach|laden[- ]?überwach)\b",
            r"\b(umkleide|umkleide[- ]?raum|toilette|sanitärbereich)\b",
        ],
        "norms": [
            "Art. 6 DSGVO",
            "Art. 5 DSGVO",
            "§ 4 BDSG",
        ],
    },
    {
        "name": "speicherdauer",
        "triggers": [
            r"\bwie\s+lange\s+(darf|muss|kann|soll)\b",
            r"\b(speicher(n|t|ung)?|aufbewahr(en|ung)?)\b.{0,40}\b(frist|dauer|lang|zeitraum)\b",
            r"\b(speicher[- ]?(dauer|frist)|löschfrist|aufbewahrungsfrist)\b",
            r"\b(archivierung|archiviert|archivieren)\b",
            r"\b(nach\s+(ablauf|ende|kündigung).*?(löschen|aufheben|vernichten))\b",
        ],
        "norms": [
            "Art. 5 DSGVO",
            "Art. 17 DSGVO",
        ],
    },
    {
        "name": "minderjaehrige",
        "triggers": [
            r"\b(kind(er|es)?|minderjähr(ig|ige|iger)|jugendliche?)\b",
            r"\b(unter\s+(16|18)\s+(jahr|jahren)?|schüler(in)?)\b",
            r"\b(eltern(teil|einwilligung|zustimmung)?)\b",
            r"\b(teenager|teens?|u18|u16)\b",
        ],
        "norms": [
            "Art. 8 DSGVO",
            "Art. 7 DSGVO",
            "Art. 6 DSGVO",
        ],
    },
]


# ─────────────────────────────────────────────────────────
# Kern-Funktionen
# ─────────────────────────────────────────────────────────

def expand_query_to_norms(query: str) -> List[str]:
    """
    Analysiert die Query und gibt alle Normen zurück, die durch getriggerte
    Cluster identifiziert wurden.

    Mehrfach-Mapping erlaubt: eine Query kann mehrere Cluster triggern,
    alle Normen werden additiv gesammelt. Duplikate werden entfernt,
    Reihenfolge deterministisch (Cluster-Reihenfolge, dann Norm-Reihenfolge).

    Args:
        query: Suchanfrage (beliebige Sprache/Länge)

    Returns:
        Liste von Norm-Strings (z.B. ["Art. 6 DSGVO", "Art. 28 DSGVO"]).
        Leer wenn kein Cluster getriggert.
    """
    query_lower = query.lower()
    matched_norms: List[str] = []

    for cluster in CLUSTERS:
        triggered = False
        for pattern in cluster["triggers"]:
            if re.search(pattern, query_lower, re.IGNORECASE):
                triggered = True
                break
        if triggered:
            for norm in cluster["norms"]:
                if norm not in matched_norms:
                    matched_norms.append(norm)

    return matched_norms


def analyze_query(query: str) -> dict:
    """
    Debug/Analytics-Version: gibt strukturiertes Ergebnis mit allen
    getriggerten Clustern und den gemappten Normen zurück.

    Args:
        query: Suchanfrage

    Returns:
        Dict mit keys:
            query: str  – die Original-Query
            matched_clusters: list[dict]  – jeder Cluster mit name/triggers/norms
            all_norms: list[str]  – alle Normen dedupliziert
    """
    query_lower = query.lower()
    matched_clusters = []
    matched_norms: List[str] = []

    for cluster in CLUSTERS:
        matched_triggers = []
        for pattern in cluster["triggers"]:
            m = re.search(pattern, query_lower, re.IGNORECASE)
            if m:
                matched_triggers.append(m.group(0))

        if matched_triggers:
            matched_clusters.append({
                "name": cluster["name"],
                "triggers": matched_triggers,
                "norms": cluster["norms"],
            })
            for norm in cluster["norms"]:
                if norm not in matched_norms:
                    matched_norms.append(norm)

    return {
        "query": query,
        "matched_clusters": matched_clusters,
        "all_norms": matched_norms,
    }
