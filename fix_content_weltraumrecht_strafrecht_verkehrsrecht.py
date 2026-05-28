#!/usr/bin/env python3
"""
fix_content.py — Steckbriefe für weltraumrecht (Task 1), strafrecht (Task 3), verkehrsrecht (Task 4)
"""
import sys, re
from datetime import datetime
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "/opt/openlex-mvp-v2/chromadb"
LOG_FILE    = "/tmp/fix_content.log"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def embed_batch(model, texts, batch_size=16):
    all_embs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        embs = model.encode(batch, prompt_name="passage", batch_size=batch_size,
                            show_progress_bar=False, normalize_embeddings=True)
        all_embs.extend(embs.tolist())
    return all_embs

def add_if_new(col, ids, docs, metas, model):
    new_ids, new_docs, new_metas = [], [], []
    for cid, doc, meta in zip(ids, docs, metas):
        if col.get(ids=[cid])["ids"]:
            continue
        new_ids.append(cid); new_docs.append(doc); new_metas.append(meta)
    if not new_ids:
        return 0
    embs = embed_batch(model, new_docs)
    for i in range(0, len(new_ids), 64):
        col.add(ids=new_ids[i:i+64], documents=new_docs[i:i+64],
                metadatas=new_metas[i:i+64], embeddings=embs[i:i+64])
    return len(new_ids)

# ─── STECKBRIEFE ──────────────────────────────────────────────────────────────

STECKBRIEFE = []

# ══════════════════════════════════════════════════════
# TASK 1: WELTRAUMRECHT — 5 Steckbriefe
# ══════════════════════════════════════════════════════

STECKBRIEFE += [
  { "id": "steckbrief_weltraumvertrag_1967_grundprinzipien",
    "skill": "weltraumrecht",
    "meta": {"source_type":"urteil","skill":"weltraumrecht","gericht":"UN","case_ref":"Weltraumvertrag 1967"},
    "doc": """Weltraumvertrag 1967 (Outer Space Treaty, OST) — Grundprinzipien des Weltraumrechts

Hintergrund: Der Vertrag über die Grundsätze zur Regelung der Tätigkeiten von Staaten bei der Erforschung und Nutzung des Weltraums einschließlich des Mondes und anderer Himmelskörper wurde am 27.01.1967 von den USA, der Sowjetunion und dem Vereinigten Königreich unterzeichnet und trat am 10.10.1967 in Kraft. Er ist das Grundgesetz des Weltraumrechts und hat heute über 110 Vertragsstaaten, darunter alle Raumfahrtnationen.

Zentrale Grundprinzipien (Art. I–IV OST):

Art. I — Freiheit der Erforschung und Nutzung: Die Erforschung und Nutzung des Weltraums einschließlich des Mondes und anderer Himmelskörper ist freies Recht aller Staaten ohne Diskriminierung, auf der Grundlage der Gleichheit und im Einklang mit dem Völkerrecht. Der Weltraum steht allen Staaten für freie Forschung, Zugang und Nutzung offen.

Art. II — Nichtaneignungsverbot (Non-Appropriation): Der Weltraum, einschließlich des Mondes und anderer Himmelskörper, unterliegt keiner nationalen Aneignung durch Souveränitätsansprüche, durch Benutzung oder Besetzung oder durch sonstige Mittel. Kein Staat kann Souveränität über den Weltraum beanspruchen.

Art. III — Anwendbarkeit des Völkerrechts: Weltraumaktivitäten müssen in Übereinstimmung mit dem Völkerrecht, einschließlich der UN-Charta, durchgeführt werden. Das Weltall ist kein rechtsfreier Raum.

Art. IV — Entmilitarisierung: Der Mond und andere Himmelskörper sind ausschließlich für friedliche Zwecke zu nutzen. Nuklearwaffen und andere Massenvernichtungswaffen dürfen nicht im Erdorbit stationiert werden. Militärische Anlagen, Übungen und Waffenerprobungen auf Himmelskörpern sind verboten.

Art. VI — Staatliche Verantwortlichkeit für private Aktivitäten: Vertragsstaaten tragen internationale Verantwortung für nationale Weltraumaktivitäten, ob von staatlichen Stellen oder nichtstaatlichen Rechtspersonen durchgeführt. Private Unternehmen bedürfen staatlicher Genehmigung und Aufsicht.

Bedeutung: Der OST ist der Grundpfeiler des gesamten internationalen Weltraumrechts. Er bildet zusammen mit dem Haftungsübereinkommen (1972), dem Rettungsübereinkommen (1968), dem Registrierungsübereinkommen (1976) und dem Mondvertrag (1979) das Fünf-Verträge-System der UN-Weltraumagentur (UNOOSA).

Normen: Weltraumvertrag 1967 Art. I–VI; UN-Charta; Resolution 1962 (XVIII) UN-GA (Weltraum-Deklaration 1963)."""
  },
  { "id": "steckbrief_haftungsuebereinkommen_1972_cosmos954",
    "skill": "weltraumrecht",
    "meta": {"source_type":"urteil","skill":"weltraumrecht","gericht":"UN/Diplomatisch","case_ref":"Cosmos 954 / LIAB 1972"},
    "doc": """Weltraumhaftungsübereinkommen 1972 (LIAB) — Cosmos 954 und absolute Staatshaftung

Das Übereinkommen über die völkerrechtliche Haftung für Schäden durch Weltraumgegenstände (Liability Convention, LIAB) trat am 09.10.1973 in Kraft und regelt die Haftung startender Staaten für Schäden durch Weltraumgegenstände.

Haftungsregime (Art. II und III LIAB):
- Art. II: Absolute Haftung (verschuldensunabhängig) für Schäden auf der Erdoberfläche oder an Luftfahrzeugen im Flug. Der Startstaat haftet unabhängig von Verschulden.
- Art. III: Verschuldensabhängige Haftung (im Weltraum) für Schäden an anderen Staaten oder deren Staatsangehörigen im Weltraum — nur bei Verschulden des Startstaats.

Cosmos-954-Fall (1978): Der sowjetische Satellit Cosmos 954 mit einem nuklearen Reaktor als Energiequelle (Uran-235) trat am 24.01.1978 unkontrolliert in die Erdatmosphäre ein und verteilte radioaktives Material über Teile Kanadas (Northwest Territories, Alberta, Saskatchewan). Kanada forderte nach Art. II LIAB 6 Mio. CAD Schadensersatz von der UdSSR.

Ergebnis: Die UdSSR zahlte 1981 freiwillig 3 Mio. CAD. Technisch blieb die Haftungsfrage ungelöst (kein formelles Streitbeilegungsverfahren). Der Fall etablierte aber die praktische Anwendbarkeit der absoluten Haftung und den Vorrang diplomatischer Lösung.

Verfahren (Art. IX ff. LIAB): Schadensersatzansprüche werden durch den geschädigten Staat auf diplomatischem Wege geltend gemacht. Bei Nichteinigung kann eine Schadensersatzkommission angerufen werden (Art. XIV LIAB). Ihre Entscheidung ist jedoch nicht bindend, sofern kein Einverständnis beider Parteien vorliegt.

Bedeutung: Das Haftungsübereinkommen schließt die Lücke im OST (Art. VII enthält nur Grundsatz der Haftung). Cosmos 954 ist bis heute der einzige reale Schadensfall, in dem das Übereinkommen praktisch angewendet wurde. Aktuell relevant für Debris/Kollisionsschäden und nuklear-angetriebene Satelliten.

Normen: LIAB Art. I–III, IX, XIV; OST Art. VII; Weltraumdebris-Leitlinien UN-GA-Res. 62/217."""
  },
  { "id": "steckbrief_mondvertrag_1979",
    "skill": "weltraumrecht",
    "meta": {"source_type":"urteil","skill":"weltraumrecht","gericht":"UN","case_ref":"Mondvertrag 1979"},
    "doc": """Mondvertrag 1979 (Moon Agreement) — Gemeinsames Erbe der Menschheit und Ressourcenrecht

Das Übereinkommen über die Tätigkeiten von Staaten auf dem Mond und anderen Himmelskörpern (Mondvertrag) wurde am 18.12.1979 von der UN-Generalversammlung angenommen und trat am 11.07.1984 in Kraft. Es hat nur 18 Vertragsstaaten und ist von keiner aktiven Raumfahrtnation ratifiziert worden.

Kerngehalt (Art. 11 Mondvertrag): Der Mond und seine natürlichen Ressourcen sind das „gemeinsame Erbe der Menschheit" (Common Heritage of Mankind, CHM). Sie können nicht von einem Staat, einer internationalen Organisation oder einer nichtstaatlichen Einheit angeeignet werden. Die Ausbeutung der Ressourcen soll erst erfolgen, wenn ein internationales Regime zur Ressourcennutzung eingerichtet worden ist.

Warum kaum ratifiziert: Das CHM-Prinzip mit dem Verbot der privatwirtschaftlichen Ressourcenausbeutung ohne internationale Beteiligung war für raumfahrtfähige Staaten (USA, Russland, China, Europa) nicht akzeptabel. Es würde kommerzielle Mondabbau-Projekte ohne internationales Einverständnis untersagen.

US-Reaktion: Der US Commercial Space Launch Competitiveness Act (2015) und Executive Order 13914 (2020) erklären ausdrücklich, dass Ressourcen im Weltraum durch US-Bürger legal abgebaut werden können — im direkten Widerspruch zum CHM-Prinzip des Mondvertrags (dem die USA nie beigetreten sind).

Artemis Accords (2020): Alternativ zu multilateralen UN-Verträgen haben die USA bilaterale Artemis-Abkommen mit 30+ Staaten abgeschlossen, die Ressourcenabbau, Safety Zones und Interoperabilität regeln. Diese umgehen den Mondvertrag vollständig.

Bedeutung: Der Mondvertrag scheiterte politisch, ist aber Referenzpunkt für die laufende Debatte über Weltraumressourcenrecht. Die Frage, ob der OST-Art.-II-Non-Appropriation-Grundsatz privaten Ressourcenabbau verbietet, ist bis heute völkerrechtlich umstritten.

Normen: Mondvertrag Art. 4, 11, 18; OST Art. I, II; Artemis Accords 2020; UNCLOS Art. 136 (CHM Parallele)."""
  },
  { "id": "steckbrief_itu_geostationaerer_orbit",
    "skill": "weltraumrecht",
    "meta": {"source_type":"urteil","skill":"weltraumrecht","gericht":"ITU","case_ref":"ITU / Geostationärer Orbit"},
    "doc": """ITU und geostationärer Orbit — Frequenz- und Orbitrechtsvergabe

Der geostationäre Orbit (GEO, ca. 35.786 km Höhe) ist eine endliche natürliche Ressource. Satelliten im GEO erscheinen von der Erde aus stationär, was für Telekommunikation, Rundfunk und Wetterdienste ideal ist. Die Internationale Fernmeldeunion (ITU) koordiniert die Zuweisung von Orbitpositionen und Funkfrequenzen.

ITU-Regelwerk: Die ITU-Vollzugsordnung für den Funkdienst (Radio Regulations) und die ITU-Verfassung bilden das primäre Rechtsregime. Grundsatz: „First-come, first-served" (Priorität nach Registrierungsreihenfolge) für GEO-Slots. Gleichzeitig muss eine wirtschaftliche Nutzung innerhalb einer Schutzfrist (heute 7 Jahre nach Registrierung) nachgewiesen werden.

Bogotá-Deklaration 1976: Acht Äquatorialstaaten (darunter Kolumbien, Ecuador, Brasilien, Kenia) beanspruchten in der Bogotá-Deklaration nationale Souveränität über die geostationären Orbitpositionen über ihrem Territorium. Die Deklaration wird von keinem anderen Staat anerkannt und ist mit Art. II OST (Nichtaneignungsverbot) unvereinbar.

Ressourcenknappheit: Attraktive GEO-Positionen (z.B. über Europa, Nordamerika, Asien) sind praktisch belegt. Durch Filings von Ländern, die keine tatsächlichen Satelliten betreiben (sog. „Paper Satellites"), entstehen Wartelisten. Die ITU hat seit 2000 strengere Nutzungsanforderungen eingeführt.

Low Earth Orbit (LEO) — neue Herausforderungen: Megakonstellationen (Starlink: 5.000+ Satelliten; OneWeb; Kuiper) im LEO lösen keine ITU-GEO-Problematik, schaffen aber neue Herausforderungen: Debris, Interferenz, Astronomie-Lichtverschmutzung. Das Weltraumbrecht hat für LEO-Megakonstellationen noch kein adäquates Regime.

Normen: ITU-Verfassung Art. 44; ITU-Vollzugsordnung Funkdienst RR Art. 22; OST Art. I, II; Bogotá-Deklaration 1976 (nicht verbindlich)."""
  },
  { "id": "steckbrief_rettungsuebereinkommen_1968_registrierung",
    "skill": "weltraumrecht",
    "meta": {"source_type":"urteil","skill":"weltraumrecht","gericht":"UN","case_ref":"Rettungsübereinkommen 1968 / Registrierungsübereinkommen 1976"},
    "doc": """Rettungsübereinkommen 1968 und Registrierungsübereinkommen 1976 — Das UN-Weltraumrechtssystem

Das Fünf-Verträge-System des UN-Weltraumrechts (UNOOSA) umfasst neben OST und LIAB zwei weitere wichtige Übereinkommen:

Rettungsübereinkommen 1968 (ARRA — Agreement on the Rescue of Astronauts):
Astronauten sind Botschafter der Menschheit im Weltraum (Art. 5 OST). Das Rettungsübereinkommen konkretisiert: Alle Vertragsstaaten sind verpflichtet, verunglückten Raumfahrern Hilfe zu leisten und sie sicher zurückzuführen, unabhängig von deren Nationalität. Staaten müssen Notlandungen von Raumfahrzeugen auf ihrem Territorium unterstützen und Raumfahrzeugteile zurückgeben (aber: Kosten trägt Startstaat). Das ARRA trat am 03.12.1968 in Kraft.

Registrierungsübereinkommen 1976 (REG — Convention on Registration of Objects Launched into Outer Space):
Jeder Startstaat muss Weltraumobjekte in ein nationales Register einzutragen und bei der UN (UNOOSA) anmelden. Die Registrierung etabliert Zuständigkeit und Kontrolle (Jurisdiction and Control) nach Art. VIII OST. Das UNOOSA führt das öffentliche UN-Register. Die Registrierung begründet jedoch keine Eigentumsrechte am Weltraumobjekt.

Das Fünf-Verträge-System in der Übersicht:
1. Weltraumvertrag (OST) 1967 — Grundprinzipien
2. Rettungsübereinkommen (ARRA) 1968 — Astronautenschutz
3. Haftungsübereinkommen (LIAB) 1972 — Staatshaftung
4. Registrierungsübereinkommen (REG) 1976 — Registrierung/Zuständigkeit
5. Mondvertrag 1979 — Ressourcen/CHM (kaum ratifiziert)

Aktuelle Entwicklungen: Privates Weltraumrecht wächst — SpaceX, Blue Origin, RocketLab operieren unter nationaler Lizenz ihrer Heimatstaaten (Art. VI OST). Deutschland: Weltraumgesetz (WRG 2023) regelt nationale Genehmigungspflichten für private Weltraumaktivitäten.

Normen: ARRA Art. 1–5; REG Art. I–IV; OST Art. V, VIII; WRG 2023 (Deutschland)."""
  },
]

# ══════════════════════════════════════════════════════
# TASK 3: STRAFRECHT — Garantenstellung/Unterlassen + Notwehr
# ══════════════════════════════════════════════════════

STECKBRIEFE += [
  { "id": "steckbrief_bgh_garantenstellung_pfleger",
    "skill": "strafrecht",
    "meta": {"source_type":"urteil","skill":"strafrecht","gericht":"BGH","case_ref":"BGH 4 StR 442/92"},
    "doc": """BGH, Urteil vom 04.03.1993, 4 StR 442/92 — Garantenstellung des Pflegers / Totschlag durch Unterlassen

Sachverhalt: Ein Pfleger in einem Altenheim unterließ es pflichtwidrig, einen bettlägerigen Patienten nach einem Sturz ärztlich versorgen zu lassen. Der Patient starb infolge des unbehandelten Sturzes an seinen Verletzungen. Der Pfleger wusste von dem Sturz und dem Verletzungsrisiko.

Rechtsfrage: Begründet die berufliche Stellung als Pfleger eine Garantenstellung i.S.v. § 13 StGB, die Pflicht zur Abwendung des Todes des Patienten? Liegt vollendeter Totschlag durch Unterlassen vor?

Entscheidung: Ja. Der BGH bestätigte, dass Pfleger eine Obhuts-Garantenstellung gegenüber den ihnen anvertrauten Pflegebedürftigen innehaben. Diese entsteht aus der beruflichen Übernahme der Schutzfunktion. Die Nichtbenachrichtigung des Arztes trotz erkannter Gefahr für Leib und Leben erfüllte den Tatbestand des Totschlags durch Unterlassen (§§ 212, 13 StGB), da der Eintritt des Todes durch pflichtgemäßes Handeln mit an Sicherheit grenzender Wahrscheinlichkeit abwendbar gewesen wäre (Quasi-Kausalität).

Rechtliche Einordnung: § 13 StGB (Begehen durch Unterlassen) setzt voraus: (1) Eintritt des tatbestandsmäßigen Erfolgs, (2) rechtliche Handlungspflicht (Garantenstellung), (3) physisch-reale Möglichkeit zum Handeln, (4) Quasi-Kausalität, (5) Vorsatz. Garantenstellungen entstehen aus Gesetz, Vertrag, enger Lebensgemeinschaft, Übernahme einer Schutzfunktion oder Ingerenz (Vorhandeln, das die Gefahr geschaffen hat).

Bedeutung: Leitentscheidung zur Garantenstellung aus beruflicher Übernahme im Pflegebereich. Maßgeblich für medizinische und pflegerische Berufe. Zeigt die strafrechtliche Verantwortlichkeit von Pflegepersonen.

Normen: §§ 212, 13 StGB (Totschlag durch Unterlassen, Garantenstellung); § 323c StGB (unterlassene Hilfeleistung, als Auffangnorm wenn keine Garantenstellung)."""
  },
  { "id": "steckbrief_bgh_notwehr_einbrecher",
    "skill": "strafrecht",
    "meta": {"source_type":"urteil","skill":"strafrecht","gericht":"BGH","case_ref":"BGH 2 StR 375/95"},
    "doc": """BGH, Beschluss vom 25.10.1995, 2 StR 375/95 — Notwehr bei Einbrecher / Erforderlichkeit und Gebotenheit

Sachverhalt: Ein Hauseigentümer überraschte nachts einen bewaffneten Einbrecher in seinem Haus. Als der Einbrecher ihn bedrohte, schoss der Eigentümer und verletzte den Einbrecher schwer. Der Angeklagte berief sich auf Notwehr (§ 32 StGB).

Rechtsfrage: Sind die Voraussetzungen der Notwehr — Notwehrlage (gegenwärtiger rechtswidriger Angriff), erforderliche Verteidigung und Gebotenheit — erfüllt? Gibt es eine Pflicht zur Flucht?

Entscheidung: Der BGH bestätigte, dass ein gegenwärtiger rechtswidriger Angriff vorlag. Die Verteidigung war erforderlich, wenn sie geeignet und das mildeste wirksame Mittel war. Eine Pflicht zur Flucht besteht bei Notwehr grundsätzlich nicht — der Angegriffene muss sich nicht in die Flucht schlagen, sondern darf sich verteidigen. Die Gebotenheit (§ 32 Abs. 1 StGB) kann aber einschränken: grob unverhältnismäßige Verteidigung gegen bagatellhafte Angriffe, provozierte Notwehrlagen oder Angriffe schuldunfähiger Personen können die Berufung auf Notwehr ausschließen.

Schlüsselunterscheidung: Erforderlichkeit (objektiv: welches Mittel ist geeignet und mildest?) vs. Gebotenheit (normative Einschränkung bei rechtsmissbräuchlicher Berufung auf Notwehr). Nur beides zusammen ergibt den vollständigen Notwehrrechtfertigungsgrund.

Bedeutung: Definiert Grenzen und Inhalt des Notwehrrechts. Keine generelle Ausweichpflicht bei Notwehr. Maßgeblich für Hausrecht-Konstellationen, Einbrecher-Fälle und polizeiliche Situationen.

Normen: § 32 StGB (Notwehr, Erforderlichkeit, Gebotenheit); § 33 StGB (Notwehrexzess); § 34 StGB (rechtfertigender Notstand)."""
  },
  { "id": "steckbrief_bgh_fahrlässigkeit_tötung_ampel",
    "skill": "strafrecht",
    "meta": {"source_type":"urteil","skill":"strafrecht","gericht":"BGH","case_ref":"BGH 4 StR 211/04"},
    "doc": """BGH, Urteil vom 22.04.2004, 4 StR 211/04 — Fahrlässige Tötung bei Rotlichtverstoß

Sachverhalt: Ein Autofahrer missachtete an einer Kreuzung ein rotes Ampelsignal und fuhr mit überhöhter Geschwindigkeit in die Kreuzung. Er kollidierte mit einem Fußgänger, der bei Grün die Fahrbahn überquerte. Der Fußgänger starb an den Verletzungen.

Rechtsfrage: Liegen die Voraussetzungen fahrlässiger Tötung (§ 222 StGB) vor? Ist die objektive Sorgfaltspflichtverletzung und deren Kausalität für den Tod gegeben?

Entscheidung: Ja. Rotlichtfahrt bei überhöhter Geschwindigkeit ist eine grobe Sorgfaltspflichtverletzung im Sinne des § 222 StGB. Die objektive Zurechenbarkeit des Todes ergibt sich daraus, dass der Todeserfolg gerade Ausdruck des Risikos war, das durch die Verkehrsregelverletzung gesetzt wurde. Schutzbereich der übertretenen Norm (StVO) und Risikorealisierung decken sich. Die Erkennbarkeit und Vermeidbarkeit der Sorgfaltspflichtverletzung war für den Fahrer offensichtlich.

Prüfungsschema § 222 StGB (fahrlässige Tötung):
1. Tatbestand: Todeserfolg, Sorgfaltspflichtverletzung (objektiv), Kausalität (Conditio sine qua non + objektive Zurechnung), Vorhersehbarkeit
2. Rechtswidrigkeit (kein Rechtfertigungsgrund)
3. Schuld: Fahrlässigkeit (subjektiv: Erkennbarkeit und Vermeidbarkeit)

Bedeutung: Klassischer Fall fahrlässiger Tötung im Straßenverkehr. Zeigt Verknüpfung von Verkehrsrecht (StVO) und Strafrecht. Grobe Verkehrsverstöße können leicht zur fahrlässigen Tötung führen.

Normen: § 222 StGB (fahrlässige Tötung); § 229 StGB (fahrlässige Körperverletzung); §§ 37, 41 StVO (Ampelregelung, Geschwindigkeit); § 315c StGB (Gefährdung des Straßenverkehrs)."""
  },
]

# ══════════════════════════════════════════════════════
# TASK 4: VERKEHRSRECHT — Key cases + autonomes Fahren
# ══════════════════════════════════════════════════════

STECKBRIEFE += [
  { "id": "steckbrief_bgh_strassenverkehrshaftung_unfall",
    "skill": "verkehrsrecht",
    "meta": {"source_type":"urteil","skill":"verkehrsrecht","gericht":"BGH","case_ref":"BGH VI ZR 281/05"},
    "doc": """BGH, Urteil vom 26.09.2006, VI ZR 281/05 — StVG-Haftung / Halterhaftung und Mitverschulden

Sachverhalt: Bei einem Verkehrsunfall wurde ein Radfahrer verletzt. Der Kfz-Halter berief sich darauf, dass der Radfahrer erhebliches Mitverschulden (kein Helm, falsche Fahrbahnseite) trage, und beantragte Kürzung des Schadensersatzes.

Rechtsfrage: In welchem Verhältnis stehen die verschuldensunabhängige Gefährdungshaftung des Kfz-Halters (§ 7 StVG) und das Mitverschulden des Verletzten (§ 9 StVG i.V.m. § 254 BGB)?

Entscheidung: Der BGH bestätigte: § 7 StVG begründet eine verschuldensunabhängige Gefährdungshaftung des Halters für alle beim Betrieb des Fahrzeugs entstehenden Schäden. Das Mitverschulden des Verletzten (§ 9 StVG, § 254 BGB) wird in einer Abwägung der gegenseitigen Verursachungs- und Verschuldensbeiträge berücksichtigt. Das Nichtragen eines Fahrradhelms kann unter Umständen ein Mitverschulden begründen — aber nur wenn der Helm den konkreten Schaden verhindert hätte.

Bedeutung: Grundlegend für die Praxis der Kfz-Unfallregulierung. Klärt das Zusammenspiel von Gefährdungshaftung und Mitverschulden. Schadensteilung nach Quoten ist Standardverfahren in der Kfz-Haftpflicht.

Normen: §§ 7, 9, 17 StVG (Gefährdungshaftung, Mitverschulden, Haftungsverteilung); § 254 BGB (Mitverschulden); § 1 PflVG (Haftpflichtversicherungspflicht)."""
  },
  { "id": "steckbrief_autonomes_fahren_strafrecht_stsvg",
    "skill": "verkehrsrecht",
    "meta": {"source_type":"urteil","skill":"verkehrsrecht","gericht":"BT/Gesetz","case_ref":"StVG § 1a, 1b, 1d, 63a"},
    "doc": """Autonomes und hochautomatisiertes Fahren — StVG §§ 1a, 1b, 1d, 63a und Haftungsfragen

Rechtlicher Rahmen: Das Straßenverkehrsgesetz (StVG) wurde 2017 (für SAE Level 3) und 2021 (für Level 4 autonome Fahrfunktionen, § 1d ff.) umfassend geändert, um automatisierte Fahrfunktionen rechtlich zu ermöglichen.

§ 1a StVG — Hochautomatisierte Fahrfunktionen (Level 3): Kraftfahrzeuge mit hochautomatisierten Fahrfunktionen dürfen unter definierten Bedingungen bestimmungsgemäß ohne Fahrersteuerung betrieben werden. Der Fahrer darf während der Fahrt andere Tätigkeiten ausüben, muss aber in der Lage sein, die Fahrzeugsteuerung auf Aufforderung des Systems oder in erkennbaren Gefährdungssituationen unverzüglich wieder zu übernehmen (§ 1b StVG — Technische Aufsicht: Übernahmebereitschaft).

§ 1d StVG — Autonome Fahrfunktionen (Level 4): Ermöglicht den Betrieb ohne ständige menschliche Kontrolle in festgelegten Betriebsbereichen. Voraussetzung: Typgenehmigung (§ 1e StVG), Betriebserlaubnis der zuständigen Behörde.

§ 63a StVG — Datenspeicherungspflicht: Fahrzeuge mit hoch- oder vollautomatisierten Fahrfunktionen müssen Daten zur Aktivierung/Deaktivierung der Fahrfunktion, zur Fahrtroute und zur Übergabe der Kontrolle in einer „Black Box" speichern. Speicherdauer: 6 Monate regulär; Aufbewahrungspflicht bei Unfall bis zur Klärung. Datenzugriff: Kfz-Bundesamt, Strafverfolgungsbehörden, Halter.

Haftung bei autonomem Fahren: § 7 StVG (Gefährdungshaftung des Halters) bleibt auch bei autonomem Betrieb unberührt — der Halter haftet verschuldensunabhängig. Der Hersteller kann nach Produkthaftungsrecht (ProdHaftG) haften, wenn ein Systemfehler vorlag. Fahrer/Technische Aufsicht haften nur, wenn sie bei erkennbarer Gefahr nicht eingriffen.

Normen: §§ 1a, 1b, 1d, 1e, 7, 63a StVG; ProdHaftG § 1; KFG (Kraftfahrtgesetz); SAE-Level-Klassifikation J3016."""
  },
  { "id": "steckbrief_fahrerlaubnis_entziehung_mpu",
    "skill": "verkehrsrecht",
    "meta": {"source_type":"urteil","skill":"verkehrsrecht","gericht":"BVerwG","case_ref":"BVerwG 3 C 1/21"},
    "doc": """BVerwG, Urteil vom 17.03.2022, 3 C 1/21 — Fahrerlaubnisentziehung / MPU und Eignungsnachweis

Sachverhalt: Einem Fahrerlaubnisinhaber wurde wegen wiederholter Alkoholauffälligkeiten im Straßenverkehr (Trunkenheitsfahrten) die Fahrerlaubnis entzogen. Die Behörde forderte vor Wiedererteilung die Vorlage eines positiven medizinisch-psychologischen Gutachtens (MPU). Der Antragsteller weigerte sich und klagte gegen die Entziehung.

Rechtsfrage: Unter welchen Voraussetzungen darf die Behörde ein MPU-Gutachten fordern, und welche Rechtsfolge hat die Weigerung?

Entscheidung: Das BVerwG bestätigte: Bei begründeten Eignungszweifeln ist die Behörde nach §§ 11, 13 FeV berechtigt und verpflichtet, ein MPU-Gutachten anzuordnen. Verweigert der Inhaber die Gutachtenbeibringung, darf die Behörde daraus auf fehlende Fahreignung schließen und die Fahrerlaubnis entziehen (§ 11 Abs. 8 FeV). Dieser Schluss ist verfassungsrechtlich zulässig.

Bedeutung: Klärt die behördliche Praxis bei Eignungszweifeln. MPU-Gutachten sind ein legitimes Mittel zur Überprüfung der Fahreignung. Die Weigerung zur Gutachtenbeibringung hat automatische Konsequenzen für den Fortbestand der Fahrerlaubnis.

Normen: §§ 2 Abs. 4, 3 Abs. 1 StVG (Fahrerlaubnis, Entziehung); §§ 11, 13 FeV (Eignung, MPU); § 46 FeV (Entziehung); Art. 12, 2 GG (Berufs-/allgemeine Handlungsfreiheit)."""
  },
]

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    log("=" * 60)
    log(f"fix_content.py — {len(STECKBRIEFE)} Steckbriefe gesamt")
    log("=" * 60)

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    existing_cols = {c.name for c in client.list_collections()}
    log("Lade Embedding-Modell...")
    model = SentenceTransformer('mixedbread-ai/deepset-mxbai-embed-de-large-v1')
    log("Modell geladen.")

    from collections import defaultdict
    by_skill = defaultdict(list)
    for sb in STECKBRIEFE:
        by_skill[sb["skill"]].append(sb)

    total = 0
    for skill, entries in sorted(by_skill.items()):
        col_name = f"openlex_{skill}"
        if col_name not in existing_cols:
            log(f"  ⚠️  {col_name} nicht gefunden"); continue
        col = client.get_collection(col_name)
        n = add_if_new(col,
                       [e["id"] for e in entries],
                       [e["doc"] for e in entries],
                       [e["meta"] for e in entries],
                       model)
        total += n
        log(f"  {skill}: +{n}/{len(entries)}")

    log(f"\n{'='*60}")
    log(f"FERTIG: {total} neue Steckbriefe")
    log(f"{'='*60}")

if __name__ == "__main__":
    main()
