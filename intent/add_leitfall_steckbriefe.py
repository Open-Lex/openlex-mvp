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
