#!/usr/bin/env python3
"""
add_leitfall_steckbriefe.py — Fügt Leitfall-Steckbriefe zu ChromaDB hinzu.
Macht bekannte Urteilsnamen (Lüth, Schrems, Van Gend en Loos …) per Semantik auffindbar.

Aufruf: venv/bin/python add_leitfall_steckbriefe.py [--dry-run] [--skill grundrechte]
"""
import argparse
import sys
from pathlib import Path

CHROMADB_PATH = "/opt/openlex-mvp-v2/chromadb"
MODEL_NAME    = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"

# ── Steckbrief-Texte ──────────────────────────────────────────────────────────
STECKBRIEFE = [

  # ── GRUNDRECHTE / BVerfG ────────────────────────────────────────────────────
  {"id": "steckbrief_lueth", "skill": "grundrechte", "text": """
Lüth-Urteil (BVerfGE 7, 198) — Bundesverfassungsgericht, 15. Januar 1958, 1 BvR 400/51

Erich Lüth, Hamburger Senatspressesprecher, rief 1950 öffentlich zum Boykott des Films
"Unsterbliche Geliebte" des NS-Regisseurs Veit Harlan auf. Das Landgericht Hamburg untersagte
den Boykottaufruf wegen sittenwidriger Schädigung (§ 826 BGB). Das BVerfG hob dies auf.

Leitsätze:
1. Die Grundrechte sind nicht nur Abwehrrechte gegen den Staat, sondern begründen eine
   objektive Werteordnung, die alle Bereiche des Rechts durchdringt — auch das Privatrecht.
   Dies nennt man mittelbare Drittwirkung der Grundrechte.
2. Zivilgerichte müssen bei der Auslegung privatrechtlicher Generalklauseln (§ 826, § 242 BGB)
   die Grundrechte als Auslegungsmaßstab berücksichtigen (Ausstrahlungswirkung der Grundrechte).
3. Die Meinungsfreiheit (Art. 5 Abs. 1 GG) ist eines der vornehmsten Grundrechte in einem
   freiheitlich-demokratischen Staatswesen.
4. Abwägung zwischen Meinungsfreiheit und Persönlichkeitsrecht muss grundrechtskonform erfolgen.

Bedeutung: Das Lüth-Urteil ist Grundlage der Lehre von der mittelbaren Drittwirkung der
Grundrechte und der Ausstrahlungswirkung des GG auf alle Rechtsbereiche. Pflichtlektüre im
deutschen Jurastudium. BVerfGE 7, 198 ff. / 1 BvR 400/51.
""".strip()},

  {"id": "steckbrief_volkszaehlung", "skill": "grundrechte", "text": """
Volkszählungsurteil (BVerfGE 65, 1) — Bundesverfassungsgericht, 15. Dezember 1983,
1 BvR 209/83 u.a.

Anlass: Das Volkszählungsgesetz 1983 sah eine umfassende Erhebung personenbezogener Daten vor.
Zahlreiche Bürger erhoben Verfassungsbeschwerde.

Leitsätze:
1. Das BVerfG leitet aus Art. 2 Abs. 1 i.V.m. Art. 1 Abs. 1 GG ein Grundrecht auf
   informationelle Selbstbestimmung ab.
2. Jeder Mensch hat das Recht, selbst über die Preisgabe und Verwendung seiner persönlichen
   Daten zu entscheiden.
3. Der Einzelne darf nicht zum bloßen Objekt staatlicher Datenverarbeitung werden.
4. Einschränkungen bedürfen einer klaren gesetzlichen Grundlage; Datensparsamkeit und
   Zweckbindung sind verfassungsrechtliche Gebote.

Bedeutung: Ursprung des deutschen Datenschutzrechts und verfassungsrechtliche Grundlage der
DSGVO und des BDSG. Das Recht auf informationelle Selbstbestimmung ist seitdem ein
Grundrecht im deutschen Verfassungsrecht. Volkszählung, Mikrozensus, Datenschutz, BVerfGE 65,1.
""".strip()},

  {"id": "steckbrief_elfes", "skill": "grundrechte", "text": """
Elfes-Urteil (BVerfGE 6, 32) — Bundesverfassungsgericht, 16. Januar 1957, 1 BvR 253/56
(Elfes-Entscheidung, Elfes-Fall, allgemeine Handlungsfreiheit)

Sachverhalt: Wilhelm Elfes (CDU-Politiker, Bürgermeister von Krefeld) beantragte einen
Reisepass für Auslandsreisen zu Friedenskongressen. Die Behörde verweigerte ihm den Pass
mit Hinweis auf seine Kontakte zu kommunistisch beeinflussten Organisationen. Elfes sah
seine Ausreisefreiheit verletzt und erhob Verfassungsbeschwerde zum BVerfG.

Leitsätze des Elfes-Urteils:
1. Art. 2 Abs. 1 GG (allgemeine Handlungsfreiheit / allgemeines Freiheitsrecht) ist das
   umfassende Auffanggrundrecht: Es schützt jede menschliche Handlung und Verhaltensweise,
   die nicht durch ein spezielleres Grundrecht (Art. 3–17 GG) erfasst wird. Ausreise und
   Reisefreiheit fallen daher in den Schutzbereich von Art. 2 Abs. 1 GG.
2. Der Begriff "verfassungsmäßige Ordnung" in der Schranke des Art. 2 Abs. 1 GG meint die
   Gesamtheit aller formell und materiell verfassungsgemäßen Rechtsnormen (weite Auslegung).
3. Als Auffanggrundrecht gilt Art. 2 Abs. 1 GG subsidiär überall, wo speziellere Grundrechte
   nicht eingreifen. Jeder staatliche Eingriff in die allgemeine Handlungsfreiheit bedarf
   einer verfassungsgemäßen gesetzlichen Grundlage.

Dogmatische Bedeutung: Das Elfes-Urteil ist Ausgangspunkt der ständigen BVerfG-Rechtsprechung
zur allgemeinen Handlungsfreiheit als Auffanggrundrecht. Jede staatliche Beschränkung
menschlicher Freiheit — auch banale Alltagshandlungen wie Reiten (Reiten-im-Walde-Fall),
Reisen oder die Nutzung von Produkten — wird an Art. 2 Abs. 1 GG gemessen.
Elfes-Urteil, Reisepass verweigert, Ausreisefreiheit, allgemeines Freiheitsrecht,
BVerfGE 6, 32, 1 BvR 253/56, Art. 2 Abs. 1 GG Auffanggrundrecht.
""".strip()},

  {"id": "steckbrief_apotheker", "skill": "grundrechte", "text": """
Apothekenurteil / Apothekerurteil (BVerfGE 7, 377) — Bundesverfassungsgericht,
11. Juni 1958, 1 BvR 596/56

Das bayerische Apothekengesetz schränkte die Zulassung neuer Apotheken durch eine
Bedürfnisprüfung stark ein. Das BVerfG entwickelte die Drei-Stufen-Theorie zu Art. 12 GG.

Drei-Stufen-Theorie (Berufsfreiheit, Art. 12 Abs. 1 GG):
Stufe 1 — Berufsausübungsregelungen: Eingriffe zulässig bei vernünftigen Gemeinwohlgründen.
Stufe 2 — Subjektive Zulassungsvoraussetzungen (persönliche Eigenschaften): Eingriffe zulässig
  zum Schutz überragender Gemeinschaftsgüter.
Stufe 3 — Objektive Zulassungsvoraussetzungen (unabhängig von Person): Eingriffe nur zur
  Abwehr nachweisbarer schwerwiegender Gefahren für überragend wichtige Gemeinschaftsgüter.
Je stärker der Eingriff in die Berufsfreiheit, desto gewichtigere Rechtfertigung erforderlich.

Bedeutung: Standardprüfungsschema für Eingriffe in Art. 12 GG (Berufsfreiheit).
Drei-Stufen-Theorie, Apothekenurteil, Bedürfnisprüfung, BVerfGE 7, 377.
""".strip()},

  {"id": "steckbrief_mephisto", "skill": "grundrechte", "text": """
Mephisto-Urteil (BVerfGE 30, 173) — Bundesverfassungsgericht, 24. Februar 1971,
1 BvR 435/68

Klaus Manns Roman "Mephisto" (1936) basierte erkennbar auf dem NS-Kollaborateur und
Schauspieler Gustaf Gründgens. Der BGH hatte die Verbreitung des Romans verboten.

Leitsätze:
1. Kunstfreiheit (Art. 5 Abs. 3 GG) ist vorbehaltlos gewährleistet, aber durch
   kollidierendes Verfassungsrecht einschränkbar (insbesondere Menschenwürde, Art. 1 GG).
2. Je enger die Anlehnung eines Kunstwerks an eine erkennbare reale Person, desto mehr
   tritt Kunstfreiheit hinter das Persönlichkeitsrecht zurück.
3. Postmortaler Persönlichkeitsschutz: Auch Verstorbene genießen Menschenwürdeschutz;
   nahe Angehörige können ihn geltend machen.

Bedeutung: Leitfall zur Abwägung von Kunstfreiheit gegen Persönlichkeitsrecht und
Menschenwürde. Grundlage für postmortalen Persönlichkeitsschutz. Vorbehaltlose Grundrechte,
Schranken aus kollidierendem Verfassungsrecht. BVerfGE 30, 173.
""".strip()},

  {"id": "steckbrief_solange", "skill": "grundrechte", "text": """
Solange I (BVerfGE 37, 271, 1974) und Solange II (BVerfGE 73, 339, 1986)
— Bundesverfassungsgericht

Solange I (2 BvL 52/71, 29. Mai 1974):
Solange der EG ein dem GG gleichwertiger Grundrechtsschutz fehlt, überprüft das BVerfG
EU-Sekundärrecht an deutschen Grundrechten (Reservekompetenz).

Solange II (2 BvR 197/83, 22. Oktober 1986):
Da die EU mittlerweile einen dem GG entsprechenden Grundrechtsschutz entwickelt hat,
verzichtet das BVerfG auf Überprüfung von EU-Recht, solange dieser Schutz gewährleistet ist.

Leitsätze:
1. Das BVerfG behält eine Identitätskontrolle vor: Ultra-vires-Akte der EU und Verletzungen
   der Verfassungsidentität (Art. 79 Abs. 3 GG) werden weiterhin geprüft.
2. Kooperationsverhältnis zwischen BVerfG und EuGH (kein Überordnungsverhältnis).
3. Ergänzt durch Lissabon-Urteil (BVerfGE 123, 267) und PSPP-Urteil (2020).

Bedeutung: Grundlage des Verhältnisses zwischen BVerfG und EuGH. Solange-Klausel,
Identitätskontrolle, Anwendungsvorrang EU-Recht mit nationalen Grenzen.
""".strip()},

  {"id": "steckbrief_lissabon", "skill": "grundrechte", "text": """
Lissabon-Urteil (BVerfGE 123, 267) — Bundesverfassungsgericht, 30. Juni 2009,
2 BvE 2/08 u.a. (Lissabon-Urteil des BVerfG, Lissabon-Entscheidung)

Anlass: Mehrere Verfassungsbeschwerden und Organstreitverfahren gegen das Zustimmungsgesetz
zum Vertrag von Lissabon (EU-Reformvertrag, 2007). Beschwerdeführer u.a. Peter Gauweiler
(CSU) und die Fraktion der Linken. Das BVerfG prüfte, ob die europäische Integration
noch mit dem Demokratieprinzip, dem Grundsatz der Volkssouveränität und der
Verfassungsidentität des Grundgesetzes vereinbar ist.

Leitsätze des Lissabon-Urteils:
1. Der Vertrag von Lissabon ist mit dem Grundgesetz vereinbar, aber das Begleitgesetz
   muss die Integrationsverantwortung von Bundestag und Bundesrat substantiell stärken
   (Integrationsverantwortungsgesetz, Parlamentsbeteiligungsgesetz).
2. Verfassungsidentität und Ewigkeitsklausel (Art. 79 Abs. 3 GG): Unübertragbare
   Kernbereiche staatlicher Souveränität — Menschenwürde, Demokratieprinzip, Rechtsstaat,
   Bundesstaatlichkeit, Sozialstaatsprinzip — sind der EU-Integration dauerhaft entzogen.
   Das BVerfG prüft deren Verletzung durch Identitätskontrolle.
3. Ultra-vires-Kontrolle: Das BVerfG behält die Kompetenz, EU-Rechtsakte zu prüfen, die
   offensichtlich außerhalb der übertragenen Kompetenzen liegen (ausbrechende Rechtsakte,
   Ultra-vires-Akte). Angewendet im PSPP-Urteil (2020) gegen die EZB.
4. Demokratieprinzip: Nationale Parlamente müssen hinreichend eingebunden bleiben.
   Automatische Kompetenzausdehnung ohne Parlamentszustimmung ("Brückenklauseln") ist
   unzulässig (keine Blankovollmacht für EU-Vertragsänderungen).
5. Integrationsgrenze: Deutschland kann grundsätzlich in einem europäischen Bundesstaat
   aufgehen — aber nur durch ein neues, durch Volksabstimmung legitimiertes Grundgesetz.

Bedeutung: Das Lissabon-Urteil ist neben Maastricht-Urteil (BVerfGE 89, 155) und dem
PSPP-Urteil (2 BvR 859/15, 2020) das wichtigste BVerfG-Urteil zur Europäischen
Integration. Es sichert die Verfassungsidentität Deutschlands und definiert die Grenzen
des Integrationsprogramms. BVerfGE 123, 267, Lissabon, Vertrag von Lissabon,
2 BvE 2/08, Verfassungsidentität, Ultra-vires, Identitätskontrolle, Integrationsverantwortung.
""".strip()},

  {"id": "steckbrief_spiegel", "skill": "grundrechte", "text": """
Spiegel-Urteil (BVerfGE 20, 162) — Bundesverfassungsgericht, 5. August 1966,
1 BvR 586/62 u.a. (Spiegel-Affäre)

Anlass: Razzia in Spiegel-Redaktion und Verhaftung von Rudolf Augstein wegen angeblichen
Landesverrats (Veröffentlichung über Bundeswehr-Manöver "Fallex 62").

Leitsätze:
1. Die Pressefreiheit (Art. 5 Abs. 1 S. 2 GG) schützt Presse als Institution in einem
   freiheitlich-demokratischen Staatswesen (institutionelle Garantie).
2. Eine freie, nicht von der öffentlichen Gewalt gelenkte Presse ist für den demokratischen
   Staat unentbehrlich.
3. Der Landesverratsverdacht allein rechtfertigt nicht unverhältnismäßige Eingriffe in die
   Pressefreiheit (Verhältnismäßigkeit).

Bedeutung: Grundsatzentscheidung zur Pressefreiheit als institutionelle Garantie.
Pressefreiheit, Spiegel-Affäre, Art. 5 GG, BVerfGE 20, 162.
""".strip()},

  {"id": "steckbrief_reiten_im_walde", "skill": "grundrechte", "text": """
Reiten im Walde (BVerfGE 80, 137) — Bundesverfassungsgericht, 6. Juni 1989,
1 BvR 921/85

Das hessische Waldgesetz untersagte das Reiten im Wald abseits besonders ausgewiesener
Wege. Der Beschwerdeführer sah seine allgemeine Handlungsfreiheit verletzt.

Leitsätze:
1. Art. 2 Abs. 1 GG (allgemeines Freiheitsrecht) schützt als Auffanggrundrecht auch das
   Reiten in der freien Natur — eine banale Alltagstätigkeit.
2. Eingriffe in Art. 2 Abs. 1 GG sind nur zulässig, wenn sie mit der verfassungsmäßigen
   Ordnung vereinbar sind (formelle und materielle Verfassungsmäßigkeit).
3. Das Waldgesetz ist verhältnismäßig — Schutz des Waldes ist legitimes Ziel.

Bedeutung: Illustriert, dass Art. 2 Abs. 1 GG wirklich jede Verhaltensform erfasst
(Auffanggrundrecht). Allgemeine Handlungsfreiheit, Reiten im Wald, BVerfGE 80, 137.
""".strip()},

  {"id": "steckbrief_herrenreiter", "skill": "grundrechte", "text": """
Herrenreiterfall (BGHZ 26, 349) — Bundesgerichtshof, 14. Februar 1958, I ZR 151/56

Ein bekannter Reiter wurde ohne seine Zustimmung in einer Werbeanzeige für ein
Potenzmittel abgebildet.

Leitsätze:
1. Das allgemeine Persönlichkeitsrecht (Art. 2 Abs. 1 i.V.m. Art. 1 Abs. 1 GG) ist ein
   sonstiges Recht i.S.d. § 823 Abs. 1 BGB.
2. Verletzung des Persönlichkeitsrechts durch ungenehmigte kommerzielle Nutzung des Bildnisses
   kann zu Schadensersatz führen.
3. Geldentschädigung (Schmerzensgeld) auch ohne Vermögensschaden möglich bei schwerwiegender
   Verletzung des Persönlichkeitsrechts.

Bedeutung: Begründet die zivilrechtliche Geldentschädigung für Persönlichkeitsrechtsverletzungen.
Allgemeines Persönlichkeitsrecht, § 823 BGB, Recht am eigenen Bild. BGHZ 26, 349.
""".strip()},

  # ── EUROPARECHT / EuGH ──────────────────────────────────────────────────────
  {"id": "steckbrief_vangendenloos", "skill": "europarecht", "text": """
Van Gend en Loos (EuGH Rs. 26/62) — Europäischer Gerichtshof, 5. Februar 1963

NV Algemene Transport- en Expeditie Onderneming van Gend en Loos gegen Niederländische
Finanzverwaltung. Das niederländische Transportunternehmen Van Gend en Loos importierte
Kunstharz aus Deutschland. Die Niederlande hatte nach EWG-Vertragsbeginn einen Zoll erhöht —
entgegen Art. 12 EWGV (heute Art. 30 AEUV).

Leitsätze — Unmittelbare Wirkung des Gemeinschaftsrechts:
1. Das EWG-Recht ist eine neue Rechtsordnung des Völkerrechts, zu deren Gunsten die Staaten
   ihre Souveränitätsrechte eingeschränkt haben.
2. Das Gemeinschaftsrecht kann unmittelbare Wirkung entfalten und dem Einzelnen Rechte
   verleihen, die nationale Gerichte zu schützen haben (Direktwirkung / unmittelbare Wirkung).
3. Voraussetzungen: Die Norm muss klar, bestimmt, unbedingt sein und keiner weiteren
   Durchführungsmaßnahme bedürfen.

Bedeutung: Van Gend en Loos ist eine der bedeutendsten EuGH-Entscheidungen überhaupt.
Zusammen mit Costa/ENEL (1964) begründet es die Grundpfeiler des EU-Rechtssystems:
Direktwirkung und Anwendungsvorrang. EuGH 26/62, Unmittelbare Wirkung, Direktwirkung.
""".strip()},

  {"id": "steckbrief_costa_enel", "skill": "europarecht", "text": """
Costa/ENEL (EuGH Rs. 6/64) — Europäischer Gerichtshof, 15. Juli 1964

Flaminio Costa gegen ENEL (Ente Nazionale Energia Elettrica). Nach Verstaatlichung des
italienischen Elektrizitätssektors weigerte sich Costa, seine Stromrechnung zu zahlen, und
berief sich auf Verstoß gegen EWG-Recht.

Leitsätze — Vorrang des Gemeinschaftsrechts:
1. Das EWG-Recht ist in die Rechtsordnungen der Mitgliedstaaten integriert.
2. Die Mitgliedstaaten haben durch EWG-Beitritt dauerhaft Souveränitätsrechte eingeschränkt.
3. Das Gemeinschaftsrecht hat Vorrang (Anwendungsvorrang) vor dem nationalen Recht,
   einschließlich späterer nationaler Gesetze.
4. Nationale Gerichte müssen entgegenstehendes nationales Recht unangewendet lassen.

Bedeutung: Costa/ENEL begründet den Anwendungsvorrang des EU-Rechts. Nationaler
Gesetzgeber kann EU-Recht nicht durch spätere Gesetze außer Kraft setzen.
EuGH C-6/64, Anwendungsvorrang, Vorrang des Unionsrechts.
""".strip()},

  {"id": "steckbrief_francovich", "skill": "europarecht", "text": """
Francovich und Bonifaci (EuGH Rs. C-6/90 und C-9/90) — EuGH, 19. November 1991

Italien hatte die Insolvenzschutz-Richtlinie 80/987/EWG nicht umgesetzt. Arbeitnehmer
insolventer Unternehmen erhielten keine Lohngarantie und klagten gegen den Staat.

Leitsätze — Staatshaftung / Mitgliedstaatshaftung:
1. Mitgliedstaaten haften gegenüber Einzelnen für Schäden durch Verletzung des EU-Rechts
   (Francovich-Doktrin / europarechtliche Staatshaftung).
2. Voraussetzungen: (a) Verletzte Norm verleiht dem Einzelnen Rechte; (b) Verstoß ist
   hinreichend qualifiziert; (c) Kausalzusammenhang zwischen Verstoß und Schaden.
3. Mitgliedstaaten können sich nicht auf eigene Nichtimplementierung berufen.

Bedeutung: Begründet die Staatshaftung im Europarecht. Ergänzt durch Brasserie du Pêcheur
(C-46/93). Zentrales Durchsetzungsinstrument des EU-Rechts. EuGH C-6/90, Staatshaftung.
""".strip()},

  {"id": "steckbrief_cassis", "skill": "europarecht", "text": """
Cassis de Dijon (EuGH Rs. 120/78) — Europäischer Gerichtshof, 20. Februar 1979

Rewe-Zentral AG gegen Bundesmonopolverwaltung für Branntwein. Die Einfuhr des
französischen Likörs "Cassis de Dijon" (15-20% Alkohol) wurde verboten, weil er
den deutschen Mindestalkohol für Likör (25%) nicht erreichte.

Leitsätze — Warenverkehrsfreiheit, gegenseitige Anerkennung:
1. Nationale Vorschriften, die als mengenmäßige Einfuhrbeschränkung wirken (Art. 34 AEUV),
   sind nur zulässig, wenn sie zwingenden Erfordernissen des Allgemeininteresses dienen.
2. Grundsatz der gegenseitigen Anerkennung: Waren, die in einem Mitgliedstaat rechtmäßig
   hergestellt und in den Verkehr gebracht wurden, dürfen grundsätzlich EU-weit vertrieben werden
   (country of origin principle).
3. Zwingende Erfordernisse: Verbraucherschutz, Lauterkeit, Umweltschutz können
   Beschränkungen rechtfertigen (Cassis-Rechtfertigungsgründe).

Bedeutung: Revolutionierte den EU-Binnenmarkt. Grundsatz der gegenseitigen Anerkennung
ermöglicht Binnenmarkt ohne vollständige Harmonisierung. EuGH C-120/78, Cassis-Formel.
""".strip()},

  {"id": "steckbrief_bosman", "skill": "europarecht", "text": """
Bosman (EuGH Rs. C-415/93) — Europäischer Gerichtshof, 15. Dezember 1995

Jean-Marc Bosman, belgischer Fußballprofi, wollte nach Vertragsende zum FC Dunkerque
(Frankreich) wechseln. RFC Lüttich blockierte mit überhöhter Ablöse. UEFA-Regeln sahen
Ablösegebühren auch nach Vertragsende und Ausländerbeschränkungen für EU-Spieler vor.

Leitsätze:
1. Die Freizügigkeit der Arbeitnehmer (Art. 45 AEUV) gilt für Berufssportler.
2. Transfergebühren nach Vertragsablauf beschränken die Freizügigkeit unzulässig.
3. Ausländerklauseln (Begrenzung EU-Spieler pro Mannschaft) verstoßen gegen das
   Diskriminierungsverbot wegen der Staatsangehörigkeit.

Bedeutung: Revolutionierte den europäischen Fußball — Bosman-Ablöse (ablösefreier
Wechsel nach Vertragsende), Abschaffung der Ausländerklausel für EU-Spieler.
Grundfreiheiten im Profisport. EuGH C-415/93.
""".strip()},

  {"id": "steckbrief_keck", "skill": "europarecht", "text": """
Keck und Mithouard (EuGH Rs. C-267/91, C-268/91) — EuGH, 24. November 1993

Keck und Mithouard wurden wegen Verstoßes gegen ein französisches Gesetz verurteilt,
das den Weiterverkauf von Waren unter Einstandspreis (Verkauf mit Verlust) verbot.

Leitsätze — Verkaufsmodalitäten:
1. Keck-Formel: Nationale Regelungen über Verkaufsmodalitäten (wann, wo, von wem, zu welchem
   Preis Waren verkauft werden dürfen) fallen nicht unter Art. 34 AEUV (Warenverkehrsfreiheit),
   wenn sie für alle Wirtschaftsteilnehmer im nationalen Hoheitsgebiet gelten und den
   tatsächlichen Zugang zum Markt nicht stärker beeinträchtigen als für inländische Waren.
2. Abgrenzung Produktanforderungen (fallen unter Art. 34 AEUV) vs. Verkaufsmodalitäten
   (fallen grundsätzlich nicht darunter, Keck-Ausnahme).

Bedeutung: Schränkt die Weite von Cassis de Dijon ein; verhindert Missbrauch der
Warenverkehrsfreiheit bei bloßen Verkaufsmodalitäten. EuGH C-267/91, Keck-Formel.
""".strip()},

  {"id": "steckbrief_mangold", "skill": "europarecht", "text": """
Mangold (EuGH Rs. C-144/04) — Europäischer Gerichtshof, 22. November 2005

Werner Mangold, 56 Jahre, wurde befristet eingestellt. Das deutsche Recht erlaubte
unbegrenzte Befristung für Arbeitnehmer über 52 Jahre ohne sachlichen Grund.

Leitsätze:
1. Das Verbot der Altersdiskriminierung ist ein allgemeiner Grundsatz des Unionsrechts,
   der unabhängig von der Umsetzungsfrist der Gleichbehandlungsrahmenrichtlinie gilt.
2. Nationale Gerichte müssen EU-rechtswidrige nationale Vorschriften unangewendet lassen,
   auch wenn die Umsetzungsfrist noch nicht abgelaufen ist.
3. Erga-omnes-Wirkung: Allgemeine Grundsätze des EU-Rechts wirken horizontal.

Bedeutung: Mangold ist umstritten — BVerfG und einige Stimmen kritisierten die extensive
Ableitung von Grundsätzen ohne ausdrückliche Rechtsgrundlage (EuGH C-144/04).
Altersdiskriminierung, allgemeiner Grundsatz Unionsrecht.
""".strip()},

  {"id": "steckbrief_plaumann", "skill": "europarecht", "text": """
Plaumann & Co. (EuGH Rs. 25/62) — Europäischer Gerichtshof, 15. Juli 1963

Plaumann, ein Klementinen-Importeur, klagte auf Nichtigerklärung einer
Kommissionsentscheidung, die Zollbefreiungen verweigerte.

Leitsätze — Plaumann-Formel (Zulässigkeit der Nichtigkeitsklage, Art. 263 AEUV):
1. Eine natürliche oder juristische Person ist nur dann individuell betroffen (Art. 263
   Abs. 4 AEUV), wenn eine Entscheidung sie wegen bestimmter persönlicher Eigenschaften oder
   besonderer Umstände berührt, die sie aus dem Kreis aller übrigen Personen herausheben.
2. Wer als Mitglied einer offenen Gruppe (z.B. alle Klementinen-Importeure) betroffen ist,
   ist nicht individuell betroffen — Klage unzulässig.

Bedeutung: Die Plaumann-Formel begrenzt den Zugang Privater zum EuGH erheblich.
Stark kritisiert als zu restriktiv. EuGH C-25/62, individuelle Betroffenheit, Nichtigkeitsklage.
""".strip()},

  # ── DATENSCHUTZ ─────────────────────────────────────────────────────────────
  {"id": "steckbrief_schrems", "skill": "datenschutz", "text": """
Schrems I (EuGH C-362/14, 6. Oktober 2015) und Schrems II (EuGH C-311/18, 16. Juli 2020)
— Europäischer Gerichtshof, Datentransfer USA

Schrems I: Max Schrems beanstandete, dass Facebook Irland seine Daten in die USA übermittelt,
wo sie dem NSA-Zugriff (PRISM-Programm) ausgesetzt sind. Der EuGH erklärte das Safe-Harbor-
Abkommen für ungültig.

Schrems II: Schrems focht den Nachfolger-Mechanismus EU-US Privacy Shield an. Der EuGH
erklärte auch diesen für ungültig, da er kein dem EU-Niveau gleichwertiges Schutzniveau bietet.

Leitsätze:
1. Drittländer müssen angemessenes Schutzniveau (Art. 45 DSGVO) bieten — der Sache nach
   gleichwertig mit EU-Datenschutz.
2. Standardvertragsklauseln (SCC) bleiben gültig, aber nur wenn im Einzelfall Schutzniveau
   nachweisbar ist (Transfer Impact Assessment erforderlich).
3. Aufsichtsbehörden müssen Transfers aussetzen, wenn Schutzniveau nicht gewährleistet.

Bedeutung: Wichtigste Urteile zum internationalen Datentransfer. Unternehmen müssen jeden
Datentransfer in Drittländer prüfen. Schrems, Safe Harbor, Privacy Shield, DSGVO Art. 44 ff.
""".strip()},

  {"id": "steckbrief_googlespain", "skill": "datenschutz", "text": """
Google Spain / Recht auf Vergessenwerden (EuGH C-131/12) — EuGH, 13. Mai 2014

Mario Costeja González wollte, dass Google Links zu alten Zeitungsartikeln über eine
Zwangsversteigerung seines Hauses aus den Suchergebnissen entfernt. Die Schulden waren
längst beglichen, die Informationen aber weiterhin abrufbar.

Leitsätze:
1. Suchmaschinenbetreiber sind datenschutzrechtlich Verantwortliche für die Verarbeitung
   personenbezogener Daten auf verlinkten Webseiten.
2. Es besteht ein Recht auf Löschung von Suchergebnissen ("Recht auf Vergessenwerden"),
   wenn Daten unzutreffend, unzulänglich, nicht mehr relevant oder übermäßig sind.
3. Abwägung mit Informationsfreiheit der Öffentlichkeit erforderlich; bei Personen des
   öffentlichen Lebens ist der Schutz schwächer.

Bedeutung: Grundlage für Art. 17 DSGVO (Recht auf Löschung). Google muss seitdem
Löschanträge für Suchergebnisse prüfen (Millionen eingegangen). EuGH C-131/12.
""".strip()},

  {"id": "steckbrief_planet49", "skill": "datenschutz", "text": """
Planet49 (EuGH C-673/17) — Europäischer Gerichtshof, 1. Oktober 2019

Planet49 veranstaltete ein Online-Gewinnspiel. Eines der Einwilligungs-Checkboxen für
Cookies und Werbung war vorab angekreuzt. Nutzer mussten aktiv abwählen.

Leitsätze:
1. Eine vorab angekreuzte Checkbox stellt keine wirksame Einwilligung (Consent) i.S.d.
   DSGVO und der ePrivacy-Richtlinie dar.
2. Einwilligung muss aktiv und freiwillig erfolgen (Opt-in, nicht Opt-out).
3. Information über Speicherdauer und Drittpartei-Zugang ist Voraussetzung für wirksame
   Einwilligung.

Bedeutung: Klärt die Cookie-Einwilligung nach DSGVO/ePrivacy. Vorangekreuzte Checkboxen
sind unzulässig. Opt-in-Pflicht für nicht technisch notwendige Cookies. EuGH C-673/17.
""".strip()},

  # ── STRAFRECHT / BGH ────────────────────────────────────────────────────────
  {"id": "steckbrief_lederspray", "skill": "strafrecht", "text": """
Ledersprayfall (BGH NJW 1990, 2560) — Bundesgerichtshof, 6. Juli 1990, 2 StR 549/89

Nach zahlreichen Gesundheitsschäden (Lungenschäden) durch ein Lederpflegespray wurden
Geschäftsführer und Verantwortliche wegen fahrlässiger Körperverletzung angeklagt.
Das Produkt wurde nicht rechtzeitig zurückgerufen.

Leitsätze:
1. Kausalität: Epidemiologischer Beweis genügt bei Massendelikten; kein Einzelnachweis
   für jeden Schadensfall erforderlich.
2. Garantenstellung von Unternehmensführern: Wer ein gefährliches Produkt in Verkehr bringt,
   hat eine Rückrufpflicht, wenn die Gefährlichkeit bekannt wird.
3. Kollegialhaftung: Jedes Mitglied eines Gremiums (z.B. Geschäftsführer), das an einer
   rechtswidrigen Entscheidung mitwirkt, ist strafrechtlich mitverantwortlich.

Bedeutung: Leitfall zur strafrechtlichen Produkthaftung, Garantenpflicht von
Unternehmensführern und Kollegialhaftung. BGH 2 StR 549/89, Lederspray.
""".strip()},

  {"id": "steckbrief_sirius", "skill": "strafrecht", "text": """
Sirius-Fall (BGH NStZ 1985, 24) — Bundesgerichtshof, 15. Oktober 1985, 4 StR 444/85

Ein Mann überredete sein Opfer, in einer Badewanne eine Haarlichtmaschine zu benutzen,
die er als Mittel zur "Seelenwanderung" ausgab — in Wirklichkeit plante er den Tod des
Opfers durch Stromschlag. Das Opfer überlebte durch Zufall.

Leitsätze — Mittelbare Täterschaft kraft Wissensherrschaft:
1. Mittelbare Täterschaft (§ 25 Abs. 1 Alt. 2 StGB): Wer einen anderen als vorsatzloses
   Werkzeug einsetzt (das Opfer kennt den tatsächlichen Gefahrplan nicht), ist mittelbarer Täter.
2. Tatherrschaft durch Wissensherrschaft: Der Hintermann hat die Tatherrschaft, weil er
   den entscheidenden Informationsvorsprung über die Tatumstände hat.
3. Tatbestandsirrtum des Werkzeugs: Das Opfer handelt ohne Vorsatz, da es die
   todbringende Natur der Handlung nicht kennt.

Bedeutung: Klassischer Schulfall zur mittelbaren Täterschaft durch Herbeiführung eines
vorsatzlosen Werkzeugs. § 25 Abs. 1 Alt. 2 StGB, Werkzeugirrtum, Sirius-Fall.
""".strip()},

  {"id": "steckbrief_weichensteller", "skill": "strafrecht", "text": """
Weichensteller-Fall (BGH NStZ 2004, 499) — Bundesgerichtshof

Ein Weichensteller stellte eine Weiche falsch und verursachte dadurch einen Zugunfall.
Streitfrage: Täterschaft oder Beihilfe, wenn der Weichensteller "nur" die Weiche stellt
und ein anderer (der Lokführer) die unmittelbare Ursache setzt.

Leitsätze — Abgrenzung Täterschaft/Beihilfe:
1. Täterschaft (§ 25 StGB) erfordert Tatherrschaft — der Täter hält das Ob und Wie des
   Tatablaufs in den Händen.
2. Beihilfe (§ 27 StGB): Unterstützungshandlung ohne eigene Tatherrschaft.
3. Subjektive Theorie (BGH-Rspr.): Täter will die Tat als eigene; Gehilfe nur als fremde.
4. Objektiv-subjektive Kombinationstheorie in der Praxis: Tatherrschaft + Täterwille.

Bedeutung: Standardfall zur Abgrenzung Täterschaft/Beihilfe. Tatherrschaftslehre,
subjektive Theorie des BGH, § 25/27 StGB.
""".strip()},

  {"id": "steckbrief_katzenkoenig", "skill": "strafrecht", "text": """
Katzenkönig-Fall (BGH NStZ 1988, 406) — Bundesgerichtshof, 15. September 1988,
4 StR 352/88

Eine Gruppe um einen "Führer" glaubte an Übernatürliches. Der Anführer überredete
Mitglieder, an der Tötung eines Mitglieds mitzuwirken — unter Vortäuschung okkulter Rituale
und falscher Überzeugung, das Opfer sei eine "Katze" (in Menschengestalt).

Leitsätze — Mittäterschaft trotz Irrtum über Handlungsherrschaft:
1. Mittäterschaft (§ 25 Abs. 2 StGB): Arbeitsteilige gemeinschaftliche Tatausführung
   mit gemeinsamem Tatentschluss.
2. Wer irrig glaubt, nur Werkzeug eines anderen zu sein (Handlungsherrschaft liegt
   tatsächlich bei ihm), ist dennoch Täter, wenn er objektiv die Tatherrschaft innehat.
3. Irrtum über die eigene Handlungsherrschaft schließt Täterschaft nicht aus.

Bedeutung: Schulfall zu Irrtum über Täterrolle und Mittäterschaft im Aberglaubenskontext.
§ 25 Abs. 2 StGB, Mittäterschaft, Katzenkönig.
""".strip()},

  {"id": "steckbrief_wittig", "skill": "strafrecht", "text": """
Wittig-Fall (BGH NJW 1984, 1397) — Bundesgerichtshof, 4. Juli 1984, 3 StR 96/84

Frau Wittig, Ärztin, fand ihren Patienten bewusstlos nach Suizidversuch vor. Obwohl
medizinische Hilfe noch möglich gewesen wäre, unterließ sie jede Rettungsmaßnahme,
da der Patient ihr früher seinen Suizidwillen mitgeteilt hatte.

Leitsätze — Garantenpflicht vs. Patientenautonomie:
1. Ärzte haben eine Garantenstellung gegenüber ihren Patienten (§ 13 StGB).
2. Ein früherer geäußerter Suizidwille des Patienten kann die Garantenpflicht
   des Arztes ausschließen oder einschränken, wenn er ernstlich und endgültig ist.
3. Abwägung: Patientenautonomie (Selbstbestimmungsrecht) vs. Lebensschutzpflicht.
4. BGH: Die Freisprechung war im Ergebnis vertretbar (sehr umstritten).

Bedeutung: Grundlegender Fall zu Garantenpflicht, Selbstbestimmungsrecht und
ärztlicher Verantwortung beim Suizid. § 13 StGB, Garantenstellung, unterlassene Hilfeleistung.
""".strip()},

  {"id": "steckbrief_roserosahl", "skill": "strafrecht", "text": """
Rose-Rosahl (Preußisches Obertribunal, 1858)

Historischer Schulfall zum error in persona und aberratio ictus (Irrtumskonstellationen
beim Vorsatzdelikt): Schlichting sollte im Auftrag von Rosahl den Moses Harnich töten.
Schlichting erschoss versehentlich den unbeteiligten Rose.

Leitsätze:
1. Error in persona: Irrtum des unmittelbaren Täters über die Identität des Opfers —
   für den Täter irrelevant (Person ≠ schutzwürdiges Interesse).
2. Aberratio ictus (Abirren des Angriffs): Für den Hintermann (Rosahl), der eine
   bestimmte Person als Ziel vorgegeben hatte, ist der Tod eines anderen kein
   "error in persona" — es fehlt an der Kausalität für die konkrete Tat.
3. Umstritten: Anstiftung zum Mord an Harnich + fahrlässige Tötung von Rose?

Bedeutung: Klassischer Klausurfall zu error in persona und aberratio ictus.
Strafrecht AT, Vorsatz, Irrtum, Kausalität, Rose-Rosahl.
""".strip()},

  # ── SACHENRECHT ─────────────────────────────────────────────────────────────
  {"id": "steckbrief_parkettstaebefall", "skill": "sachenrecht", "text": """
Parkettstäbefall (BGHZ 55, 176) — Bundesgerichtshof, 26. März 1971, V ZR 134/69

Ein Unternehmen verarbeitete Holzstäbe (Eigentum des Auftraggebers) zu Parkettstäben.
Streitfrage: Wer ist Eigentümer der verarbeiteten Parkettstäbe?

Leitsätze — § 950 BGB (Verarbeitung):
1. § 950 BGB: Wer durch Verarbeitung eine neue bewegliche Sache herstellt, erwirbt
   das Eigentum an der neuen Sache — auch wenn der Rohstoff einem anderen gehört.
2. Eine "neue Sache" entsteht, wenn das Endergebnis wesentlich über bloße Bearbeitung
   hinausgeht (wesentliche Wertschöpfung). Aus Holzstäben werden Parkettstäbe — neue Sache.
3. Wertvergleich: Verarbeitungswert darf nicht erheblich geringer sein als Stoffwert
   (§ 950 Abs. 1 S. 2 BGB).

Bedeutung: Standardfall zu § 950 BGB (Verarbeitungseigentum). Zusammen mit
Verbindung (§ 946 BGB) und Vermischung (§ 948 BGB) Grundlage des gesetzlichen
Eigentumserwerbsrechts. BGHZ 55, 176, Parkettstäbefall.
""".strip()},

  {"id": "steckbrief_linoleumrollen", "skill": "sachenrecht", "text": """
Linoleumrollenfall (RGZ 62, 331) — Reichsgericht, 1906

Händler lagerten Linoleumrollen im Besitz eines Kommissionärs. Der Kommissionär veräußerte
die Rollen entgegen dem Eigentumsvorbehalt. Kläger forderte Schadensersatz aus § 823 BGB.

Leitsätze:
1. Das Eigentum (§ 903 BGB) ist ein "sonstiges Recht" i.S.d. § 823 Abs. 1 BGB.
2. Besitz allein ist kein sonstiges Recht i.S.d. § 823 Abs. 1 BGB (umstritten).
3. § 823 BGB schützt absolute Rechte (Eigentum, Besitz als faktische Herrschaft,
   Persönlichkeitsrecht) gegen rechtswidrige Eingriffe.

Bedeutung: Historischer Grundsatzfall zu § 823 Abs. 1 BGB und dem Begriff "sonstiges Recht".
RGZ 62, 331, Linoleumrollenfall, Besitzschutz, Deliktsrecht.
""".strip()},

  # ── ARBEITSRECHT ────────────────────────────────────────────────────────────
  {"id": "steckbrief_schultz_hoff", "skill": "arbeitsrecht", "text": """
Schultz-Hoff / Stringer (EuGH Rs. C-350/06 und C-520/06) — EuGH, 20. Januar 2009

Schultz-Hoff war dauerhaft erkrankt und konnte seinen Jahresurlaub nicht nehmen.
Nach deutschem Recht (§ 7 Abs. 3 BUrlG) verfiel der Urlaub mit Ablauf des
Übertragungszeitraums (31. März des Folgejahres). Der EuGH prüfte Vereinbarkeit
mit der Arbeitszeitrichtlinie 2003/88/EG.

Leitsätze:
1. Jahresurlaub nach Art. 7 Arbeitszeitrichtlinie darf nicht verfallen, wenn
   krankheitsbedingte Arbeitsunfähigkeit die Inanspruchnahme verhindert hat.
2. Bei Beendigung des Arbeitsverhältnisses besteht Anspruch auf finanzielle
   Abgeltung des krankheitsbedingt nicht genommenen Urlaubs.
3. Nationales Recht, das Urlaubsverfall bei Langzeiterkrankung vorsieht, ist
   unionsrechtswidrig und unangewendet zu lassen.

Bedeutung: Grundlegende Änderung der deutschen Urlaubsrechtspraxis.
Folgeurteil KHS (C-214/10): Mindest-Übertragungszeitraum 15 Monate.
EuGH C-350/06, Urlaubsübertragung, Langzeiterkrankung, BUrlG.
""".strip()},

  # ── URHEBERRECHT ────────────────────────────────────────────────────────────
  {"id": "steckbrief_metall_auf_metall", "skill": "urheberrecht", "text": """
Metall auf Metall — Kraftwerk vs. Pelham (BGH + BVerfG + EuGH, 2008–2020)

Hintergrund: Musikgruppe Kraftwerk (Song "Metall auf Metall", 1977). Moses Pelham sampelte
eine 2-Sekunden-Rhythmussequenz für den Rap-Song "Nur mir" (Sabrina Setlur, 1997).

Zentrale Rechtsfragen:
1. Leistungsschutzrecht des Tonträgerherstellers (§ 85 UrhG): Selbst kürzeste Tonsequenzen
   aus einem Tonträger dürfen ohne Lizenz nicht verwendet werden (Vervielfältigungsrecht).
2. Freie Benutzung (§ 24 UrhG a.F.): Sampling ist nur als "freie Benutzung" erlaubt,
   wenn das Original nicht erkennbar bleibt — hier nicht der Fall.
3. EuGH-Vorlage (C-476/17): Sampling verletzt Vervielfältigungsrecht, außer die Sequenz
   ist im neuen Werk verändert und nicht erkennbar (EuGH 2019).
4. BVerfG: Kunstfreiheit (Art. 5 Abs. 3 GG / Art. 13 GRCh) muss gegen Leistungsschutzrecht
   abgewogen werden. BVerfG betonte Bedeutung des Samplings für Kunstform "Hip-Hop".

Bedeutung: Wichtigstes deutsches Urteil zum Musik-Sampling. Betrifft Produzenten,
Musiklabels, Künstler. Grenzen des erlaubten Samplings im Urheberrecht.
BGH I ZR 112/06, Metall auf Metall, Sampling, § 85 UrhG.
""".strip()},

  # ── GESELLSCHAFTSRECHT ──────────────────────────────────────────────────────
  {"id": "steckbrief_autokran", "skill": "gesellschaftsrecht", "text": """
Autokran (BGHZ 95, 330) — Bundesgerichtshof, 16. September 1985, II ZR 275/84
(Autokran-Urteil, Autokran-Entscheidung, GmbH-Konzernhaftung)

Sachverhalt: Die Autokran GmbH (Spezialunternehmen für Autokranvermietung) wurde von ihrer
Muttergesellschaft dauerhaft und umfassend wie ein interner Betrieb geführt. Die Mutter
entzog der GmbH systematisch Liquidität: Sie übernahm lukrative Aufträge direkt, zwang der
GmbH nachteilige Verträge auf und leitete Gewinne ab. Als die Autokran GmbH insolvent wurde,
klagten ihre Gläubiger nicht gegen die GmbH (kein Vermögen), sondern gegen die
Muttergesellschaft auf persönliche Haftung — Haftungsdurchgriff.

Leitsätze des Autokran-Urteils (qualifiziert faktischer Konzern, Existenzvernichtungshaftung):
1. Qualifiziert faktischer Konzern: Wer eine GmbH dauerhaft und umfassend leitet und
   dabei einzelne Nachteile nicht durch Ausgleichsmaßnahmen kompensiert, haftet als
   herrschende Gesellschaft analog §§ 302, 303 AktG für alle Verbindlichkeiten der GmbH.
2. Haftungsdurchgriff / Haftungsbeschränkungsdurchbrechung: § 13 Abs. 2 GmbHG
   (Haftungsbeschränkung auf Gesellschaftsvermögen) gilt nicht, wenn das GmbH-Konzept
   systematisch zur Gläubigerschädigung missbraucht wird (gesellschaftsrechtlicher
   Durchgriff, Missbrauch der Haftungsbeschränkung).
3. Fortentwicklung — Trihotel (BGHZ 173, 246, BGH 2007): Der qualifiziert faktische
   Konzern als dogmatische Figur wird aufgegeben. Stattdessen: Existenzvernichtungshaftung
   nach § 826 BGB — vorsätzliche sittenwidrige Schädigung durch existenzvernichtenden
   Eingriff (Entziehung von Gesellschaftsvermögen, das zur Gläubigerbefriedigung benötigt
   wird). Subsidiär und innenrechtlich.

Bedeutung: Das Autokran-Urteil ist der historische Ausgangspunkt der deutschen
Existenzvernichtungshaftung und GmbH-Konzernhaftung. Zusammen mit Bremer Vulkan
(BGHZ 149, 10, 2001) und Trihotel (BGHZ 173, 246, 2007) bildet es das maßgebliche
Dreigestirn der GmbH-Konzernhaftung. BGHZ 95, 330, Autokran, II ZR 275/84,
Durchgriffshaftung, Existenzvernichtungshaftung, § 826 BGB, GmbH-Konzern.
""".strip()},

  {"id": "steckbrief_bremer_vulkan", "skill": "gesellschaftsrecht", "text": """
Bremer Vulkan (BGHZ 149, 10) — Bundesgerichtshof, 17. September 2001, II ZR 178/99

Konzernmutter entzog der Tochter-GmbH (Bremer Vulkan AG) Liquidität durch ein
konzernweites Cash-Pool-System und ließ sie in die Insolvenz gehen. Die GmbH hatte
Subventionen für ostdeutsche Werften erhalten, die dann zweckentfremdet wurden.

Leitsätze:
1. Gesellschafter einer GmbH haften nicht per se für Verbindlichkeiten der GmbH.
2. Haftungsdurchgriff (Existenzvernichtungshaftung): Gesellschafter, die das Gesellschafts-
   vermögen planmäßig entziehen und damit Gläubigerinteressen vorsätzlich verletzen,
   haften persönlich nach § 826 BGB (später: Trihotel-Formel).
3. Qualifizierter faktischer Konzern als eigenständige Haftungsgrundlage aufgegeben;
   stattdessen § 826 BGB als einheitliche Grundlage.

Bedeutung: Bremer Vulkan + Trihotel (BGHZ 173, 246) bilden das aktuelle System der
Existenzvernichtungshaftung. BGHZ 149, 10, § 826 BGB, GmbH-Haftung.
""".strip()},

  {"id": "steckbrief_maastricht", "skill": "europarecht", "text": """
Maastricht-Urteil / Brunner-Urteil (BVerfGE 89, 155) — Bundesverfassungsgericht,
12. Oktober 1993, 2 BvR 2134/92 und 2 BvR 2159/92

Verfassungsmäßigkeit des Maastricht-Vertrags (Vertrag über die Europäische Union, 1992).
Beschwerdeführer u.a. Manfred Brunner, daher auch Brunner-Urteil.

Leitsätze:
1. Der Maastricht-Vertrag ist mit dem GG vereinbar, aber unter dem Vorbehalt, dass die
   EU nicht über ihre Kompetenzen hinaus handelt (Ultra-vires-Kontrolle).
2. Staatsvolk-Demokratie: Die demokratische Legitimation der EU fließt über die
   Mitgliedstaaten und ihre Parlamente; ein eigenständiges EU-Volk im staatsrechtlichen
   Sinne existiert nicht.
3. Kompetenz-Kompetenz: Die EU hat keine Kompetenz, sich selbst weitere Kompetenzen zu
   verleihen; dies liegt bei den Mitgliedstaaten als "Herren der Verträge".
4. Identitätskontrolle des BVerfG: Verletzungen von Verfassungsidentität (Art. 79 Abs. 3 GG)
   können vom BVerfG geprüft werden.

Bedeutung: Vorläufer und Grundlage des Lissabon-Urteils (BVerfGE 123, 267).
BVerfGE 89, 155, Maastricht, Brunner, Integrationsgrenze.
""".strip()},

  {"id": "steckbrief_omega", "skill": "europarecht", "text": """
Omega Spielhallen (EuGH Rs. C-36/02) — Europäischer Gerichtshof, 14. Oktober 2004

Eine Bonn Behörde verbot den Betrieb der "Laserdrome"-Anlage der Firma Omega Spielhallen
GmbH, in der Spieler symbolisch auf Menschen schossen (Laserspiel). Omega betrieb die
Anlage mit Geräten eines britischen Unternehmens. Die Behörde sah die Menschenwürde verletzt.

Leitsätze — Grundrechte als Schranke der Grundfreiheiten:
1. Mitgliedstaaten dürfen Grundfreiheiten (hier: Dienstleistungsfreiheit) beschränken,
   um nationale Grundrechtswerte (hier: Menschenwürde, Art. 1 GG) zu schützen.
2. Die Menschenwürde ist auch ein allgemeiner Grundsatz des Gemeinschaftsrechts.
3. Verhältnismäßigkeit ist zu prüfen — nationale Wertvorstellungen können legitimer Grund
   für Beschränkungen sein, auch wenn andere Mitgliedstaaten die Tätigkeit erlauben.

Bedeutung: Zeigt, wie nationale Grundrechtswerte EU-Grundfreiheiten einschränken können.
Grundrechte als Schranke, Menschenwürde, EuGH C-36/02, Dienstleistungsfreiheit.
""".strip()},

  {"id": "steckbrief_altrip", "skill": "verwaltungsrecht", "text": """
Altrip-Urteil (EuGH Rs. C-72/12) — Europäischer Gerichtshof, 7. November 2013
(Altrip-Entscheidung, Altrip, Verbandsklage UVP)

Sachverhalt: Der BUND (Bund für Umwelt und Naturschutz Deutschland, Naturschutzbund)
klagte in Bayern gegen die Genehmigung eines Deichbaus in der Gemeinde Altrip ohne
ordnungsgemäße Umweltverträglichkeitsprüfung (UVP). Das Verwaltungsgericht fragte
den EuGH, unter welchen Voraussetzungen anerkannte Umweltverbände UVP-Verfahrensfehler
vor deutschen Gerichten rügen dürfen.

Leitsätze — Altrip:
1. Verbandsklage ohne subjektive Rechtsverletzung: Anerkannte Umweltverbände
   (§ 63 BNatSchG, § 2 UmwRG) können UVP-Verfahrensfehler vor Gericht rügen,
   auch ohne dass sie eine subjektive Rechtsverletzung (Verletzung eigener Rechte)
   geltend machen müssen — das Umweltrechtsbehelfsgesetz (UmwRG) war insoweit
   europarechtswidrig.
2. Effektiver Rechtsschutz (Art. 11 UVP-RL, Art. 9 Aarhus-Konvention): EU-Recht
   und die Aarhus-Konvention verlangen einen weiten Zugang zu Gerichten bei
   UVP-Verstößen — nationales Recht, das Verbandsklagen auf subjektive
   Rechtsverletzungen beschränkt, ist unvereinbar mit der UVP-Richtlinie.
3. Kausalitätserfordernis: Ein UVP-Verfahrensfehler führt nur dann zur Aufhebung
   der Genehmigung, wenn das Ergebnis des Verfahrens ohne den Fehler möglicherweise
   anders ausgefallen wäre (Ergebnisrelevanz).

Bedeutung — Altrip (EuGH C-72/12, 7. November 2013): Wegweisendes Urteil zum
Umweltrechtsbehelfsgesetz (UmwRG) und der Verbandsklage im deutschen Verwaltungsrecht.
Stärkt die Klagebefugnis von Umweltverbänden erheblich. Grundlage für die Reform des
UmwRG 2017. Altrip, EuGH C-72/12, UVP-Richtlinie, Verbandsklage, subjektive
Rechtsverletzung, Klagebefugnis, Aarhus-Konvention, Umweltrecht, Verwaltungsrecht,
BUND, Naturschutzbund, Deichbau, UmwRG, Umweltrechtsbehelfsgesetz.
""".strip()},
# 84 neue Steckbriefe (noch nicht im Skript)

  {"id": "steckbrief_arbeitnehmerueberlassung_aüg", "skill": "arbeitsrecht", "text": """
Arbeitnehmerüberlassung — Scheinwerkvertrag (AÜG)
— Bundesarbeitsgericht, BAG NZA 2013, 1367
(§ 1 AÜG, Scheinwerkvertrag, Arbeitnehmerüberlassungsgesetz)

Sachverhalt: Ein Unternehmen schloss mit einer Fremdfirma einen Werkvertrag, durch den
Arbeitnehmer der Fremdfirma dauerhaft im Betrieb des Unternehmens tätig wurden und
dabei dessen Weisungen unterlagen. Das BAG prüfte, ob tatsächlich ein Werkvertrag oder
eine verdeckte Arbeitnehmerüberlassung (illegale Leiharbeit) vorlag.

Leitsätze (AÜG — Scheinwerkvertrag):
1. Abgrenzung Werkvertrag/Arbeitnehmerüberlassung: Ein Werkvertrag liegt vor, wenn der
   Auftragnehmer eigenverantwortlich ein bestimmtes Ergebnis schuldet und das Weisungsrecht
   gegenüber seinen Arbeitnehmern selbst ausübt. Arbeitnehmerüberlassung liegt dagegen vor,
   wenn der Auftraggeber (Entleiher) das Weisungsrecht über die eingesetzten Arbeitnehmer
   tatsächlich ausübt.
2. Scheinwerkvertrag: Wird ein Werkvertrag vereinbart, aber tatsächlich Arbeitnehmerüberlassung
   praktiziert, liegt ein Scheinwerkvertrag (§ 117 BGB analog) vor — es greift das AÜG.
3. Erlaubnispflicht (§ 1 AÜG): Arbeitnehmerüberlassung ist nur mit behördlicher Erlaubnis
   zulässig. Ohne Erlaubnis ist der Überlassungsvertrag nichtig; das Arbeitsverhältnis
   gilt als zwischen dem Leiharbeitnehmer und dem Entleiher begründet (§ 10 AÜG).
4. Equal-Pay-Grundsatz: Leiharbeitnehmer haben grundsätzlich Anspruch auf gleiche
   Vergütung wie vergleichbare Stammarbeitnehmer des Entleihers (§ 8 AÜG).

Bedeutung: Grundlegend für die Abgrenzung von Werk- und Dienstverträgen zu Leiharbeit.
Hohe Praxisrelevanz bei Outsourcing und Werkvertragsgestaltung.

Schlagwörter: AÜG, Arbeitnehmerüberlassung, Scheinwerkvertrag, § 1 AÜG, § 10 AÜG,
Weisungsrecht, Leiharbeit, Equal Pay, BAG NZA 2013 1367, Outsourcing, Arbeitsrecht.
""".strip()},

  {"id": "steckbrief_bag_kündigung_interessenabwägung", "skill": "arbeitsrecht", "text": """
Kündigung — Interessenabwägung und soziale Rechtfertigung (§ 1 KSchG)
— Bundesarbeitsgericht, BAG NJW 2012, 1098

Sachverhalt: Ein langjähriger Arbeitnehmer wurde wegen Schlechtleistung und Fehlzeiten
ordentlich gekündigt. Der Arbeitnehmer erhob Kündigungsschutzklage und machte geltend,
die Kündigung sei sozial ungerechtfertigt.

Leitsätze (§ 1 KSchG — soziale Rechtfertigung der Kündigung):
1. Soziale Rechtfertigung (§ 1 Abs. 2 KSchG): Eine ordentliche Kündigung ist sozial
   gerechtfertigt, wenn sie durch Gründe in der Person, dem Verhalten des Arbeitnehmers
   oder durch dringende betriebliche Erfordernisse bedingt ist.
2. Verhältnismäßigkeit und Ultima-ratio-Prinzip: Die Kündigung ist das schärfste Mittel
   des Arbeitgebers und muss das letzte Mittel sein (Ultima Ratio). Mildere Mittel
   (Abmahnung, Versetzung, Änderungskündigung) sind vorrangig einzusetzen.
3. Interessenabwägung: Bei verhaltensbedingter und personenbedingter Kündigung ist eine
   umfassende Interessenabwägung vorzunehmen: Berücksichtigt werden Dauer der Betriebszugehörigkeit,
   Lebensalter, Unterhaltspflichten, Schwere der Pflichtverletzung.
4. Abmahnung: Vor einer verhaltensbedingten Kündigung ist grundsätzlich eine Abmahnung
   erforderlich (Warn- und Dokumentationsfunktion), außer bei schwerwiegenden Pflichtverletzungen.

Bedeutung: Zentrale Entscheidung zur Prüfung der sozialen Rechtfertigung nach KSchG.
Standardmaßstab in der Kündigungsschutzpraxis.

Schlagwörter: § 1 KSchG, soziale Rechtfertigung, Kündigung, Interessenabwägung, Ultima Ratio,
Abmahnung, verhaltensbedingter Grund, personenbedingter Grund, BAG NJW 2012 1098, Arbeitsrecht.
""".strip()},

  {"id": "steckbrief_betriebsübergang_613a", "skill": "arbeitsrecht", "text": """
Betriebsübergang — Kontinuität des Arbeitsverhältnisses (§ 613a BGB)
— Bundesarbeitsgericht, BAG NJW 2001, 1963
(§ 613a BGB, Betriebsinhaberwechsel, Arbeitnehmerrechte)

Sachverhalt: Ein Unternehmen übernahm durch Kauf wesentliche Teile des Betriebs eines
insolventen Unternehmens (Maschinen, Kundenstamm, Personal). Fraglich war, ob die
Arbeitsverhältnisse automatisch auf den neuen Betriebsinhaber übergingen.

Leitsätze (§ 613a BGB — Betriebsübergang):
1. Betriebsübergang (§ 613a Abs. 1 BGB): Geht ein Betrieb oder Betriebsteil durch
   Rechtsgeschäft auf einen anderen Inhaber über, tritt dieser in die Rechte und Pflichten
   aus den zum Zeitpunkt des Übergangs bestehenden Arbeitsverhältnissen ein. Der Übergang
   erfolgt kraft Gesetzes — kein Einverständnis der Arbeitnehmer erforderlich.
2. Begriff des Betriebsübergangs: Ein Betriebsübergang liegt vor, wenn eine wirtschaftliche
   Einheit unter Wahrung ihrer Identität auf einen neuen Inhaber übergeht. Bei Dienstleistungen
   kommt es vor allem auf den Übergang von Arbeitnehmern, Ausstattung und Kundenstamm an
   (EuGH-Rechtsprechung: Süzen, Ayse Süzen, C-13/95).
3. Widerspruchsrecht der Arbeitnehmer: Arbeitnehmer können dem Übergang widersprechen
   (§ 613a Abs. 6 BGB). Dann verbleibt das Arbeitsverhältnis beim alten Betriebsinhaber,
   der jedoch mangels Arbeitsplatz kündigen darf.
4. Kündigungsverbot: Die Kündigung wegen des Betriebsübergangs ist unwirksam (§ 613a
   Abs. 4 BGB). Andere Kündigungsgründe bleiben jedoch zulässig.

Bedeutung: § 613a BGB ist der wichtigste Schutz des Arbeitnehmers beim Unternehmensverkauf.
Umsetzung der EG-Betriebsübergangsrichtlinie (2001/23/EG).

Schlagwörter: § 613a BGB, Betriebsübergang, Betriebsinhaberwechsel, Arbeitnehmerrechte,
BAG NJW 2001 1963, Widerspruchsrecht, Kündigungsverbot, Richtlinie 2001/23/EG, Insolvenz.
""".strip()},

  {"id": "steckbrief_schultz_hoff", "skill": "arbeitsrecht", "text": """
Schultz-Hoff / Stringer (EuGH Rs. C-350/06 und C-520/06) — EuGH, 20. Januar 2009

Schultz-Hoff war dauerhaft erkrankt und konnte seinen Jahresurlaub nicht nehmen.
Nach deutschem Recht (§ 7 Abs. 3 BUrlG) verfiel der Urlaub mit Ablauf des
Übertragungszeitraums (31. März des Folgejahres). Der EuGH prüfte Vereinbarkeit
mit der Arbeitszeitrichtlinie 2003/88/EG.

Leitsätze:
1. Jahresurlaub nach Art. 7 Arbeitszeitrichtlinie darf nicht verfallen, wenn
   krankheitsbedingte Arbeitsunfähigkeit die Inanspruchnahme verhindert hat.
2. Bei Beendigung des Arbeitsverhältnisses besteht Anspruch auf finanzielle
   Abgeltung des krankheitsbedingt nicht genommenen Urlaubs.
3. Nationales Recht, das Urlaubsverfall bei Langzeiterkrankung vorsieht, ist
   unionsrechtswidrig und unangewendet zu lassen.

Bedeutung: Grundlegende Änderung der deutschen Urlaubsrechtspraxis.
Folgeurteil KHS (C-214/10): Mindest-Übertragungszeitraum 15 Monate.
EuGH C-350/06, Urlaubsübertragung, Langzeiterkrankung, BUrlG.
""".strip()},

  {"id": "steckbrief_bond_urteil", "skill": "bank_kapitalmarktrecht", "text": """
Bond-Urteil (BGH NJW 1993, 2433) — Bundesgerichtshof, XI. Zivilsenat,
6. Juli 1993, XI ZR 12/93
(Anlageberatung, Sorgfaltspflicht, anleger- und anlagegerechte Beratung)

Sachverhalt: Ein Anleger fragte seine Bank nach einer sicheren Anlage und wurde in
riskante Bonds (Argentinien-Anleihen) investiert. Die Anleihen fielen erheblich im Wert.
Der Anleger klagte auf Schadensersatz wegen fehlerhafter Anlageberatung.

Leitsätze (BGH NJW 1993, 2433 — Anlageberatung):
1. Anlegergerechte Beratung: Die Bank muss den Anleger anlegergerecht beraten. Dabei
   muss sie die persönliche Situation des Anlegers ermitteln (Risikobereitschaft,
   Anlageziel, Kenntnisse, finanzielle Verhältnisse) und ihr die Empfehlung anpassen.
2. Anlagegerechte Beratung: Zusätzlich muss die empfohlene Anlage selbst anlagegerecht
   sein — die Bank muss über alle wesentlichen Risiken aufklären, die die Anlage mit
   sich bringt.
3. Aufklärungspflicht: Vor einer Empfehlung muss die Bank über alle für die Anlageentscheidung
   erheblichen Risiken informieren, insbesondere Emittentenrisiko, Kursrisiken, Liquidität.
4. Schadensersatz: Bei Verletzung der Beratungspflichten aus dem Beratungsvertrag
   (§ 280 Abs. 1 BGB) kann der Anleger den Differenzschaden oder Naturalrestitution
   (Rückgabe der Anlage gegen Kaufpreiserstattung) verlangen.

Bedeutung: Grundlegendes Urteil zur Bankenhaftung bei der Anlageberatung. Ausgangspunkt
des gesamten deutschen Beratungsrechts im Kapitalmarkt; Basis der MiFID-Umsetzung.

Schlagwörter: BGH NJW 1993 2433, Bond-Urteil, Anlageberatung, anlegergerecht, anlagegerecht,
Aufklärungspflicht, Beratungsvertrag, § 280 BGB, Schadensersatz, Bank, Kapitalmarktrecht.
""".strip()},

  {"id": "steckbrief_deka_prospekthaftung", "skill": "bank_kapitalmarktrecht", "text": """
DEKA-Investment / Prospekthaftung — Bundesgerichtshof, BGH NJW 2012, 758
(Prospekthaftung, Kapitalanlage, §§ 21 ff. WpPG)

Sachverhalt: Anleger investierten in Kapitalanlagen auf Grundlage eines fehlerhaften
Verkaufsprospekts, der wesentliche Risiken verschwieg oder verharmloste. Die Anleger
verloren erhebliche Teile ihres eingesetzten Kapitals und klagten aus Prospekthaftung.

Leitsätze (Prospekthaftung):
1. Prospekthaftung im engeren Sinne (§§ 21 ff. WpPG, früher §§ 44 ff. BörsG a.F.):
   Wer für einen fehlerhaften Verkaufsprospekt verantwortlich ist (Emittent, Hintermann,
   Prospektverantwortlicher), haftet Anlegern, die im Vertrauen auf den Prospekt
   Wertpapiere erwerben und dadurch Schaden nehmen.
2. Fehler im Prospekt: Ein Prospekt ist fehlerhaft, wenn er unrichtige oder irreführende
   Angaben enthält oder wesentliche Angaben verschweigt, die für die Anlageentscheidung
   erheblich sind.
3. Kausalitätsvermutung: Es wird vermutet, dass der Anleger bei richtigem Prospekt
   nicht investiert hätte (Anlagestimmung, fraudulent inducement). Der Anspruchsgegner
   kann diese Vermutung widerlegen.
4. Prospekthaftung im weiteren Sinne (c.i.c., § 311 Abs. 2 BGB): Neben der gesetzlichen
   Prospekthaftung kommt eine Haftung aus culpa in contrahendo in Betracht, wenn der
   Berater/Vermittler persönliches Vertrauen in Anspruch genommen hat.

Bedeutung: Grundlegend für die Kapitalmarkt-Prospekthaftung. Klärt Tatbestandsmerkmale
und Kausalitätsvermutung.

Schlagwörter: Prospekthaftung, §§ 21 ff. WpPG, BGH NJW 2012 758, Emittent, Verkaufsprospekt,
Anleger, Kausalitätsvermutung, c.i.c., § 311 BGB, Kapitalmarktrecht, Schadensersatz.
""".strip()},

  {"id": "steckbrief_arglistige_taeuschung_haus", "skill": "bgb_at", "text": """
Arglistige Täuschung beim Häuserkauf (§ 123 BGB) — Bundesgerichtshof
— BGH NJW 1995, 2361 (Palandt-Versteigerungs-Fall / Häuserkauf arglistige Täuschung)

Sachverhalt: Ein Hausverkäufer verschwieg dem Käufer bekannte Feuchtigkeitsschäden im
Keller und andere Baumängel. Nach Vertragsschluss wurden die Mängel offenbar. Der
Käufer focht den Kaufvertrag wegen arglistiger Täuschung (§ 123 BGB) an und verlangte
Rückzahlung des Kaufpreises.

Leitsätze (§ 123 BGB — Arglistige Täuschung):
1. Arglistige Täuschung setzt voraus: (a) eine Täuschungshandlung (Vorspiegelung falscher
   Tatsachen oder Verschweigen offenbarungspflichtiger Umstände), (b) Arglist (Vorsatz
   oder mindestens bedingter Vorsatz bzgl. der Täuschungswirkung), (c) dadurch hervorgerufener
   Irrtum und (d) Kausalität zwischen Irrtum und Willenserklärung.
2. Offenbarungspflicht beim Immobilienkauf: Verkäufer sind verpflichtet, alle ihnen
   bekannten Umstände zu offenbaren, die für den Käufer erkennbar wesentlich sind und
   über die er nach Treu und Glauben (§ 242 BGB) Aufklärung erwarten darf — insbesondere
   Baumängel, Feuchtigkeitsschäden, Altlasten.
3. Anfechtungsfrist: Die Anfechtung muss binnen Jahresfrist ab Entdeckung der Täuschung
   erklärt werden (§ 124 BGB).
4. Rechtsfolge: Bei erfolgreicher Anfechtung ist der Vertrag von Anfang an nichtig
   (§ 142 Abs. 1 BGB); der Verkäufer muss Kaufpreis zurückzahlen, Käufer das Haus zurückgeben.

Bedeutung: Wichtiger Praxisfall zum Anfechtungsrecht wegen arglistiger Täuschung
beim Immobilienkauf. Zeigt Aufklärungspflichten des Verkäufers und Folgen ihrer Verletzung.

Schlagwörter: § 123 BGB, arglistige Täuschung, Anfechtung, Offenbarungspflicht,
Immobilienkauf, Feuchtigkeitsschäden, Baumängel, § 124 BGB Jahresfrist, § 142 BGB
Nichtigkeit, Häuserkauf, BGB AT.
""".strip()},

  {"id": "steckbrief_blankounterschrift", "skill": "bgb_at", "text": """
Blankounterschrift-Fall / Anscheinsvollmacht (§ 172 BGB analog)
— Bundesgerichtshof, BGH NJW 1986, 2944

Sachverhalt: Jemand unterzeichnete ein leeres Blatt Papier (Blankovollmacht), das später
von einem anderen mit einem Rechtsgeschäft ausgefüllt und zur Begründung einer Vollmacht
genutzt wurde. Der "Vollmachtgeber" wollte das ausgefüllte Rechtsgeschäft nicht gegen sich
gelten lassen, da er keine entsprechende Vollmacht erteilen wollte. Der Dritte berief sich
auf den Vertrauensschutz.

Leitsätze (Anscheinsvollmacht, § 172 BGB):
1. Anscheinsvollmacht: Wer durch sein Verhalten den Rechtsschein einer Vollmacht erzeugt
   und dabei fahrlässig handelt, muss sich diesen Rechtsschein wie eine echte Vollmacht
   zurechnen lassen, wenn der Geschäftsgegner gutgläubig auf die Vollmacht vertraut.
2. Blankounterschrift: Das Unterzeichnen eines leeren Formulars begründet den Rechtsschein
   einer Vollmacht, wenn der Unterzeichner die Gefahr der Ausfüllung erkannte oder hätte
   erkennen können. Er muss sich die Ausfüllung in den Grenzen des Blankettrahmens zurechnen
   lassen.
3. Abgrenzung zur Duldungsvollmacht: Die Anscheinsvollmacht setzt kein tatsächliches
   Dulden früherer Vertretungshandlungen voraus, sondern genügt mit dem objektiven
   Rechtsschein einer Vollmacht.
4. Schutz des Vertrauens im Rechtsverkehr (§ 242 BGB): Wer fahrlässig einen Vollmachtsschein
   erzeugt, ist nach Treu und Glauben gehalten, diesen gegen sich gelten zu lassen.

Bedeutung: Leitfall zur Anscheinsvollmacht. Zeigt, wie Vertrauensschutzgedanken im
Stellvertretungsrecht wirken.

Schlagwörter: Anscheinsvollmacht, Duldungsvollmacht, § 172 BGB, Blankounterschrift,
Vollmachtsschein, Rechtsschein, Vertrauensschutz, gutgläubig, fahrlässig, BGB AT,
Stellvertretung, Zurechnung.
""".strip()},

  {"id": "steckbrief_buergschaft_sittenwidrigkeit", "skill": "bgb_at", "text": """
Bürgschaft-Sittenwidrigkeit — Finanziell überforderter Angehöriger (BGHZ 125, 206)
— Bundesgerichtshof, IX. Zivilsenat, 24. Februar 1994, IX ZR 93/93

Sachverhalt: Die Klägerin (Tochter, gelernte Verkäuferin ohne nennenswertes Vermögen) verbürgte
sich für einen Bankkredit ihres Vaters in Höhe von 100.000 DM. Die Bank nahm sie nach
Insolvenz des Vaters in voller Höhe in Anspruch. Die Tochter war erkennbar finanziell
völlig überfordert; die Bürgschaft überstieg ihr Jahreseinkommen um ein Vielfaches.

Leitsätze (BGHZ 125, 206):
1. Sittenwidrigkeit (§ 138 Abs. 1 BGB) einer Bürgschaft durch finanziell krass überforderten
   Angehörigen: Eine Bürgschaft ist sittenwidrig und nichtig, wenn (a) der Bürge
   finanziell krass überfordert ist (die Bürgschaftssumme liegt in einem offensichtlichen
   Missverhältnis zu seinem Einkommen/Vermögen), (b) der Bürge aus emotionaler Verbundenheit
   (Verwandtschaft, Liebesbeziehung) handelt und (c) die Bank diese Lage kennt oder
   kennen muss.
2. Indizwirkung: Ist der Bürge ein naher Angehöriger ohne nennenswertes Einkommen, wird
   die emotionale Beeinflussbarkeit und das Fehlen eines eigenen wirtschaftlichen Interesses
   vermutet; der Kreditgeber muss diese Indizien widerlegen.
3. Keine Heilung durch Ratenzahlungsvereinbarung oder Teilleistungen.

Bedeutung: Grundlegendes Urteil zum Schutz finanziell überforderter Angehörigenbürgen
vor sittenwidrigen Vertragsgestaltungen der Banken. Angeknüpft wird an § 138 BGB
(Sittenwidrigkeit). Massive praktische Bedeutung für das Bankrecht und Verbraucherschutz.

Schlagwörter: § 138 BGB Sittenwidrigkeit, Bürgschaft, Angehörigenbürgschaft, krasse
finanzielle Überforderung, emotionale Verbundenheit, Verwandtschaft, Bankrecht,
BGHZ 125 206, IX ZR 93/93, Verbraucherschutz, Nichtigkeit.
""".strip()},

  {"id": "steckbrief_dreiecksverhältnis_leistungskondiktion", "skill": "bgb_at", "text": """
Dreiecksverhältnis / Leistungskondiktion (§ 812 Abs. 1 S. 1 Alt. 1 BGB)
— Bundesgerichtshof, BGH NJW 1966, 1451

Sachverhalt: A schuldet B Geld; A weist C an, an B zu zahlen. C zahlt an B. Das
Grundverhältnis A-B ist nichtig; das Valutaverhältnis A-C besteht. Fraglich war, ob B
von A oder von C kondizieren muss, und welcher Kondiktionsanspruch vorgeht.

Leitsätze (Leistungskondiktion im Dreiecksverhältnis):
1. Leistungskondiktion (§ 812 Abs. 1 S. 1 Alt. 1 BGB — "durch Leistung"): Leistung
   ist die bewusste und zweckgerichtete Vermehrung fremden Vermögens. Im Dreiecksverhältnis
   gilt: C leistet an B (im Deckungsverhältnis: A→C; im Valutaverhältnis: A→B).
2. Subsidiarität der Eingriffskondiktion: Die Eingriffskondiktion tritt hinter die
   Leistungskondiktion zurück. Im Dreiecksverhältnis kondiziert die benachteiligte Partei
   im jeweiligen Leistungsverhältnis: B kondiziert von A (Valutaverhältnis nichtig);
   A kondiziert von C (Deckungsverhältnis nichtig).
3. Durchgriffskondiktion ist ausgeschlossen: C kann nicht direkt von B kondizieren,
   wenn A (Anweisender) insolvent ist — dies schützt B vor unerwarteten Rückforderungen.
4. Ausnahme: Wenn der Anweisende (A) keine wirksame Anweisung erteilt (z.B. Fälschung,
   Geschäftsunfähigkeit), kann ausnahmsweise ein direkter Durchgriff des Zahlenden (C)
   auf den Empfänger (B) in Betracht kommen.

Bedeutung: Grundlegender Fall zu Leistungsbeziehungen im Dreiecksverhältnis. Zeigt das
System der Leistungskondiktionen und ihre Abgrenzung zur Eingriffskondiktion.

Schlagwörter: § 812 Abs. 1 S. 1 Alt. 1 BGB, Leistungskondiktion, Dreiecksverhältnis,
Anweisung, Valutaverhältnis, Deckungsverhältnis, Subsidiarität, Durchgriffskondiktion,
Bereicherungsrecht, BGB AT.
""".strip()},

  {"id": "steckbrief_haakjoeringskoed", "skill": "bgb_at", "text": """
Haakjöringsköd-Fall (RGZ 99, 147) — Reichsgericht, 1920
(falsa demonstratio non nocet, Auslegung von Willenserklärungen, übereinstimmender Irrtum)

Sachverhalt: In einem Kaufvertrag wurde als Kaufgegenstand "Haakjöringsköd" bezeichnet.
Verkäufer und Käufer verstanden darunter beide Walfleisch (norw.: Haifischfleisch), obwohl
der norwegische Begriff wörtlich "Haifischfleisch" bedeutet. Als Streit über den
Vertragsgegenstand entstand, stellte das Gericht fest, dass beide Parteien subjektiv
Walfleisch meinen wollten, auch wenn der objektive Wortlaut etwas anderes bedeutete.

Leitsätze:
1. Falsa demonstratio non nocet (eine falsche Bezeichnung schadet nicht): Wenn beide
   Parteien eines Vertrags ein und dasselbe meinen, ist dieser übereinstimmende Wille
   maßgeblich — nicht der objektive Wortlaut der Erklärungen. Der Vertrag kommt mit dem
   von beiden gewollten Inhalt zustande, auch wenn die verwendete Bezeichnung sachlich falsch ist.
2. Auslegung von Willenserklärungen (§§ 133, 157 BGB): Maßstab ist der übereinstimmende
   Wille der Parteien zum Zeitpunkt des Vertragsschlusses. Nur wenn kein übereinstimmender
   Wille feststellbar ist, kommt die objektive Auslegung (Empfängerhorizont) zum Tragen.
3. Kein Irrtum — kein Anfechtungsrecht: Da der Vertrag genau das enthält, was beide
   Parteien wollten (Walfleisch), liegt kein relevanter Irrtum i.S.d. § 119 BGB vor,
   und eine Anfechtung scheidet aus.

Dogmatische Bedeutung: Grundlegendes Urteil zur Vertragsauslegung und zum Grundsatz
"falsa demonstratio non nocet". Zeigt, dass subjektiver Konsens der Parteien den
objektiven Wortsinn überlagert. Fundamental für die Auslegungslehre im BGB.

Schlagwörter: Falsa demonstratio non nocet, Auslegung Willenserklärung, §§ 133 157 BGB,
übereinstimmender Irrtum, Vertragsauslegung, Haakjöringsköd, Walfleisch, Haifischfleisch,
RGZ 99 147, BGB Allgemeiner Teil, subjektiver Empfängerhorizont.
""".strip()},

  {"id": "steckbrief_hamburger_schulfall", "skill": "bgb_at", "text": """
Hamburger Schulfall (Steppdeckenfall) — Offenkundigkeit bei der Stellvertretung
(§ 164 BGB) — BGH NJW 1962, 32

Sachverhalt: Ein Lehrer kaufte Steppdecken bei einem Händler, ohne ausdrücklich zu erklären,
für wen er kaufe. Er handelte in Wirklichkeit im Namen der Schule (einer öffentlich-rechtlichen
Körperschaft). Fraglich war, ob das Offenkundigkeitsprinzip des § 164 Abs. 1 BGB
("im Namen des Vertretenen") gewahrt war, wenn der Vertreter nicht ausdrücklich erklärt,
für wen er handelt.

Leitsätze (§ 164 BGB — Stellvertretung, Offenkundigkeitsprinzip):
1. Offenkundigkeit (§ 164 Abs. 1 S. 1 BGB): Eine Stellvertretung wirkt nur dann für
   und gegen den Vertretenen, wenn der Vertreter "im Namen des Vertretenen" handelt.
   Dies kann ausdrücklich (ausdrückliche Stellvertretung) oder konkludent aus den
   Umständen hervorgehen (stillschweigende / konkludente Stellvertretung).
2. Konkludentes Handeln im fremden Namen: Ergibt sich aus den Umständen eindeutig,
   dass der Handelnde nicht für sich selbst, sondern für einen anderen handelt, genügt
   dies dem Offenkundigkeitsprinzip — der Vertreter muss den Vertretenen nicht namentlich
   benennen.
3. Handeln unter fremdem Namen vs. Handeln in eigenem Namen: Wer erkennbar nur als
   Organ oder Beauftragter einer Organisation handelt, handelt im fremden Namen.
4. Abgrenzung: Kauft jemand eindeutig in seiner Funktion als Amtsperson oder Beauftragter,
   wird die Schule (Vertretener) Vertragspartner.

Bedeutung: Grundfall zum Offenkundigkeitsprinzip bei der Stellvertretung. Verdeutlicht,
dass konkludentes Handeln im fremden Namen ausreicht.

Schlagwörter: § 164 BGB, Stellvertretung, Offenkundigkeitsprinzip, konkludente Stellvertretung,
im Namen des Vertretenen, Hamburger Schulfall, Steppdeckenfall, BGB AT, Vertreter.
""".strip()},

  {"id": "steckbrief_hyazinthen", "skill": "bgb_at", "text": """
Hyazinthen-Fall — Eigenschaftsirrtum (BGH NJW 1979, 1886)
— Bundesgerichtshof, 21. November 1975, V ZR 119/75

Sachverhalt: Jemand kaufte Blumenzwiebeln, die als Hyazinthen angeboten wurden. Es
stellte sich heraus, dass die Zwiebeln zwar botanisch Hyazinthen waren, aber eine
minderwertige Sorte (nicht die erwartete Qualitätssorte). Der Käufer wollte den
Kauf anfechten und berief sich auf einen Eigenschaftsirrtum nach § 119 Abs. 2 BGB.
Fraglich war, ob ein Irrtum über Eigenschaften der Kaufsache vorliegt.

Leitsätze:
1. Eigenschaftsirrtum (§ 119 Abs. 2 BGB): Ein zur Anfechtung berechtigender Irrtum liegt
   vor, wenn der Erklärende über eine verkehrswesentliche Eigenschaft der Person oder
   Sache irrt. Verkehrswesentlich sind solche Eigenschaften, die nach der Verkehrsanschauung
   den Wert oder die Brauchbarkeit der Sache erheblich beeinflussen.
2. Sortenqualität als Eigenschaft: Die Qualitätsstufe (Sorte) einer Pflanze ist eine
   verkehrswesentliche Eigenschaft im Sinne von § 119 Abs. 2 BGB, sofern sie für den
   Verkehr erheblich ist.
3. Abgrenzung zum Sachmangel (§§ 434 ff. BGB): Eigenschaftsirrtum und Sachmangel
   können nebeneinander vorliegen; die Anfechtung nach § 119 Abs. 2 BGB ist grundsätzlich
   möglich, unterliegt aber der Schadensersatzpflicht (§ 122 BGB).
4. Anfechtungsfrist: Die Anfechtung muss unverzüglich (§ 121 BGB) nach Entdeckung des
   Irrtums erklärt werden.

Bedeutung: Lehrfall zur Abgrenzung von Eigenschaftsirrtum (§ 119 Abs. 2 BGB) und
Sachmangel (Kaufrecht). Verdeutlicht den Begriff der verkehrswesentlichen Eigenschaft.

Schlagwörter: § 119 Abs. 2 BGB, Eigenschaftsirrtum, verkehrswesentliche Eigenschaft,
Anfechtung, Hyazinthen, Blumenzwiebeln, Sorte, Sachmangel, § 122 BGB, BGB AT.
""".strip()},

  {"id": "steckbrief_insichgeschaeft", "skill": "bgb_at", "text": """
Insichgeschäft / Selbstkontrahierung (§ 181 BGB)
— Bundesgerichtshof, BGH NJW 1971, 1355

Sachverhalt: Ein GmbH-Geschäftsführer schloss im Namen der GmbH einen Vertrag mit sich
selbst als Privatperson ab (Kauf eines Grundstücks: GmbH = Käufer, Geschäftsführer =
Verkäufer). Das Rechtsgeschäft war ohne ausdrückliche Gestattung durch die Gesellschaft
abgeschlossen worden. Fraglich war, ob das Geschäft nach § 181 BGB unwirksam ist.

Leitsätze (§ 181 BGB — Insichgeschäft):
1. Verbot des Insichgeschäfts (§ 181 BGB): Ein Vertreter kann im Namen des Vertretenen
   kein Rechtsgeschäft mit sich selbst im eigenen Namen (Selbstkontrahierung) oder als
   Vertreter eines Dritten (Mehrvertretung) abschließen, es sei denn, das Rechtsgeschäft
   besteht ausschließlich in der Erfüllung einer Verbindlichkeit.
2. Rechtsfolge: Verstöße gegen § 181 BGB führen zur schwebenden Unwirksamkeit (nicht
   Nichtigkeit); das Rechtsgeschäft kann durch den Vertretenen genehmigt werden (§ 184 BGB).
3. Gestattung: Das Verbot des § 181 BGB ist dispositiv — der Vertretene kann den Vertreter
   ausdrücklich vom Verbot des Selbstkontrahierens befreien (im GmbH-Recht durch
   Gesellschafterbeschluss oder Satzung).
4. GmbH-Recht: § 181 BGB gilt für GmbH-Geschäftsführer; Befreiung muss im Handelsregister
   eingetragen werden, um Dritten gegenüber wirksam zu sein.

Bedeutung: Zentrale Norm zur Vermeidung von Interessenkonflikten bei der Stellvertretung.
Hohe praktische Relevanz im GmbH- und Gesellschaftsrecht.

Schlagwörter: § 181 BGB, Insichgeschäft, Selbstkontrahierung, Mehrvertretung, Vertreter,
GmbH-Geschäftsführer, schwebende Unwirksamkeit, Genehmigung § 184 BGB, Befreiung,
BGB AT, Interessenkonflikt.
""".strip()},

  {"id": "steckbrief_muenzautomat", "skill": "bgb_at", "text": """
Münzautomat-Fall / Eingriffskondiktion (§ 812 BGB)
— Bundesgerichtshof (Zuweisungsgehalt, Eingriffskondiktion)

Sachverhalt: Jemand leerte unberechtigt einen Münzautomaten (Zigarettenautomaten) und
behielt das Geld. Der Eigentümer des Automaten verlangte Herausgabe des erlangten Geldes
nach Bereicherungsrecht (§ 812 Abs. 1 S. 1 Alt. 2 BGB — Eingriffskondiktion).
Fraglich war, ob ein Eingriff in den "Zuweisungsgehalt" eines fremden Rechts vorliegt.

Leitsätze (§ 812 BGB — Eingriffskondiktion, Zuweisungsgehalt):
1. Eingriffskondiktion (§ 812 Abs. 1 S. 1 Alt. 2 BGB — "in sonstiger Weise"): Der
   Kondiktionsanspruch entsteht, wenn jemand auf Kosten eines anderen ohne rechtlichen
   Grund etwas erlangt, ohne dass eine Leistung des Gläubigers vorliegt (Nichtleistungskondiktion).
2. Zuweisungsgehalt: Die Eingriffskondiktion greift nur, wenn der Eingreifende in den
   Zuweisungsgehalt eines Rechts des Gläubigers eingreift. Ein Recht hat Zuweisungsgehalt,
   wenn es dem Rechtsinhaber ausschließlich die Nutzung und Verwertung des betreffenden
   Gegenstands vorbehält. Eigentumsrecht, Urheberrecht, Persönlichkeitsrecht haben
   Zuweisungsgehalt.
3. Abgrenzung zur Leistungskondiktion: Die Leistungskondiktion (§ 812 Abs. 1 S. 1 Alt. 1 BGB)
   hat Vorrang vor der Eingriffskondiktion im Dreiecksverhältnis.
4. Keine Einschränkung durch Subsidiarität: Zwischen Täter und Eigentümer ist die
   Eingriffskondiktion direkt anwendbar.

Bedeutung: Klassischer Lehrfall zur Eingriffskondiktion und zum Zuweisungsgehalt im
Bereicherungsrecht. Grundlage für das Verständnis der §§ 812 ff. BGB.

Schlagwörter: § 812 BGB, Eingriffskondiktion, Zuweisungsgehalt, Nichtleistungskondiktion,
Bereicherungsrecht, Münzautomat, § 812 Abs. 1 S. 1 Alt. 2 BGB, Eigentumsrecht, BGB AT.
""".strip()},

  {"id": "steckbrief_schrottimmobilien", "skill": "bgb_at", "text": """
Schrottimmobilien-Fall (BGHZ 159, 94) — Bundesgerichtshof, XI. Zivilsenat,
16. Mai 2006, XI ZR 6/04

Sachverhalt: Anleger wurden durch Vermittler dazu gebracht, überteuerte Eigentumswohnungen
("Schrottimmobilien") zu erwerben, die durch Darlehen finanziert wurden. Die Banken,
die die Finanzierung übernahmen, waren in das Vermittlungssystem eingebunden. Als die
Wohnungen erheblich an Wert verloren und Mieten ausblieben, machten die Erwerber
Ansprüche wegen Aufklärungspflichtverletzung (culpa in contrahendo, c.i.c.) gegen
die Banken geltend.

Leitsätze (BGHZ 159, 94 — Schrottimmobilien):
1. Culpa in contrahendo (c.i.c.) / Haftung aus vorvertraglichem Schuldverhältnis
   (§ 311 Abs. 2 BGB, §§ 241 Abs. 2, 280 BGB): Eine Bank haftet dem Darlehensnehmer
   für Aufklärungspflichtverletzungen, wenn sie über einen schwerwiegenden Interessenkonflikt
   oder besondere Risiken aufklärungspflichtige Kenntnisse hat.
2. Ausnahmsweise Aufklärungspflicht der Bank über den Wert der Immobilie, wenn (a) die Bank
   einen Wissensvorsprung über Umstände hat, die für den Kaufentschluss des Käufers von
   entscheidender Bedeutung sind und (b) das finanzierte Geschäft mit dem Darlehen eine
   wirtschaftliche Einheit bildet.
3. Institutionalisiertes Zusammenwirken von Bank und Vermittler begründet Zurechnung
   von Täuschungshandlungen des Vermittlers zulasten der Bank (§ 278 BGB analog).

Bedeutung: Meilenstein der BGH-Rechtsprechung zur Bankenhaftung bei Schrottimmobilien.
Basis für zahlreiche Schadensersatzklagen geschädigter Anleger.

Schlagwörter: culpa in contrahendo, c.i.c., § 311 Abs. 2 BGB, Aufklärungspflichtverletzung,
Schrottimmobilien, Bankenhaftung, Wissensvorsprung, BGHZ 159 94, XI ZR 6/04, § 278 BGB,
wirtschaftliche Einheit, Schadensersatz.
""".strip()},

  {"id": "steckbrief_trierer_weinversteigerung", "skill": "bgb_at", "text": """
Trierer Weinversteigerung — Lehrbuchfall zum Erklärungsbewusstsein (BGB AT)
(Erklärungsbewusstsein, Willenserklärung, Rechtsbindungswille, fiktiver Lehrfall)

Sachverhalt (Lehrbuchbeispiel): Bei einer Weinversteigerung in Trier hebt ein Besucher
seinen Arm, um einem Bekannten zu winken und ihn zu grüßen. Der Auktionator interpretiert
das Armheben als Gebot und erteilt den Zuschlag. Der Besucher wollte keine Willenserklärung
abgeben und weigert sich zu zahlen. Fraglich ist, ob ohne Erklärungsbewusstsein (Bewusstsein,
eine rechtlich erhebliche Erklärung abzugeben) eine wirksame Willenserklärung vorliegt.

Rechtliche Bedeutung — Meinungsstreit zum Erklärungsbewusstsein:
1. Willenstheorie (strenge Auffassung): Fehlt das Erklärungsbewusstsein vollständig, liegt
   gar keine Willenserklärung vor. Der Besucher wäre danach nicht gebunden.
2. Erklärungstheorie (objektive Auffassung): Maßgeblich ist allein das äußere Erscheinungsbild
   — ein objektiver Empfänger darf auf die Erklärung vertrauen. Der Besucher wäre gebunden.
3. Herrschende Meinung / BGH-Lösung (Fahrlässigkeitslösung): Erklärungsbewusstsein ist
   grundsätzlich Voraussetzung der Willenserklärung. War sein Fehlen jedoch fahrlässig —
   hätte der Erklärende bei Anwendung der im Verkehr erforderlichen Sorgfalt erkennen können,
   dass sein Verhalten als Gebot aufgefasst wird —, so muss er sich die Erklärung zurechnen
   lassen. Rechtsfolge: Wirksame (aber anfechtbare) Willenserklärung, Anfechtung nach
   § 119 Abs. 1 BGB (Inhaltsirrtum), Schadensersatz nach § 122 BGB (negatives Interesse).

Einschlägige Normen: § 116 BGB (geheimer Vorbehalt), § 118 BGB (Scheingeschäft),
§ 119 Abs. 1 BGB (Anfechtung Inhaltsirrtum), § 122 BGB (Schadensersatz nach Anfechtung),
§ 133 BGB (Auslegung), § 157 BGB (Treu und Glauben bei Auslegung).

Dogmatische Bedeutung: Der Lehrfall ist zentrales Ausbildungsbeispiel für den Streit um das
Erklärungsbewusstsein als Tatbestandselement der Willenserklärung. Das Spannungsverhältnis
zwischen Willens- und Erklärungstheorie wird hier besonders anschaulich. Die h.M. folgt der
BGH-Fahrlässigkeitslösung: Schutz des Erklärungsgegners durch Zurechnung bei schuldhaft
fehlendem Erklärungsbewusstsein, kombiniert mit Anfechtungsrecht des Erklärenden.

Schlagwörter: Willenserklärung, Erklärungsbewusstsein, Rechtsbindungswille, Willenstheorie,
Erklärungstheorie, Fahrlässigkeitslösung, Anfechtung § 119 BGB, § 122 BGB, Versteigerung,
Armheben, Gebot, BGB AT, Rechtsgeschäftslehre, Lehrbuchfall, Lehrfall.
""".strip()},

  {"id": "steckbrief_verwirkung_kreditkuendigung", "skill": "bgb_at", "text": """
Verwirkung — Treu und Glauben (§ 242 BGB) bei Kreditkündigung
— Bundesgerichtshof, BGH NJW 2002, 3165

Sachverhalt: Eine Bank kündigte nach jahrelanger widerspruchsloser Zusammenarbeit ohne
sachlichen Grund und ohne Vorwarnung einen langjährigen Kredit fristlos. Der Kreditnehmer
berief sich auf Verwirkung des Kündigungsrechts: Die Bank habe durch ihr jahrelanges Schweigen
und Dulden das Vertrauen des Kreditnehmers erweckt, die Kündigung werde nicht mehr ausgeübt.

Leitsätze (§ 242 BGB — Treu und Glauben, Verwirkung):
1. Verwirkung ist ein Unterfall des Verbots widersprüchlichen Verhaltens (venire contra
   factum proprium) und ergibt sich aus § 242 BGB. Ein Recht ist verwirkt, wenn der
   Berechtigte es über längere Zeit nicht geltend gemacht hat (Zeitmoment) und der
   Verpflichtete darauf vertrauen durfte, das Recht werde auch künftig nicht mehr
   ausgeübt (Umstandsmoment).
2. Bloßes Zeitablauf genügt nicht für Verwirkung — erforderlich ist zusätzlich ein
   Vertrauenstatbestand (konkretes Verhalten des Berechtigten, das Vertrauen begründet).
3. Bei der Kreditkündigung gilt: Auch wenn keine ausdrückliche Kündigung erklärt wird,
   kann bei konkreten Umständen (z.B. jahrelange Duldung trotz Vertragsverletzung)
   eine Verwirkung des Kündigungsrechts eintreten.
4. Grenzen: Verwirkung ist keine Verjährung; sie setzt schützenswerte Vertrauensposition
   des Schuldners voraus.

Bedeutung: Leitfall zu Treu und Glauben (§ 242 BGB) und Verwirkung im Vertragsrecht.
§ 242 BGB ist einer der wichtigsten Generalklauseln des deutschen Zivilrechts.

Schlagwörter: § 242 BGB, Treu und Glauben, Verwirkung, venire contra factum proprium,
Zeitmoment, Umstandsmoment, widersprüchliches Verhalten, Kreditkündigung, Bank,
Vertrauensschutz, BGB AT.
""".strip()},

  {"id": "steckbrief_berliner_testament", "skill": "erbrecht", "text": """
Berliner Testament — Bindungswirkung (§ 2270 BGB)
— Bundesgerichtshof, IV. Zivilsenat, BGH NJW 1973, 240

Sachverhalt: Eheleute errichteten ein gemeinschaftliches Testament (Berliner Testament,
§ 2269 BGB), in dem sie sich gegenseitig als Alleinerben und nach dem Tod des Letztversterbenden
ein gemeinsames Kind als Schlusserben einsetzten. Nach dem Tod des ersten Ehegatten
widerrief der überlebende Ehegatte das Testament und setzte eine andere Person als Erben ein.

Leitsätze (§ 2270 BGB — wechselbezügliche Verfügung, Bindungswirkung):
1. Wechselbezüglichkeit (§ 2270 BGB): Verfügungen in einem gemeinschaftlichen Testament
   sind wechselbezüglich, wenn sie in dem Sinne voneinander abhängen, dass die eine
   Verfügung nicht ohne die andere gelten soll (gegenseitige Bedingtheit).
2. Bindungswirkung nach dem Tod des Erstversterbenden: Wechselbezügliche Verfügungen
   des gemeinschaftlichen Testaments werden nach dem Tod des erstversterbenden Ehegatten
   für den Überlebenden bindend — er kann sie nicht einseitig widerrufen.
3. Widerruf zu Lebzeiten beider Ehegatten: Zu Lebzeiten beider Ehegatten kann jeder
   Ehegatte seinen Teil des Testaments widerrufen (§ 2271 Abs. 1 BGB), muss den
   anderen jedoch benachrichtigen (§ 2271 Abs. 1 S. 2 BGB).
4. Erbverzicht und Schlusserbenbestimmung: Nach dem Tod des Erstversterbenden kann der
   Überlebende durch Erbverzicht (§ 2346 BGB) oder Ausschlagung der Erbschaft die
   Bindungswirkung überwinden.

Bedeutung: Leitfall zur Bindungswirkung des gemeinschaftlichen Testaments. Zentral für
das Erbrecht bei Ehegatten.

Schlagwörter: Berliner Testament, § 2269 BGB, § 2270 BGB, wechselbezügliche Verfügung,
Bindungswirkung, gemeinschaftliches Testament, § 2271 BGB, Schlusserbe, Widerruf, Erbrecht.
""".strip()},

  {"id": "steckbrief_pflichtteilsergaenzung", "skill": "erbrecht", "text": """
Pflichtteilsergänzung bei Schenkungen (BGHZ 98, 226) — Bundesgerichtshof, IV. Zivilsenat,
27. April 1987, IVa ZR 52/86
(§ 2325 BGB — 10-Jahres-Frist)

Sachverhalt: Der Erblasser hatte zu Lebzeiten seinem neuen Ehepartner Vermögenswerte
geschenkt, um seinen Kindern aus erster Ehe den Pflichtteil zu schmälern. Nach dem Tod
des Erblassers machten die Kinder einen Pflichtteilsergänzungsanspruch geltend. Die Schenkung
lag mehr als 10 Jahre vor dem Erbfall.

Leitsätze (BGHZ 98, 226 — § 2325 BGB, Pflichtteilsergänzung):
1. Pflichtteilsergänzungsanspruch (§ 2325 BGB): Pflichtteilsberechtigte (Abkömmlinge,
   Eltern, Ehegatte) können Ergänzung des Pflichtteils verlangen, wenn der Erblasser
   zu Lebzeiten Schenkungen gemacht hat, die den Nachlass und damit den Pflichtteil
   geschmälert haben.
2. 10-Jahres-Frist und Abschmelzungsregel: Schenkungen werden nur berücksichtigt, wenn
   sie innerhalb von 10 Jahren vor dem Erbfall vorgenommen wurden. Pro Jahr, das die
   Schenkung länger zurückliegt, vermindert sich der Ergänzungsanspruch um 10 %
   ("Abschmelzungsmodell", heute ausdrücklich in § 2325 Abs. 3 BGB).
3. Leistung an Ehegatten: Der BGH hat entschieden, dass die 10-Jahres-Frist bei
   Schenkungen an den Ehegatten erst mit der Scheidung oder dem Tod beginnt zu laufen
   (Hemmung während der Ehe).
4. Berechnung: Der Pflichtteil berechnet sich aus dem wirklichen Nachlass plus dem
   ergänzend anzurechnenden Schenkungswert.

Bedeutung: Grundlegendes Urteil zu § 2325 BGB. Klärt die Abschmelzungsregel und
die besondere Behandlung von Ehegatten bei der Pflichtteilsergänzung.

Schlagwörter: § 2325 BGB, Pflichtteilsergänzung, Schenkung, 10-Jahres-Frist,
Abschmelzungsmodell, BGHZ 98 226, Pflichtteil, Erblasser, Ehegatte, Erbrecht.
""".strip()},

  {"id": "steckbrief_alpine_investments", "skill": "europarecht", "text": """
Alpine Investments (EuGH C-384/93) — Europäischer Gerichtshof, 10. Mai 1995
(Dienstleistungsfreiheit, Herkunftsstaatsbeschränkung, cold calling)

Sachverhalt: Die Niederlande verboten niederländischen Finanzdienstleistern (Alpine
Investments), potenzielle Kunden in anderen EU-Mitgliedstaaten unaufgefordert telefonisch
zu kontaktieren (cold calling). Alpine Investments sah darin eine Verletzung der
Dienstleistungsfreiheit.

Leitsätze (EuGH C-384/93 — Herkunftsstaatsbeschränkung):
1. Herkunftsstaatsbeschränkungen fallen unter Art. 56 AEUV: Nicht nur Maßnahmen des
   Aufnahmestaats (klassischer Fall), sondern auch Maßnahmen des Herkunftsstaats, die
   die Ausfuhr von Dienstleistungen behindern, können gegen Art. 56 AEUV verstoßen.
2. Rechtfertigung: Die niederländische Maßnahme war durch zwingende Gründe des
   Allgemeininteresses (Schutz der Anleger, Integrität des Finanzmarkts) gerechtfertigt
   und verhältnismäßig.
3. Abgrenzung zu Keck (Warenverkehr): Im Warenverkehr sind bloße Verkaufsmodalitäten
   (Keck, 1993) nicht MEQR; im Dienstleistungsbereich gibt es keine analoge "Keck-Ausnahme".
4. Unterschied zu Säger: Alpine Investments zeigt, dass Art. 56 AEUV auch Herkunftsstaaten
   bindet (beide Richtungen der Freiheit).

Bedeutung: Präzisiert die Reichweite der Dienstleistungsfreiheit auf Herkunftsstaaten.
Wichtig für das Finanzdienstleistungsrecht.

Schlagwörter: EuGH C-384/93, Alpine Investments, cold calling, Dienstleistungsfreiheit,
Art. 56 AEUV, Herkunftsstaatsbeschränkung, Finanzmarkt, Keck, Verkaufsmodalitäten, Anleger.
""".strip()},

  {"id": "steckbrief_altmark_trans", "skill": "europarecht", "text": """
Altmark Trans (EuGH C-280/00) — Europäischer Gerichtshof, 24. Juli 2003
(Staatliche Beihilfen, öffentliche Ausgleichszahlungen, vier Kriterien, Art. 107 AEUV)

Sachverhalt: Die Altmark Trans GmbH erhielt vom Land Sachsen-Anhalt staatliche Zuschüsse
für den Betrieb eines öffentlichen Linienverkehrs (ÖPNV). Ein Konkurrenzunternehmen
klagte, es handele sich um eine unzulässige staatliche Beihilfe (Art. 107 AEUV), die
ohne Notifizierung gewährt worden sei.

Leitsätze (EuGH C-280/00 — Altmark-Kriterien):
1. Ausgleichszahlungen als keine Beihilfe (Altmark-Kriterien): Staatliche Ausgleichszahlungen
   für öffentliche Dienstleistungsverpflichtungen (Daseinsvorsorge) stellen keine staatliche
   Beihilfe (Art. 107 Abs. 1 AEUV) dar, wenn alle vier Altmark-Kriterien erfüllt sind:
   (1) Das Unternehmen trägt klar definierte gemeinnützige Verpflichtungen (Gemeinwirtschaftliche Verpflichtungen).
   (2) Die Parameter für den Ausgleich sind zuvor objektiv und transparent festgelegt.
   (3) Der Ausgleich überschreitet nicht die Kosten zuzüglich eines angemessenen Gewinns.
   (4) Der Ausgleich wird entweder durch öffentliche Ausschreibung ermittelt oder anhand
       der Kosten eines effizienten, gut geführten Unternehmens (Effizienzmaßstab).
2. Keine Beihilfe bei Erfüllung aller Kriterien: Sind alle vier Kriterien erfüllt,
   liegt keine staatliche Beihilfe vor; keine Notifizierung bei der EU-Kommission nötig.
3. Praktische Bedeutung: ÖPNV, Krankenhäuser, Postdienste, Rundfunk.

Bedeutung: Entscheidend für die Abgrenzung von Beihilfe und zulässigem Ausgleich bei
öffentlichen Dienstleistungen. Vier Altmark-Kriterien sind Prüfungsstandard.

Schlagwörter: EuGH C-280/00, Altmark Trans, staatliche Beihilfe, Art. 107 AEUV,
Altmark-Kriterien, Daseinsvorsorge, Ausgleichszahlungen, ÖPNV, Notifizierung,
gemeinwirtschaftliche Verpflichtungen.
""".strip()},

  {"id": "steckbrief_baumbast", "skill": "europarecht", "text": """
Baumbast (EuGH C-413/99) — Europäischer Gerichtshof, 17. September 2002
(Unionsbürgerschaft, unmittelbare Wirkung, Aufenthaltsrecht, Art. 21 AEUV)

Sachverhalt: Herr Baumbast, ein deutscher Staatsangehöriger, lebte mit seiner
kolumbianischen Ehefrau und Kindern in Großbritannien. Er war nicht mehr erwerbstätig
und seine Krankenversicherung hatte keine unbegrenzte Deckung. Großbritannien verweigerte
die Verlängerung seiner Aufenthaltserlaubnis.

Leitsätze (EuGH C-413/99 — Aufenthaltsrecht, Verhältnismäßigkeit):
1. Unmittelbare Wirkung des Aufenthaltsrechts (Art. 21 Abs. 1 AEUV): Das Aufenthaltsrecht
   der Unionsbürger (Art. 21 Abs. 1 AEUV, früher Art. 18 EGV) hat unmittelbare Wirkung —
   es verleiht direkt Rechte, auf die sich der Einzelne vor nationalen Gerichten berufen kann.
2. Verhältnismäßigkeit nationaler Einschränkungen: Mitgliedstaaten können das Aufenthaltsrecht
   aus Gründen der öffentlichen Ordnung, Sicherheit und Gesundheit sowie aus wirtschaftlichen
   Gründen beschränken, aber nur verhältnismäßig. Die Ausweisung aufgrund unzureichender
   Krankenversicherung war unverhältnismäßig.
3. Familienmitglieder aus Drittstaaten: Drittstaatsangehörige Familienangehörige von
   Unionsbürgern haben ein abgeleitetes Aufenthaltsrecht, das sich aus dem Aufenthaltsrecht
   des Unionsbürgers ergibt.
4. Erweiterung von Martinez Sala: Baumbast stärkt die Unionsbürgerschaft als eigenständige
   und direkt anwendbare Rechtsposition.

Bedeutung: Landmark case zur Unionsbürgerschaft und zum Aufenthaltsrecht als unmittelbar
wirksames Recht. Grundlage der Unionsbürger-Richtlinie 2004/38/EG.

Schlagwörter: EuGH C-413/99, Baumbast, Unionsbürgerschaft, Art. 21 AEUV, Aufenthaltsrecht,
unmittelbare Wirkung, Verhältnismäßigkeit, Familienangehörige, Richtlinie 2004/38/EG.
""".strip()},

  {"id": "steckbrief_brasserie_factortame", "skill": "europarecht", "text": """
Brasserie du Pêcheur / Factortame III (EuGH C-46/93 und C-48/93)
— Europäischer Gerichtshof, 5. März 1996
(Staatshaftung, qualifizierter Verstoß, Francovich-Erweiterung)

Sachverhalt: Zwei verbundene Rechtssachen:
- Brasserie du Pêcheur (Deutschland): Ein französisches Brauunternehmen klagte gegen
  Deutschland wegen eines Einfuhrverbots für Bier (Reinheitsgebot = MEQR), das EU-Recht
  verletzte.
- Factortame (UK): Britische Fischer spanischer Herkunft klagten gegen das britische
  Merchant Shipping Act, das gegen Niederlassungsfreiheit verstieß.

Leitsätze (EuGH C-46/93 — Staatshaftung, qualifizierter Verstoß):
1. Staatshaftung auch bei Gesetzgebung: Die Francovich-Haftung gilt nicht nur für
   Verwaltungsakte, sondern auch für Gesetze des Parlaments, die EU-Recht verletzen.
2. Drei Voraussetzungen der Staatshaftung: (1) Verletzung einer Norm, die dem Einzelnen
   Rechte verleiht, (2) qualifizierter (hinreichend schwerwiegender) Verstoß, (3) unmittelbarer
   Kausalzusammenhang zwischen Verstoß und Schaden.
3. Qualifizierter Verstoß: Ein Verstoß ist qualifiziert, wenn der Mitgliedstaat die
   Grenzen seiner Ermessen offenkundig und erheblich überschritten hat (z.B. klarer und
   eindeutiger Verstoß gegen gefestigte EuGH-Rechtsprechung).
4. Nationales Schadensersatzrecht gilt: Die Voraussetzungen und der Umfang des Schadensersatzes
   richten sich nach nationalem Recht, sofern es nicht diskriminierend ist und den
   EU-Anspruch nicht praktisch unmöglich macht.

Bedeutung: Wesentliche Erweiterung der Francovich-Staatshaftung auf Gesetzgebungsakte.
Drei-Stufen-Schema der Staatshaftung ist bis heute gültig.

Schlagwörter: EuGH C-46/93, Brasserie du Pêcheur, Factortame, Staatshaftung, qualifizierter
Verstoß, Francovich, Gesetzgebung, Art. 107 AEUV, Kausalität, nationales Schadensersatzrecht.
""".strip()},

  {"id": "steckbrief_cilfit", "skill": "europarecht", "text": """
CILFIT (EuGH Rs. 283/81) — Europäischer Gerichtshof, 6. Oktober 1982
(Vorlagepflicht, acte clair, acte éclairé, Art. 267 AEUV)

Sachverhalt: Das Corte Suprema di Cassazione (italienisches Kassationsgericht) fragte
den EuGH, unter welchen Voraussetzungen ein letztinstanzliches nationales Gericht
von der Vorlagepflicht nach Art. 177 EWGV (heute Art. 267 Abs. 3 AEUV) befreit ist.

Leitsätze (Rs. 283/81 — Vorlagepflicht, acte clair):
1. Grundsatz der Vorlagepflicht: Letztinstanzliche nationale Gerichte sind grundsätzlich
   verpflichtet, dem EuGH Fragen zur Auslegung des EU-Rechts vorzulegen (Art. 267 Abs. 3
   AEUV), um eine einheitliche Auslegung zu gewährleisten.
2. Ausnahmen (CILFIT-Formel):
   a) Acte clair: Die Vorlagepflicht entfällt, wenn die richtige Anwendung des EU-Rechts
      derart offenkundig ist, dass kein Raum für vernünftige Zweifel bleibt. Das setzt
      voraus, dass die Auslegung ebenso offensichtlich für die Gerichte anderer Mitgliedstaaten
      und den EuGH wäre.
   b) Acte éclairé: Die Vorlagepflicht entfällt, wenn der EuGH die Rechtsfrage bereits
      in einem gleichartigen Fall entschieden hat (obiter dicta genügen nicht).
3. Strenge Anforderungen an acte clair: Das Gericht muss alle Sprachfassungen des
   EU-Rechts berücksichtigen und die Besonderheiten der EU-Rechtssprache beachten.
4. Weiterentwicklung (EuGH, Consorzio Italian Management, 2021): Der EuGH hat die
   CILFIT-Anforderungen bestätigt, aber klarer gefasst.

Bedeutung: Grundlegendes Urteil zur Vorlagepflicht nach Art. 267 AEUV. CILFIT-Formel
ist der Maßstab für alle letztinstanzlichen Gerichte in der EU.

Schlagwörter: EuGH Rs. 283/81, CILFIT, Vorlagepflicht, acte clair, acte éclairé,
Art. 267 AEUV, Vorlageverfahren, letztinstanzliches Gericht, einheitliche Auslegung.
""".strip()},

  {"id": "steckbrief_costa_enel", "skill": "europarecht", "text": """
Costa/ENEL (EuGH Rs. 6/64) — Europäischer Gerichtshof, 15. Juli 1964

Flaminio Costa gegen ENEL (Ente Nazionale Energia Elettrica). Nach Verstaatlichung des
italienischen Elektrizitätssektors weigerte sich Costa, seine Stromrechnung zu zahlen, und
berief sich auf Verstoß gegen EWG-Recht.

Leitsätze — Vorrang des Gemeinschaftsrechts:
1. Das EWG-Recht ist in die Rechtsordnungen der Mitgliedstaaten integriert.
2. Die Mitgliedstaaten haben durch EWG-Beitritt dauerhaft Souveränitätsrechte eingeschränkt.
3. Das Gemeinschaftsrecht hat Vorrang (Anwendungsvorrang) vor dem nationalen Recht,
   einschließlich späterer nationaler Gesetze.
4. Nationale Gerichte müssen entgegenstehendes nationales Recht unangewendet lassen.

Bedeutung: Costa/ENEL begründet den Anwendungsvorrang des EU-Rechts. Nationaler
Gesetzgeber kann EU-Recht nicht durch spätere Gesetze außer Kraft setzen.
EuGH C-6/64, Anwendungsvorrang, Vorrang des Unionsrechts.
""".strip()},

  {"id": "steckbrief_dano", "skill": "europarecht", "text": """
Dano (EuGH C-333/13) — Europäischer Gerichtshof, 11. November 2014
(Unionsbürgerschaft, Sozialleistungen, wirtschaftlich inaktive Unionsbürger)

Sachverhalt: Frau Dano, rumänische Staatsangehörige, lebte seit Jahren in Deutschland,
war nie erwerbstätig und hatte keine ernsthafte Absicht, Arbeit zu suchen. Deutschland
verweigerte ihr Grundsicherungsleistungen (SGB II / Hartz IV). Sie berief sich auf das
Diskriminierungsverbot (Art. 18 AEUV) und die Unionsbürgerschaft.

Leitsätze (EuGH C-333/13 — Dano):
1. Kein unbegrenztes Sozialleistungsrecht für wirtschaftlich inaktive Unionsbürger:
   Mitgliedstaaten können wirtschaftlich inaktive Unionsbürger, die sich ausschließlich
   zum Bezug von Sozialleistungen im Land aufhalten, von bestimmten Sozialleistungen
   ausschließen.
2. Aufenthaltsrecht als Voraussetzung: Das Diskriminierungsverbot (Art. 18 AEUV) gilt
   nur im Rahmen eines rechtmäßigen Aufenthalts. Unionsbürger ohne ausreichende Mittel
   und Krankenversicherung haben kein Aufenthaltsrecht (Art. 7 Richtlinie 2004/38/EG).
3. Abkehr von Grzelczyk/Trojani: Der EuGH hat die weitgehende Solidaritätspflicht
   für wirtschaftlich inaktive Unionsbürger eingeschränkt.
4. Sozialhilfetourismus: Mitgliedstaaten dürfen sich davor schützen, dass die Einwanderung
   ausschließlich zum Sozialleistungsbezug erfolgt.

Bedeutung: Wichtiges Korrektiv zur Unionsbürgerrechtsprechung. Zeigt Grenzen der
Solidaritätspflicht der Aufnahmestaaten gegenüber wirtschaftlich inaktiven EU-Bürgern.

Schlagwörter: EuGH C-333/13, Dano, Sozialleistungen, wirtschaftlich inaktive Unionsbürger,
Art. 18 AEUV, Art. 20 AEUV, Aufenthaltsrecht, Richtlinie 2004/38/EG, SGB II, Hartz IV.
""".strip()},

  {"id": "steckbrief_dassonville", "skill": "europarecht", "text": """
Dassonville (EuGH Rs. 8/74) — Europäischer Gerichtshof, 11. Juli 1974
(Maßnahmen gleicher Wirkung wie mengenmäßige Beschränkungen, MEQR, Art. 34 AEUV)

Sachverhalt: Die belgische Regierung verlangte für Importe von Scotch Whisky aus
Frankreich ein offizielles Herkunftszeugnis der britischen Behörden, das nur erhältlich war,
wenn der Whisky direkt aus dem Vereinigten Königreich importiert wurde. Die Brüder Dassonville
importierten Scotch Whisky von Frankreich nach Belgien ohne dieses Zeugnis und wurden
strafrechtlich verfolgt.

Leitsätze (Rs. 8/74 — Dassonville-Formel, MEQR):
1. Dassonville-Formel (Definition der MEQR): "Jede Handelsregelung der Mitgliedstaaten,
   die geeignet ist, den innergemeinschaftlichen Handel unmittelbar oder mittelbar,
   tatsächlich oder potenziell zu behindern, ist als Maßnahme gleicher Wirkung wie eine
   mengenmäßige Beschränkung (MEQR) anzusehen."
2. Weite Definition: Die Formel erfasst nicht nur diskriminierende, sondern auch
   unterschiedslos anwendbare Maßnahmen, die den Import faktisch erschweren.
3. Einschränkung durch Cassis de Dijon: Unterschiedslos anwendbare Maßnahmen können
   aus zwingenden Erfordernissen des Allgemeininteresses (Cassis-Formel) gerechtfertigt
   sein; rein diskriminierende Maßnahmen nur nach Art. 36 AEUV (öffentliche Ordnung,
   Gesundheit, etc.).
4. Art. 34 AEUV: Mengenmäßige Einfuhrbeschränkungen und alle MEQR sind verboten
   (Art. 34 AEUV, früher Art. 30 EWGV/Art. 28 EGV).

Bedeutung: Grundlegendes Urteil zum freien Warenverkehr. Dassonville-Formel ist bis
heute der Ausgangspunkt jeder MEQR-Prüfung.

Schlagwörter: EuGH Rs. 8/74, Dassonville, MEQR, Maßnahmen gleicher Wirkung, Art. 34 AEUV,
freier Warenverkehr, Dassonville-Formel, Cassis de Dijon, mengenmäßige Beschränkungen.
""".strip()},

  {"id": "steckbrief_faccini_dori", "skill": "europarecht", "text": """
Faccini Dori (EuGH C-91/92) — Europäischer Gerichtshof, 14. Juli 1994
(Keine horizontale Direktwirkung von Richtlinien, Haustürgeschäfte)

Sachverhalt: Frau Faccini Dori widerrief einen Vertrag über einen Sprachkurs, den sie
bei einem Haustürgeschäft abgeschlossen hatte. Die Haustürwiderrufsrichtlinie (85/577/EWG)
war von Italien nicht umgesetzt worden. Fraglich war, ob sie sich direkt auf die Richtlinie
gegenüber dem Privatunternehmen berufen konnte.

Leitsätze (EuGH C-91/92 — horizontale Direktwirkung):
1. Bestätigung von Marshall I: Der EuGH bestätigte ausdrücklich, dass Richtlinien
   keine horizontale Direktwirkung zwischen Privatpersonen entfalten. Die Klägerin konnte
   sich nicht direkt auf die Haustürwiderrufsrichtlinie gegen das Privatunternehmen berufen.
2. Richtlinienkonforme Auslegung als Ausweg: Nationale Gerichte sind verpflichtet, nationales
   Recht richtlinienkonform auszulegen (Marleasing-Doktrin), auch wenn keine Direktwirkung
   besteht.
3. Staatshaftung (Francovich): Wenn der Staat eine Richtlinie nicht umsetzt und dem Einzelnen
   dadurch Schaden entsteht, haftet der Staat auf Schadensersatz (Francovich-Doktrin).
4. Abgrenzung: Auch Kücükdeveci (2010) hat keine horizontale Richtlinienwirkung begründet,
   sondern auf den allgemeinen Gleichheitsgrundsatz abgestellt.

Bedeutung: Bestätigt die restriktive Rechtsprechung zur Direktwirkung. Zeigt die alternativen
Wege (richtlinienkonforme Auslegung, Staatshaftung) zur Durchsetzung von Richtlinienrechten.

Schlagwörter: EuGH C-91/92, Faccini Dori, horizontale Direktwirkung, Richtlinie, Marshall I,
Haustürgeschäft, richtlinienkonforme Auslegung, Francovich, Staatshaftung, Art. 288 AEUV.
""".strip()},

  {"id": "steckbrief_foto_frost", "skill": "europarecht", "text": """
Foto-Frost (EuGH Rs. 314/85) — Europäischer Gerichtshof, 22. Oktober 1987
(Ungültigkeitserklärung von EU-Recht, Monopol des EuGH)

Sachverhalt: Das Finanzgericht Hamburg hatte Zweifel an der Gültigkeit einer EG-Verordnung
(Zollrecht). Das deutsche Gericht fragte, ob es die Verordnung selbst für ungültig erklären
darf oder ob es dem EuGH vorlegen muss.

Leitsätze (Rs. 314/85 — Ungültigkeitserklärung, Monopol EuGH):
1. Ungültigkeitserklärung ist ausschließliche Kompetenz des EuGH: Nationale Gerichte
   können Sekundärrecht der EU (Verordnungen, Richtlinien, Beschlüsse) nicht für ungültig
   erklären. Nur der EuGH ist dazu befugt (Ungültigkeitsmonopol des EuGH).
2. Pflicht zur Vorlage: Zweifelt ein nationales Gericht an der Gültigkeit von EU-Recht,
   muss es dem EuGH vorlegen (Art. 267 AEUV), auch wenn es kein letztinstanzliches Gericht
   ist (Ausnahme vom acte-clair-Prinzip: Ungültigkeitsfragen sind immer vorzulegen).
3. Einheitlicher Rechtsschutz: Würden nationale Gerichte EU-Recht selbst für ungültig
   erklären können, würde die einheitliche Anwendung des EU-Rechts im gesamten Binnenmarkt
   gefährdet.
4. Einstweiliger Rechtsschutz: Bei Eilbedürftigkeit können nationale Gerichte die
   Anwendung von EU-Recht aussetzen und gleichzeitig vorlegen (EuGH Zuckerfabrik).

Bedeutung: Festigt das Monopol des EuGH bei der Ungültigkeitserklärung von EU-Sekundärrecht.
Foto-Frost-Doktrin ist fundamentales Prinzip des EU-Verfassungsrechts.

Schlagwörter: EuGH Rs. 314/85, Foto-Frost, Ungültigkeitserklärung, Ungültigkeitsmonopol,
Art. 267 AEUV, nationales Gericht, Vorlage, Sekundärrecht, einheitliche Anwendung.
""".strip()},

  {"id": "steckbrief_gebhard", "skill": "europarecht", "text": """
Gebhard (EuGH C-55/94) — Europäischer Gerichtshof, 30. November 1995
(Niederlassungsfreiheit, Vier-Stufen-Test, Art. 49 AEUV)

Sachverhalt: Der deutsche Rechtsanwalt Reinhard Gebhard war in Mailand dauerhaft als
Avvocato tätig, ohne die für die Niederlassung erforderliche Erlaubnis der italienischen
Anwaltskammer eingeholt zu haben. Er wurde disziplinarisch verfolgt. Der EuGH klärte,
ob die Niederlassungsfreiheit verletzt war.

Leitsätze (EuGH C-55/94 — Gebhard, Vier-Stufen-Test):
1. Abgrenzung Niederlassung/Dienstleistungsfreiheit: Niederlassung (Art. 49 AEUV) liegt vor,
   wenn jemand dauerhaft und stabil am wirtschaftlichen Leben eines anderen Mitgliedstaats
   teilnimmt. Dienstleistungsfreiheit (Art. 56 AEUV) gilt für vorübergehende Tätigkeiten.
2. Vier-Stufen-Test (Gebhard-Formel) — Rechtfertigung von Beschränkungen der Grundfreiheiten:
   Nationale Maßnahmen, die Grundfreiheiten beschränken, sind nur zulässig, wenn sie
   (1) nicht diskriminierend sind,
   (2) durch zwingende Allgemeininteressen gerechtfertigt sind,
   (3) geeignet sind, das angestrebte Ziel zu erreichen,
   (4) nicht über das zur Zielerreichung erforderliche Maß hinausgehen (Verhältnismäßigkeit).
3. Anerkennungsprinzip: Bei reglementierten Berufen müssen Mitgliedstaaten ausländische
   Qualifikationen anerkennen, soweit sie gleichwertig sind (Anerkennungsrichtlinien).
4. Universalität der Formel: Die Gebhard-Formel gilt für alle Grundfreiheiten (nicht nur
   Niederlassungsfreiheit).

Bedeutung: Die Gebhard-Formel ist der universelle Vier-Stufen-Test für die Rechtfertigung
von Beschränkungen der EU-Grundfreiheiten. Zentrales Schema im EU-Wirtschaftsrecht.

Schlagwörter: EuGH C-55/94, Gebhard, Niederlassungsfreiheit, Art. 49 AEUV, Vier-Stufen-Test,
Verhältnismäßigkeit, zwingende Allgemeininteressen, Dienstleistungsfreiheit, Art. 56 AEUV.
""".strip()},

  {"id": "steckbrief_keck", "skill": "europarecht", "text": """
Keck und Mithouard (EuGH Rs. C-267/91, C-268/91) — EuGH, 24. November 1993

Keck und Mithouard wurden wegen Verstoßes gegen ein französisches Gesetz verurteilt,
das den Weiterverkauf von Waren unter Einstandspreis (Verkauf mit Verlust) verbot.

Leitsätze — Verkaufsmodalitäten:
1. Keck-Formel: Nationale Regelungen über Verkaufsmodalitäten (wann, wo, von wem, zu welchem
   Preis Waren verkauft werden dürfen) fallen nicht unter Art. 34 AEUV (Warenverkehrsfreiheit),
   wenn sie für alle Wirtschaftsteilnehmer im nationalen Hoheitsgebiet gelten und den
   tatsächlichen Zugang zum Markt nicht stärker beeinträchtigen als für inländische Waren.
2. Abgrenzung Produktanforderungen (fallen unter Art. 34 AEUV) vs. Verkaufsmodalitäten
   (fallen grundsätzlich nicht darunter, Keck-Ausnahme).

Bedeutung: Schränkt die Weite von Cassis de Dijon ein; verhindert Missbrauch der
Warenverkehrsfreiheit bei bloßen Verkaufsmodalitäten. EuGH C-267/91, Keck-Formel.
""".strip()},

  {"id": "steckbrief_koebler", "skill": "europarecht", "text": """
Köbler (EuGH C-224/01) — Europäischer Gerichtshof, 30. September 2003
(Staatshaftung, höchstes Gericht, qualifizierter Verstoß)

Sachverhalt: Prof. Dr. Köbler war österreichischer Universitätsprofessor und beantragte
eine Dienstalterszulage, die nach österreichischem Recht nur für in Österreich zurückgelegte
Dienstzeiten gewährt wurde — nicht für Beschäftigungszeiten in anderen EU-Mitgliedstaaten.
Der Verwaltungsgerichtshof (höchstes Verwaltungsgericht) versagte die Zulage. Köbler klagte
auf Staatshaftung wegen Verletzung der Arbeitnehmerfreizügigkeit (Art. 45 AEUV) durch das
höchste Gericht.

Leitsätze (EuGH C-224/01 — Staatshaftung, höchstes Gericht):
1. Staatshaftung auch bei Rechtsprechungsorganen: Ein Mitgliedstaat kann für Schäden
   haften, die dem Einzelnen durch Verstöße des höchsten nationalen Gerichts gegen
   EU-Recht entstehen (Erweiterung der Francovich/Brasserie-Rechtsprechung auf Gerichte).
2. Qualifizierter Verstoß als Voraussetzung: Die Haftung tritt nur bei einem qualifizierten
   Verstoß ein — also wenn das Gericht die einschlägige EU-Rechtsprechung des EuGH
   offenkundig verkannt hat und die Vorlagepflicht nach Art. 267 AEUV verletzt hat.
3. Hohe Hürde: Angesichts der Funktion der Rechtssicherheit und der Rechtskraft ist der
   Maßstab strenger als bei Verwaltungshandeln. Einfache Rechtsirrtümer genügen nicht.
4. Vorlagepflicht als Sicherheitsnetz: Hätte das höchste Gericht vorgelegt und der EuGH
   hätte die Rechtsfrage im Sinne Köblers entschieden, wäre der Schaden vermieden worden.

Bedeutung: Fundamentales Urteil zur Staatshaftung wegen Justizirrtums. Stärkt den Druck
auf letztinstanzliche Gerichte zur Vorlage an den EuGH.

Schlagwörter: EuGH C-224/01, Köbler, Staatshaftung, höchstes Gericht, qualifizierter Verstoß,
Art. 267 AEUV, Vorlagepflicht, Francovich, Brasserie, Arbeitnehmerfreizügigkeit, Art. 45 AEUV.
""".strip()},

  {"id": "steckbrief_laval", "skill": "europarecht", "text": """
Laval (EuGH C-341/05) — Europäischer Gerichtshof, 18. Dezember 2007
(Streikrecht, Dienstleistungsfreiheit, Entsenderecht, Kollektivmaßnahmen)

Sachverhalt: Das lettische Bauunternehmen Laval entsandte Arbeitnehmer nach Schweden,
wo schwedische Gewerkschaften durch kollektive Maßnahmen (Blockade) versuchten, Laval
zur Anwendung schwedischer Tarifverträge zu zwingen. Laval sah darin eine Verletzung
der Dienstleistungsfreiheit.

Leitsätze (EuGH C-341/05 — Streikrecht und Dienstleistungsfreiheit):
1. Streikrecht als Grundrecht — aber kein Vorrang: Das Streikrecht ist als Grundrecht
   anerkannt (Art. 28 GRCh), kann aber die Ausübung der Dienstleistungsfreiheit beschränken.
2. Kollektive Maßnahmen als Beschränkung der Dienstleistungsfreiheit: Gewerkschaftliche
   Maßnahmen, die einen Dienstleistungserbringer zwingen, höhere als die Mindestbedingungen
   der Entsenderichtlinie anzuwenden, sind eine Beschränkung der Dienstleistungsfreiheit
   (Art. 56 AEUV).
3. Entsenderichtlinie (96/71/EG) als Maximum: Die Entsenderichtlinie legt Mindestbedingungen
   fest; Aufnahmestaaten dürfen ausländische Dienstleister grundsätzlich nicht dazu
   zwingen, über diese Mindestbedingungen hinaus tätig zu werden.
4. Verhältnismäßigkeit: Die schwedischen Gewerkschaftsmaßnahmen waren unverhältnismäßig.

Bedeutung: Kontroverse Entscheidung, die das Streikrecht der Dienstleistungsfreiheit
unterordnet. Zusammen mit Viking Grundlage für die Debatte über "social dumping".

Schlagwörter: EuGH C-341/05, Laval, Streikrecht, Dienstleistungsfreiheit, Art. 56 AEUV,
Entsenderichtlinie 96/71/EG, kollektive Maßnahmen, Viking, Gewerkschaft, Verhältnismäßigkeit.
""".strip()},

  {"id": "steckbrief_les_verts", "skill": "europarecht", "text": """
Les Verts (EuGH Rs. 294/83) — Europäischer Gerichtshof, 23. April 1986
(EG als Rechtsgemeinschaft, Nichtigkeitsklage, Art. 230 EGV, Art. 263 AEUV)

Sachverhalt: Die französische Partei "Les Verts" (Die Grünen) klagte vor dem EuGH gegen
eine Entscheidung des Europäischen Parlaments über die Verteilung von Haushaltsmitteln
für den Europawahlkampf, von der "Les Verts" als nichtparlamentarische Partei
ausgeschlossen worden war.

Leitsätze (Rs. 294/83 — EG als Rechtsgemeinschaft):
1. EG als Rechtsgemeinschaft (Communauté de droit): Die Europäische Gemeinschaft ist
   eine Rechtsgemeinschaft — weder die Mitgliedstaaten noch die Organe der EG sind
   der Kontrolle durch Recht entzogen. Alle Rechtsakte der EG-Organe müssen mit dem
   EG-Primärrecht vereinbar sein.
2. Vollständiges Rechtsschutzsystem: Der EG-Vertrag schafft ein vollständiges System
   von Klagemöglichkeiten und Verfahren, um die Rechtmäßigkeit von Handlungen der
   EG-Organe zu kontrollieren (gerichtliche Kontrolle aller Organe).
3. Erweiterung der Klagebefugnis: Auch Handlungen des Europäischen Parlaments (damals
   nicht ausdrücklich in Art. 173 EWGV aufgeführt) unterliegen der Nichtigkeitsklage,
   wenn sie Rechtswirkungen gegenüber Dritten entfalten.
4. Grundlage für Art. 263 AEUV: Das Urteil hat zur Erweiterung der Nichtigkeitsklage
   auf alle Organe mit Außenwirkung beigetragen.

Bedeutung: Grundlegendes Verfassungsurteil der EU. Begründet das Konzept der EU als
Rechtsgemeinschaft und das vollständige Rechtsschutzsystem.

Schlagwörter: EuGH Rs. 294/83, Les Verts, Rechtsgemeinschaft, communauté de droit,
Art. 263 AEUV, Nichtigkeitsklage, gerichtliche Kontrolle, Europäisches Parlament,
Klagebefugnis, Europarecht.
""".strip()},

  {"id": "steckbrief_maastricht", "skill": "europarecht", "text": """
Maastricht-Urteil / Brunner-Urteil (BVerfGE 89, 155) — Bundesverfassungsgericht,
12. Oktober 1993, 2 BvR 2134/92 und 2 BvR 2159/92

Verfassungsmäßigkeit des Maastricht-Vertrags (Vertrag über die Europäische Union, 1992).
Beschwerdeführer u.a. Manfred Brunner, daher auch Brunner-Urteil.

Leitsätze:
1. Der Maastricht-Vertrag ist mit dem GG vereinbar, aber unter dem Vorbehalt, dass die
   EU nicht über ihre Kompetenzen hinaus handelt (Ultra-vires-Kontrolle).
2. Staatsvolk-Demokratie: Die demokratische Legitimation der EU fließt über die
   Mitgliedstaaten und ihre Parlamente; ein eigenständiges EU-Volk im staatsrechtlichen
   Sinne existiert nicht.
3. Kompetenz-Kompetenz: Die EU hat keine Kompetenz, sich selbst weitere Kompetenzen zu
   verleihen; dies liegt bei den Mitgliedstaaten als "Herren der Verträge".
4. Identitätskontrolle des BVerfG: Verletzungen von Verfassungsidentität (Art. 79 Abs. 3 GG)
   können vom BVerfG geprüft werden.

Bedeutung: Vorläufer und Grundlage des Lissabon-Urteils (BVerfGE 123, 267).
BVerfGE 89, 155, Maastricht, Brunner, Integrationsgrenze.
""".strip()},

  {"id": "steckbrief_mangold", "skill": "europarecht", "text": """
Mangold (EuGH Rs. C-144/04) — Europäischer Gerichtshof, 22. November 2005

Werner Mangold, 56 Jahre, wurde befristet eingestellt. Das deutsche Recht erlaubte
unbegrenzte Befristung für Arbeitnehmer über 52 Jahre ohne sachlichen Grund.

Leitsätze:
1. Das Verbot der Altersdiskriminierung ist ein allgemeiner Grundsatz des Unionsrechts,
   der unabhängig von der Umsetzungsfrist der Gleichbehandlungsrahmenrichtlinie gilt.
2. Nationale Gerichte müssen EU-rechtswidrige nationale Vorschriften unangewendet lassen,
   auch wenn die Umsetzungsfrist noch nicht abgelaufen ist.
3. Erga-omnes-Wirkung: Allgemeine Grundsätze des EU-Rechts wirken horizontal.

Bedeutung: Mangold ist umstritten — BVerfG und einige Stimmen kritisierten die extensive
Ableitung von Grundsätzen ohne ausdrückliche Rechtsgrundlage (EuGH C-144/04).
Altersdiskriminierung, allgemeiner Grundsatz Unionsrecht.
""".strip()},

  {"id": "steckbrief_marleasing", "skill": "europarecht", "text": """
Marleasing (EuGH C-106/89) — Europäischer Gerichtshof, 13. November 1990
(Richtlinienkonforme Auslegung, Pflicht der nationalen Gerichte)

Sachverhalt: Ein spanisches Gericht hatte über die Nichtigkeit einer Gesellschaftsgründung
zu entscheiden. Die GmbH-Richtlinie (erste gesellschaftsrechtliche Richtlinie, 68/151/EWG)
enthielt eine abschließende Liste von Nichtigkeitsgründen, die in Spanien (noch) nicht
umgesetzt worden war. Konnte das Gericht das spanische Recht richtlinienkonform auslegen?

Leitsätze (EuGH C-106/89 — Marleasing):
1. Richtlinienkonforme Auslegungspflicht: Nationale Gerichte sind verpflichtet, ihr gesamtes
   nationales Recht — sowohl vor als auch nach Erlass der Richtlinie erlassene Normen —
   im Licht des Wortlauts und Zwecks der Richtlinie auszulegen, um das von ihr angestrebte
   Ziel zu erreichen.
2. Umfang der Pflicht: Die richtlinienkonforme Auslegung gilt für das gesamte nationale
   Recht, nicht nur für Umsetzungsvorschriften. Auch älteres Recht ist richtlinienkonform
   auszulegen.
3. Grenze contra legem: Die richtlinienkonforme Auslegung findet ihre Grenze dort, wo
   sie zu einer Auslegung contra legem führen würde (klarer Wortlaut schließt richtlinienkonforme
   Auslegung aus — Pfeiffer, EuGH 2004).
4. Keine Direktwirkung trotzdem: Die richtlinienkonforme Auslegung ist kein Surrogat
   für Direktwirkung — sie löst das Problem nur, wenn nationales Recht auslegungsfähig ist.

Bedeutung: Grundlegendes Urteil zur richtlinienkonformen Auslegung. Kernpflicht jedes
nationalen Gerichts beim Umgang mit EU-Richtlinien.

Schlagwörter: EuGH C-106/89, Marleasing, richtlinienkonforme Auslegung, Pflicht, nationales Gericht,
contra legem, Pfeiffer, Direktwirkung, Art. 288 AEUV, Richtlinie, Auslegung.
""".strip()},

  {"id": "steckbrief_marshall_i", "skill": "europarecht", "text": """
Marshall I (EuGH Rs. 152/84) — Europäischer Gerichtshof, 26. Februar 1986
(Keine horizontale Direktwirkung von Richtlinien, Art. 288 AEUV)

Sachverhalt: Helen Marshall, Angestellte der Southampton Area Health Authority
(öffentlicher Arbeitgeber), wurde mit 62 Jahren in den Ruhestand versetzt, obwohl männliche
Kollegen bis 65 arbeiten durften. Sie berief sich auf die Gleichbehandlungsrichtlinie
(76/207/EWG), die von Großbritannien nicht fristgerecht umgesetzt worden war.

Leitsätze (Rs. 152/84 — Marshall I):
1. Vertikale Direktwirkung nicht umgesetzter Richtlinien: Eine Richtlinie, die einem Staat
   klare und unbedingte Verpflichtungen auferlegt, die er nach Ablauf der Umsetzungsfrist
   nicht erfüllt hat, kann vom Einzelnen gegenüber dem Staat (und staatlichen Stellen)
   unmittelbar angewendet werden (vertikale Direktwirkung).
2. Keine horizontale Direktwirkung: Eine Richtlinie kann dem Einzelnen gegenüber einer
   anderen Privatperson kein Recht verleihen, auf das er sich vor Gericht berufen könnte
   (keine horizontale Direktwirkung). Richtlinien verpflichten nur Mitgliedstaaten.
3. Emissionsfehler des Staates: Wer gegen eine Richtlinie verstößt, die er hätte umsetzen
   müssen, kann sich nicht darauf berufen, dass die Richtlinie nicht gegen ihn gilt.
4. Abgrenzung von Verordnungen: Verordnungen (Art. 288 Abs. 2 AEUV) haben volle Direktwirkung
   auch gegenüber Privaten; Richtlinien nicht.

Bedeutung: Klassische Entscheidung zur fehlenden horizontalen Direktwirkung von EU-Richtlinien.
Grundlage der richtlinienkonformen Auslegung und des Staatshaftungsrechts (Francovich).

Schlagwörter: EuGH Rs. 152/84, Marshall I, Richtlinie, horizontale Direktwirkung, vertikale
Direktwirkung, Art. 288 AEUV, Gleichbehandlung, keine horizontale Wirkung, Privatperson.
""".strip()},

  {"id": "steckbrief_martinez_sala", "skill": "europarecht", "text": """
Martinez Sala (EuGH C-85/96) — Europäischer Gerichtshof, 12. Mai 1998
(Unionsbürgerschaft, Diskriminierungsverbot, Art. 18, 20 AEUV)

Sachverhalt: María Martínez Sala, eine spanische Staatsangehörige, lebte seit Jahren
in Deutschland, war aber nicht erwerbstätig. Deutschland verweigerte ihr eine Leistung
(Kindererziehungsgeld), da sie keinen Aufenthaltstitel besaß, obwohl deutsche Staatsangehörige
und EU-Ausländer mit Aufenthaltstitel die Leistung erhielten.

Leitsätze (EuGH C-85/96 — Unionsbürgerschaft):
1. Unionsbürgerschaft (Art. 20 AEUV) als unmittelbar anwendbarer Status: Jeder EU-Bürger
   ist Unionsbürger; diese Eigenschaft verleiht das Recht, sich nicht wegen der
   Staatsangehörigkeit diskriminieren zu lassen, soweit der Anwendungsbereich des EU-Rechts
   eröffnet ist.
2. Diskriminierungsverbot (Art. 18 AEUV): Sobald ein EU-Bürger sich rechtmäßig in einem
   anderen Mitgliedstaat aufhält, darf er gegenüber Staatsangehörigen dieses Staates
   nicht wegen der Staatsangehörigkeit benachteiligt werden.
3. Rechtmäßiger Aufenthalt als Anknüpfungspunkt: Der EuGH knüpft die Anwendung des
   Diskriminierungsverbots an den rechtmäßigen Aufenthalt — nicht an Erwerbstätigkeit.
4. Wegbereiter der Baumbast-Rechtsprechung: Martinez Sala öffnete die Tür zur unmittelbaren
   Wirkung der Unionsbürgerschaft als eigenständige Rechtsgrundlage.

Bedeutung: Pioneering case zur Unionsbürgerschaft als Grundlage des EU-Diskriminierungsverbots.
Startpunkt einer bedeutenden Rechtsprechungslinie.

Schlagwörter: EuGH C-85/96, Martinez Sala, Unionsbürgerschaft, Art. 20 AEUV, Art. 18 AEUV,
Diskriminierungsverbot, Staatsangehörigkeit, rechtmäßiger Aufenthalt, Kindererziehungsgeld.
""".strip()},

  {"id": "steckbrief_omega", "skill": "europarecht", "text": """
Omega Spielhallen (EuGH Rs. C-36/02) — Europäischer Gerichtshof, 14. Oktober 2004

Eine Bonn Behörde verbot den Betrieb der "Laserdrome"-Anlage der Firma Omega Spielhallen
GmbH, in der Spieler symbolisch auf Menschen schossen (Laserspiel). Omega betrieb die
Anlage mit Geräten eines britischen Unternehmens. Die Behörde sah die Menschenwürde verletzt.

Leitsätze — Grundrechte als Schranke der Grundfreiheiten:
1. Mitgliedstaaten dürfen Grundfreiheiten (hier: Dienstleistungsfreiheit) beschränken,
   um nationale Grundrechtswerte (hier: Menschenwürde, Art. 1 GG) zu schützen.
2. Die Menschenwürde ist auch ein allgemeiner Grundsatz des Gemeinschaftsrechts.
3. Verhältnismäßigkeit ist zu prüfen — nationale Wertvorstellungen können legitimer Grund
   für Beschränkungen sein, auch wenn andere Mitgliedstaaten die Tätigkeit erlauben.

Bedeutung: Zeigt, wie nationale Grundrechtswerte EU-Grundfreiheiten einschränken können.
Grundrechte als Schranke, Menschenwürde, EuGH C-36/02, Dienstleistungsfreiheit.
""".strip()},

  {"id": "steckbrief_pfeiffer", "skill": "europarecht", "text": """
Pfeiffer (EuGH C-397/01 bis C-403/01) — Europäischer Gerichtshof, 5. Oktober 2004
(Richtlinienkonforme Auslegung, contra legem, Arbeitszeitrichtlinie)

Sachverhalt: Deutsche Rettungssanitäter klagten gegen überlange Arbeitszeiten (bis zu
49 Stunden pro Woche) auf der Grundlage der Arbeitszeitrichtlinie (93/104/EG), die
eine 48-Stunden-Woche vorschrieb. Deutschland hatte die Richtlinie nicht vollständig
umgesetzt. Fraglich war, ob die richtlinienkonforme Auslegung des deutschen ArbZG
möglich war.

Leitsätze (EuGH C-397/01 — Pfeiffer):
1. Pflicht zur richtlinienkonformen Auslegung: Nationale Gerichte müssen ihr gesamtes
   nationales Recht richtlinienkonform auslegen, um das Ziel der Richtlinie zu erreichen
   (Bestätigung von Marleasing).
2. Grenze: contra legem: Die richtlinienkonforme Auslegung findet ihre Grenze, wenn
   sie zu einer Auslegung contra legem des nationalen Rechts führen würde — d.h. wenn
   der klare und eindeutige Wortlaut des nationalen Rechts der richtlinienkonformen
   Auslegung entgegensteht.
3. Unmöglichkeit richtlinienkonformer Auslegung → Staatshaftung: Wenn eine richtlinienkonforme
   Auslegung nicht möglich ist, können die Betroffenen ggf. Staatshaftung (Francovich)
   geltend machen.
4. Horizontale Lage: Selbst bei contra legem-Sperre kann keine horizontale Direktwirkung
   begründet werden; nur vertikale Direktwirkung ist möglich.

Bedeutung: Präzisiert die Grenzen der Marleasing-Pflicht. Contra-legem-Grenze ist
entscheidendes Kriterium für die Reichweite der richtlinienkonformen Auslegung.

Schlagwörter: EuGH C-397/01, Pfeiffer, richtlinienkonforme Auslegung, contra legem,
Arbeitszeitrichtlinie, Marleasing, Grenze, Staatshaftung, Francovich, Art. 288 AEUV.
""".strip()},

  {"id": "steckbrief_plaumann", "skill": "europarecht", "text": """
Plaumann & Co. (EuGH Rs. 25/62) — Europäischer Gerichtshof, 15. Juli 1963

Plaumann, ein Klementinen-Importeur, klagte auf Nichtigerklärung einer
Kommissionsentscheidung, die Zollbefreiungen verweigerte.

Leitsätze — Plaumann-Formel (Zulässigkeit der Nichtigkeitsklage, Art. 263 AEUV):
1. Eine natürliche oder juristische Person ist nur dann individuell betroffen (Art. 263
   Abs. 4 AEUV), wenn eine Entscheidung sie wegen bestimmter persönlicher Eigenschaften oder
   besonderer Umstände berührt, die sie aus dem Kreis aller übrigen Personen herausheben.
2. Wer als Mitglied einer offenen Gruppe (z.B. alle Klementinen-Importeure) betroffen ist,
   ist nicht individuell betroffen — Klage unzulässig.

Bedeutung: Die Plaumann-Formel begrenzt den Zugang Privater zum EuGH erheblich.
Stark kritisiert als zu restriktiv. EuGH C-25/62, individuelle Betroffenheit, Nichtigkeitsklage.
""".strip()},

  {"id": "steckbrief_saeger_dennemeyer", "skill": "europarecht", "text": """
Säger/Dennemeyer (EuGH C-76/90) — Europäischer Gerichtshof, 25. Juli 1991
(Dienstleistungsfreiheit, Beschränkungsverbot, Art. 56 AEUV)

Sachverhalt: Die britische Firma Dennemeyer bot deutschen Unternehmen die Überwachung
ihrer Patente und Fristen an (Patent-Renewals-Service). Dies war in Deutschland Rechtsanwälten
und Patentanwälten vorbehalten. Deutschland verbot Dennemeyer die Tätigkeit mangels
Zulassung.

Leitsätze (EuGH C-76/90 — Dienstleistungsfreiheit, Beschränkungsverbot):
1. Beschränkungsverbot (Art. 56 AEUV): Art. 56 AEUV verbietet nicht nur diskriminierende,
   sondern auch unterschiedslos anwendbare nationale Regelungen, die geeignet sind,
   die Tätigkeit eines Dienstleistungserbringers aus einem anderen Mitgliedstaat zu
   untersagen oder zu behindern.
2. Breiter Anwendungsbereich: Bereits die potenzielle Behinderung einer grenzüberschreitenden
   Dienstleistung (auch ohne Diskriminierung) kann einen Verstoß gegen Art. 56 AEUV darstellen.
3. Rechtfertigung: Beschränkungen sind nur zulässig aus zwingenden Gründen des
   Allgemeininteresses und müssen verhältnismäßig sein (Gebhard-Formel).
4. Herkunftslandprinzip: Ein Dienstleistungserbringer unterliegt grundsätzlich dem Recht
   seines Herkunftsstaats und muss im Aufnahmestaat nicht zusätzliche Anforderungen erfüllen,
   wenn sein Herkunftsstaat gleichwertigen Schutz bietet.

Bedeutung: Wegweisendes Urteil zur Dienstleistungsfreiheit. Erweitert das Beschränkungsverbot
auf unterschiedslos anwendbare Maßnahmen (parallel zu Cassis de Dijon beim Warenverkehr).

Schlagwörter: EuGH C-76/90, Säger Dennemeyer, Dienstleistungsfreiheit, Art. 56 AEUV,
Beschränkungsverbot, unterschiedslos anwendbar, zwingende Allgemeininteressen, Herkunftslandprinzip.
""".strip()},

  {"id": "steckbrief_simmenthal_ii", "skill": "europarecht", "text": """
Simmenthal II (EuGH Rs. 106/77) — Europäischer Gerichtshof, 9. März 1978
(Vorrang des EU-Rechts, nationales Gericht, unmittelbare Anwendung)

Sachverhalt: Das Pretura (Amtsgericht) von Susa in Italien war mit einem Fall befasst,
bei dem nationales italienisches Recht mit Gemeinschaftsrecht (EG-Recht) unvereinbar war.
Das Pretura fragte den EuGH, ob es das nationale Recht von sich aus unangewendet lassen
durfte, oder ob es zunächst die Verfassungswidrigkeit durch das Verfassungsgericht
feststellen lassen musste.

Leitsätze (Rs. 106/77 — Anwendungsvorrang, nationales Gericht):
1. Anwendungsvorrang des Unionsrechts: Das Gemeinschaftsrecht (EU-Recht) hat Vorrang vor
   jedem entgegenstehenden nationalen Recht, einschließlich späterer nationaler Gesetze.
   Dies gilt für alle nationalen Gerichte — nicht nur für Verfassungsgerichte.
2. Pflicht zur unmittelbaren Nichtanwendung: Jedes nationale Gericht ist verpflichtet,
   entgegenstehendes nationales Recht von Amts wegen unangewendet zu lassen — ohne
   dass es die Nichtigkeit des nationalen Rechts durch ein höheres Gericht (z.B.
   Verfassungsgericht) feststellen lassen müsste.
3. Kein Verfahrenserfordernis: Mechanismen des nationalen Rechts, die eine Überprüfung
   durch das Verfassungsgericht vorschreiben, dürfen den Anwendungsvorrang nicht verzögern
   oder verhindern.
4. Effet utile: Die volle Wirksamkeit des Gemeinschaftsrechts (effet utile) würde
   beeinträchtigt, wenn nationale Gerichte nicht sofort handeln könnten.

Bedeutung: Fundamentales Urteil zum Anwendungsvorrang des EU-Rechts. Jedes nationale
Gericht ist unmittelbarer Hüter des EU-Rechts.

Schlagwörter: EuGH Rs. 106/77, Simmenthal II, Anwendungsvorrang, EU-Recht, nationales Gericht,
unmittelbare Anwendung, effet utile, Vorrang, Verfassungsgericht, Europarecht.
""".strip()},

  {"id": "steckbrief_viking_line", "skill": "europarecht", "text": """
Viking Line (EuGH C-438/05) — Europäischer Gerichtshof, 11. Dezember 2007
(Niederlassungsfreiheit, kollektive Maßnahmen, Streikrecht, Art. 49 AEUV)

Sachverhalt: Das finnische Fährschiffunternehmen Viking Line wollte sein Schiff Rosella
auf Estland umflaggen (Reflagging), um finnische Seeleute durch billiger bezahlte
estnische Seeleute zu ersetzen. Die finnische und internationale Seeleutegewerkschaft
bedrohten Viking mit kollektiven Maßnahmen. Viking klagte auf Verletzung der Niederlassungsfreiheit.

Leitsätze (EuGH C-438/05 — Viking Line):
1. Gewerkschaftliche Kollektivmaßnahmen unterliegen EU-Grundfreiheiten: Kollektive
   Maßnahmen privater Organisationen (Gewerkschaften) können die Niederlassungsfreiheit
   (Art. 49 AEUV) beeinträchtigen und müssen an ihr gemessen werden.
2. Keine absolute Immunität des Streikrechts: Das Recht auf kollektive Maßnahmen ist
   ein Grundrecht, schränkt aber nicht die EU-Grundfreiheiten aus. Es bedarf einer
   Abwägung.
3. Verhältnismäßigkeitsprüfung: Kollektive Maßnahmen sind nur zulässig, wenn sie einem
   legitimen Ziel (Schutz der Arbeitnehmer) dienen und verhältnismäßig sind.
4. Horizontale Wirkung der Grundfreiheiten: Art. 49 AEUV bindet auch private Akteure,
   wenn diese erhebliche wirtschaftliche Macht haben.

Bedeutung: Zusammen mit Laval der wichtigste EU-Rechtsfall zum Spannungsverhältnis
zwischen wirtschaftlichen Grundfreiheiten und Arbeitnehmerrechten.

Schlagwörter: EuGH C-438/05, Viking Line, Niederlassungsfreiheit, Art. 49 AEUV,
kollektive Maßnahmen, Streikrecht, Laval, Gewerkschaft, Verhältnismäßigkeit, Reflagging.
""".strip()},

  {"id": "steckbrief_duesseldorfer_tabelle", "skill": "familienrecht", "text": """
Düsseldorfer Tabelle — Kindesunterhalt (BGH XII ZR 72/08, 2010)
— Bundesgerichtshof, XII. Zivilsenat, 17. November 2010
(Unterhaltsbemessung, Selbstbehalt, Mindestunterhalt)

Sachverhalt und Hintergrund: Die Düsseldorfer Tabelle ist eine Leitlinie der
Oberlandesgerichte zur Bemessung des Kindesunterhalts (keine Rechtsverordnung).
Der BGH hat in mehreren Entscheidungen (u.a. XII ZR 72/08) die Grundsätze der
Unterhaltsberechnung konkretisiert, insbesondere den Selbstbehalt des Unterhaltspflichtigen
und die Anpassung an das Nettoeinkommen.

Leitsätze (Kindesunterhalt — Düsseldorfer Tabelle, BGH):
1. Mindestunterhalt (§ 1612a BGB): Minderjährige Kinder haben Anspruch auf Mindestunterhalt
   in Höhe des Doppelten des sächlichen Existenzminimums. Der Mindestunterhalt wird durch
   die erste Einkommensstufe der Düsseldorfer Tabelle definiert.
2. Selbstbehalt des Unterhaltspflichtigen: Dem barunterhaltspflichtigen Elternteil ist
   ein angemessener Selbstbehalt zu belassen, der nicht für Unterhalt herangezogen werden
   darf. Der notwendige Selbstbehalt gegenüber minderjährigen Kindern beträgt nach der
   aktuellen Tabelle mind. 1.450 Euro (2024).
3. Einkommensermittlung: Das für den Unterhalt maßgebliche Einkommen umfasst alle
   Einkünfte (Nettoeinkommen). Bereinigungen sind vorzunehmen (z.B. berufsbedingte Aufwendungen).
4. Halbteilungsgrundsatz beim Ehegattenunterhalt: Beim nachehelichen Unterhalt wird das
   Nettoeinkommen beider Ehegatten hälftig geteilt (§ 1578 Abs. 1 BGB).

Bedeutung: Die Düsseldorfer Tabelle ist de facto verbindlicher Standard für Gerichte
und Anwälte. Der BGH hat sie durch seine Rechtsprechung gestärkt.

Schlagwörter: Düsseldorfer Tabelle, Kindesunterhalt, § 1612a BGB, Selbstbehalt, Mindestunterhalt,
BGH XII ZR 72/08, Unterhaltsberechnung, Nettoeinkommen, Halbteilungsgrundsatz, Familienrecht.
""".strip()},

  {"id": "steckbrief_zugewinnausgleich_stichtag", "skill": "familienrecht", "text": """
Zugewinnausgleich — Stichtagsprinzip (§ 1378 BGB)
— Bundesgerichtshof, XII. Zivilsenat, BGH NJW 2013, 1452

Sachverhalt: Im Rahmen eines Zugewinnausgleichsverfahrens stritten die Ehegatten darum,
welcher Zeitpunkt für die Bewertung des Endvermögens maßgeblich ist und wie nachträgliche
Wertveränderungen zu berücksichtigen sind.

Leitsätze (Zugewinnausgleich, Stichtagsprinzip):
1. Stichtagsprinzip beim Zugewinnausgleich (§ 1376 Abs. 2, 3 BGB): Das Endvermögen wird
   am Tag der Rechtshängigkeit des Scheidungsantrags bewertet (Stichtag, § 1384 BGB bei
   Scheidung). Nachträgliche Wertveränderungen nach dem Stichtag bleiben grundsätzlich
   außer Betracht.
2. Ausgleich des Zugewinns (§ 1373 BGB): Zugewinn ist der Betrag, um den das Endvermögen
   eines Ehegatten das Anfangsvermögen übersteigt. Der Ehegatte mit dem höheren Zugewinn
   hat dem anderen die Hälfte des Überschusses zu erstatten (§ 1378 Abs. 1 BGB).
3. Illoyale Vermögensminderungen (§ 1375 Abs. 2 BGB): Verschwendung, Schenkungen ohne
   Zustimmung oder unentgeltliche Übertragungen nach Antragstellung werden dem Endvermögen
   hinzugerechnet (Hinzurechnungstatbestände).
4. Auskunftspflicht: Beide Ehegatten sind zur Auskunft über ihr Anfangs- und Endvermögen
   verpflichtet (§ 1379 BGB).

Bedeutung: Präzisiert das Stichtagsprinzip beim Zugewinnausgleich.
Wichtig für die Praxis bei vermögensrechtlichen Auseinandersetzungen nach Scheidung.

Schlagwörter: Zugewinnausgleich, § 1378 BGB, Stichtagsprinzip, § 1384 BGB, Endvermögen,
Anfangsvermögen, Zugewinn, § 1373 BGB, § 1375 BGB, illoyale Vermögensminderung,
Familienrecht, Scheidung.
""".strip()},

  {"id": "steckbrief_bremer_vulkan", "skill": "gesellschaftsrecht", "text": """
Bremer Vulkan (BGHZ 149, 10) — Bundesgerichtshof, 17. September 2001, II ZR 178/99

Konzernmutter entzog der Tochter-GmbH (Bremer Vulkan AG) Liquidität durch ein
konzernweites Cash-Pool-System und ließ sie in die Insolvenz gehen. Die GmbH hatte
Subventionen für ostdeutsche Werften erhalten, die dann zweckentfremdet wurden.

Leitsätze:
1. Gesellschafter einer GmbH haften nicht per se für Verbindlichkeiten der GmbH.
2. Haftungsdurchgriff (Existenzvernichtungshaftung): Gesellschafter, die das Gesellschafts-
   vermögen planmäßig entziehen und damit Gläubigerinteressen vorsätzlich verletzen,
   haften persönlich nach § 826 BGB (später: Trihotel-Formel).
3. Qualifizierter faktischer Konzern als eigenständige Haftungsgrundlage aufgegeben;
   stattdessen § 826 BGB als einheitliche Grundlage.

Bedeutung: Bremer Vulkan + Trihotel (BGHZ 173, 246) bilden das aktuelle System der
Existenzvernichtungshaftung. BGHZ 149, 10, § 826 BGB, GmbH-Haftung.
""".strip()},

  {"id": "steckbrief_itt_treupflichten", "skill": "gesellschaftsrecht", "text": """
ITT-Entscheidung — Treupflichten des GmbH-Gesellschafters (BGH NJW 1994, 3288)
— Bundesgerichtshof, II. Zivilsenat, 1. April 1993, II ZR 140/91

Sachverhalt: In einer GmbH nutzte ein Mehrheitsgesellschafter seine Mehrheitsposition,
um in der Gesellschafterversammlung Beschlüsse zu fassen, die einseitig seinen Interessen
dienten und die Minderheitsgesellschafter benachteiligten. Ein Minderheitsgesellschafter
klagte auf Feststellung der Unwirksamkeit dieser Beschlüsse.

Leitsätze (ITT-Entscheidung — Treupflichten GmbH):
1. Treupflichten in der GmbH: GmbH-Gesellschafter sind kraft ihrer Mitgliedschaft
   zur gegenseitigen Rücksichtnahme verpflichtet (gesellschaftsrechtliche Treuepflicht).
   Diese Pflicht gilt sowohl zwischen Gesellschaftern als auch im Verhältnis des
   Mehrheitsgesellschafters zur Gesellschaft.
2. Schranken der Mehrheitsherrschaft: Der Mehrheitsgesellschafter darf seine Mehrheit
   nicht treuwidrig einsetzen, um Minderheitsgesellschafter zu schädigen oder deren
   Mitgliedschaftsrechte zu entwerten. Beschlüsse, die gegen die Treuepflicht verstoßen,
   sind anfechtbar oder nichtig.
3. Inhaltskontrolle von Gesellschafterbeschlüssen: Gesellschafterbeschlüsse unterliegen
   einer materiellen Überprüfung auf Vereinbarkeit mit der Treuepflicht (nicht nur
   formale Kontrolle).
4. Abwägung: Treuepflicht ist kein absoluter Schutz der Minderheit; legitime
   Mehrheitsinteressen können überwiegen.

Bedeutung: Grundlegendes Urteil zur Treupflicht im GmbH-Recht. Zusammen mit dem
Girmes-Urteil (BGH 1995) Basis des gesellschaftsrechtlichen Minderheitsschutzes.

Schlagwörter: ITT, BGH NJW 1994 3288, Treupflicht, GmbH, Mehrheitsgesellschafter,
Minderheitsgesellschafter, Gesellschafterbeschluss, Inhaltskontrolle, Anfechtung,
Minderheitsschutz, gesellschaftsrechtliche Treuepflicht.
""".strip()},

  {"id": "steckbrief_macrotron", "skill": "gesellschaftsrecht", "text": """
Macrotron — Delisting (BGHZ 153, 47) — Bundesgerichtshof, II. Zivilsenat,
25. November 2002, II ZR 133/01
(Delisting, Minderheitsschutz, Pflichtangebot)

Sachverhalt: Die Macrotron GmbH wollte ihre Aktien von der Börse nehmen (Delisting)
und stellte einen Antrag auf Widerruf der Börsenzulassung. Minderheitsaktionäre widersprachen,
da ihnen durch das Delisting der Markt für ihre Aktien entzogen würde.

Leitsätze (BGHZ 153, 47 — Delisting, Minderheitsschutz):
1. Delisting als Eingriff in Mitgliedschaftsrechte: Das vollständige Rückzug von der Börse
   (Delisting) beeinträchtigt die Handelbarkeit der Aktien und damit das Vermögensrecht
   der Aktionäre erheblich.
2. Pflicht zur Abfindung: Ein Delisting ist nur zulässig, wenn der Mehrheitsaktionär
   oder die Gesellschaft den Minderheitsaktionären ein Pflichtangebot zum Kauf ihrer
   Aktien zu einem angemessenen Preis macht (Barabfindungsangebot).
3. Angemessene Abfindung: Die Abfindung richtet sich nach dem Börsenkurs und dem
   inneren Wert der Gesellschaft; der Börsenkurs ist Mindestmaß.
4. Überwindung durch BVerfG und BGH: Nach dem BVerfG-Beschluss (2012) und dem BGH-Urteil
   (2013, "Frosta") wurde die Macrotron-Rechtsprechung erheblich eingeschränkt; heute
   richtet sich der Minderheitsschutz beim Delisting nach § 39 BörsG.

Bedeutung: Grundlegendes Urteil zum Delisting-Schutz der Minderheitsaktionäre.
Wegweisend für die Rechtsentwicklung bei § 39 BörsG.

Schlagwörter: BGHZ 153 47, Macrotron, Delisting, Minderheitsschutz, Pflichtangebot,
Barabfindung, Börsenkurs, § 39 BörsG, Aktienrecht, Hauptversammlung.
""".strip()},

  {"id": "steckbrief_akerberg_fransson", "skill": "grundrechte", "text": """
Åkerberg Fransson (EuGH C-617/10) — Europäischer Gerichtshof, 26. Februar 2013
(Anwendungsbereich der Grundrechtecharta, ne bis in idem, Art. 50 GRCh)

Sachverhalt: Hans Åkerberg Fransson, ein schwedischer Fischer, hatte Steuern hinterzogen.
Er wurde zunächst mit einem Steuerzuschlag (Verwaltungsmaßnahme) belegt und dann auch
strafrechtlich verfolgt. Er berief sich auf den Grundsatz ne bis in idem (Art. 50 GRCh —
Verbot der Doppelbestrafung). Das schwedische Gericht fragte, ob die GRCh anwendbar sei.

Leitsätze (EuGH C-617/10 — Anwendungsbereich GRCh):
1. Weiter Anwendungsbereich der GRCh (Art. 51 Abs. 1 GRCh): Die GRCh gilt für
   Mitgliedstaaten, wenn sie "Recht der Union durchführen". Dies ist weit auszulegen:
   Schon ein hinreichender Bezug zum EU-Recht genügt. Nicht erforderlich ist,
   dass die Maßnahme ausschließlich EU-Recht umsetzt.
2. Steuerhinterziehung und EU-Recht: Da die Mehrwertsteuer (MwSt) EU-Recht (EU-MwSt-
   Richtlinie) unterliegt, betrifft die Verfolgung von Steuerhinterziehung EU-Recht —
   damit ist die GRCh anwendbar.
3. Ne bis in idem (Art. 50 GRCh): Der Grundsatz verbietet die doppelte Verfolgung und
   Bestrafung für dieselbe Tat. Verwaltungssanktion + Strafverfolgung kann Art. 50 GRCh
   verletzen (wenn Verwaltungssanktion "strafrechtlicher Natur" i.S.d. EMRK ist).
4. Kritik am weiten Anwendungsbereich: Das BVerfG hat Åkerberg Fransson als ultra-vires
   kritisiert (PSPP-Bezug).

Bedeutung: Wegweisendes Urteil zum weiten Anwendungsbereich der GRCh. Bestimmt, wann
Mitgliedstaaten an die Grundrechtecharta gebunden sind.

Schlagwörter: EuGH C-617/10, Åkerberg Fransson, Grundrechtecharta, GRCh, Art. 51 GRCh,
Anwendungsbereich, ne bis in idem, Art. 50 GRCh, Doppelbestrafung, Steuerhinterziehung, MwSt.
""".strip()},

  {"id": "steckbrief_apotheker", "skill": "grundrechte", "text": """
Apothekenurteil / Apothekerurteil (BVerfGE 7, 377) — Bundesverfassungsgericht,
11. Juni 1958, 1 BvR 596/56

Das bayerische Apothekengesetz schränkte die Zulassung neuer Apotheken durch eine
Bedürfnisprüfung stark ein. Das BVerfG entwickelte die Drei-Stufen-Theorie zu Art. 12 GG.

Drei-Stufen-Theorie (Berufsfreiheit, Art. 12 Abs. 1 GG):
Stufe 1 — Berufsausübungsregelungen: Eingriffe zulässig bei vernünftigen Gemeinwohlgründen.
Stufe 2 — Subjektive Zulassungsvoraussetzungen (persönliche Eigenschaften): Eingriffe zulässig
  zum Schutz überragender Gemeinschaftsgüter.
Stufe 3 — Objektive Zulassungsvoraussetzungen (unabhängig von Person): Eingriffe nur zur
  Abwehr nachweisbarer schwerwiegender Gefahren für überragend wichtige Gemeinschaftsgüter.
Je stärker der Eingriff in die Berufsfreiheit, desto gewichtigere Rechtfertigung erforderlich.

Bedeutung: Standardprüfungsschema für Eingriffe in Art. 12 GG (Berufsfreiheit).
Drei-Stufen-Theorie, Apothekenurteil, Bedürfnisprüfung, BVerfGE 7, 377.
""".strip()},

  {"id": "steckbrief_ert", "skill": "grundrechte", "text": """
ERT (EuGH C-260/89) — Europäischer Gerichtshof, 18. Juni 1991
(Grundrechtsbindung bei Berufung auf Ausnahmen vom Unionsrecht, Art. 10 EMRK)

Sachverhalt: Die griechische staatliche Rundfunkanstalt ERT hatte ein gesetzliches
Monopol auf Radio- und TV-Sendungen. Ein privater TV-Sender (Dimotiki Etairia) machte
geltend, das Monopol verletze die Dienstleistungsfreiheit (Art. 56 AEUV). Griechenland
verteidigte das Monopol mit öffentlichen Interessen (Art. 106 Abs. 2 AEUV).

Leitsätze (EuGH C-260/89 — ERT):
1. Grundrechtsbindung bei Berufung auf Rechtfertigungsgründe: Wenn ein Mitgliedstaat
   sich auf Rechtfertigungsgründe (Ausnahmen vom Unionsrecht) beruft, muss er dabei
   die EU-Grundrechte beachten. Die EU-Grundrechte gelten auch für solche nationalen
   Maßnahmen, die in den Anwendungsbereich des Unionsrechts fallen.
2. Informationsfreiheit (Art. 10 EMRK): Ein Rundfunkmonopol muss mit dem Recht auf
   freie Meinungsäußerung und Informationsfreiheit (Art. 10 EMRK, heute Art. 11 GRCh)
   vereinbar sein.
3. Abgrenzung zu Wachauf: Wachauf betraf die Durchführung von EU-Recht; ERT betrifft
   die Berufung auf EU-Ausnahmen — beide führen zur EU-Grundrechtsbindung.
4. Anwendungsbereich der GRCh (Art. 51 Abs. 1 GRCh): ERT-Doktrin ist durch "soweit
   sie Unionsrecht durchführen" in Art. 51 GRCh grundsätzlich kodifiziert.

Bedeutung: Erweitert die EU-Grundrechtsbindung auf Fälle, in denen Mitgliedstaaten
sich auf Ausnahmen vom EU-Recht berufen. Zusammen mit Wachauf Basis des Art. 51 GRCh.

Schlagwörter: EuGH C-260/89, ERT, Grundrechtsbindung, Ausnahmen Unionsrecht, Art. 51 GRCh,
Art. 10 EMRK, Art. 11 GRCh, Rundfunkmonopol, Dienstleistungsfreiheit, Informationsfreiheit.
""".strip()},

  {"id": "steckbrief_internationale_handelsgesellschaft", "skill": "grundrechte", "text": """
Internationale Handelsgesellschaft (EuGH Rs. 11/70) — Europäischer Gerichtshof,
17. Dezember 1970
(Grundrechte als allgemeine Grundsätze des EU-Rechts, Vorrang des EU-Rechts)

Sachverhalt: Ein deutsches Unternehmen (Internationale Handelsgesellschaft) klagte gegen
eine EWG-Getreideordnung, die eine Exportlizenz mit Kaution erforderte. Das Verwaltungsgericht
Frankfurt hielt die Verordnung für unvereinbar mit deutschen Grundrechten (GG) und legte
dem EuGH vor, ob das EU-Recht den nationalen Verfassungsprinzipien weichen muss.

Leitsätze (Rs. 11/70 — Grundrechte als allgemeine Grundsätze des EU-Rechts):
1. Vorrang des EU-Rechts auch gegenüber nationalem Verfassungsrecht: Die Gültigkeit von
   Gemeinschaftsrecht kann nicht an nationalen Verfassungsgrundsätzen gemessen werden.
   Würde dem nationalen Verfassungsrecht Vorrang eingeräumt, würde die einheitliche Anwendung
   des EU-Rechts gefährdet.
2. Grundrechte als allgemeine Grundsätze des Gemeinschaftsrechts: Der EuGH entwickelte
   Grundrechte als ungeschriebene allgemeine Grundsätze des Gemeinschaftsrechts — abgeleitet
   aus den gemeinsamen Verfassungsüberlieferungen der Mitgliedstaaten und der EMRK.
3. Eigenständiger EU-Grundrechtsschutz: Der Schutz der Grundrechte wird in das EU-Recht
   integriert und vom EuGH gewährleistet — nicht von nationalen Verfassungsgerichten.
4. Solange-Reaktion: Das BVerfG reagierte mit der "Solange I"-Entscheidung (1974),
   behielt sich die Kontrolle vor, bis ein äquivalenter EU-Grundrechtsschutz besteht.

Bedeutung: Grundlegendes Urteil zur Entwicklung des EU-Grundrechtsschutzes. Startpunkt
der Grundrechtsjudikatur des EuGH als allgemeine Grundsätze.

Schlagwörter: EuGH Rs. 11/70, Internationale Handelsgesellschaft, Grundrechte,
allgemeine Grundsätze, EU-Recht, Vorrang, nationales Verfassungsrecht, Solange,
BVerfG, EMRK, Verfassungsüberlieferungen.
""".strip()},

  {"id": "steckbrief_kueckuekdeveci", "skill": "grundrechte", "text": """
Kücükdeveci (EuGH C-555/07) — Europäischer Gerichtshof, 19. Januar 2010
(Horizontale Wirkung des allgemeinen Gleichheitsgrundsatzes, Altersdiskriminierung)

Sachverhalt: Seda Kücükdeveci war mit 18 Jahren in ein deutsches Unternehmen eingetreten.
Nach 10 Jahren wurde sie entlassen. Das deutsche Kündigungsschutzrecht rechnete
Beschäftigungszeiten vor dem 25. Lebensjahr nicht auf die Kündigungsschutzfristen an.
Dies benachteiligte junge Arbeitnehmer, die früh zu arbeiten beginnen.

Leitsätze (EuGH C-555/07 — horizontale Wirkung, Altersdiskriminierung):
1. Allgemeines Verbot der Altersdiskriminierung als EU-Primärrecht: Das Verbot der
   Diskriminierung wegen des Alters ist ein allgemeiner Grundsatz des EU-Rechts (heute
   Art. 21 GRCh), der — anders als Richtlinien — unmittelbare (horizontale) Wirkung
   zwischen Privaten entfalten kann.
2. Unanwendbarkeit nationalen Rechts: Nationales Recht, das gegen diesen Grundsatz
   verstößt, muss von nationalen Gerichten auch in Rechtsstreitigkeiten zwischen
   Privatpersonen unangewendet gelassen werden.
3. Abgrenzung zur Richtlinien-Direktwirkung: Kücükdeveci stützt sich nicht auf die
   Gleichbehandlungsrahmenrichtlinie (2000/78/EG) direkt (die keine horizontale Wirkung
   hat), sondern auf den allgemeinen Gleichheitsgrundsatz als Primärrecht.
4. Vorlageverpflichtung: Das vorlegende Gericht hätte dem EuGH vorlegen müssen, was
   es (nach anfänglicher Eigenentscheidung) schließlich auch tat.

Bedeutung: Bahnbrechendes Urteil zur horizontalen Wirkung primärrechtlicher Grundsätze.
Unterscheidet sich von der fehlenden horizontalen Direktwirkung von Richtlinien.

Schlagwörter: EuGH C-555/07, Kücükdeveci, horizontale Wirkung, Altersdiskriminierung,
Art. 21 GRCh, allgemeiner Gleichheitsgrundsatz, Primärrecht, Richtlinie 2000/78/EG,
Privatpersonen, Mangold, Europarecht.
""".strip()},

  {"id": "steckbrief_nold", "skill": "grundrechte", "text": """
Nold (EuGH Rs. 4/73) — Europäischer Gerichtshof, 14. Mai 1974
(EMRK und gemeinsame Verfassungsüberlieferungen als Grundrechtsquellen EU)

Sachverhalt: Das Kohlegroßhandelsunternehmen Nold KG klagte gegen eine Entscheidung der
Kommission, die neue Bedingungen für den Kohlehandel einführte und Nold faktisch vom
Markt ausschloss. Nold machte Verletzung seines Eigentumsrechts und des Rechts auf freie
Berufsausübung geltend.

Leitsätze (Rs. 4/73 — Nold, Grundrechtsquellen):
1. EMRK als Grundrechtsquelle: Die EMRK stellt besondere Hinweise dar, die bei der
   Festlegung von Grundrechten als allgemeinen Grundsätzen des Gemeinschaftsrechts
   zu berücksichtigen sind.
2. Gemeinsame Verfassungsüberlieferungen: Die gemeinsamen Verfassungsüberlieferungen
   der Mitgliedstaaten sind ebenfalls Quelle der EU-Grundrechte. Der EuGH orientiert
   sich an ihnen, auch wenn nicht alle Mitgliedstaaten identische Grundrechte kennen.
3. Schranken der Grundrechte: Grundrechte können durch Anforderungen des Gemeinwohls,
   die die EU verfolgt, eingeschränkt werden, wenn der Wesensgehalt nicht angetastet wird.
4. Weiterentwicklung: Die Grundrechtecharta (GRCh, Art. 6 Abs. 1 EUV n.F.) hat diese
   allgemeinen Grundsätze kodifiziert; Art. 6 Abs. 3 EUV behält EMRK und
   Verfassungsüberlieferungen als Rechtsquellen.

Bedeutung: Präzisiert die Grundrechtsquellen des EU-Rechts. EMRK und Verfassungsüberlieferungen
sind bis heute Auslegungsmaßstab (Art. 52 Abs. 3, 4 GRCh).

Schlagwörter: EuGH Rs. 4/73, Nold, EMRK, Verfassungsüberlieferungen, Grundrechte,
allgemeine Grundsätze, EU-Recht, Eigentum, Art. 6 EUV, GRCh, Grundrechtecharta.
""".strip()},

  {"id": "steckbrief_solange", "skill": "grundrechte", "text": """
Solange I (BVerfGE 37, 271, 1974) und Solange II (BVerfGE 73, 339, 1986)
— Bundesverfassungsgericht

Solange I (2 BvL 52/71, 29. Mai 1974):
Solange der EG ein dem GG gleichwertiger Grundrechtsschutz fehlt, überprüft das BVerfG
EU-Sekundärrecht an deutschen Grundrechten (Reservekompetenz).

Solange II (2 BvR 197/83, 22. Oktober 1986):
Da die EU mittlerweile einen dem GG entsprechenden Grundrechtsschutz entwickelt hat,
verzichtet das BVerfG auf Überprüfung von EU-Recht, solange dieser Schutz gewährleistet ist.

Leitsätze:
1. Das BVerfG behält eine Identitätskontrolle vor: Ultra-vires-Akte der EU und Verletzungen
   der Verfassungsidentität (Art. 79 Abs. 3 GG) werden weiterhin geprüft.
2. Kooperationsverhältnis zwischen BVerfG und EuGH (kein Überordnungsverhältnis).
3. Ergänzt durch Lissabon-Urteil (BVerfGE 123, 267) und PSPP-Urteil (2020).

Bedeutung: Grundlage des Verhältnisses zwischen BVerfG und EuGH. Solange-Klausel,
Identitätskontrolle, Anwendungsvorrang EU-Recht mit nationalen Grenzen.
""".strip()},

  {"id": "steckbrief_wachauf", "skill": "grundrechte", "text": """
Wachauf (EuGH Rs. 5/88) — Europäischer Gerichtshof, 13. Juli 1989
(Bindung der Mitgliedstaaten an EU-Grundrechte bei Durchführung des EU-Rechts)

Sachverhalt: Hubert Wachauf war Pächter einer Milchwirtschaft in Bayern. Bei Pachtende
verweigerten die deutschen Behörden ihm (auf Grundlage einer EWG-Milchquotenverordnung)
die Entschädigung für die von ihm aufgebauten Milchquoten. Wachauf machte geltend, seine
Grundrechte (Eigentumsrecht) seien verletzt.

Leitsätze (Rs. 5/88 — Wachauf):
1. Grundrechtsbindung bei Durchführung von EU-Recht: Wenn Mitgliedstaaten EU-Recht
   durchführen (umsetzen, vollziehen), sind sie an die EU-Grundrechte gebunden.
   Nationale Maßnahmen zur Durchführung des EU-Rechts dürfen die EU-Grundrechte nicht
   verletzen.
2. Spielraum der Mitgliedstaaten: Soweit EU-Recht den Mitgliedstaaten einen Umsetzungsspielraum
   lässt, müssen sie diesen grundrechtskonform ausüben.
3. Eigentumsrecht als EU-Grundrecht: Das Eigentumsrecht und das Recht auf freie
   Berufsausübung sind EU-Grundrechte, die auch gegenüber nationalen Durchführungsmaßnahmen
   gelten.
4. Kodifizierung in Art. 51 GRCh: Art. 51 Abs. 1 GRCh kodifiziert, dass die GRCh für
   Mitgliedstaaten gilt, wenn sie EU-Recht durchführen (Bestätigung der Wachauf-Doktrin).

Bedeutung: Grundlegendes Urteil zur Bindung der Mitgliedstaaten an EU-Grundrechte.
Wachauf-Doktrin ist heute in Art. 51 Abs. 1 GRCh kodifiziert.

Schlagwörter: EuGH Rs. 5/88, Wachauf, Grundrechtsbindung, Mitgliedstaaten, Durchführung EU-Recht,
Art. 51 GRCh, Grundrechtecharta, Eigentumsrecht, Milchquote, EU-Grundrechte.
""".strip()},

  {"id": "steckbrief_handelsvertreterausgleich_89b", "skill": "handelsrecht", "text": """
Handelsvertreterausgleich (§ 89b HGB) — Bundesgerichtshof, BGH NJW 2012, 1879
(Ausgleichsanspruch, Kündigung, Unternehmervorteil)

Sachverhalt: Ein Handelsvertreter vermittelte über Jahre Kunden für seinen Unternehmer.
Nach Kündigung des Handelsvertretervertrags durch den Unternehmer machte der Handelsvertreter
seinen Ausgleichsanspruch nach § 89b HGB geltend. Streitig war die Höhe des Ausgleichs
und ob ein Ausschlussgrund vorlag.

Leitsätze (§ 89b HGB — Handelsvertreterausgleich):
1. Ausgleichsanspruch (§ 89b Abs. 1 HGB): Der Handelsvertreter hat bei Vertragsbeendigung
   Anspruch auf einen angemessenen Ausgleich, wenn und soweit (a) er neue Kunden geworben
   oder bestehende Geschäftsverbindungen wesentlich erweitert hat, (b) der Unternehmer
   aus diesen Geschäftsverbindungen nach Vertragsende noch erhebliche Vorteile zieht und
   (c) die Zahlung des Ausgleichs der Billigkeit entspricht.
2. Berechnung: Der Ausgleich beträgt höchstens die durchschnittliche Jahresprovision der
   letzten 5 Jahre (§ 89b Abs. 2 HGB). Der EuGH hat die Ausgleichsmethode präzisiert
   (Gütegrundsatz).
3. Ausschluss (§ 89b Abs. 3 HGB): Der Anspruch ist ausgeschlossen, wenn der Handelsvertreter
   das Vertragsverhältnis selbst gekündigt hat (außer aus wichtigem Grund) oder wenn
   der Unternehmer aus wichtigem Grund kündigt.
4. Unabdingbarkeit: § 89b HGB ist einseitig zwingend — der Ausgleichsanspruch kann nicht
   vor Vertragsbeendigung vertraglich ausgeschlossen werden.

Bedeutung: Zentraler Anspruch des Handelsvertreters bei Vertragsbeendigung. Schutznorm
für selbstständige Vertriebsmittler.

Schlagwörter: § 89b HGB, Handelsvertreterausgleich, Ausgleichsanspruch, Kündigung,
Unternehmervorteil, Jahresprovision, BGH NJW 2012 1879, Handelsvertretervertrag,
Handelsrecht.
""".strip()},

  {"id": "steckbrief_ruegepflicht_377_hgb", "skill": "handelsrecht", "text": """
Rügepflicht beim Handelskauf (§ 377 HGB) — Bundesgerichtshof, BGH NJW 1997, 1914
(unverzügliche Mängelrüge, Gewährleistung im Handelsrecht)

Sachverhalt: Ein Kaufmann (K) kaufte von einem anderen Kaufmann (V) Waren. Nach Erhalt
der Waren stellte K erst nach einigen Tagen Mängel fest. Er zeigte diese V an. V berief
sich darauf, die Rüge sei verspätet — K habe damit seine Gewährleistungsrechte verloren.

Leitsätze (§ 377 HGB — Untersuchungs- und Rügepflicht):
1. Untersuchungs- und Rügepflicht (§ 377 HGB): Beim Handelskauf (beide Parteien
   Kaufleute) ist der Käufer verpflichtet, die Ware unverzüglich nach Ablieferung
   zu untersuchen und erkennbare Mängel unverzüglich anzuzeigen. "Unverzüglich" bedeutet
   ohne schuldhaftes Zögern — in der Praxis je nach Branche 2-7 Werktage.
2. Folgen unterlassener Rüge: Unterlässt der Käufer die rechtzeitige Rüge, gilt die
   Ware als genehmigt; Gewährleistungsrechte (§§ 437 ff. BGB i.V.m. § 381 HGB) sind
   ausgeschlossen.
3. Versteckte Mängel: Mängel, die bei ordnungsgemäßer Untersuchung nicht erkennbar waren
   (versteckte Mängel), müssen unverzüglich nach Entdeckung gerügt werden (§ 377 Abs. 3 HGB).
4. Arglist: Bei arglistigem Verschweigen des Mangels durch den Verkäufer greift § 377 HGB
   nicht — der Verkäufer kann sich nicht auf die verspätete Rüge berufen (§ 377 Abs. 5 HGB).

Bedeutung: Zentrale Norm des Handelskaufs. Die Rügepflicht nach § 377 HGB ist strenger
als im BGB-Kauf und gilt nur bei beidseitigem Kaufmann.

Schlagwörter: § 377 HGB, Rügepflicht, Handelskauf, Mängelrüge, unverzüglich, Kaufmann,
Gewährleistung, versteckte Mängel, Arglist, § 437 BGB, Handelsrecht.
""".strip()},

  {"id": "steckbrief_absonderung_sicherungsübereignung", "skill": "insolvenzrecht", "text": """
Absonderung und Sicherungsübereignung in der Insolvenz (§ 51 InsO)
— Bundesgerichtshof, BGH NJW 2005, 1644

Sachverhalt: Eine Bank hatte sich zur Sicherung ihrer Kreditforderung das Eigentum an
Maschinen des Schuldners übereignen lassen (Sicherungsübereignung). Nach Eröffnung des
Insolvenzverfahrens über das Vermögen des Schuldners machte die Bank ihre Rechte als
Sicherungseigentümerin gegenüber dem Insolvenzverwalter geltend. Fraglich waren die
Rechte der Bank in der Insolvenz.

Leitsätze (§ 51 InsO — Absonderungsrecht):
1. Absonderungsrecht (§ 51 Nr. 1 InsO): Gläubiger, die an einem Gegenstand des
   Schuldners ein Pfandrecht oder ein gleichgestelltes Recht haben (z.B. Sicherungsübereignung),
   sind absonderungsberechtigt: Sie können aus dem Erlös des Sicherungsguts vorrangig
   Befriedigung verlangen.
2. Sicherungsübereignung als Absonderungsrecht: Der Sicherungseigentümer hat trotz
   zivilrechtlichen Eigentums kein Aussonderungsrecht (§ 47 InsO), sondern nur ein
   Absonderungsrecht (§ 51 Nr. 1 InsO). Der Insolvenzverwalter hat das Verwertungsrecht.
3. Verwertung durch den Insolvenzverwalter (§ 166 InsO): Der Insolvenzverwalter hat das
   Recht, Sicherungsgut zu verwerten, wenn es sich im Besitz des Insolvenzschuldners befindet.
   Dem Sicherungsgläubiger stehen Kostenbeiträge (§§ 170, 171 InsO) zu.
4. Feststellungskosten und Verwertungskosten: Vom Erlös werden Kostenpauschalen abgezogen
   (4 % Feststellungskosten + 5 % Verwertungskosten, § 171 InsO).

Bedeutung: Grundlegend für das Sicherheitenrecht in der Insolvenz. Zeigt den Unterschied
zwischen Aussonderung und Absonderung.

Schlagwörter: § 51 InsO, Absonderungsrecht, Sicherungsübereignung, § 47 InsO, Aussonderung,
§ 166 InsO, Verwertungsrecht, Insolvenzverwalter, §§ 170 171 InsO, Kostenpauschale, Insolvenzrecht.
""".strip()},

  {"id": "steckbrief_insolvenzanfechtung_129", "skill": "insolvenzrecht", "text": """
Insolvenzanfechtung — Gläubigerbenachteiligung (§ 129 InsO)
— Bundesgerichtshof, BGH NJW 2003, 3560

Sachverhalt: Kurz vor der Insolvenz zahlte der Schuldner einzelne Gläubiger bevorzugt
aus (sog. Befriedigungshandlung). Der Insolvenzverwalter focht diese Zahlungen nach
§§ 129 ff. InsO an und verlangte Rückzahlung an die Insolvenzmasse.

Leitsätze (§§ 129, 130, 131 InsO — Insolvenzanfechtung):
1. Grundvoraussetzung der Anfechtung (§ 129 InsO): Anfechtbar sind Rechtshandlungen,
   die vor Verfahrenseröffnung vorgenommen wurden und die Insolvenzgläubiger benachteiligen
   (Gläubigerbenachteiligung). Die Benachteiligung liegt vor, wenn die Handlung das zur
   Befriedigung aller Gläubiger verfügbare Vermögen geschmälert hat.
2. Kongruente Deckung (§ 130 InsO): Sicherungen oder Befriedigung, auf die der Gläubiger
   einen fälligen Anspruch hatte (kongruent), sind anfechtbar, wenn sie innerhalb der
   letzten 3 Monate vor Antragstellung vorgenommen wurden und der Gläubiger die
   Zahlungsunfähigkeit kannte.
3. Inkongruente Deckung (§ 131 InsO): Leistungen, auf die der Gläubiger keinen Anspruch
   hatte (z.B. vorzeitige Zahlung, andere Leistung als geschuldet) sind leichter anfechtbar
   — innerhalb von 3 Monaten vor Antragstellung, ohne Kenntnis der Zahlungsunfähigkeit.
4. Vorsatzanfechtung (§ 133 InsO): Anfechtbar sind Rechtshandlungen des Schuldners mit
   Gläubigerbenachteiligungsvorsatz innerhalb von 10 Jahren vor Antragstellung.

Bedeutung: Kernrecht der Insolvenzanfechtung. Schützt die Gläubigergleichbehandlung
(par conditio creditorum) im Insolvenzverfahren.

Schlagwörter: § 129 InsO, Insolvenzanfechtung, Gläubigerbenachteiligung, §§ 130 131 133 InsO,
kongruente Deckung, inkongruente Deckung, Vorsatzanfechtung, Insolvenzverwalter, Insolvenzmasse.
""".strip()},

  {"id": "steckbrief_stoererhaftung_wlan_mcfadden", "skill": "it_recht", "text": """
BGH Störerhaftung WLAN — McFadden (BGH I ZR 174/14) — Bundesgerichtshof und
EuGH C-484/14, 15. September 2016
(WLAN-Haftung, Urheberrechtsverletzung, Störerhaftung, Haftungsprivileg)

Sachverhalt: Tobias McFadden betrieb ein offenes, ungesichertes WLAN (kostenloses WLAN
für Kunden seines Musikgeschäfts). Über dieses WLAN wurde urheberrechtlich geschützte
Musik ohne Erlaubnis des Rechtsinhabers heruntergeladen. Sony Music klagte auf
Schadensersatz und Unterlassung gegen McFadden als WLAN-Betreiber.

Leitsätze (BGH I ZR 174/14, EuGH C-484/14):
1. Keine Schadensersatzhaftung des WLAN-Betreibers: Der EuGH stellte fest, dass der
   Betreiber eines offenen WLAN grundsätzlich nicht auf Schadensersatz haftet, wenn
   Dritte über das WLAN Urheberrechtsverletzungen begehen (Art. 12 e-Commerce-Richtlinie,
   § 8 TMG a.F. / § 1 Abs. 2 TDG).
2. Keine Störerhaftung für WLAN-Betreiber (nach Gesetzesreform): Der BGH und der EuGH
   haben klargestellt, dass WLAN-Betreiber nicht mehr als Störer auf Unterlassung in
   Anspruch genommen werden dürfen, wenn sie ihr Netz nicht gesichert haben
   (Aufhebung der älteren deutschen Störerhaftungsrechtsprechung durch § 8 TMG n.F./§ 1 TDG).
3. Technische Maßnahmen als Auflage: Gerichte können WLAN-Betreiber verpflichten,
   technische Maßnahmen zum Schutz vor Urheberrechtsverletzungen zu treffen
   (z.B. Passwortsicherung), ohne Schadensersatz oder Unterlassung aufzuerlegen.
4. Safe-Harbor-Prinzip: Diensteanbieter, die nur als Durchgangsleiter (Mere Conduit)
   fungieren, genießen Haftungsprivileg nach der e-Commerce-Richtlinie.

Bedeutung: Grundlegend für die WLAN-Haftung in Deutschland. Beendete die Unsicherheit
über die Haftung von WLAN-Betreibern und Hotspot-Anbietern.

Schlagwörter: BGH I ZR 174/14, EuGH C-484/14, McFadden, WLAN-Haftung, Störerhaftung,
§ 8 TMG, e-Commerce-Richtlinie, Urheberrecht, Haftungsprivileg, Mere Conduit, Hotspot.
""".strip()},

  {"id": "steckbrief_courage_crehan", "skill": "kartellrecht", "text": """
Courage/Crehan (EuGH C-453/99) — Europäischer Gerichtshof, 20. September 2001
(Private Kartellrechtsdurchsetzung, Schadensersatz, Art. 101 AEUV)

Sachverhalt: Courage, ein britisches Brauunternehmen, hatte mit Wirten (u.a. Crehan)
Bierbezugsverträge abgeschlossen, die möglicherweise gegen das Kartellrecht (Art. 81 EGV,
heute Art. 101 AEUV) verstießen. Als Courage Crehan auf Zahlung verklagte, machte
Crehan widerklagend Schadensersatz für kartellbedingte Mehrpreise geltend. Fraglich
war, ob Privatpersonen EU-Kartellrecht privat durchsetzen können.

Leitsätze (EuGH C-453/99 — private Kartellschadensersatzklage):
1. Recht auf Schadensersatz: Jede Person kann Schadensersatz verlangen, die durch einen
   Verstoß gegen Art. 101 AEUV (Kartellverbot) einen Schaden erlitten hat. Dies ergibt
   sich direkt aus dem Primärrecht der EU und ist notwendig für die volle Wirksamkeit
   des EU-Kartellrechts (effet utile).
2. Private Enforcement: Die private Kartellrechtsdurchsetzung (private enforcement)
   ist ein wesentliches Komplement zur behördlichen Durchsetzung (public enforcement)
   durch die Kommission und nationale Behörden.
3. Beibehaltung von Kartellvertragsparteien als Kläger: Auch ein am Kartell beteiligter
   Vertragsteil kann Schadensersatz verlangen, wenn er in wirtschaftlicher Abhängigkeit
   handelte und seinen Beitrag nicht ausschlaggebend war.
4. Umsetzung durch Kartellschadensersatzrichtlinie (2014/104/EU): Diese Grundsätze wurden
   durch die Richtlinie 2014/104/EU kodifiziert (in Deutschland: §§ 33 ff. GWB).

Bedeutung: Grundlegendes Urteil zur privaten Kartellrechtsdurchsetzung in Europa.
Ausgangspunkt des modernen private enforcement.

Schlagwörter: EuGH C-453/99, Courage Crehan, Kartellschadensersatz, Art. 101 AEUV,
private enforcement, Schadensersatz, Richtlinie 2014/104/EU, § 33 GWB, effet utile,
Privatklage, Kartellrecht.
""".strip()},

  {"id": "steckbrief_hoffmann_la_roche", "skill": "kartellrecht", "text": """
Hoffmann-La Roche (EuGH Rs. 85/76) — Europäischer Gerichtshof, 13. Februar 1979
(Marktbeherrschende Stellung, Treuerabatte, Missbrauch, Art. 102 AEUV)

Sachverhalt: Hoffmann-La Roche, einer der weltgrößten Pharmahersteller, hatte mit
seinen Abnehmern Vereinbarungen über Treuerabatte getroffen: Abnehmer, die ihren
gesamten oder überwiegenden Bedarf bei Roche deckten, erhielten Sonderrabatte.
Die EU-Kommission sah darin einen Missbrauch der marktbeherrschenden Stellung.

Leitsätze (Rs. 85/76 — Marktbeherrschung, Treuerabatte):
1. Begriff der marktbeherrschenden Stellung (Art. 102 AEUV): Eine Stellung wirtschaftlicher
   Stärke, die ein Unternehmen in die Lage versetzt, die Aufrechterhaltung wirksamen
   Wettbewerbs auf dem relevanten Markt zu verhindern und ein spürbares Maß an
   Unabhängigkeit gegenüber Wettbewerbern, Abnehmern und Verbrauchern zu verhalten.
2. Treuerabatte als Missbrauch: Treuerabatte (Exklusivitätsrabatte), die Abnehmer dazu
   veranlassen, ihren Bedarf ausschließlich oder überwiegend bei dem marktbeherrschenden
   Unternehmen zu decken, sind grundsätzlich missbräuchlich nach Art. 102 AEUV.
3. Marktabschottungseffekt: Treuerabatte haben einen Bindungseffekt (tying effect), der
   Wettbewerber vom Zugang zum Markt ausschließt und damit den Wettbewerb verfälscht.
4. Keine Rechtfertigung durch Effizienz: Bei einer solchen systematischen Bindungspraxis
   können Effizienzvorteile den Missbrauch grundsätzlich nicht rechtfertigen.

Bedeutung: Grundlegendes Urteil zur marktbeherrschenden Stellung und zum Missbrauch
durch Treuerabatte. Bis heute Maßstab für die Beurteilung von Rabattsystemen.

Schlagwörter: EuGH Rs. 85/76, Hoffmann-La Roche, marktbeherrschende Stellung, Art. 102 AEUV,
Treuerabatte, Exklusivitätsrabatte, Missbrauch, Marktabschottung, Pharmaindustrie.
""".strip()},

  {"id": "steckbrief_informed_consent_aufklaerung", "skill": "medizinrecht", "text": """
Informed Consent — Ärztliche Aufklärungspflicht (BGH NJW 2005, 1718)
— Bundesgerichtshof, VI. Zivilsenat

Sachverhalt: Ein Patient wurde vor einer Operation nur unzureichend über die Risiken
des Eingriffs aufgeklärt. Nach der Operation traten Komplikationen auf, über die er
nicht informiert worden war. Der Patient klagte auf Schadensersatz wegen Verletzung der
Aufklärungspflicht und mangelhafter Einwilligung.

Leitsätze (Ärztliche Aufklärungspflicht, Einwilligung):
1. Aufklärungspflicht als Voraussetzung wirksamer Einwilligung: Ein medizinischer Eingriff
   ist nur rechtmäßig, wenn der Patient zuvor wirksam eingewilligt hat. Die Einwilligung
   setzt eine ordnungsgemäße Aufklärung voraus (Selbstbestimmungsaufklärung).
2. Umfang der Aufklärung: Der Arzt muss über Art, Umfang, Zweck und Risiken des Eingriffs
   aufklären, sowie über Behandlungsalternativen. Aufgeklärt werden muss über alle Risiken,
   die für den Patienten in seiner Situation wesentlich sein können — auch seltene Risiken,
   wenn sie bei Eintritt schwerwiegend sind.
3. Rechtzeitigkeit: Die Aufklärung muss rechtzeitig vor dem Eingriff erfolgen, sodass der
   Patient genügend Zeit zur Überlegung hat. Aufklärung am Operationstag selbst ist
   grundsätzlich zu spät.
4. Beweislast: Der Arzt trägt die Beweislast dafür, dass er die Aufklärung ordnungsgemäß
   durchgeführt hat und eine wirksame Einwilligung vorlag.

Bedeutung: Grundlegend für das Arzthaftungsrecht. Informed Consent als Grundvoraussetzung
jeden ärztlichen Handelns. Grundlage der §§ 630d, 630e BGB (Patientenrechtegesetz 2013).

Schlagwörter: Informed Consent, Aufklärungspflicht, Einwilligung, § 630d BGB, § 630e BGB,
Arzthaftung, BGH NJW 2005 1718, Selbstbestimmungsaufklärung, Beweislast, Medizinrecht.
""".strip()},

  {"id": "steckbrief_organisationsverschulden_krankenhaus", "skill": "medizinrecht", "text": """
Organisationsverschulden im Krankenhaus — § 823 BGB, Arzthaftung
— Bundesgerichtshof, BGH NJW 1995, 1611

Sachverhalt: In einem Krankenhaus war nicht ausreichend qualifiziertes Personal verfügbar,
als ein Patient eine lebensbedrohliche Komplikation erlitt. Infolge der unzureichenden
Besetzung kam es zu einer Verzögerung der Behandlung, die zu Dauerschäden führte. Der
Patient klagte auf Schadensersatz wegen Organisationsverschuldens des Krankenhauses.

Leitsätze (Organisationsverschulden, Beweislast):
1. Organisationsverschulden: Das Krankenhaus haftet nicht nur für Fehler des einzelnen
   Arztes, sondern auch für strukturelle Mängel der Organisation (unzureichende Besetzung,
   fehlende Ausstattung, mangelhafte Kommunikation). Organisationsfehler sind als
   eigenständige Haftungsgrundlage anerkannt.
2. Beweislastumkehr bei grobem Behandlungsfehler: Liegt ein grober Behandlungs- oder
   Organisationsfehler vor, der geeignet war, den eingetretenen Schaden zu verursachen,
   wird die Kausalität zwischen Fehler und Schaden zugunsten des Patienten vermutet.
   Das Krankenhaus muss die Vermutung widerlegen.
3. Vollbeherrschbarer Risikobereich: Schäden aus einem Bereich, der vom Krankenhaus
   vollständig beherrscht werden kann (z.B. Hygienemängel, Geräteversagen), werden
   ebenfalls dem Krankenhaus zugerechnet (Beweislastumkehr).
4. Dokumentationspflicht: Fehlt eine ordnungsgemäße Dokumentation der Behandlung,
   kann dies ebenfalls Beweislast zugunsten des Patienten auslösen (§ 630h Abs. 3 BGB).

Bedeutung: Grundlegend für die Krankenhausorganisationshaftung und Beweislastverteilung
im Arzthaftungsrecht.

Schlagwörter: Organisationsverschulden, Krankenhaus, § 823 BGB, Arzthaftung,
Beweislastumkehr, grober Behandlungsfehler, § 630h BGB, BGH NJW 1995 1611,
vollbeherrschbarer Risikobereich, Medizinrecht.
""".strip()},

  {"id": "steckbrief_contergan", "skill": "strafrecht", "text": """
Contergan-Fall — BGH / LG Aachen 1970
(Fahrlässigkeit, Arzneimittelrecht, Kausalität, § 230 StGB a.F.)

Sachverhalt: Der Wirkstoff Thalidomid (Handelsname: Contergan), ein Schlaf- und
Beruhigungsmittel der Firma Grünenthal, wurde ab 1957 ohne ausreichende Prüfung auf
Teratogenität (Fruchtschäden) in den Verkehr gebracht. Tausende Kinder wurden mit
Fehlbildungen geboren. Der Strafprozess gegen Grünenthal-Mitarbeiter vor dem LG Aachen
(Az. 6 Ks 1/66) wurde 1970 gegen Geldauflagen eingestellt.

Leitsätze und Rechtsfragen (Contergan-Fall):
1. Fahrlässigkeitshaftung bei Arzneimitteln: Hersteller haben eine erhöhte Sorgfaltspflicht
   bei der Prüfung von Arzneimitteln auf Nebenwirkungen, insbesondere teratogene Wirkungen.
   Wird die gebotene Sorgfalt (Tierstudien, klinische Prüfungen) unterlassen, liegt
   Fahrlässigkeit vor.
2. Kausalitätsprobleme: Die wissenschaftliche Feststellung der Kausalität zwischen
   Thalidomid und den Missbildungen war erschwert durch zeitlichen Abstand, viele mögliche
   Ursachen und fehlende Nachweise. Kausalität muss jedoch auch im Strafrecht voll bewiesen
   sein (in dubio pro reo).
3. Produkthaftung und Rückrufpflicht: Ein Hersteller muss ein Arzneimittel vom Markt
   nehmen, sobald Hinweise auf schwerwiegende Nebenwirkungen vorliegen. Unterlassung
   begründet strafrechtliche Fahrlässigkeit.
4. Gesetzgeberische Folge: Der Contergan-Fall führte 1976 zur Reform des Arzneimittelgesetzes
   (AMG) mit strengen Zulassungsanforderungen und Pharmakovigilanz-Pflichten.

Bedeutung: Historischer Strafprozess mit nachhaltiger Wirkung auf das Arzneimittelrecht
und die Produkthaftung. Grundlage für das moderne Arzneimittelrecht (AMG 1976).

Schlagwörter: Contergan, Thalidomid, Grünenthal, Arzneimittelrecht, AMG, Fahrlässigkeit,
§ 230 StGB a.F., Teratogenität, Kausalität, Produkthaftung, LG Aachen, Rückrufpflicht.
""".strip()},

  {"id": "steckbrief_gremienentscheidung", "skill": "strafrecht", "text": """
Gremienentscheidung / Kollegialhaftung (BGH NJW 1987, 2661)
— Bundesgerichtshof, Lederspray-Fall, 6. Juli 1990, 2 StR 549/89 (und verwandte Fälle)
(Mittäterschaft bei Kollegialentscheidungen, Gremium, § 25 Abs. 2 StGB)

Sachverhalt: In Unternehmen mit kollegialer Führung (Vorstand, Geschäftsführung) werden
Entscheidungen oft in Gremien getroffen. Bei schadensverursachenden Entscheidungen
(z.B. Fortführung des Vertriebs eines gefährlichen Produkts) war fraglich, ob alle
Gremienmitglieder als Mittäter haften, auch wenn jedes einzelne Mitglied nur eine
von mehreren Stimmen abgegeben hat und die Entscheidung auch ohne seine Stimme
zustande gekommen wäre.

Leitsätze (Kollegialhaftung bei Gremienentscheidungen):
1. Mittäterschaft bei Kollegialentscheidungen: Jedes Gremienmitglied, das für eine
   strafbare Entscheidung gestimmt hat, ist Mittäter (§ 25 Abs. 2 StGB), auch wenn
   der Beschluss ohne seine Stimme zustande gekommen wäre. Entscheidend ist die
   tatsächliche Mitwirkung und der gemeinsame Tatplan.
2. Kausalität bei Überbestimmtheit: Das Kausalitätsproblem ("überzählige Stimme")
   wird gelöst durch kumulative Kausalität: Jede Stimme war Teil der kollektiven
   Entscheidung und daher kausal.
3. Unterlassen durch Nichteinschreiten: Vorstandsmitglieder, die eine gefährliche
   Entscheidung kennen und nicht dagegen einschreiten, können als Unterlassungstäter
   haften (§ 13 StGB), wenn sie eine Garantenpflicht für das Unternehmen haben.
4. Rückrufpflicht: Wenn ein bereits in Verkehr gebrachtes Produkt gefährlich ist,
   trifft die Unternehmensleitung eine Pflicht zum Rückruf; Unterlassen begründet
   Garantenhaftung.

Bedeutung: Grundlage der strafrechtlichen Organhaftung im Unternehmen. Relevant für
Produkthaftung, Compliance und Corporate Criminal Liability.

Schlagwörter: Kollegialhaftung, Gremienentscheidung, Mittäterschaft, § 25 Abs. 2 StGB,
kumulative Kausalität, Vorstand, Geschäftsführer, Rückrufpflicht, Lederspray, § 13 StGB,
Garantenpflicht, Unternehmenstrafrecht.
""".strip()},

  {"id": "steckbrief_holzschutzmittelfall", "skill": "strafrecht", "text": """
Holzschutzmittel-Fall (BGHSt 41, 206) — Bundesgerichtshof, 6. Juli 1990, 2 StR 549/89
(Kausalität bei Produkthaftung, wissenschaftliche Unsicherheit, Körperverletzung)

Sachverhalt: Mitarbeiter einer Holzschutzmittelfirma brachten ein Holzschutzmittel in
den Verkehr, das bei Nutzern Gesundheitsschäden verursachte. Die wissenschaftliche
Kausalität zwischen Holzschutzmittel und Erkrankung war jedoch nur mit einer gewissen
Wahrscheinlichkeit, nicht mit Sicherheit feststellbar. Angeklagte Geschäftsführer
wurden wegen fahrlässiger Körperverletzung angeklagt.

Leitsätze (BGHSt 41, 206 — Kausalität, Produkthaftung, Unsicherheit):
1. Kausalität im Strafrecht (conditio-sine-qua-non-Formel): Eine Handlung ist kausal für
   den Erfolg, wenn sie nicht hinweggedacht werden kann, ohne dass der Erfolg entfiele.
   Für die Verurteilung muss die Kausalität zur vollen richterlichen Überzeugung
   (§ 261 StPO) festgestellt sein.
2. Wissenschaftliche Unsicherheit schadet: Wenn die Verursachung eines Schadens durch
   ein Produkt wissenschaftlich nicht mit Sicherheit feststellbar ist (nur wahrscheinlich),
   darf keine strafrechtliche Verurteilung erfolgen ("in dubio pro reo").
3. Keine Kausalitätsvermutung im Strafrecht: Anders als im Zivilrecht (Beweislastumkehr
   bei Produzentenhaftung, § 823 BGB i.V.m. Hühnerpest-Fall) gilt im Strafrecht kein
   Anscheinsbeweis für Kausalität bei Produktschäden.
4. Freispruch mangels Kausalitätsbeweis: Wenn nicht ausgeschlossen werden kann, dass die
   Erkrankungen andere Ursachen hatten, ist eine Verurteilung ausgeschlossen.

Bedeutung: Grundlegender Fall zu Kausalitätsproblemen im Strafrecht bei Produkthaftung.
Verdeutlicht den Grundsatz "in dubio pro reo" bei wissenschaftlicher Unsicherheit.

Schlagwörter: BGHSt 41 206, Kausalität, Produkthaftung, Holzschutzmittel, in dubio pro reo,
wissenschaftliche Unsicherheit, § 261 StPO, Körperverletzung, conditio-sine-qua-non,
fahrlässige Körperverletzung, Strafrecht.
""".strip()},

  {"id": "steckbrief_jauchegrubenfall", "skill": "strafrecht", "text": """
Jauchegrubenfall (RGSt 63, 211) — Reichsgericht, 1929
(Garantenstellung aus Ingerenz, Unterlassen, § 13 StGB)

Sachverhalt: Jemand ließ unbedacht eine Jauchegrube offen, in die ein Kind fiel und
zu ertrinken drohte. Der Eigentümer der Grube sah das Kind in der Grube, unternahm
aber nichts, um es zu retten. Das Kind ertrank. Fraglich war, ob den Eigentümer eine
Garantenpflicht traf, das Kind zu retten.

Leitsätze (Garantenstellung aus Ingerenz):
1. Garantenpflicht aus Ingerenz: Wer durch sein vorausgegangenes Tun (gefahrbegründendes
   Vorverhalten) eine Gefahr für ein Rechtsgut eines anderen geschaffen hat, ist verpflichtet,
   diese Gefahr abzuwenden (Garantenstellung aus Ingerenz). Dies gilt auch bei anfänglich
   rechtmäßigem Vorverhalten, wenn die Gefahr vorhersehbar war.
2. Offenlassen der Jauchegrube: Das Offenlassen der Grube in der Nähe von Kindern begründet
   eine gefährliche Situation; der Eigentümer hat durch sein Vorverhalten die Gefahr gesetzt.
   Daraus folgt eine Garantenpflicht, die entstandene Gefahr abzuwenden.
3. § 13 StGB (Begehen durch Unterlassen): Wer als Garant verpflichtet ist, den Eintritt
   des tatbestandlichen Erfolges zu verhindern, und es unterlässt, wird wie ein Täter durch
   aktives Tun bestraft, wenn er den Erfolg hätte verhindern können (Entsprechungsklausel).
4. Abgrenzung: Garantenpflicht aus Ingerenz setzt rechtswidriges oder gefahrbegründendes
   Vorverhalten voraus; bloße Kausalität genügt nicht.

Bedeutung: Klassischer Fall zur Garantenstellung aus Ingerenz. Grundlage für das Verständnis
des Unterlassungsdelikts nach § 13 StGB.

Schlagwörter: Garantenstellung, Ingerenz, Unterlassen, § 13 StGB, Jauchegrubenfall,
RGSt 63 211, Garantenpflicht, gefahrbegründendes Vorverhalten, Entsprechungsklausel.
""".strip()},

  {"id": "steckbrief_radfahrerunfall", "skill": "strafrecht", "text": """
Radfahrerunfall-Fall — Kausalität, hypothetisches Alternativverhalten
— Bundesgerichtshof, BGHSt 11, 1

Sachverhalt: Ein LKW-Fahrer überholte einen betrunkenen Radfahrer ohne ausreichenden
Seitenabstand. Der Radfahrer kam zu Fall und wurde überfahren. Das Gutachten ergab,
dass der Radfahrer aufgrund seiner Trunkenheit auch bei ausreichendem Seitenabstand
gestürzt und überfahren worden wäre.

Leitsätze (Kausalität, hypothetisches Alternativverhalten):
1. Conditio-sine-qua-non-Formel: Eine Handlung ist kausal für den Erfolg, wenn sie nicht
   hinweggedacht werden kann, ohne dass der Erfolg in seiner konkreten Gestalt entfiele.
   Bei überwiegend wahrscheinlichem Alternativverlauf ist Kausalität fraglich.
2. Hypothetisches Alternativverhalten: Wäre der Erfolg auch bei rechtmäßigem Alternativverhalten
   eingetreten, entfällt nicht unbedingt die Kausalität, sondern der Pflichtwidrigkeitszusammenhang
   (normative Zurechnungsfrage).
3. In dubio pro reo: Kann nicht mit Sicherheit festgestellt werden, ob das pflichtwidrige
   Verhalten den Erfolg verursacht hat, muss zugunsten des Angeklagten entschieden werden.
4. Risikoerhöhungslehre (Roxin, Gegenauffassung): Nach der Risikoerhöhungslehre genügt
   es für die Strafbarkeit, dass das pflichtwidrige Verhalten das Risiko des Erfolgseintritts
   statistisch erhöht hat — auch wenn im Einzelfall nicht beweisbar ist, ob der Erfolg
   vermieden worden wäre.

Bedeutung: Zusammen mit dem Straßenbahn-Fall Grundlage der Lehre vom Pflichtwidrigkeitszusammenhang.
Zentral für die Fahrlässigkeitsprüfung im Strafrecht.

Schlagwörter: Kausalität, Pflichtwidrigkeitszusammenhang, hypothetisches Alternativverhalten,
BGHSt 11 1, Radfahrerunfall, Fahrlässigkeit, in dubio pro reo, Risikoerhöhungslehre,
conditio-sine-qua-non, Strafrecht AT.
""".strip()},

  {"id": "steckbrief_rettungsring", "skill": "strafrecht", "text": """
Rettungsring-Fall — Beihilfe und Abgrenzung zur Täterschaft
— Bundesgerichtshof, BGH NJW 1954, 1251

Sachverhalt: A beobachtete, wie B im See zu ertrinken drohte. C war am Ufer und hätte
leicht einen Rettungsring zu A werfen können, um diesem die Rettung zu ermöglichen. C
weigerte sich. B ertrank. Fraglich war, ob C als Täter (durch Unterlassen) oder als
Gehilfe anzusehen war, und ob überhaupt eine Strafbarkeit vorlag.

Leitsätze (Rettungsring-Fall — Beihilfe, Abgrenzung):
1. Beihilfe durch Unterlassen: Wer eine Beihilfehandlung (Unterstützung des Täters)
   durch Unterlassen erbringt, haftet als Gehilfe (§ 27 StGB), wenn er eine Garantenpflicht
   hatte, die tatfördernde Unterlassung zu vermeiden.
2. Abgrenzung Täter/Gehilfe bei Unterlassen: Die subjektive Theorie fragt, ob der
   Unterlassende die Tat als eigene oder als fremde will. Die Tatherrschaftslehre
   fragt nach der Herrschaft über das Geschehen.
3. Pflicht zur Nothilfe (§ 323c StGB): Unabhängig von Garantenpflichten trifft jeden
   die allgemeine Pflicht zur Nothilfe (§ 323c StGB — unterlassene Hilfeleistung),
   wenn Hilfe zumutbar und ohne erhebliche Eigengefahr möglich ist.
4. Abgrenzung zur echten Täterschaft durch Unterlassen: Wer als Garant verpflichtet ist,
   einen Erfolg zu verhindern, und ihn unterlässt, ist Unterlassungstäter (§§ 212, 13 StGB);
   wer nur die Tat eines anderen fördert, ist Gehilfe.

Bedeutung: Klassischer Lehrfall zur Beihilfe durch Unterlassen und zu § 323c StGB.
Verdeutlicht die Abgrenzung von Täterschaft und Teilnahme beim Unterlassungsdelikt.

Schlagwörter: Beihilfe, § 27 StGB, Unterlassen, § 13 StGB, § 323c StGB, Nothilfe,
Rettungsring, Garantenpflicht, Abgrenzung Täterschaft Teilnahme, subjektive Theorie,
Tatherrschaft.
""".strip()},

  {"id": "steckbrief_straßenbahn_pflichtwidrigkeit", "skill": "strafrecht", "text": """
Straßenbahn-Fall / Pflichtwidrigkeit — Objektive Zurechnung, rechtmäßiges Alternativverhalten
— Bundesgerichtshof, BGH NJW 1957, 1460

Sachverhalt: Ein Straßenbahnführer überholte einen betrunkenen Radfahrer mit zu geringem
Seitenabstand (Pflichtverstoß). Der Radfahrer stürzte und wurde überfahren. Es stellte
sich heraus, dass der Radfahrer auch bei Einhaltung des korrekten Seitenabstands
(rechtmäßiges Alternativverhalten) gestürzt und überfahren worden wäre, weil er infolge
seiner Trunkenheit ohnehin ins Wanken geraten wäre.

Leitsätze (rechtmäßiges Alternativverhalten, objektive Zurechnung):
1. Rechtmäßiges Alternativverhalten als Zurechnungsproblem: Der tatbestandliche Erfolg
   muss auf die Pflichtwidrigkeit des Täters zurückführbar sein (Pflichtwidrigkeitszusammenhang).
   Wäre der Erfolg auch bei pflichtgemäßem Alternativverhalten eingetreten, fehlt der
   Pflichtwidrigkeitszusammenhang.
2. Schutzbereichslehre (h.M.): Entscheidend ist nicht nur, ob der Erfolg vermieden worden
   wäre, sondern ob die verletzte Sorgfaltsnorm gerade diesen Erfolg verhindern sollte
   (Schutzzweck der Norm). Lag der Schaden außerhalb des Schutzbereichs der verletzten
   Norm, fehlt die objektive Zurechnung.
3. Konsequenz im Straßenbahn-Fall: Da der Seitenabstand gerade Kollisionen verhindern
   soll und die Kollision auch bei Abstandseinhaltung eingetreten wäre, fehlt der
   Pflichtwidrigkeitszusammenhang — Freispruch.
4. Bedeutung für die Fahrlässigkeitsprüfung: Fahrlässigkeitsstrafbarkeit setzt kausalen
   und normativen Zusammenhang zwischen Pflichtverletzung und Erfolg voraus.

Bedeutung: Grundlegendes Urteil zur objektiven Zurechnung und zum Pflichtwidrigkeitszusammenhang
bei der Fahrlässigkeit. Standardfall im Strafrecht-AT.

Schlagwörter: Objektive Zurechnung, Pflichtwidrigkeitszusammenhang, rechtmäßiges
Alternativverhalten, Fahrlässigkeit, Straßenbahn, Radfahrer, Schutzbereich der Norm,
BGH NJW 1957 1460, Strafrecht AT.
""".strip()},

  {"id": "steckbrief_weichensteller", "skill": "strafrecht", "text": """
Weichensteller-Fall (BGH NStZ 2004, 499) — Bundesgerichtshof

Ein Weichensteller stellte eine Weiche falsch und verursachte dadurch einen Zugunfall.
Streitfrage: Täterschaft oder Beihilfe, wenn der Weichensteller "nur" die Weiche stellt
und ein anderer (der Lokführer) die unmittelbare Ursache setzt.

Leitsätze — Abgrenzung Täterschaft/Beihilfe:
1. Täterschaft (§ 25 StGB) erfordert Tatherrschaft — der Täter hält das Ob und Wie des
   Tatablaufs in den Händen.
2. Beihilfe (§ 27 StGB): Unterstützungshandlung ohne eigene Tatherrschaft.
3. Subjektive Theorie (BGH-Rspr.): Täter will die Tat als eigene; Gehilfe nur als fremde.
4. Objektiv-subjektive Kombinationstheorie in der Praxis: Tatherrschaft + Täterwille.

Bedeutung: Standardfall zur Abgrenzung Täterschaft/Beihilfe. Tatherrschaftslehre,
subjektive Theorie des BGH, § 25/27 StGB.
""".strip()},

  {"id": "steckbrief_wittig", "skill": "strafrecht", "text": """
Wittig-Fall (BGH NJW 1984, 1397) — Bundesgerichtshof, 4. Juli 1984, 3 StR 96/84

Frau Wittig, Ärztin, fand ihren Patienten bewusstlos nach Suizidversuch vor. Obwohl
medizinische Hilfe noch möglich gewesen wäre, unterließ sie jede Rettungsmaßnahme,
da der Patient ihr früher seinen Suizidwillen mitgeteilt hatte.

Leitsätze — Garantenpflicht vs. Patientenautonomie:
1. Ärzte haben eine Garantenstellung gegenüber ihren Patienten (§ 13 StGB).
2. Ein früherer geäußerter Suizidwille des Patienten kann die Garantenpflicht
   des Arztes ausschließen oder einschränken, wenn er ernstlich und endgültig ist.
3. Abwägung: Patientenautonomie (Selbstbestimmungsrecht) vs. Lebensschutzpflicht.
4. BGH: Die Freisprechung war im Ergebnis vertretbar (sehr umstritten).

Bedeutung: Grundlegender Fall zu Garantenpflicht, Selbstbestimmungsrecht und
ärztlicher Verantwortung beim Suizid. § 13 StGB, Garantenstellung, unterlassene Hilfeleistung.
""".strip()},

  {"id": "steckbrief_marlene_dietrich", "skill": "urheberrecht", "text": """
Marlene Dietrich (BGHZ 143, 214) — Bundesgerichtshof, I. Zivilsenat,
1. Dezember 1999, I ZR 49/97
(postmortales Persönlichkeitsrecht, kommerzielle Verwertung, Recht am eigenen Bild)

Sachverhalt: Nach dem Tod von Marlene Dietrich verwendeten verschiedene Unternehmen
ihr Bildnis und ihren Namen für kommerzielle Zwecke (z.B. auf Merchandising-Artikeln),
ohne die Erlaubnis ihrer Erben eingeholt zu haben. Die Erben klagten auf Unterlassung
und Schadensersatz.

Leitsätze (BGHZ 143, 214 — postmortales Persönlichkeitsrecht):
1. Postmortales Persönlichkeitsrecht mit vermögensrechtlichem Charakter: Das allgemeine
   Persönlichkeitsrecht (APR, Art. 2 Abs. 1 i.V.m. Art. 1 Abs. 1 GG) schützt auch nach
   dem Tod einer Person deren ideelle Interessen (Würde, Andenken). Darüber hinaus hat
   das APR einen vermögensrechtlichen Bestandteil: Das Recht, das eigene Bild und den
   eigenen Namen kommerziell zu nutzen (right of publicity).
2. Vererblichkeit: Der vermögensrechtliche Bestandteil des APR ist vererblich. Die Erben
   können die kommerzielle Nutzung des Bildnisses und Namens des Verstorbenen steuern
   und unerlaubte Verwendungen untersagen.
3. Schutzfrist: Der postmortale Schutz besteht nach Ansicht des BGH grundsätzlich 10 Jahre
   nach dem Tod; er verlängert sich bei fortdauernder kommerzieller Nutzung.
4. Anspruchsgrundlagen: Unterlassung (§ 1004 BGB analog), Schadensersatz (§ 823 BGB),
   Bereicherung (§ 812 BGB) oder Lizenzanalogie.

Bedeutung: Grundlegendes Urteil zur Vererblichkeit und kommerziellen Dimension des
Persönlichkeitsrechts. Grundlage des Merchandising-Schutzes für Prominente.

Schlagwörter: BGHZ 143 214, Marlene Dietrich, postmortales Persönlichkeitsrecht, APR,
Vererblichkeit, Recht am eigenen Bild, right of publicity, §§ 22 23 KUG, Merchandising,
§ 823 BGB, Urheberrecht.
""".strip()},

  {"id": "steckbrief_metall_auf_metall", "skill": "urheberrecht", "text": """
Metall auf Metall — Kraftwerk vs. Pelham (BGH + BVerfG + EuGH, 2008–2020)

Hintergrund: Musikgruppe Kraftwerk (Song "Metall auf Metall", 1977). Moses Pelham sampelte
eine 2-Sekunden-Rhythmussequenz für den Rap-Song "Nur mir" (Sabrina Setlur, 1997).

Zentrale Rechtsfragen:
1. Leistungsschutzrecht des Tonträgerherstellers (§ 85 UrhG): Selbst kürzeste Tonsequenzen
   aus einem Tonträger dürfen ohne Lizenz nicht verwendet werden (Vervielfältigungsrecht).
2. Freie Benutzung (§ 24 UrhG a.F.): Sampling ist nur als "freie Benutzung" erlaubt,
   wenn das Original nicht erkennbar bleibt — hier nicht der Fall.
3. EuGH-Vorlage (C-476/17): Sampling verletzt Vervielfältigungsrecht, außer die Sequenz
   ist im neuen Werk verändert und nicht erkennbar (EuGH 2019).
4. BVerfG: Kunstfreiheit (Art. 5 Abs. 3 GG / Art. 13 GRCh) muss gegen Leistungsschutzrecht
   abgewogen werden. BVerfG betonte Bedeutung des Samplings für Kunstform "Hip-Hop".

Bedeutung: Wichtigstes deutsches Urteil zum Musik-Sampling. Betrifft Produzenten,
Musiklabels, Künstler. Grenzen des erlaubten Samplings im Urheberrecht.
BGH I ZR 112/06, Metall auf Metall, Sampling, § 85 UrhG.
""".strip()},

  {"id": "steckbrief_parfuemflakon", "skill": "urheberrecht", "text": """
Parfümflakon-Entscheidung (BGH GRUR 1995, 581) — Bundesgerichtshof, I. Zivilsenat,
22. Juni 1995, I ZR 119/93
(Designschutz, Urheberrechtsschutz für Gebrauchsgegenstände, angewandte Kunst)

Sachverhalt: Ein Parfümhersteller gestaltete einen Flakon in einer besonderen,
ästhetisch ansprechenden Form. Ein Konkurrent brachte einen nahezu identischen Flakon
auf den Markt. Der Hersteller klagte auf urheberrechtlichen Schutz des Flakons als
Werk der angewandten Kunst.

Leitsätze (BGH GRUR 1995, 581 — Designschutz, angewandte Kunst):
1. Urheberrechtsschutz für Gebrauchsgegenstände (§ 2 Abs. 1 Nr. 4 UrhG — Werke der
   angewandten Kunst): Gebrauchsgegenstände können urheberrechtlichen Schutz genießen,
   wenn sie eine hinreichende Gestaltungshöhe aufweisen, die das rein Handwerkliche
   übersteigt und eine persönliche geistige Schöpfung darstellt.
2. Frühere Rechtsprechung (erhöhte Gestaltungshöhe): Der BGH forderte früher für
   angewandte Kunst eine "deutlich höhere" Gestaltungshöhe als für Werke der bildenden
   Kunst, um den Designschutz (§§ 1 ff. DesignG) vom Urheberrechtsschutz abzugrenzen.
3. Neue Rechtsprechung (Geburtstagszug-Entscheidung, BGH 2014): Der BGH hat diese erhöhte
   Anforderung aufgegeben. Für angewandte Kunst gilt derselbe Maßstab wie für andere
   Werkarten — die normale Schöpfungshöhe des § 2 Abs. 2 UrhG.
4. Abgrenzung DesignG/UrhG: Designschutz und Urheberrechtsschutz schließen sich nicht
   gegenseitig aus; paralleler Schutz ist möglich.

Bedeutung: Wichtige Entscheidung zur Schutzfähigkeit von Industriedesign im Urheberrecht.
Wegbereiter für die modernere Geburtstagszug-Rechtsprechung.

Schlagwörter: BGH GRUR 1995 581, Parfümflakon, angewandte Kunst, § 2 UrhG, Gestaltungshöhe,
Designschutz, DesignG, Gebrauchsgegenstand, persönliche geistige Schöpfung, Urheberrecht.
""".strip()},

  {"id": "steckbrief_anastasia", "skill": "verkehrsrecht", "text": """
Anastasia-Fall (BGHZ 43, 289) — Bundesgerichtshof, VI. Zivilsenat, 20. März 1965,
VI ZR 9/65
(Allgemeines Persönlichkeitsrecht, Sphärentheorie)

Sachverhalt: Die Frau, die behauptete, die zaristische Prinzessin Anastasia zu sein,
klagte gegen Veröffentlichungen, in denen ihre Identitätsbehauptung öffentlich als
falsch bezeichnet wurde, und gegen die daraus resultierenden Eingriffe in ihr Privatleben.
Das BVerfG hatte 1958 im Lüth-Urteil das allgemeine Persönlichkeitsrecht (APR) entwickelt.
Fraglich war, wie weit der zivilrechtliche Schutz des APR reicht.

Leitsätze (BGHZ 43, 289 — Allgemeines Persönlichkeitsrecht, Sphärentheorie):
1. Allgemeines Persönlichkeitsrecht (APR): Das APR (Art. 2 Abs. 1 i.V.m. Art. 1 Abs. 1 GG)
   schützt die Persönlichkeit des Menschen umfassend. Es ist ein sonstiges Recht i.S.v.
   § 823 Abs. 1 BGB.
2. Sphärentheorie: Für die Abwägung, wie weit der Schutz des APR reicht, wird die
   Persönlichkeit in Sphären unterteilt:
   - Intimsphäre (Kernbereich): absoluter Schutz, keine Abwägung möglich.
   - Privatsphäre: starker Schutz; Eingriffe bedürfen überwiegender Interessen.
   - Sozialsphäre (öffentliche Sphäre): geringerer Schutz; öffentliche Kritik grundsätzlich
     zulässig.
3. Abwägung mit Meinungsfreiheit (Art. 5 Abs. 1 GG) und Pressefreiheit (Art. 5 Abs. 2 GG):
   Je stärker der Eingriff in den Kernbereich, desto höhere Anforderungen an die Rechtfertigung.
4. Schadensersatz und Unterlassung: Bei Verletzung des APR kommen Schadensersatz (§ 823
   BGB) und Unterlassungsanspruch (§ 1004 BGB analog) in Betracht.

Bedeutung: Grundlage der Sphärentheorie im zivilrechtlichen Persönlichkeitsschutz.
Regelmäßig zitiert bei Fragen zur Medienberichterstattung und zum Datenschutz.

Schlagwörter: Allgemeines Persönlichkeitsrecht, APR, BGHZ 43 289, Sphärentheorie,
Intimsphäre, Privatsphäre, Sozialsphäre, § 823 BGB, § 1004 BGB, Persönlichkeitsschutz,
Anastasia.
""".strip()},

  {"id": "steckbrief_caroline_monaco", "skill": "verkehrsrecht", "text": """
Caroline von Monaco I (BGHZ 131, 332) — Bundesgerichtshof, VI. Zivilsenat,
15. November 1994, VI ZR 56/94; und EGMR, 24. Juni 2004 (von Hannover/Deutschland)

Sachverhalt: Prinzessin Caroline von Monaco klagte gegen die Veröffentlichung von
Fotos in deutschen Boulevardmedien, die sie in alltäglichen Situationen (Einkaufen,
Restaurantbesuch, Reiten) zeigten. Sie begehrte Unterlassung und Schadensersatz wegen
Verletzung ihres allgemeinen Persönlichkeitsrechts.

Leitsätze — Caroline von Monaco I (BGHZ 131, 332 und BGH 1995):
1. Relative Person der Zeitgeschichte: Personen der Zeitgeschichte (Prominente) müssen
   Bildberichterstattung über ihr öffentliches Auftreten grundsätzlich dulden. "Relative"
   Personen der Zeitgeschichte sind nur in ihrem zeitgeschichtlich relevanten Kontext
   schutzlos.
2. Schutz der Privatsphäre auch für Prominente: Selbst Personen der Zeitgeschichte haben
   ein schützenswertes Recht auf Privatsphäre in Bereichen, die nichts mit ihrer
   öffentlichen Funktion zu tun haben (Rückzugsbereich).
3. Geldentschädigung bei APR-Verletzung: Bei schwerwiegenden Persönlichkeitsrechtsverletzungen
   kommt auch eine Geldentschädigung (Schmerzensgeld) in Betracht, um eine Prävention zu
   erzielen (§ 823 BGB i.V.m. Art. 1, 2 GG).
4. EGMR-Entscheidung (2004): Der EGMR befand, dass Deutschland durch die Zulassung solcher
   Fotos Art. 8 EMRK (Recht auf Achtung des Privatlebens) verletzt hatte. Daraufhin änderte
   der BGH seine Rechtsprechung zum Bildnisschutz.

Bedeutung: Wegweisend für das Recht am eigenen Bild (§§ 22, 23 KUG) und den Schutz des
allgemeinen Persönlichkeitsrechts prominenter Personen.

Schlagwörter: Caroline von Monaco, BGHZ 131 332, APR, allgemeines Persönlichkeitsrecht,
Person der Zeitgeschichte, Bildberichterstattung, § 823 BGB, §§ 22 23 KUG, EGMR Art. 8 EMRK,
Privatsphäre, Geldentschädigung.
""".strip()},

  {"id": "steckbrief_salatblatt", "skill": "verkehrsrecht", "text": """
Salatblatt-Fall (BGHZ 37, 341) — Bundesgerichtshof, VI. Zivilsenat, 10. März 1962,
VI ZR 215/61

Sachverhalt: In einem Selbstbedienungsrestaurant lag ein Salatblatt auf dem Boden, das
eine Kundin übersah und auf dem sie ausrutschte und sich verletzte. Die Kundin klagte
gegen den Restaurantbetreiber aus § 823 Abs. 1 BGB wegen Verletzung der
Verkehrssicherungspflicht.

Leitsätze (BGHZ 37, 341 — Verkehrssicherungspflicht):
1. Verkehrssicherungspflicht (§ 823 Abs. 1 BGB): Wer eine Gefahrenquelle schafft oder
   unterhält, ist verpflichtet, alle zumutbaren Maßnahmen zu ergreifen, um Dritte vor
   daraus resultierenden Schäden zu schützen. Diese Pflicht trifft insbesondere Betreiber
   von Einrichtungen, die dem öffentlichen Verkehr geöffnet sind.
2. Umfang der Verkehrssicherungspflicht: Der Betreiber eines Restaurants muss den Boden
   regelmäßig auf rutschige Gegenstände kontrollieren und diese umgehend entfernen.
   Die Häufigkeit der Kontrollen richtet sich nach der Intensität der Nutzung und dem
   erkennbaren Gefahrenpotenzial.
3. Mitverschulden (§ 254 BGB): Das Mitverschulden des Geschädigten wird berücksichtigt,
   wenn dieser erkennbare Gefahren nicht beachtet hat. Im konkreten Fall: Sorglosigkeit
   des Geschädigten kann haftungsmindernd wirken.
4. Verschulden: Bei Verletzung der Verkehrssicherungspflicht indiziert der Verstoß
   das Verschulden; der Betreiber muss sich entlasten.

Bedeutung: Grundlegender Fall zur Verkehrssicherungspflicht bei Betrieb öffentlich
zugänglicher Einrichtungen. Standardfall im Deliktsrecht.

Schlagwörter: Verkehrssicherungspflicht, § 823 Abs. 1 BGB, BGHZ 37 341, Salatblatt,
Restaurant, Rutschgefahr, Schadensersatz, Mitverschulden § 254 BGB, Betreiberpflicht.
""".strip()},

  {"id": "steckbrief_schwimmerschalter", "skill": "verkehrsrecht", "text": """
Schwimmerschalter-Fall (BGHZ 67, 359) — Bundesgerichtshof, VI. Zivilsenat,
11. Januar 1977, VI ZR 268/74
(Weiterfresserschäden, § 823 Abs. 1 BGB, Eigentumsverletzung)

Sachverhalt: Ein fehlerhafter Schwimmerschalter (Zulieferteil) verursachte einen Schaden
an der Maschine, in die er eingebaut war. Fraglich war, ob der Schaden an der gesamten
Maschine als Eigentumsverletzung i.S.d. § 823 Abs. 1 BGB zu werten ist, oder ob es
sich um einen reinen Vermögensschaden (Mangelfolgeschaden) handelt, der nur über
Vertragsrecht geltend gemacht werden kann.

Leitsätze (BGHZ 67, 359 — Weiterfresserschäden):
1. Eigentumsverletzung durch Weiterfresserschäden: Schäden, die ein mangelhaftes Teil
   an der Gesamtsache anrichtet, in die es integriert wurde, können eine Eigentumsverletzung
   nach § 823 Abs. 1 BGB begründen. Dies gilt, wenn der Schaden über den ursprünglichen
   Mangel des Teils hinaus auf andere Teile der Sache "weiterfrisst".
2. Abgrenzung vom Mangelschaden: Der bloße Mangel des gelieferten Teils selbst (Wert des
   fehlerhaften Schwimmerschalters) ist kein Schaden am Eigentum i.S.d. § 823 BGB —
   dieser muss über das Vertragsrecht (Gewährleistung) geltend gemacht werden.
3. Deliktsrechtlicher Schutz des Integritätsinteresses: Sobald der Schaden über den
   Mangel hinausgeht und Teile beschädigt, die ursprünglich mangelfrei waren ("Weiterfresser"),
   greift § 823 Abs. 1 BGB.
4. Abgrenzung zur reinen Vermögensschäden: Reine Vermögensschäden (entgangener Gewinn)
   ohne Verletzung eines absoluten Rechts sind über § 823 BGB nicht ersatzfähig.

Bedeutung: Grundlage der Weiterfresserschadenrechtsprechung. Verdeutlicht die Abgrenzung
von Delikts- und Vertragsrecht beim Produktschaden.

Schlagwörter: BGHZ 67 359, Weiterfresserschäden, § 823 Abs. 1 BGB, Eigentumsverletzung,
Mangelschaden, Integritätsinteresse, Produkthaftung, Schwimmerschalter, Deliktsrecht,
Vertragsrecht.
""".strip()},

]

# ── Embedding + ChromaDB ──────────────────────────────────────────────────────
def run(dry_run: bool, filter_skill: str | None):
    import chromadb
    from sentence_transformers import SentenceTransformer

    print(f"[add_steckbriefe] Lade Modell {MODEL_NAME} …", flush=True)
    model = SentenceTransformer(MODEL_NAME)
    print(f"[add_steckbriefe] Dim={model.get_embedding_dimension()}, device={model.device}", flush=True)

    client = chromadb.PersistentClient(path=CHROMADB_PATH)

    # gruppiere nach skill
    by_skill: dict[str, list[dict]] = {}
    for sb in STECKBRIEFE:
        skill = sb["skill"]
        if filter_skill and skill != filter_skill:
            continue
        by_skill.setdefault(skill, []).append(sb)

    for skill, sbs in by_skill.items():
        col_name = f"openlex_{skill}"
        try:
            col = client.get_collection(col_name)
        except Exception:
            print(f"  [SKIP] Collection {col_name!r} nicht gefunden", flush=True)
            continue

        # Prüfe welche IDs schon existieren
        existing = set()
        try:
            res = col.get(ids=[s["id"] for s in sbs])
            existing = set(res["ids"])
        except Exception:
            pass

        to_add = [s for s in sbs if s["id"] not in existing]
        if not to_add:
            print(f"  [OK] {col_name}: alle {len(sbs)} Steckbriefe bereits vorhanden", flush=True)
            continue

        texts = [s["text"] for s in to_add]
        ids   = [s["id"]   for s in to_add]
        metas = [{"source": "steckbrief_leitfall", "skill": s["skill"],
                  "item_type": "urteil_steckbrief"} for s in to_add]

        print(f"  Embedde {len(to_add)} Steckbriefe für {col_name} …", flush=True)
        vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

        if dry_run:
            print(f"  [DRY-RUN] würde {len(to_add)} Dokumente in {col_name} hinzufügen", flush=True)
        else:
            col.add(ids=ids, embeddings=[v.tolist() for v in vecs],
                    documents=texts, metadatas=metas)
            print(f"  [OK] {len(to_add)} Steckbriefe → {col_name}", flush=True)

    print("[add_steckbriefe] Fertig.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skill", default=None, help="Nur diesen Skill verarbeiten")
    args = parser.parse_args()
    run(args.dry_run, args.skill)
