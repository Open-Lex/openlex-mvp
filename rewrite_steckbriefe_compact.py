#!/usr/bin/env python3
"""
Rewrite der 5 problematischen IGH/EMRK-Steckbriefe:
Judge trunciert Chunks auf 800 Zeichen → alle Schlüsselinhalte MÜSSEN
in den ersten 800 Zeichen stehen.
"""

import sys
sys.path.insert(0, '/opt/openlex-mvp-v2')
import chromadb
from sentence_transformers import SentenceTransformer

CHROMADB_PATH = "/opt/openlex-mvp-v2/chromadb"
MODEL_NAME    = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"
COLLECTION    = "openlex_voelkerrecht"

# Kompakte Vollversionen — Schlüsselinhalte in den ersten ~750 Zeichen
REWRITES = {

"steckbrief_igh_corfu_channel": """IGH, Urteil vom 09.04.1949 — Corfu Channel Case (UK v. Albanien)

Entscheidung in Kürze: (1) Albanien verletzt Warnpflicht → Verantwortlichkeit bejaht. (2) Kriegsschiffe haben Durchfahrtsrecht durch internationale Meerengen auch ohne Genehmigung des Küstenstaates. (3) Britische Minenräumaktion verletzt albanische Souveränität.

Warnpflicht: Albanien wusste von den Minen (oder hätte es wissen müssen) und gab keine Warnung. Staaten haben Warnpflicht gegenüber anderen Staaten für Gefahren auf ihrem Territorium. Kein Erfordernis, die Minen selbst gelegt zu haben — Unterlassen der Warnung genügt. Staatenverantwortlichkeit als Grundsatz des Völkergewohnheitsrechts.

Durchfahrtsrecht (internationale Meerenge): Korfukanal = internationale Meerenge. Kriegsschiffe haben das Recht der unschuldigen Durchfahrt durch internationale Meerengen; Albanien durfte dieses Recht nicht einseitig einschränken. Kodifiziert in SRÜ/UNCLOS Art. 37 (internationale Meerengen für Schifffahrt), Art. 38 (Transitdurchfahrt).

Normen: SRÜ Art. 37 (Meerengen, Durchfahrt); ILC-Artikel Staatenverantwortlichkeit; Art. 38 IGH-Statut.

Sachverhalt: Oktober 1946 — zwei britische Kriegsschiffe liefen im Korfukanal (zwischen Albanien und der griechischen Insel Korfu) auf albanische Seeminen; erhebliche Schäden, viele Tote. Albanien hatte die Minen nicht gelegt (vermutlich Deutschland im Zweiten Weltkrieg oder ein dritter Staat). Albanien bestritt Kenntnis und Verantwortlichkeit, rügte außerdem eine britische Souveränitätsverletzung durch Minenräumungsoperationen.

Bedeutung: Erstes IGH-Urteil (Hauptsache). Begründet Warnpflicht und Durchfahrtsrecht als Gewohnheitsrecht; Vorläufer des UNCLOS (SRÜ).
""",

"steckbrief_igh_barcelona_traction": """IGH, Urteil vom 05.02.1970 — Barcelona Traction (Belgien v. Spanien)

Entscheidung in Kürze: (1) Belgien ist für die Aktionäre nicht aktivlegitimiert — diplomatischer Schutz steht dem Heimatstaat der Gesellschaft (Kanada) zu, nicht dem Heimatstaat der Aktionäre. (2) Erga-omnes-Doktrin entwickelt.

Diplomatischer Schutz / Aktionäre: Belgien wollte für seine Staatsangehörigen (belgische Aktionäre der in Kanada eingetragenen Barcelona Traction Company) diplomatischen Schutz ausüben. Der IGH verneinte: Aktivlegitimation hat der Heimatstaat der Gesellschaft (Inkorporationsstaat = Kanada), nicht der Heimatstaat der Aktionäre. Aktionäre ≠ Gesellschaft. Art. 34 IGH-Statut: Nur Staaten können Parteien vor dem IGH sein; Belgiens Legitimation fehlt.

Erga-omnes-Verpflichtungen: Bahnbrechendes Diktum — Das Gericht unterschied: (a) bilaterale Schutzpflichten zwischen Staaten; (b) Verpflichtungen erga omnes = gegenüber der gesamten Staatengemeinschaft (z.B. Verbot von Aggression, Völkermord, Apartheid, Sklaverei). Bei erga-omnes-Verletzungen ist jeder Staat zur Geltendmachung berechtigt. Heimatstaat Gesellschaft (Kanada) war zuständig.

Normen: Art. 34 IGH-Statut (Parteifähigkeit, Aktivlegitimation); ILC-Artikel Staatenverantwortlichkeit Art. 48 (erga omnes).

Sachverhalt: Die in Kanada eingetragene Barcelona Traction Company betrieb Elektrizitätswerke in Spanien, befand sich aber vorwiegend im Eigentum belgischer Aktionäre. Spanien brachte das Unternehmen durch Maßnahmen in Konkurs. Belgien klagte für seine Staatsangehörigen (als Aktionäre) gegen Spanien.

Bedeutung: Eckpfeiler des diplomatischen Schutzes und der erga-omnes-Doktrin.
""",

"steckbrief_igh_atomwaffen_gutachten": """IGH, Gutachten vom 08.07.1996 — Legalität von Atomwaffen (Nuclear Weapons Advisory Opinion)

Ergebnis: Einsatz oder Androhung von Atomwaffen ist grundsätzlich unvereinbar mit humanitärem Völkerrecht. Kein explizites allgemeines Verbot, aber Unterscheidungsgebot und Verhältnismäßigkeit kaum einzuhalten. Pflicht zur Abrüstung nach NVV (Nichtverbreitungsvertrag).

Humanitäres Völkerrecht: Atomwaffen verletzen regelmäßig zwei Kerngebote:
1. Unterscheidungsgebot (distinction): Atomwaffen können nicht zwischen Kombattanten und Zivilbevölkerung unterscheiden — Verstoß gegen humanitäres Völkerrecht.
2. Verhältnismäßigkeit (proportionality): Atomwaffe überschreitet militärisches Ziel in aller Regel massiv — Verhältnismäßigkeit kaum gewährbar.
3. Verbot unnötigen Leidens — radioaktiver Fallout als unnötiges Leiden.

Gewaltverbot: Art. 2 Nr. 4 UN-Charta verbietet Androhung und Einsatz von Gewalt. Art. 51 UN-Charta: Selbstverteidigung als Ausnahme — auch hier gelten humanitäres Völkerrecht und Verhältnismäßigkeit. Ausnahme offen: In extremem Selbstverteidigungsfall (Überlebensfall eines Staates) hat der IGH 1996 die Rechtslage nicht abschließend beurteilt (Non liquet).

NVV (Nichtverbreitung): Art. VI NVV — Alle Vertragsstaaten müssen in gutem Glauben Abrüstungsverhandlungen führen. Gutachten 1996 bekräftigt diese Pflicht. Weiterentwicklung: TPNW (Atomwaffenverbotsvertrag 2021).

Sachverhalt: UN-Generalversammlung bat den IGH 1994 um Gutachten zur Frage: Ist der Einsatz oder die Androhung von Atomwaffen nach dem Völkerrecht erlaubt?
""",

"steckbrief_igh_kosovo_gutachten": """IGH, Gutachten vom 22.07.2010 — Kosovo-Unabhängigkeitserklärung

Ergebnis: Die einseitige Unabhängigkeitserklärung Kosovos (17.02.2008) verletzt das allgemeine Völkerrecht nicht. Das Völkerrecht enthält kein generelles Verbot einseitiger Unabhängigkeitserklärungen. Offen gelassen: Ob ein Recht auf externe Selbstbestimmung (Sezession) besteht.

Selbstbestimmungsrecht der Völker: Art. 1 UN-Charta (Selbstbestimmung als Ziel der UN); Art. 55 UN-Charta; IPBPR Art. 1; IPWSKR Art. 1. Das Selbstbestimmungsrecht gilt primär intern (demokratische Teilhabe). Externes Selbstbestimmungsrecht / Sezession: nur in Ausnahmefällen (Kolonialfall, schwere Unterdrückung — remedial secession); der IGH ließ die Frage offen.

Territoriale Integrität: Art. 2 Nr. 1 UN-Charta (Souveränität, territoriale Integrität). Das Prinzip schützt Staaten vor anderen Staaten, gilt aber nur eingeschränkt gegenüber eigenen Bevölkerungen bei Selbstbestimmung. Die Unabhängigkeitserklärung Kosovos richtete sich nicht gegen einen anderen Staat, sondern war ein innenpolitischer Akt.

SR-Resolution 1244 (1999): Verwaltet Kosovo nach NATO-Intervention 1999. Enthält kein Verbot einer späteren Unabhängigkeitserklärung, nach Ansicht des Gerichts.

Normen: Art. 1 UN-Charta (Selbstbestimmung); Art. 2 Nr. 1 UN-Charta; SR-Res. 1244; Deklaration 2625 (freundschaftliche Beziehungen); IPBPR Art. 1.

Bedeutung: Kein Präzedenzfall für allgemeines Sezessionsrecht; Klarstellung dass einseitige Unabhängigkeitserklärungen als solche nicht verboten sind. Politisch umstritten; bis 2024 über 100 Anerkennungen.

Sachverhalt: Kosovo erklärte am 17.02.2008 einseitig die Unabhängigkeit von Serbien. Serbien und andere Staaten bestritten die Rechtmäßigkeit; die UN-Generalversammlung bat den IGH um ein Gutachten 2010.
""",

"steckbrief_emrk_individualbeschwerde_verfahren": """EMRK — Individualbeschwerdeverfahren (Art. 34 und Art. 35 EMRK)

Art. 34 EMRK (Individualbeschwerde): „Der Gerichtshof kann von jeder natürlichen Person, nichtstaatlichen Organisation oder Personengruppe Beschwerden entgegennehmen." Beschwerdeberechtigt: natürliche Personen, NGOs, Personengruppen. Nicht: Staaten (→ Art. 33 Staatenbeschwerde).

Opfereigenschaft (Art. 34): Unmittelbarer Opferstatus (direct victim) nötig — kein Popularklagerecht. Mittelbares Opfer (Angehörige) bei eigenem Zugangshindernis möglich. Potenzielles Opfer bei unmittelbarer Bedrohung (streitig).

Art. 35 EMRK — Zulässigkeitsvoraussetzungen:
1. Erschöpfung innerstaatlicher Rechtsmittel (alle effektiven, zugänglichen Mittel).
2. Frist: 4 Monate nach endgültiger innerstaatlicher Entscheidung (seit Protokoll 15, 2022; vorher 6 Monate).
3. Keine Anonymität; kein Missbrauch; keine identische frühere Beschwerde; keine offensichtliche Unzulässigkeit; erhebliche Benachteiligung erforderlich (Bagatellgrenze, Art. 35 Abs. 3 lit. b).

Zuständigkeit (Art. 1 EMRK): Nicht nur territorial — Hoheitsgewalt (jurisdiction) auch bei effective control über fremdes Gebiet oder einzelne Personen (Loizidou v. Türkei 1996: Nordzypern; Al-Skeini v. UK 2011: Irak).

Verfahren: Einzelrichter (offensichtlich unzulässig), Kammer (7 Richter, Regelfall), Große Kammer (17 Richter, schwerwiegende Rechtsfragen). Güterliche Einigung (Art. 39), gerechte Entschädigung (Art. 41).

Leitfälle: Loizidou v. Türkei 1996 (Art. 34, Opfereigenschaft, Jurisdiktion), Handyside v. UK 1976 (Art. 35, Margin of Appreciation), Öcalan v. Türkei 2005 (Art. 3/6 EMRK, faires Verfahren).
""",
}

def embed_text(model, text):
    return model.encode([text], show_progress_bar=False).tolist()[0]

print("Loading model …")
model = SentenceTransformer(MODEL_NAME)

print("Connecting to ChromaDB …")
client = chromadb.PersistentClient(CHROMADB_PATH)
col    = client.get_collection(COLLECTION)

ids_to_update = list(REWRITES.keys())
res = col.get(ids=ids_to_update, include=['metadatas'])

updated_ids, updated_docs, updated_metas, updated_embs = [], [], [], []
for id_, meta in zip(res['ids'], res['metadatas']):
    new_doc = REWRITES[id_].strip()
    # Verify first 800 chars
    first800 = new_doc[:800]
    print(f"\n{id_} — first 800 chars:")
    print(first800)
    print(f"  → Length: {len(new_doc)} chars, first800: {len(first800)} chars")

    updated_ids.append(id_)
    updated_docs.append(new_doc)
    updated_metas.append(meta)
    updated_embs.append(embed_text(model, new_doc))

col.update(ids=updated_ids, documents=updated_docs,
           metadatas=updated_metas, embeddings=updated_embs)
print(f"\n✓ {len(updated_ids)} Steckbriefe neu geschrieben und re-embedded.")
print(f"  Collection: {col.count()} docs")
