#!/usr/bin/env python3
"""
create_methodenwissen.py – Erstellt ~55 Methodenwissen-Chunks als JSON-Dateien
und embeddet sie in die ChromaDB-Collection 'openlex_datenschutz'.
"""

from __future__ import annotations

import json
import os
import re
import time

BASE_DIR = os.path.expanduser("~/openlex-mvp")
MW_DIR = os.path.join(BASE_DIR, "data", "methodenwissen")
CHROMADB_DIR = os.path.join(BASE_DIR, "chromadb")
COLLECTION = "openlex_datenschutz"
MODEL_NAME = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"
os.makedirs(MW_DIR, exist_ok=True)

VERWEIS_RE = re.compile(
    r"Art\.?\s*\d+\s*(?:Abs\.?\s*\d+\s*)?(?:(?:lit\.?\s*[a-z]|Nr\.?\s*\d+)\s*)?(?:DSGVO|DS-GVO|GDPR|GRCh|AEUV|EUV)"
    r"|§§?\s*\d+[a-z]?\s*(?:Abs\.?\s*\d+\s*)?[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß]*",
    re.UNICODE,
)

# ═══════════════════════════════════════════════════════════════════════════
# ALLE METHODENWISSEN-CHUNKS
# ═══════════════════════════════════════════════════════════════════════════

CHUNKS = [
    # ── 1. Normenhierarchie ──────────────────────────────────────────────
    {
        "thema": "Normenhierarchie im EU-Datenschutzrecht",
        "text": (
            "Die Normenhierarchie im europäischen Datenschutzrecht gliedert sich in mehrere Ebenen: "
            "1. EU-Primärrecht: Art. 7 GRCh (Achtung des Privatlebens), Art. 8 GRCh (Schutz personenbezogener Daten), "
            "Art. 16 AEUV (Rechtsgrundlage für EU-Datenschutzgesetzgebung). "
            "2. EU-Sekundärrecht: DSGVO (Verordnung (EU) 2016/679) als unmittelbar geltendes Recht in allen Mitgliedstaaten. "
            "3. Nationales Umsetzungsrecht: BDSG als nationale Konkretisierung im Rahmen der DSGVO-Öffnungsklauseln. "
            "4. Landesdatenschutzgesetze (LDSG) der 16 Bundesländer für Landesbehörden. "
            "5. Sektorspezifisches Datenschutzrecht: TTDSG, TKG, SGB X, AO, BetrVG. "
            "Bei Konflikten gilt: EU-Primärrecht bricht EU-Sekundärrecht bricht nationales Recht (Anwendungsvorrang)."
        ),
    },
    {
        "thema": "Anwendungsvorrang des EU-Rechts (Costa/ENEL, Simmenthal)",
        "text": (
            "Der Anwendungsvorrang des EU-Rechts ist ein fundamentales Prinzip: Steht nationales Recht im Widerspruch zu EU-Recht, "
            "muss das nationale Recht unangewendet bleiben (nicht aufgehoben, sondern verdrängt). "
            "Grundlegende Urteile: EuGH Rs. 6/64 Costa/ENEL (1964): Erstmalige Feststellung des Vorrangs. "
            "EuGH Rs. 106/77 Simmenthal (1978): Jedes nationale Gericht muss EU-widrige nationale Vorschriften von Amts wegen unangewendet lassen. "
            "Für die DSGVO bedeutet das: § 1 Abs. 5 BDSG ordnet ausdrücklich an, dass die DSGVO Vorrang hat. Nationale Regelungen "
            "die über die DSGVO hinausgehen sind nur zulässig, soweit die DSGVO dies durch Öffnungsklauseln erlaubt. "
            "Praktische Relevanz: EuGH C-34/21 erklärte § 26 BDSG für unanwendbar, weil er gegen Art. 88 Abs. 2 DSGVO verstößt."
        ),
    },
    {
        "thema": "Öffnungsklauseln der DSGVO – Übersicht",
        "text": (
            "Die DSGVO enthält circa 69 Öffnungsklauseln, die den Mitgliedstaaten Spielräume für nationale Regelungen einräumen. "
            "Die wichtigsten Öffnungsklauseln: "
            "Art. 6 Abs. 2, 3 DSGVO: Rechtsgrundlagen für Verarbeitung durch öffentliche Stellen (nationale Rechtsgrundlagen). "
            "Art. 9 Abs. 2 lit. b DSGVO: Verarbeitung besonderer Kategorien im Arbeitsrecht. "
            "Art. 23 DSGVO: Beschränkungen der Betroffenenrechte (z.B. für nationale Sicherheit). "
            "Art. 85 DSGVO: Datenverarbeitung und Meinungsfreiheit/Medien (Medienprivileg). "
            "Art. 87 DSGVO: Verarbeitung nationaler Kennnummern (Personalausweisnummer, Steuer-ID). "
            "Art. 88 DSGVO: Beschäftigtendatenschutz – zentrale Öffnungsklausel für § 26 BDSG (durch C-34/21 in Frage gestellt). "
            "Art. 90 DSGVO: Geheimhaltungspflichten (Berufsgeheimnisträger). "
            "Systematik: Öffnungsklauseln sind eng auszulegen. Die nationale Regelung muss die DSGVO-Grundsätze wahren (Art. 5 DSGVO)."
        ),
    },
    {
        "thema": "Deutsche Umsetzung der DSGVO-Öffnungsklauseln im BDSG",
        "text": (
            "Das BDSG nutzt die DSGVO-Öffnungsklauseln in folgenden Vorschriften: "
            "§ 22 BDSG: Verarbeitung besonderer Kategorien personenbezogener Daten (Art. 9 Abs. 2 lit. b, g, h, i, j DSGVO). "
            "§ 26 BDSG: Beschäftigtendatenschutz (Art. 88 DSGVO) – ACHTUNG: EuGH C-34/21 hat festgestellt, dass § 26 Abs. 1 BDSG "
            "nicht den Anforderungen des Art. 88 Abs. 2 DSGVO genügt und daher unanwendbar ist. "
            "§ 27 BDSG: Datenverarbeitung zu wissenschaftlichen/historischen Forschungszwecken (Art. 89 DSGVO). "
            "§ 31 BDSG: Schutz des Wirtschaftsverkehrs bei Scoring und Bonitätsauskünften. "
            "§§ 32-37 BDSG: Konkretisierung der Betroffenenrechte, Beschränkungen nach Art. 23 DSGVO. "
            "§ 38 BDSG: Pflicht zur Benennung eines Datenschutzbeauftragten (ab 20 Personen ständig mit Datenverarbeitung befasst). "
            "§§ 42-43 BDSG: Strafvorschriften und Bußgelder (Art. 84 DSGVO)."
        ),
    },
    {
        "thema": "Verhältnis DSGVO zu ePrivacy/TTDSG (lex specialis)",
        "text": (
            "Das TTDSG (Telekommunikation-Telemedien-Datenschutz-Gesetz) setzt die ePrivacy-Richtlinie (2002/58/EG) um. "
            "Im Verhältnis zur DSGVO gilt: Die ePrivacy-Richtlinie ist lex specialis (vorrangige Spezialregelung) gegenüber der DSGVO "
            "für den Bereich der elektronischen Kommunikation (Art. 95 DSGVO, EG 173 DSGVO). "
            "Kernregel: § 25 TTDSG regelt den Zugriff auf Endgeräte (Cookies, Fingerprinting): "
            "Grundsätzlich Einwilligungserfordernis, Ausnahmen nur für technisch notwendige Zugriffe. "
            "EuGH C-673/17 Planet49: Opt-in-Einwilligung für Cookies erforderlich, vorausgefüllte Checkbox genügt nicht. "
            "Zweistufige Prüfung in der Praxis: 1. Stufe: Zugriff auf Endgerät nach § 25 TTDSG (ePrivacy). "
            "2. Stufe: Verarbeitung der erhobenen Daten nach DSGVO (Rechtsgrundlage aus Art. 6 DSGVO erforderlich). "
            "Die geplante ePrivacy-Verordnung soll die Richtlinie ablösen, ist aber seit 2017 im Gesetzgebungsverfahren."
        ),
    },
    {
        "thema": "Verhältnis DSGVO zu sektorspezifischem Recht (SGB X, AO, TKG, BetrVG, KUG)",
        "text": (
            "Neben BDSG und TTDSG existiert sektorspezifisches Datenschutzrecht, das teils auf DSGVO-Öffnungsklauseln beruht: "
            "SGB X (§§ 67-85a): Sozialdatenschutz. Spezialgesetzliche Regelung für Sozialdaten. Vorrang vor BDSG, aber DSGVO-Grundsätze gelten. "
            "Abgabenordnung (AO, §§ 29b-30): Steuergeheimnis als datenschutzrechtliche Spezialregelung. § 29b AO als Rechtsgrundlage "
            "für Finanzbehörden neben Art. 6 Abs. 1 lit. e DSGVO. "
            "TKG 2021: Telekommunikationsspezifischer Datenschutz, ergänzt TTDSG für Verkehrs- und Standortdaten. "
            "BetrVG: Betriebsverfassungsrechtlicher Datenschutz. § 79a BetrVG regelt Verantwortlichkeit des Betriebsrats. "
            "EuGH C-65/23: Betriebsvereinbarungen nach § 26 Abs. 4 BDSG müssen vollständig DSGVO-konform sein (Art. 88 Abs. 2 DSGVO). "
            "KUG (Kunsturhebergesetz): § 22 KUG Recht am eigenen Bild – Verhältnis zur DSGVO umstritten, "
            "BGH und Literatur nehmen weitgehend Fortgeltung neben der DSGVO an (Art. 85 Abs. 2 DSGVO)."
        ),
    },

    # ── 2. Quellengewichtung ─────────────────────────────────────────────
    {
        "thema": "Quellengewichtung im Datenschutzrecht – 10-Rang-System",
        "text": (
            "Für die juristische Analyse im Datenschutzrecht gilt folgende Hierarchie der Rechtsquellen und Autoritäten: "
            "Rang 1 – EuGH-Urteile: Bindend erga omnes für die Auslegung der DSGVO. Höchste Autorität. "
            "Rang 2 – EuG-Urteile: Erstinstanzlich für EU-Organe, bindend aber durch EuGH überprüfbar. "
            "Rang 3 – Generalanwalts-Schlussanträge: Nicht bindend, aber hohe persuasive Autorität. Werden in ca. 80% der Fälle vom EuGH übernommen. "
            "Rang 4 – Bundesgerichte (BVerfG, BGH, BVerwG, BAG, BFH, BSG): Nationale höchstrichterliche Rechtsprechung. "
            "Rang 5 – Instanzgerichte (OLG, LG, VG, LAG): Erstinstanzliche Entscheidungen, keine Bindungswirkung über den Einzelfall hinaus. "
            "Rang 6 – EDSA/EDPB-Leitlinien: Nicht rechtsverbindlich, aber hohe praktische Relevanz. Aufsichtsbehörden orientieren sich daran. "
            "Rang 7 – DSK-Beschlüsse: Gemeinsame Position der deutschen Aufsichtsbehörden. Nicht bindend, aber einheitliche Verwaltungspraxis. "
            "Rang 8 – Einzelne Aufsichtsbehörden (BfDI, LfDI, LDA): Regionale Verwaltungspraxis, ggf. abweichend von DSK. "
            "Rang 9 – Fachliteratur: Kommentare (Kühling/Buchner, Simitis/Hornung/Spiecker, Gola), Aufsätze, Handbücher. "
            "Rang 10 – Community-Wissen: Praxisberichte, Blog-Beiträge, Meinungen in Fachforen."
        ),
    },
    {
        "thema": "Umgang mit Meinungsstreit im Datenschutzrecht",
        "text": (
            "Im Datenschutzrecht bestehen zahlreiche ungeklärte Rechtsfragen und Meinungsstreite. Methodischer Umgang: "
            "1. Ausgangspunkt: DSGVO-Text und Erwägungsgründe als primäre Quelle. "
            "2. EuGH-Rechtsprechung hat Vorrang vor nationaler Rechtsprechung und Literatur. "
            "3. Bei ungeklärter EuGH-Frage: GA-Schlussanträge und Tendenzen in der EuGH-Rechtsprechung analysieren. "
            "4. Deutsche Gerichte: BGH-Position hat Leitfunktion, aber EuGH kann jederzeit anders entscheiden (Vorlageverfahren Art. 267 AEUV). "
            "5. EDSA-Leitlinien: Nicht bindend, aber repräsentieren den Konsens der Aufsichtsbehörden. Abweichung bedarf guter Begründung. "
            "6. Transparenz: Bei echtem Meinungsstreit alle vertretenen Positionen darstellen, Hauptargumente benennen, "
            "eigene Position begründen, Risiko einer abweichenden Auffassung der Aufsichtsbehörde/Gerichte benennen. "
            "7. Praxishinweis: Im Zweifel die aufsichtsbehördliche Position als sicheren Weg empfehlen, "
            "aber auf alternative Auffassungen hinweisen."
        ),
    },

    # ── 3. Auslegungsmethoden ────────────────────────────────────────────
    {
        "thema": "Grammatische Auslegung der DSGVO (Wortlaut, Mehrsprachigkeit)",
        "text": (
            "Die grammatische Auslegung orientiert sich am Wortlaut der Norm. Bei der DSGVO als EU-Verordnung gelten Besonderheiten: "
            "1. Alle 24 Amtssprachen sind gleichermaßen verbindlich (Art. 55 EUV). "
            "2. Bei Abweichungen zwischen Sprachfassungen ist die Bedeutung zu ermitteln, die allen Fassungen am besten gerecht wird. "
            "3. EuGH prüft regelmäßig mehrere Sprachfassungen (mindestens EN, FR, DE). "
            "4. DSGVO-Begriffe sind autonom auszulegen (unabhängig von nationalen Rechtsbegriffen). "
            "Beispiel: 'personenbezogene Daten' in Art. 4 Nr. 1 DSGVO hat einen EU-autonomen Bedeutungsgehalt, "
            "der nicht mit dem deutschen Verständnis vor der DSGVO gleichgesetzt werden darf. "
            "EuGH C-434/16 Nowak: Auch Prüfungsantworten sind personenbezogene Daten – weite Auslegung des Begriffs."
        ),
    },
    {
        "thema": "Systematische Auslegung der DSGVO (Erwägungsgründe als Kontext)",
        "text": (
            "Die systematische Auslegung betrachtet den Normzusammenhang und die Binnenstruktur der DSGVO: "
            "1. Erwägungsgründe (EG 1–173): Zentrale Auslegungshilfe. Kein eigenständiger Normcharakter, aber maßgeblich für das Verständnis "
            "der Artikelbestimmungen. EuGH zitiert Erwägungsgründe regelmäßig zur Begründung. "
            "2. Kapitelstruktur: Die DSGVO ist in 11 Kapitel gegliedert. Normen eines Kapitels sind im Zusammenhang zu lesen. "
            "3. Querbezüge: Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse) ist im Lichte von EG 47 und EG 48 auszulegen. "
            "Art. 17 (Löschung) im Zusammenhang mit Art. 17 Abs. 3 (Ausnahmen). "
            "4. Grundsatzartikel Art. 5 DSGVO: Alle spezifischen Vorschriften sind im Lichte der sieben Grundsätze auszulegen. "
            "5. Verhältnis zu Kapitel V (Drittlandtransfer): Jede Verarbeitung muss sowohl Art. 6 als auch Kapitel V genügen."
        ),
    },
    {
        "thema": "Teleologische Auslegung der DSGVO (Doppelzweck Art. 1)",
        "text": (
            "Die teleologische Auslegung fragt nach dem Sinn und Zweck der Norm: "
            "Art. 1 DSGVO definiert einen Doppelzweck: "
            "Abs. 1: Schutz natürlicher Personen bei der Verarbeitung personenbezogener Daten. "
            "Abs. 2: Gewährleistung des freien Verkehrs personenbezogener Daten in der Union. "
            "Diese beiden Ziele stehen in einem Spannungsverhältnis und müssen in einen praktischen Ausgleich gebracht werden. "
            "Kein absoluter Vorrang des Datenschutzes – EuGH stellt regelmäßig klar, dass die DSGVO keinen absoluten Schutz gewährt, "
            "sondern eine Abwägung erfordert (EG 4 DSGVO). "
            "Teleologische Reduktion ist möglich: Wenn der Wortlaut zu weit gefasst ist, kann er im Lichte des Normzwecks eingeschränkt werden. "
            "Beispiel: EuGH C-131/12 Google Spain – teleologische Auslegung des Begriffs 'Verantwortlicher' trotz weitem Wortlaut."
        ),
    },
    {
        "thema": "Historische Auslegung (RL 95/46/EG als Vorgänger)",
        "text": (
            "Die historische Auslegung berücksichtigt die Entstehungsgeschichte: "
            "1. Richtlinie 95/46/EG (Datenschutzrichtlinie) als unmittelbare Vorgängerin der DSGVO. "
            "Viele DSGVO-Begriffe wurden aus der RL übernommen – die EuGH-Rechtsprechung zur RL bleibt daher relevant. "
            "2. Gesetzgebungshistorie: Kommissionsentwurf 2012, EP-Änderungen, Trilog-Verhandlungen. "
            "Ratsdokumente und Parlamentsberichte können zur Auslegung herangezogen werden. "
            "3. Konvention 108 des Europarats (1981) als historischer Vorläufer des europäischen Datenschutzrechts. "
            "4. OECD Privacy Guidelines (1980) als internationaler Kontext. "
            "Praxisrelevanz: Wenn der EuGH einen DSGVO-Begriff noch nicht ausgelegt hat, kann die Rechtsprechung "
            "zur RL 95/46/EG als Orientierung dienen (z.B. zur Definition von 'personenbezogene Daten', 'Verantwortlicher')."
        ),
    },
    {
        "thema": "EU-spezifische Auslegungsmethoden (autonome Auslegung, effet utile, Grundrechte)",
        "text": (
            "EU-spezifische Auslegungsgrundsätze für die DSGVO: "
            "1. Autonome Auslegung: EU-Rechtsbegriffe sind unabhängig vom nationalen Recht auszulegen. "
            "Acte clair: Wenn die Auslegung so offenkundig ist, dass kein vernünftiger Zweifel besteht, muss nicht vorgelegt werden. "
            "Acte éclairé: Wenn der EuGH die Frage bereits entschieden hat. "
            "2. Effet utile (praktische Wirksamkeit): Die Auslegung muss sicherstellen, dass die DSGVO ihre volle Wirksamkeit entfaltet. "
            "EuGH wendet diesen Grundsatz regelmäßig an, z.B. weite Auslegung des Begriffs 'personenbezogene Daten'. "
            "3. Grundrechtskonforme Auslegung: Art. 7 GRCh (Privatleben), Art. 8 GRCh (Datenschutz). "
            "Art. 52 Abs. 1 GRCh: Einschränkungen der Grundrechte müssen verhältnismäßig sein und den Wesensgehalt achten. "
            "4. Verhältnismäßigkeitsprinzip: Jede Datenverarbeitung muss erforderlich und angemessen sein. "
            "Drei-Stufen-Test: Geeignetheit, Erforderlichkeit, Angemessenheit."
        ),
    },

    # ── 4. Allgemeine Rechtsgrundsätze ───────────────────────────────────
    {
        "thema": "Verbot mit Erlaubnisvorbehalt im Datenschutzrecht",
        "text": (
            "Das Verbot mit Erlaubnisvorbehalt ist das zentrale Strukturprinzip des Datenschutzrechts: "
            "Jede Verarbeitung personenbezogener Daten ist grundsätzlich verboten, es sei denn, es liegt eine Rechtsgrundlage vor (Art. 6 Abs. 1 DSGVO). "
            "Die sechs Erlaubnistatbestände sind abschließend: a) Einwilligung, b) Vertrag, c) rechtliche Verpflichtung, "
            "d) lebenswichtige Interessen, e) öffentliches Interesse, f) berechtigtes Interesse. "
            "Für besondere Kategorien (Art. 9 DSGVO) gilt ein doppeltes Verbot: Zusätzlich zu Art. 6 muss ein Ausnahmetatbestand nach Art. 9 Abs. 2 vorliegen. "
            "Historisch: In Deutschland seit dem Volkszählungsurteil 1983 etabliert (informationelle Selbstbestimmung als Grundrecht)."
        ),
    },
    {
        "thema": "Informationelle Selbstbestimmung (BVerfG Volkszählung 1983) und IT-Grundrecht",
        "text": (
            "Die verfassungsrechtlichen Grundlagen des deutschen Datenschutzrechts: "
            "1. BVerfG, Urteil vom 15.12.1983, 1 BvR 209/83 (Volkszählungsurteil): "
            "Herleitung des Grundrechts auf informationelle Selbstbestimmung aus Art. 2 Abs. 1 i.V.m. Art. 1 Abs. 1 GG. "
            "Kernaussage: Das Grundrecht gewährleistet die Befugnis des Einzelnen, selbst über die Preisgabe und Verwendung seiner Daten zu bestimmen. "
            "2. BVerfG, Urteil vom 27.02.2008, 1 BvR 370/07 (Online-Durchsuchung): "
            "Grundrecht auf Gewährleistung der Vertraulichkeit und Integrität informationstechnischer Systeme (IT-Grundrecht). "
            "3. BVerfG, Beschlüsse vom 06.11.2019, 1 BvR 16/13 und 1 BvR 276/17 (Recht auf Vergessen I + II): "
            "Recht auf Vergessen I: Innerhalb des Anwendungsbereichs der DSGVO sind die EU-Grundrechte (Art. 7, 8 GRCh) maßgeblich, "
            "nicht die deutschen Grundrechte. Recht auf Vergessen II: Außerhalb des EU-Rechts gelten weiterhin die deutschen Grundrechte."
        ),
    },

    # ── 5. Art. 5 DSGVO – Sieben Grundsätze ─────────────────────────────
    {
        "thema": "Art. 5 Abs. 1 lit. a DSGVO – Rechtmäßigkeit, Verarbeitung nach Treu und Glauben, Transparenz",
        "text": (
            "Art. 5 Abs. 1 lit. a DSGVO – Grundsatz der Rechtmäßigkeit, Verarbeitung nach Treu und Glauben und Transparenz: "
            "1. Rechtmäßigkeit: Verarbeitung nur auf Basis einer Rechtsgrundlage nach Art. 6 Abs. 1 DSGVO. "
            "2. Treu und Glauben (Fairness): Die Verarbeitung darf nicht gegen die vernünftigen Erwartungen der Betroffenen verstoßen. "
            "Verbot der heimlichen Datenerhebung, Verbot des Missbrauchs von Machtasymmetrien. "
            "3. Transparenz: Der Verantwortliche muss über die Verarbeitung informieren (Art. 12-14 DSGVO). "
            "Informationen müssen in präziser, transparenter, verständlicher und leicht zugänglicher Form mitgeteilt werden. "
            "EG 39 DSGVO konkretisiert den Transparenzgrundsatz. "
            "Rechtsfolge bei Verstoß: Bußgeld nach Art. 83 Abs. 5 lit. a DSGVO (bis 20 Mio. EUR / 4% Jahresumsatz)."
        ),
    },
    {
        "thema": "Art. 5 Abs. 1 lit. b DSGVO – Zweckbindung",
        "text": (
            "Art. 5 Abs. 1 lit. b DSGVO – Grundsatz der Zweckbindung: "
            "Personenbezogene Daten müssen für festgelegte, eindeutige und legitime Zwecke erhoben werden. "
            "Eine Weiterverarbeitung zu anderen Zwecken ist nur zulässig, wenn sie mit dem ursprünglichen Zweck vereinbar ist "
            "(Kompatibilitätstest nach Art. 6 Abs. 4 DSGVO). Privilegiert ist die Weiterverarbeitung zu wissenschaftlichen oder historischen "
            "Forschungszwecken und zu statistischen Zwecken (Art. 5 Abs. 1 lit. b Halbsatz 2 DSGVO). "
            "Kriterien des Kompatibilitätstests: Verbindung zwischen Zwecken, Kontext der Erhebung, Art der Daten, "
            "mögliche Folgen, Vorhandensein geeigneter Garantien (Art. 6 Abs. 4 lit. a-e DSGVO)."
        ),
    },
    {
        "thema": "Art. 5 Abs. 1 lit. c DSGVO – Datenminimierung",
        "text": (
            "Art. 5 Abs. 1 lit. c DSGVO – Grundsatz der Datenminimierung: "
            "Personenbezogene Daten müssen dem Zweck angemessen und erheblich sowie auf das für die Zwecke der Verarbeitung "
            "notwendige Maß beschränkt sein. Drei Elemente: Angemessenheit, Erheblichkeit, Beschränkung auf das Notwendige. "
            "Praktische Umsetzung: Data Protection by Design (Art. 25 Abs. 1 DSGVO) und by Default (Art. 25 Abs. 2 DSGVO). "
            "EuGH C-446/21 Schrems/Meta: Der Grundsatz der Datenminimierung begrenzt die Möglichkeit, personenbezogene Daten "
            "für Werbezwecke zu verwenden – Meta darf nicht sämtliche verfügbaren Daten für personalisierte Werbung zusammenführen."
        ),
    },
    {
        "thema": "Art. 5 Abs. 1 lit. d DSGVO – Richtigkeit",
        "text": (
            "Art. 5 Abs. 1 lit. d DSGVO – Grundsatz der Richtigkeit: "
            "Personenbezogene Daten müssen sachlich richtig und erforderlichenfalls auf dem neuesten Stand sein. "
            "Der Verantwortliche muss alle angemessenen Maßnahmen treffen, damit unrichtige Daten unverzüglich gelöscht oder berichtigt werden. "
            "Zusammenhang mit Art. 16 DSGVO (Recht auf Berichtigung) und Art. 17 DSGVO (Recht auf Löschung). "
            "EuGH C-131/12 Google Spain: Auch Suchmaschinenbetreiber müssen Richtigkeit der verlinkten Informationen berücksichtigen."
        ),
    },
    {
        "thema": "Art. 5 Abs. 1 lit. e DSGVO – Speicherbegrenzung",
        "text": (
            "Art. 5 Abs. 1 lit. e DSGVO – Grundsatz der Speicherbegrenzung: "
            "Personenbezogene Daten dürfen nur so lange in identifizierbarer Form gespeichert werden, "
            "wie es für die Zwecke der Verarbeitung erforderlich ist. "
            "Pflicht zur Festlegung von Löschfristen (Löschkonzept). Ausnahme für Archivzwecke im öffentlichen Interesse, "
            "wissenschaftliche/historische Forschungszwecke und statistische Zwecke (Art. 89 Abs. 1 DSGVO). "
            "EuGH C-77/21 Digi: Auch Sicherungskopien unterliegen der Speicherbegrenzung – Löschpflicht gilt auch für Backups."
        ),
    },
    {
        "thema": "Art. 5 Abs. 1 lit. f DSGVO – Integrität und Vertraulichkeit",
        "text": (
            "Art. 5 Abs. 1 lit. f DSGVO – Grundsatz der Integrität und Vertraulichkeit: "
            "Personenbezogene Daten müssen durch geeignete technische und organisatorische Maßnahmen (TOM) "
            "vor unbefugter oder unrechtmäßiger Verarbeitung, Verlust, Zerstörung oder Schädigung geschützt werden. "
            "Konkretisierung durch Art. 32 DSGVO (Sicherheit der Verarbeitung): Pseudonymisierung, Verschlüsselung, "
            "Vertraulichkeit, Integrität, Verfügbarkeit, Belastbarkeit, Wiederherstellbarkeit. "
            "Bei Verletzung: Meldepflicht nach Art. 33 DSGVO (72-Stunden-Frist an Aufsichtsbehörde) "
            "und Benachrichtigung der Betroffenen nach Art. 34 DSGVO bei hohem Risiko."
        ),
    },
    {
        "thema": "Art. 5 Abs. 2 DSGVO – Rechenschaftspflicht (Accountability)",
        "text": (
            "Art. 5 Abs. 2 DSGVO – Rechenschaftspflicht (Accountability): "
            "Der Verantwortliche ist für die Einhaltung der Grundsätze nach Art. 5 Abs. 1 verantwortlich "
            "und muss deren Einhaltung nachweisen können. "
            "Beweislastumkehr: Nicht der Betroffene muss den Verstoß nachweisen, sondern der Verantwortliche muss "
            "die Compliance belegen können. Praktische Umsetzung: Verarbeitungsverzeichnis (Art. 30 DSGVO), "
            "Datenschutz-Folgenabschätzung (Art. 35 DSGVO), Datenschutzbeauftragter (Art. 37 DSGVO), "
            "Dokumentation von TOM (Art. 32 DSGVO), Nachweis der Einwilligung (Art. 7 Abs. 1 DSGVO)."
        ),
    },

    # ── 6. Prüfungsschemata ──────────────────────────────────────────────
    {
        "thema": "Prüfungsschema Datenschutzrecht – 9-Schritte-Standardprüfung",
        "text": (
            "Standardprüfung Datenschutzrecht in 9 Schritten: "
            "1. Anwendbarkeit der DSGVO: Sachlich (Art. 2 – automatisierte Verarbeitung oder Dateisystem) "
            "und räumlich (Art. 3 – Niederlassungs- und Marktortprinzip). "
            "2. Personenbezug: Liegen personenbezogene Daten i.S.d. Art. 4 Nr. 1 DSGVO vor? Besondere Kategorien (Art. 9)? "
            "3. Verantwortlichkeit: Wer ist Verantwortlicher (Art. 4 Nr. 7)? Gemeinsam Verantwortliche (Art. 26)? Auftragsverarbeitung (Art. 28)? "
            "4. Rechtsgrundlage: Art. 6 Abs. 1 DSGVO (sechs Erlaubnistatbestände). Bei Art. 9: zusätzlicher Ausnahmetatbestand. "
            "5. Grundsätze: Einhaltung von Art. 5 DSGVO (Zweckbindung, Datenminimierung, Speicherbegrenzung etc.). "
            "6. Betroffenenrechte: Information (Art. 13/14), Auskunft (Art. 15), Berichtigung (Art. 16), Löschung (Art. 17), "
            "Einschränkung (Art. 18), Datenübertragbarkeit (Art. 20), Widerspruch (Art. 21). "
            "7. Technisch-organisatorische Maßnahmen: Art. 25 (Privacy by Design/Default), Art. 32 (TOM). "
            "8. Drittlandtransfer: Kapitel V (Art. 44-49 DSGVO). Angemessenheitsbeschluss, SCCs, BCRs. "
            "9. Folgen bei Verstoß: Bußgelder (Art. 83), Schadensersatz (Art. 82), Abmahnung, behördliche Maßnahmen (Art. 58)."
        ),
    },
    {
        "thema": "Prüfungsschema Einwilligung (Art. 7 DSGVO)",
        "text": (
            "Prüfung der Wirksamkeit einer Einwilligung nach Art. 4 Nr. 11, Art. 7 DSGVO: "
            "1. Freiwilligkeit: Keine Kopplung an Vertrag (Koppelungsverbot, Art. 7 Abs. 4 DSGVO). Kein Machtungleichgewicht. "
            "Echte Wahlmöglichkeit. EuGH C-61/19 Orange Romania: Vorausgefüllte Checkbox ist keine freiwillige Einwilligung. "
            "2. Bestimmtheit/Informiertheit: Für einen konkreten Fall, nach Unterrichtung über alle relevanten Umstände. "
            "Art. 13/14 DSGVO Informationspflichten müssen erfüllt sein. "
            "3. Unmissverständliche Willensbekundung: Aktive Handlung (Opt-in, nicht Opt-out). "
            "EuGH C-673/17 Planet49: Vorausgefüllte Checkbox genügt nicht. "
            "4. Jederzeitige Widerrufbarkeit: Art. 7 Abs. 3 DSGVO. Widerruf muss so einfach sein wie die Erteilung. "
            "5. Nachweisbarkeit: Verantwortlicher muss Einwilligung nachweisen können (Art. 7 Abs. 1 DSGVO). "
            "6. Besonderheiten bei Kindern: Art. 8 DSGVO (Einwilligung ab 16 Jahren, Mitgliedstaaten können bis 13 absenken)."
        ),
    },
    {
        "thema": "Prüfungsschema Berechtigtes Interesse (Art. 6 Abs. 1 lit. f DSGVO) – Dreistufiger Test",
        "text": (
            "Art. 6 Abs. 1 lit. f DSGVO – Dreistufiger Test für berechtigtes Interesse: "
            "Stufe 1 – Berechtigtes Interesse: Der Verantwortliche oder Dritte muss ein berechtigtes Interesse verfolgen. "
            "EuGH C-621/22 KNLTB: Auch rein kommerzielle Interessen können berechtigt sein. "
            "Das Interesse muss rechtmäßig, bestimmt und real (nicht hypothetisch) sein. "
            "Stufe 2 – Erforderlichkeit: Die Verarbeitung muss zur Verwirklichung des Interesses erforderlich sein. "
            "Es darf kein gleich wirksames, milderes Mittel geben. Datenminimierung beachten. "
            "Stufe 3 – Interessenabwägung: Das berechtigte Interesse darf nicht hinter den Interessen, Grundrechten und "
            "Grundfreiheiten der betroffenen Person zurückstehen. Abwägungskriterien: Art der Daten, "
            "vernünftige Erwartungen der Betroffenen (EG 47 DSGVO), Bestehen einer Kundenbeziehung, "
            "Auswirkungen auf die Betroffenen, getroffene Schutzmaßnahmen. "
            "EuGH C-252/21 Meta: Personalisierte Werbung kann grundsätzlich ein berechtigtes Interesse sein, "
            "ist aber der Abwägung zugänglich."
        ),
    },
    {
        "thema": "Prüfungsschema Datenschutz-Folgenabschätzung (DSFA, Art. 35 DSGVO)",
        "text": (
            "Art. 35 DSGVO – Datenschutz-Folgenabschätzung (DSFA): "
            "Wann erforderlich: Wenn eine Verarbeitung voraussichtlich ein hohes Risiko für die Rechte und Freiheiten natürlicher Personen birgt. "
            "Pflichtfälle: a) Systematische und umfassende Bewertung persönlicher Aspekte (Profiling), "
            "b) Umfangreiche Verarbeitung besonderer Kategorien (Art. 9) oder Strafdaten (Art. 10), "
            "c) Systematische umfangreiche Überwachung öffentlich zugänglicher Bereiche. "
            "DSK-Blacklist: 17 konkrete Verarbeitungstätigkeiten die stets eine DSFA erfordern (z.B. Scoring, Videoüberwachung). "
            "WP 248 2-aus-9-Regel: DSFA erforderlich wenn mindestens 2 von 9 Kriterien erfüllt sind. "
            "Inhalt der DSFA (Art. 35 Abs. 7): Systematische Beschreibung der Verarbeitungsvorgänge und Zwecke, "
            "Bewertung der Notwendigkeit und Verhältnismäßigkeit, Bewertung der Risiken, geplante Abhilfemaßnahmen. "
            "Konsultation: Art. 36 DSGVO – wenn DSFA ergibt, dass hohes Risiko verbleibt, muss Aufsichtsbehörde konsultiert werden."
        ),
    },
    {
        "thema": "Prüfungsschema Schadensersatz (Art. 82 DSGVO)",
        "text": (
            "Art. 82 DSGVO – Schadensersatz bei Datenschutzverstößen: "
            "1. DSGVO-Verstoß: Jeder Verstoß gegen die DSGVO kann schadensersatzpflichtig sein. "
            "2. Materieller Schaden: Konkret bezifferbare Vermögenseinbuße. "
            "3. Immaterieller Schaden: Niedrigschwellig – EuGH C-300/21 Österreichische Post: Bloßer Verstoß allein reicht nicht, "
            "es muss ein tatsächlich erlittener Schaden vorliegen, aber keine Erheblichkeitsschwelle. "
            "EuGH C-590/22: Die bloße Befürchtung eines Datenmissbrauchs kann immateriellen Schaden darstellen. "
            "EuGH C-182/22 Scalable Capital: Identitätsdiebstahl stellt immateriellen Schaden dar. "
            "EuGH C-200/23: Kontrollverlust über eigene Daten genügt als Schaden. "
            "4. Kausalität: Zwischen Verstoß und Schaden. "
            "5. Haftung: Verantwortlicher haftet, Auftragsverarbeiter nur bei Verstoß gegen Art. 28 oder eigene Pflichten. "
            "6. Beweislast: Verantwortlicher muss sich exkulpieren (Art. 82 Abs. 3 – verschuldensunabhängige Haftung mit Exkulpationsmöglichkeit). "
            "7. Ausgleichsfunktion: EuGH C-687/21 MediaMarktSaturn – Schadensersatz hat Ausgleichsfunktion, nicht Straffunktion. "
            "Keine Punitive Damages nach EU-Recht. "
            "T-354/22 Bindl: 400 EUR Schadensersatz für unrechtmäßigen Drittlandtransfer durch EU-Organ."
        ),
    },

    # ── 7. EU-Recht-Besonderheiten ───────────────────────────────────────
    {
        "thema": "Vorlageverfahren Art. 267 AEUV und One-Stop-Shop-Mechanismus",
        "text": (
            "Zentrale EU-Verfahrensinstrumente für die DSGVO-Durchsetzung: "
            "1. Vorlageverfahren (Art. 267 AEUV): Nationale Gerichte können (letzte Instanzen: müssen) dem EuGH Fragen "
            "zur Auslegung der DSGVO vorlegen. Derzeit ca. 50-80 anhängige Vorabentscheidungsersuchen zur DSGVO. "
            "2. One-Stop-Shop-Mechanismus (Art. 56 DSGVO): Bei grenzüberschreitender Verarbeitung ist eine federführende Aufsichtsbehörde zuständig. "
            "Die Zuständigkeit richtet sich nach dem Sitz der Hauptniederlassung des Verantwortlichen. "
            "3. Kohärenzverfahren (Art. 63-66 DSGVO): Sicherstellung einer einheitlichen DSGVO-Anwendung. "
            "EDSA/EDPB kann verbindliche Beschlüsse fassen (Art. 65 DSGVO). "
            "4. Dringlichkeitsverfahren (Art. 66 DSGVO): Ausnahmsweise einseitige Maßnahmen bei dringendem Handlungsbedarf. "
            "5. Rolle des EDSA (Art. 68-76 DSGVO): Koordination der Aufsichtsbehörden, Leitlinien, Stellungnahmen, bindende Beschlüsse."
        ),
    },

    # ── 8. EuGH 2024-2026 Schadensersatz ─────────────────────────────
    {
        "thema": "EuGH C-687/21 MediaMarktSaturn – Ausgleichsfunktion des Schadensersatzes",
        "text": (
            "EuGH C-687/21 (MediaMarktSaturn/Saturn Electro, Urteil): "
            "Kernaussage: Der Schadensersatzanspruch nach Art. 82 DSGVO hat eine Ausgleichsfunktion, keine Straffunktion. "
            "Es gibt keine Punitive Damages im EU-Datenschutzrecht. Der Schadensersatz muss den tatsächlich erlittenen Schaden "
            "vollständig ausgleichen, darf aber nicht darüber hinausgehen. Die Schwere des DSGVO-Verstoßes ist für die "
            "Höhe des Schadensersatzes nicht relevant – nur der tatsächliche Schaden zählt."
        ),
    },
    {
        "thema": "EuGH C-590/22 – Befürchtung von Datenmissbrauch als immaterieller Schaden",
        "text": (
            "EuGH C-590/22 (PS – Incorrect address, Urteil): "
            "Kernaussage: Die bloße Befürchtung eines Missbrauchs personenbezogener Daten kann einen immateriellen Schaden "
            "nach Art. 82 DSGVO darstellen. Es ist nicht erforderlich, dass ein tatsächlicher Missbrauch stattgefunden hat. "
            "Die Befürchtung muss allerdings begründet und nachvollziehbar sein. "
            "Kontext: Eine falsche Adresse führte dazu, dass Post mit Gesundheitsdaten an eine falsche Adresse ging. "
            "Die bloße Sorge über möglichen Missbrauch der preisgegebenen Daten wurde als Schaden anerkannt."
        ),
    },
    {
        "thema": "EuGH C-182/22 Scalable Capital – Identitätsdiebstahl als Schaden",
        "text": (
            "EuGH C-182/22 und C-189/22 (Scalable Capital, verbundene Rechtssachen): "
            "Kernaussage: Identitätsdiebstahl nach einem Datenleck stellt einen ersatzfähigen immateriellen Schaden "
            "nach Art. 82 DSGVO dar. Auch die erhöhte Gefahr künftigen Missbrauchs nach einem Datenleck kann Schaden begründen. "
            "Der EuGH bestätigt seine Linie einer niedrigschwelligen Schadensdefinition: Kein Bagatellvorbehalt, "
            "aber der Betroffene muss nachweisen, dass ein tatsächlicher (nicht bloß hypothetischer) Schaden eingetreten ist."
        ),
    },
    {
        "thema": "EuGH C-200/23 – Kontrollverlust als Schaden",
        "text": (
            "EuGH C-200/23 (Agentsia po vpisvaniyata, Urteil): "
            "Kernaussage: Der bloße Verlust der Kontrolle über die eigenen personenbezogenen Daten kann einen immateriellen Schaden "
            "nach Art. 82 DSGVO begründen. Dies gilt auch ohne nachgewiesenen konkreten Missbrauch der Daten. "
            "Der Kontrollverlust selbst – z.B. durch unbefugte Offenlegung – stellt einen eigenständigen Schaden dar."
        ),
    },
    {
        "thema": "EuGH C-507/23 – Entschuldigung als Schadensausgleich; T-354/22 Bindl – 400 EUR für Drittlandtransfer",
        "text": (
            "EuGH C-507/23 (Patērētāju tiesību aizsardzības centrs): "
            "Kernaussage: Eine aufrichtige Entschuldigung des Verantwortlichen kann unter Umständen als (Teil-)Ausgleich "
            "für immateriellen Schaden genügen. Nationale Gerichte haben Spielraum bei der Bemessung. "
            "EuG T-354/22 (Bindl v Europäisches Parlament): "
            "Kernaussage: 400 EUR immaterieller Schadensersatz für unrechtmäßigen Drittlandtransfer (Google Analytics auf EP-Webseite). "
            "Erstes Urteil eines EU-Gerichts das konkreten Schadensersatz für einen Drittlandtransfer-Verstoß zuspricht."
        ),
    },

    # ── 9. EuGH Berechtigtes Interesse + Bußgelder ──────────────────────
    {
        "thema": "EuGH C-621/22 KNLTB – Kommerzielle Interessen als berechtigtes Interesse",
        "text": (
            "EuGH C-621/22 (Koninklijke Nederlandse Lawn Tennisbond, KNLTB): "
            "Kernaussage: Auch rein kommerzielle und wirtschaftliche Interessen können ein 'berechtigtes Interesse' "
            "nach Art. 6 Abs. 1 lit. f DSGVO darstellen. Der EuGH stellt klar, dass der Begriff des berechtigten Interesses "
            "weit auszulegen ist und nicht auf altruistische oder gemeinnützige Zwecke beschränkt ist. "
            "Die Weitergabe von Mitgliederdaten an Sponsoren kann auf Art. 6 Abs. 1 lit. f gestützt werden, "
            "wenn die Interessenabwägung zugunsten des Verantwortlichen ausfällt."
        ),
    },
    {
        "thema": "EuGH C-446/21 Schrems/Meta – Datenminimierung begrenzt Werbenutzung",
        "text": (
            "EuGH C-446/21 (Schrems v Meta Platforms Ireland): "
            "Kernaussage: Der Grundsatz der Datenminimierung (Art. 5 Abs. 1 lit. c DSGVO) begrenzt die Möglichkeit, "
            "sämtliche verfügbaren personenbezogenen Daten für Werbezwecke zu aggregieren. "
            "Meta darf nicht ohne zeitliche Begrenzung alle Daten aus allen Quellen (Facebook, Instagram, Drittseiten) "
            "für personalisierte Werbung zusammenführen. Auch bei Einwilligung muss der Grundsatz der Datenminimierung gewahrt bleiben."
        ),
    },
    {
        "thema": "EuGH C-807/21 Deutsche Wohnen – Bußgelder und Verschuldensprinzip",
        "text": (
            "EuGH C-807/21 (Deutsche Wohnen SE): "
            "Kernaussage 1: Bußgelder nach Art. 83 DSGVO setzen schuldhaftes Verhalten voraus (Verschuldensprinzip). "
            "Fahrlässigkeit genügt, Vorsatz ist nicht erforderlich. "
            "Kernaussage 2: Die Aufsichtsbehörde muss kein konkretes Fehlverhalten einer natürlichen Person nachweisen "
            "(kein Durchgriff auf Organmitglieder nötig). Das Unternehmen haftet als solches. "
            "Kernaussage 3: Für die Bußgeldbemessung ist der Konzernumsatz maßgeblich (nicht nur der Umsatz der unmittelbar "
            "handelnden Konzerngesellschaft)."
        ),
    },
    {
        "thema": "EuGH C-383/23 ILVA – Konzernumsatz bei Bußgeldbemessung",
        "text": (
            "EuGH C-383/23 (ILVA A/S): "
            "Kernaussage: Bei der Berechnung der Bußgeldobergrenze nach Art. 83 Abs. 4-6 DSGVO ist der gesamte Konzernumsatz "
            "maßgeblich, nicht nur der Umsatz der einzelnen Konzerngesellschaft die den Verstoß begangen hat. "
            "Der EuGH stützt sich auf den wettbewerbsrechtlichen Unternehmensbegriff: Alle Einheiten die eine wirtschaftliche "
            "Einheit bilden, werden als ein 'Unternehmen' betrachtet. Dies bedeutet: 4% des weltweiten Konzernumsatzes "
            "als Obergrenze nach Art. 83 Abs. 5 DSGVO."
        ),
    },

    # ── 10. Beschäftigtendatenschutz ─────────────────────────────────────
    {
        "thema": "EuGH C-34/21 – § 26 BDSG unanwendbar",
        "text": (
            "EuGH C-34/21 (Hauptpersonalrat der Lehrerinnen und Lehrer): "
            "Kernaussage: § 26 Abs. 1 BDSG (Beschäftigtendatenschutz) genügt nicht den Anforderungen des Art. 88 Abs. 2 DSGVO. "
            "Art. 88 DSGVO erlaubt nationale Vorschriften zum Beschäftigtendatenschutz, aber nur wenn diese 'spezifischere Vorschriften' "
            "enthalten die 'geeignete und besondere Maßnahmen' zur Wahrung der Menschenwürde, der berechtigten Interessen und der "
            "Grundrechte der betroffenen Person umfassen. § 26 BDSG wiederholt im Wesentlichen nur Art. 6 Abs. 1 DSGVO "
            "und enthält keine spezifischeren Schutzmaßnahmen. "
            "Rechtsfolge: § 26 BDSG ist unanwendbar. Beschäftigtendatenverarbeitung muss direkt auf Art. 6 Abs. 1 DSGVO gestützt werden."
        ),
    },
    {
        "thema": "EuGH C-65/23 – Betriebsvereinbarungen müssen DSGVO-konform sein",
        "text": (
            "EuGH C-65/23 (K GmbH): "
            "Kernaussage: Betriebsvereinbarungen im Sinne von Art. 88 Abs. 1 DSGVO i.V.m. § 26 Abs. 4 BDSG "
            "müssen die Anforderungen des Art. 88 Abs. 2 DSGVO vollständig einhalten. "
            "Eine Betriebsvereinbarung darf das DSGVO-Schutzniveau nicht unterschreiten. "
            "Sie kann aber Rechtsgrundlage für die Datenverarbeitung sein, wenn sie die spezifischeren Schutzmaßnahmen enthält."
        ),
    },

    # ── 11. DPF und Drittlandtransfer ────────────────────────────────────
    {
        "thema": "Data Privacy Framework (DPF) und Prüfungsschema Drittlandtransfer",
        "text": (
            "Drittlandtransfer nach Kapitel V DSGVO – 6-Stufen-Prüfung: "
            "Stufe 1: Liegt ein Drittlandtransfer vor? (Art. 44 DSGVO – Übermittlung an Empfänger in einem Drittland). "
            "Stufe 2: Angemessenheitsbeschluss vorhanden? (Art. 45 DSGVO – z.B. DPF für USA, UK, Schweiz, Japan, Südkorea). "
            "Data Privacy Framework (DPF): EU-US-Angemessenheitsbeschluss vom 10.07.2023. "
            "EuG T-553/23 (Latombe): EuG bestätigt Gültigkeit des DPF. Schrems III wird erwartet, ist aber noch nicht anhängig. "
            "Stufe 3: Geeignete Garantien? (Art. 46 DSGVO – Standardvertragsklauseln (SCC) 2021, BCRs, Verhaltensregeln). "
            "SCC 2021: Vier Module (C2C, C2P, P2P, P2C). Transfer Impact Assessment (TIA) nach EDSA 01/2020 erforderlich. "
            "Stufe 4: Ergänzende Maßnahmen nötig? (Schrems II Anforderung – technische, organisatorische, vertragliche Maßnahmen). "
            "Stufe 5: Ausnahmen nach Art. 49 DSGVO? (Einwilligung, Vertragserfüllung, zwingendes öffentliches Interesse etc. – nur als Ultima Ratio). "
            "Stufe 6: Dokumentation und laufende Überwachung."
        ),
    },

    # ── 12. DSGVO vs. Digitalrechtsrahmen ─────────────────────────────
    {
        "thema": "DSGVO und AI Act (KI-Verordnung)",
        "text": (
            "Verhältnis DSGVO zum AI Act (Verordnung (EU) 2024/1689): "
            "Art. 10 Abs. 5 AI Act: Für das Training von KI-Systemen dürfen besondere Kategorien personenbezogener Daten "
            "verarbeitet werden, soweit dies für Bias-Erkennung und -Korrektur erforderlich ist – unter strengen Garantien. "
            "Doppelte Folgenabschätzung: Hochrisiko-KI-Systeme erfordern sowohl eine Fundamental Rights Impact Assessment (FRIA) "
            "nach Art. 27 AI Act als auch eine DSFA nach Art. 35 DSGVO, wenn personenbezogene Daten verarbeitet werden. "
            "Grundsatz: Die DSGVO gilt uneingeschränkt neben dem AI Act. Art. 2 Abs. 7 AI Act stellt klar, "
            "dass der AI Act die DSGVO-Rechte nicht berührt."
        ),
    },
    {
        "thema": "DSGVO und DSA (Digital Services Act)",
        "text": (
            "Verhältnis DSGVO zum Digital Services Act (Verordnung (EU) 2022/2065): "
            "EDPB Guidelines 3/2025: Jede Verarbeitung personenbezogener Daten die auf dem DSA basiert, "
            "braucht eine eigenständige DSGVO-Rechtsgrundlage nach Art. 6 Abs. 1 DSGVO. "
            "Der DSA allein ist keine Rechtsgrundlage für die Datenverarbeitung. "
            "Beispiele: Content-Moderation, Recommender-Systeme, Transparenzberichte, KYC-Pflichten. "
            "Koordination: Art. 2 Abs. 4 lit. g DSA verweist auf die DSGVO. Aufsichtsbehörden nach DSGVO und DSA müssen kooperieren."
        ),
    },
    {
        "thema": "DSGVO und Data Act / Data Governance Act (DGA)",
        "text": (
            "Data Act (Verordnung (EU) 2023/2854): "
            "Art. 1 Abs. 5 Data Act: Vorrang der DSGVO bei Konflikten. Die DSGVO geht dem Data Act vor. "
            "Ungeklärte Frage: Verantwortlichkeit nach Art. 4 Nr. 7 DSGVO bei Datenzugangsrechten nach dem Data Act – "
            "wer wird Verantwortlicher wenn Daten nach dem Data Act weitergegeben werden? "
            "Data Governance Act (DGA, Verordnung (EU) 2022/868): "
            "Art. 1 Abs. 3 DGA: Fünffache Absicherung des DSGVO-Vorrangs. "
            "Der DGA darf nicht als Rechtsgrundlage für die Verarbeitung personenbezogener Daten dienen. "
            "Für jede Datenweiterverwendung die personenbezogene Daten betrifft, ist eine DSGVO-Rechtsgrundlage erforderlich."
        ),
    },

    # ── 13. DSK-Blacklist und WP 248 ────────────────────────────────────
    {
        "thema": "DSK-Blacklist – 17 DSFA-pflichtige Verarbeitungen",
        "text": (
            "Die DSK (Datenschutzkonferenz) hat gemäß Art. 35 Abs. 4 DSGVO eine Liste von 17 Verarbeitungstätigkeiten erstellt, "
            "die stets eine Datenschutz-Folgenabschätzung (DSFA) erfordern: "
            "1. Umfangreiche Verarbeitung besonderer Kategorien (Art. 9), 2. Umfangreiche Verarbeitung über strafrechtliche Verurteilungen (Art. 10), "
            "3. Systematische umfangreiche Videoüberwachung, 4. Erstellung umfassender Profile, "
            "5. Verarbeitung biometrischer Daten zur Identifizierung, 6. Zusammenführung von Daten aus verschiedenen Quellen, "
            "7. Verarbeitung von Standortdaten, 8. Einsatz neuer Technologien, 9. Scoring/Profiling mit Rechtswirkung, "
            "10. Automatisierte Entscheidungsfindung (Art. 22), 11. Verarbeitung die Anonymisierung zum Ziel hat, "
            "12. Verarbeitung von Daten Schutzbedürftiger (Kinder, Arbeitnehmer, Patienten), "
            "13. Innovative Nutzung oder Anwendung neuer technologischer oder organisatorischer Lösungen, "
            "14-17: Weitere spezifische Verarbeitungen je nach Kontext."
        ),
    },
    {
        "thema": "WP 248 – 2-aus-9-Regel für DSFA-Pflicht",
        "text": (
            "Art.-29-Datenschutzgruppe WP 248 (jetzt EDPB) – 9 Kriterien für die DSFA-Pflicht: "
            "Eine DSFA ist in der Regel erforderlich, wenn mindestens 2 der folgenden 9 Kriterien erfüllt sind: "
            "1. Bewertung oder Scoring (einschließlich Profiling), 2. Automatisierte Entscheidungsfindung mit Rechtswirkung, "
            "3. Systematische Überwachung, 4. Verarbeitung sensibler/höchstpersönlicher Daten, "
            "5. Umfangreiche Datenverarbeitung (Menge der Betroffenen, Datenmenge, Dauer, geografische Ausdehnung), "
            "6. Abgleich oder Zusammenführung von Datensätzen, 7. Daten schutzbedürftiger Betroffener (Kinder, Arbeitnehmer, Patienten), "
            "8. Innovative Nutzung oder Anwendung neuer technologischer Lösungen, "
            "9. Die Verarbeitung an sich hindert Betroffene an der Ausübung eines Rechts oder der Nutzung einer Dienstleistung."
        ),
    },

    # ── 14. Scoring/KI ──────────────────────────────────────────────────
    {
        "thema": "EuGH C-634/21 SCHUFA – Scoring als automatisierte Entscheidung",
        "text": (
            "EuGH C-634/21 (SCHUFA Holding – Scoring): "
            "Kernaussage: Scoring (Bonitätsbewertung) durch die SCHUFA stellt eine 'automatisierte Entscheidung' "
            "im Sinne von Art. 22 Abs. 1 DSGVO dar, wenn der Score maßgeblichen Einfluss auf die Entscheidung eines Dritten hat "
            "(z.B. Bank bei Kreditvergabe). Es kommt nicht darauf an, dass die SCHUFA selbst keine rechtliche Entscheidung trifft – "
            "die 'Vorverlagerung' der automatisierten Entscheidung auf den Score-Anbieter ist ausreichend. "
            "Rechtsfolge: Verbot der rein automatisierten Entscheidung (Art. 22 Abs. 1 DSGVO), "
            "es sei denn, eine Ausnahme nach Art. 22 Abs. 2 greift. Außerdem: Betroffene haben Recht auf Erläuterung "
            "der involvierten Logik (Art. 15 Abs. 1 lit. h DSGVO)."
        ),
    },
    {
        "thema": "EuGH C-203/22 Dun & Bradstreet – Kein Recht auf Algorithmus, aber aussagekräftige Logik-Info",
        "text": (
            "EuGH C-203/22 (Dun & Bradstreet Austria): "
            "Kernaussage: Art. 15 Abs. 1 lit. h DSGVO gewährt kein Recht auf Offenlegung des konkreten Algorithmus "
            "oder der Berechnungsformel. Der Verantwortliche muss aber 'aussagekräftige Informationen über die involvierte Logik' "
            "bereitstellen. Das bedeutet: Allgemein verständliche Erklärung der Funktionsweise, welche Datenarten einfließen, "
            "wie die verschiedenen Faktoren gewichtet werden (in allgemeiner Form), und welche Auswirkungen die Verarbeitung "
            "auf den Betroffenen hat. Der genaue Algorithmus und die Gewichtungsparameter müssen nicht offengelegt werden "
            "(Schutz des Geschäftsgeheimnisses), aber die Erklärung muss ausreichend sein, damit der Betroffene "
            "die Entscheidung nachvollziehen und ggf. anfechten kann."
        ),
    },

    # ── 15. Zusätzliche wichtige Grundsätze ──────────────────────────────
    {
        "thema": "Ne bis in idem und nulla poena sine lege im Datenschutzrecht",
        "text": (
            "Allgemeine Rechtsgrundsätze im Datenschutzrecht: "
            "Ne bis in idem (Art. 50 GRCh): Niemand darf wegen derselben Tat zweimal bestraft werden. "
            "Relevant bei: DSGVO-Bußgeld + nationales Ordnungswidrigkeitsrecht, DSGVO-Bußgeld + DSA-Sanktion. "
            "EuGH C-117/20 Bpost und C-151/20 Nordzucker: Ne bis in idem gilt auch zwischen verschiedenen Verwaltungssanktionen. "
            "Nulla poena sine lege (Art. 49 GRCh): Keine Strafe ohne Gesetz. "
            "Art. 83 DSGVO ist die gesetzliche Grundlage für Bußgelder. Die Tatbestände müssen hinreichend bestimmt sein."
        ),
    },
    {
        "thema": "Verhältnismäßigkeitsprinzip im Datenschutzrecht (Art. 52 Abs. 1 GRCh)",
        "text": (
            "Das Verhältnismäßigkeitsprinzip durchdringt das gesamte Datenschutzrecht: "
            "Grundlage: Art. 52 Abs. 1 GRCh – Jede Einschränkung der Grundrechte aus Art. 7, 8 GRCh muss verhältnismäßig sein. "
            "Dreistufiger Test: 1. Geeignetheit: Ist die Maßnahme geeignet, den verfolgten Zweck zu erreichen? "
            "2. Erforderlichkeit: Gibt es kein milderes, gleich wirksames Mittel? "
            "3. Angemessenheit: Stehen die Nachteile in einem angemessenen Verhältnis zum verfolgten Zweck? "
            "Anwendung bei: Erforderlichkeitsprüfung in Art. 6 Abs. 1 lit. b-f DSGVO, "
            "Datenminimierung (Art. 5 Abs. 1 lit. c), Speicherbegrenzung (Art. 5 Abs. 1 lit. e), "
            "Beschränkung von Betroffenenrechten (Art. 23), Bußgeldbemessung (Art. 83 Abs. 2). "
            "EuGH C-817/19 Ligue des droits humains: Vorratsdatenspeicherung nur verhältnismäßig bei schwerer Kriminalität."
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# Hauptprogramm
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 60)
    print("OpenLex MVP – Methodenwissen erstellen + embedden")
    print("=" * 60)

    # ── TEIL 1: JSON-Dateien erstellen ──
    print(f"\n  Erstelle {len(CHUNKS)} Methodenwissen-Chunks ...")
    for i, chunk in enumerate(CHUNKS):
        chunk["source_type"] = "methodenwissen"
        chunk["normbezuege"] = list(set(VERWEIS_RE.findall(chunk["text"])))

        fname = re.sub(r'[<>:"/\\|?*\s]+', "_", chunk["thema"]).strip("_")[:80]
        fpath = os.path.join(MW_DIR, f"{fname}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)

    print(f"  {len(CHUNKS)} JSON-Dateien in {MW_DIR}")

    # ── TEIL 2: In ChromaDB embedden ──
    print(f"\n  Lade Embedding-Modell: {MODEL_NAME} ...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    print(f"  Modell geladen.")

    import chromadb
    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION, metadata={"hnsw:space": "cosine"}
    )
    before = collection.count()
    print(f"  ChromaDB: {before} Chunks vorhanden.")

    # Bereits vorhandene IDs
    existing_ids = set()
    if before > 0:
        stored = collection.get(include=[])
        existing_ids = set(stored["ids"])

    # Embedden
    items = []
    for chunk in CHUNKS:
        def _slug(t):
            for a, b in [('Ä','Ae'),('Ö','Oe'),('Ü','Ue'),('ä','ae'),('ö','oe'),('ü','ue'),('ß','ss')]: t = t.replace(a, b)
            return re.sub(r'[^a-z0-9]+', '_', t.lower()).strip('_')
        cid = f"mw_{_slug(chunk['thema'])[:60]}"
        if cid in existing_ids:
            continue
        items.append({
            "id": cid,
            "embed_text": f"{chunk['thema']} – {chunk['text']}",
            "document": chunk["text"],
            "meta": {
                "source_type": "methodenwissen",
                "thema": chunk["thema"],
                "normbezuege": ", ".join(chunk["normbezuege"][:20]),
            },
        })

    print(f"  {len(items)} neue Chunks zu embedden ...")
    if items:
        texts = [it["embed_text"] for it in items]
        ids = [it["id"] for it in items]
        metadatas = [it["meta"] for it in items]
        documents = [it["document"] for it in items]

        embeddings = model.encode(texts, show_progress_bar=True).tolist()

        collection.add(
            ids=ids, embeddings=embeddings,
            documents=documents, metadatas=metadatas,
        )

    after = collection.count()
    print(f"\n  ChromaDB vorher:  {before}")
    print(f"  ChromaDB nachher: {after}")
    print(f"  Neue Chunks:      +{after - before}")

    # Test
    print("\n  Test-Query: 'Wie prüfe ich ob eine Einwilligung wirksam ist?'")
    emb = model.encode(["Wie prüfe ich ob eine Einwilligung wirksam ist?"]).tolist()
    res = collection.query(query_embeddings=emb, n_results=3, include=["metadatas", "distances"])
    for i, (meta, dist) in enumerate(zip(res["metadatas"][0], res["distances"][0])):
        print(f"    {i+1}. [{meta.get('source_type','?')}] {meta.get('thema','')[:50]}  (dist={dist:.4f})")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
