#!/usr/bin/env python3
"""
Systemischer Fix voelkerrecht — 81.4 → >90
Hauptproblem: EMRK komplett ohne Steckbriefe (norm_presence=0.0 für Art. 34),
              Art. 24/25 UN-Charta, Art. 51 ohne Fallmaterial

Hinzugefügte Steckbriefe:
  1. EGMR Loizidou v Turkey 1996     — Art. 34 EMRK + extraterritoriale Anwendung
  2. EGMR Handyside v UK 1976         — Art. 10 EMRK, Margin of Appreciation
  3. EGMR Öcalan v Turkey 2005        — Art. 3/6 EMRK, fair trial, Todesstrafe
  4. Methodenwissen EMRK-Verfahren    — Art. 34/35 Zulässigkeitsvoraussetzungen
  5. IGH Lockerbie 1992               — Art. 24/25 UN-Charta, SR-Vorrang
  6. IGH Oil Platforms 2003           — Art. 51 Selbstverteidigung, Verhältnismäßigkeit
  7. IGH Wall Advisory Opinion 2004   — Gewaltverbot, humanitäres VR, besetztes Gebiet
  8. IGH Armed Activities Congo 2005  — Selbstverteidigung, Nichteinmischung, DRC/Uganda
"""

import sys
sys.path.insert(0, '/opt/openlex-mvp-v2')

import chromadb
from sentence_transformers import SentenceTransformer

CHROMADB_PATH = "/opt/openlex-mvp-v2/chromadb"
MODEL_NAME    = "mixedbread-ai/deepset-mxbai-embed-de-large-v1"
SKILL         = "voelkerrecht"
COLLECTION    = f"openlex_{SKILL}"

# ─── Neue Steckbriefe ────────────────────────────────────────────────────────

STECKBRIEFE = [

# ─── EMRK / EGMR ─────────────────────────────────────────────────────────────

{
"id":   "steckbrief_egmr_loizidou_emrk",
"skill": SKILL,
"meta": {
    "source_type": "urteil",
    "gericht":     "EGMR",
    "case_ref":    "Loizidou v Turkey 1996 (App. 15318/89)",
},
"doc": """EGMR, Urteil vom 18.12.1996 — Loizidou v. Türkei (Große Kammer)

Sachverhalt: Titina Loizidou, zypriotische Staatsangehörige, flüchtete 1974 aus Kyrenia
(Nordzypern) nach dem türkischen Militäreinmarsch. Sie konnte ihr Eigentum im nördlichen
Teil Zyperns nicht mehr nutzen. Die Türkei betrieb eine Dauereinrede: Der EGMR sei nicht
zuständig, weil die beanstandeten Handlungen in Nordzypern durch die "Türkische Republik
Nordzypern" (TRNZ, nur von der Türkei anerkannt) begangen worden seien, nicht durch die
Türkei selbst.

Rechtsfrage 1 — Individualbeschwerde Art. 34 EMRK:
Die Beschwerde wurde nach Art. 34 EMRK (früher Art. 25) von Loizidou als Einzelperson
eingelegt. Voraussetzungen der Zulässigkeit nach Art. 34 EMRK: (a) Beschwerdeführerin ist
eine natürliche Person; (b) Beschwerde richtet sich gegen eine Hohe Vertragspartei (Türkei
ist EMRK-Mitgliedstaat); (c) Opfereigenschaft: Die Beschwerdeführerin selbst ist
unmittelbar betroffen (Eigentumsverlust, Art. 1 ZP 1 EMRK); (d) Erschöpfung innerstaatlicher
Rechtsmittel nach Art. 35 EMRK: In der TRNZ existiert kein effektiver Rechtsweg; (e) Frist:
6 Monate nach der endgültigen innerstaatlichen Entscheidung (heute 4 Monate, seit Protokoll 15).

Rechtsfrage 2 — Extraterritoriale Zuständigkeit (Art. 1 EMRK):
Der EGMR stellte klar: Die Türkei übt effective control über Nordzypern aus, weil sie dort
massiv militärisch präsent ist (ca. 30.000 Soldaten) und die TRNZ abhängig von Türkei ist.
Staaten haften nach Art. 1 EMRK für Handlungen, durch die sie outside ihrer Grenzen
Kontrolle ausüben (Jurisdiction-Test: effective control over an area). Der Türkei wird
das Handeln der TRNZ zugerechnet.

Kernaussagen:
- Art. 34 EMRK eröffnet Individualbeschwerde für natürliche Personen, Gruppen und NGOs.
- Opfereigenschaft (victim status) verlangt unmittelbare eigene Betroffenheit; mittelbare
  ("potential victim") reicht nur, wenn Eingriff unmittelbar droht.
- Art. 1 EMRK gilt extraterritorial bei effective control; EMRK ist kein Instrument
  gegen Drittstaaten außerhalb des Hoheitsbereichs einer Vertragspartei.
- Ergebnis: Türkei verletzte Art. 1 ZP 1 EMRK (Eigentumsschutz) und Art. 8 EMRK.

Relevanz: Leitfall zu Art. 34 EMRK (Individualbeschwerde), Art. 1 EMRK (Hoheitsgewalt),
Opfereigenschaft, Erschöpfung nationaler Rechtsmittel (Art. 35 EMRK).
"""},

{
"id":   "steckbrief_egmr_handyside_emrk_art10",
"skill": SKILL,
"meta": {
    "source_type": "urteil",
    "gericht":     "EGMR",
    "case_ref":    "Handyside v UK 1976 (App. 5493/72)",
},
"doc": """EGMR, Urteil vom 07.12.1976 — Handyside v. Vereinigtes Königreich

Sachverhalt: Richard Handyside, britischer Verleger, veröffentlichte das „Little Red
Schoolbook" mit Passagen über Sexualaufklärung für Jugendliche. Britische Behörden
beschlagnahmten die Bücher nach dem Obscene Publications Act 1959. Handyside erhob
Individualbeschwerde nach Art. 34 EMRK (damals Art. 25) wegen Verletzung von Art. 10 EMRK
(Meinungsfreiheit).

Zulässigkeit nach Art. 34 / 35 EMRK:
- Art. 34 EMRK: Beschwerdeführer = natürliche Person, unmittelbar und persönlich betroffen
  (Opfereigenschaft); Beschwerde gegen das VK als Vertragsstaat.
- Art. 35 EMRK: Erschöpfung des innerstaatlichen Rechtswegs (Strafverfahren
  abgeschlossen); 6-Monatsfrist eingehalten.
- Ergebnis: Beschwerde zulässig.

Materiellrechtlich — Art. 10 EMRK:
Der EGMR etablierte das Konzept der Margin of Appreciation (Ermessensspielraum der
Vertragsstaaten). Einschränkungen der Meinungsfreiheit nach Art. 10 Abs. 2 EMRK müssen
(1) gesetzlich vorgesehen, (2) einem legitimen Ziel dienend und (3) in einer demokratischen
Gesellschaft notwendig sein (verhältnismäßig). Da Schutz der Jugend legitimes Ziel, räumte
der EGMR dem UK einen weiten Ermessensspielraum ein. Keine Verletzung Art. 10 EMRK.

Kernaussagen:
- Individualbeschwerde nach Art. 34 EMRK setzt unmittelbare, persönliche Betroffenheit
  (victim status) voraus — kein Popularklagerecht.
- Art. 35 EMRK verlangt Ausschöpfung aller innerstaatlichen Rechtsmittel, die effektiv
  und ausreichend (adequate and effective) sind.
- Margin of Appreciation: Staaten haben Spielraum bei Einschränkung von Konventionsrechten,
  solange der EGMR den Kern (essence) nicht verletzt sieht.
- Präzedenz: Grundstein für Art.-10-Dogmatik des EGMR (Pressefreiheit, Kunstfreiheit).

Relevanz: Leitfall zu Art. 10 EMRK, Margin of Appreciation, Zulässigkeitsvoraussetzungen
nach Art. 34/35 EMRK.
"""},

{
"id":   "steckbrief_egmr_oecalan_art3_art6",
"skill": SKILL,
"meta": {
    "source_type": "urteil",
    "gericht":     "EGMR",
    "case_ref":    "Öcalan v Turkey 2005 (App. 46221/99)",
},
"doc": """EGMR, Urteil vom 12.05.2005 (Große Kammer) — Öcalan v. Türkei

Sachverhalt: Abdullah Öcalan, PKK-Führer, wurde 1999 in Kenia festgenommen und in die
Türkei verbracht. Türkische Behörden verhörten ihn ohne Anwaltsbegleitung; er wurde vor
einem Staatssicherheitsgericht zum Tode verurteilt (später umgewandelt in lebenslange
Haft nach Abschaffung der Todesstrafe in der Türkei). Öcalan erhob Individualbeschwerde
nach Art. 34 EMRK wegen Verletzung von Art. 3 (Verbot unmenschlicher Behandlung),
Art. 5 (Freiheitsrecht), Art. 6 (faires Verfahren).

Zulässigkeit — Art. 34/35 EMRK:
Öcalan = natürliche Person, unmittelbar betroffen; Türkei = Vertragsstaat; innerstaatlicher
Rechtsweg erschöpft (Verfassungsgericht). Beschwerde zulässig.

Materiell — Art. 3 EMRK (Folterverbot / unmenschliche Behandlung):
Verhältnis Todesstrafe zu Art. 3 EMRK: Der EGMR stellte fest, dass die Verhängung und
Vollstreckung der Todesstrafe nach einem unfairen Verfahren Art. 3 EMRK verletzt
(„death row phenomenon"). Todesstrafe an sich ist durch ZP 13 EMRK verboten.

Materiell — Art. 6 EMRK (faires Verfahren):
- Beteiligung eines Militärrichters am Staatssicherheitsgericht verletzt das Recht auf ein
  unabhängiges und unparteiisches Gericht nach Art. 6 Abs. 1 EMRK.
- Verweigerung des Anwaltsbeistands in der entscheidenden ersten Verhörphase verletzt
  das Recht auf Verteidigung nach Art. 6 Abs. 3 lit. c EMRK.

Kernaussagen:
- Art. 34 EMRK: Individualbeschwerde steht auch Personen in Haft und auch bei
  Auslieferungssachverhalten zu; Opfereigenschaft bei unmittelbarer persönlicher Betroffenheit.
- Art. 3 EMRK enthält absolutes Verbot; kein Ausnahmen durch öffentliche Sicherheit
  (auch bei Terrorismusverdächtigen).
- Art. 6 EMRK: Recht auf faires Verfahren gilt auch in Sicherheitsgerichten; strukturelle
  Mängel (Militärrichter) genügen als Verletzungsnachweis.

Relevanz: Leitfall zu Art. 3 EMRK (absolutes Verbot), Art. 6 EMRK (fair trial),
Todesstrafe, Individualbeschwerdeverfahren Art. 34/35 EMRK.
"""},

{
"id":   "steckbrief_emrk_individualbeschwerde_verfahren",
"skill": SKILL,
"meta": {
    "source_type": "methodenwissen",
    "gericht":     "EGMR",
    "case_ref":    "EMRK Art. 34/35 — Verfahrensüberblick",
},
"doc": """Europäische Menschenrechtskonvention (EMRK) — Individualbeschwerdeverfahren
Art. 34 und 35 EMRK — systematische Übersicht

I. Individualbeschwerde nach Art. 34 EMRK

Art. 34 EMRK: „Der Gerichtshof kann von jeder natürlichen Person, nichtstaatlichen
Organisation oder Personengruppe Beschwerden entgegennehmen, die behaupten, durch eine
der Hohen Vertragsparteien in einem der in der Konvention oder den Protokollen anerkannten
Rechte verletzt zu sein."

Beschwerdeberechtigung (ratione personae):
1. Natürliche Personen — jeder Mensch unabhängig von Staatsangehörigkeit
2. Nichtstaatliche Organisationen — juristische Personen (NGO, Vereine, Unternehmen)
3. Personengruppen — mehrere Personen gemeinsam (class action möglich)
   NICHT beschwerdefähig: Staaten (→ Staatenbeschwerde Art. 33), öffentliche Institutionen,
   staatliche Unternehmen.

Beschwerdegegner: Nur Hohe Vertragsparteien der EMRK (46 Mitgliedstaaten des Europarats).

Opfereigenschaft (victim status):
- Unmittelbares Opfer (direct victim): Direkt durch Konventionsverletzung betroffen.
- Mittelbares Opfer (indirect victim): Nahe Angehörige, wenn kein Zugang zur Beschwerde.
- Potenzielles Opfer (potential victim): Wenn Eingriff unmittelbar droht (z.B. Gesetz
  unmittelbar anwendbar, ohne konkrete Vollzugsmaßnahme — str.).
- Kein Popularklagerecht: Keine Beschwerde im öffentlichen Interesse ohne eigene Betroffenheit.

II. Zulässigkeitsvoraussetzungen nach Art. 35 EMRK

Art. 35 Abs. 1 EMRK — Erschöpfung innerstaatlicher Rechtsmittel:
- Alle wirksamen und zugänglichen Rechtsmittel im Inland müssen ausgeschöpft sein.
- Maßstab: Rechtsmittel muss effektiv sein (geeignet, die Verletzung abzustellen).
- Frist: Beschwerde muss innerhalb von 4 Monaten (seit Protokoll 15, in Kraft 2022;
  davor 6 Monate) nach der endgültigen innerstaatlichen Entscheidung eingelegt werden.

Art. 35 Abs. 2/3 EMRK — Weitere Unzulässigkeitsgründe:
- Identische Beschwerde bereits geprüft (res iudicata, ne bis in idem).
- Offensichtliche Unzulässigkeit (manifestly ill-founded).
- Keine erhebliche Benachteiligung (no significant disadvantage) — Bagatellgrenze.
- Anonyme Beschwerde.
- Missbrauch des Beschwerderechts.

III. Sachliche Zuständigkeit (ratione materiae): Nur Konventionsrechte (Art. 2–18 EMRK
und Protokolle) sind beschwerdefähig, keine allgemeinen politischen Forderungen.

Räumliche Zuständigkeit (ratione loci / Art. 1 EMRK): Juristiktion ist nicht auf das
Territorium beschränkt; effektive Kontrolle (effective control) über fremdes Gebiet
oder einzelne Personen genügt (Loizidou, Banković, Al-Skeini).

IV. Verfahren vor dem EGMR
- Einzelrichter: Offensichtlich unzulässige Beschwerden (sofortige Streichung).
- Kammer (7 Richter): Regelverfahren (Zulässigkeit + Begründetheit).
- Große Kammer (17 Richter): Schwerwiegende Rechtsfragen, Abweichung von Präzedenzfall.
- Güterliche Einigung (Art. 39 EMRK): Verfahrensbeendigung durch friendly settlement.
- Gerechte Entschädigung (Art. 41 EMRK): Geldentschädigung bei Verletzung.

Leitfälle: Loizidou v Turkey 1996 (Art. 34, Jurisdiktion), Handyside v UK 1976
(Art. 34/35 + Margin of Appreciation), Öcalan v Turkey 2005 (Art. 3/6 EMRK).
"""},

# ─── UN-Sicherheitsrat / Art. 24/25 UN-Charta ────────────────────────────────

{
"id":   "steckbrief_igh_lockerbie_sr_art25",
"skill": SKILL,
"meta": {
    "source_type": "urteil",
    "gericht":     "IGH",
    "case_ref":    "Lockerbie Cases 1992 (Libya v UK/USA)",
},
"doc": """IGH, Beschluss vom 14.04.1992 — Questions of Interpretation and Application of the
1971 Montreal Convention arising from the Aerial Incident at Lockerbie
(Libyen v. Vereinigtes Königreich; Libyen v. USA)

Sachverhalt: Am 21.12.1988 explodierte Flug Pan Am 103 über Lockerbie (Schottland) —
270 Tote. Die USA und das VK verlangten von Libyen die Auslieferung zweier
libyscher Staatsangehöriger, die des Anschlags verdächtig waren. Libyen berief sich
auf die Montrealer Luftfahrtsicherheitskonvention (1971): Danach habe es das Recht, die
Verdächtigen selbst strafrechtlich zu verfolgen. Der UN-Sicherheitsrat verabschiedete
Resolutionen 731 und 748 (1992), die Libyen unter Kapitel VII zwangen, die Verdächtigen
auszuliefern und mit den Ermittlungen zu kooperieren.

Rechtsfrage 1 — Art. 24 und 25 UN-Charta (Bindungswirkung von SR-Resolutionen):
Der IGH entschied (einstweiliger Rechtsschutz), dass Resolutionen des Sicherheitsrats,
die nach Kapitel VII UN-Charta ergehen, für alle UN-Mitgliedstaaten verbindlich sind
(Art. 25 UN-Charta: „Die Mitglieder der Vereinten Nationen kommen überein, die
Beschlüsse des Sicherheitsrats … zu akzeptieren und durchzuführen."). Die Pflichten aus
der UN-Charta gehen nach Art. 103 UN-Charta allen anderen vertraglichen Pflichten vor —
auch Pflichten aus multilateralen Konventionen wie der Montrealer Konvention.

Rechtsfrage 2 — Verhältnis SR-Resolution zu Vertragspflichten:
Libyen konnte sich auf die Montrealer Konvention nicht berufen, weil die verbindliche
SR-Resolution 748 dem entgegenstand. Art. 103 UN-Charta schafft einen Vorrang der
Charta-Pflichten. Der IGH lehnte einstweilige Maßnahmen zugunsten Libyens ab.

Art. 24 UN-Charta — Befugnisse des Sicherheitsrats:
- Hauptverantwortung für Weltfrieden und internationale Sicherheit.
- Kapitel VI: Friedliche Streitbeilegung (Empfehlungen, nicht bindend).
- Kapitel VII: Maßnahmen bei Bedrohung, Bruch des Friedens, Angriffshandlung.
  Art. 39: Feststellung der Bedrohung/des Friedensbruchs → Voraussetzung für Kap. VII.
  Art. 40: Vorläufige Maßnahmen (einstweilige Verfügung).
  Art. 41: Nichtmilitärische Zwangsmaßnahmen (Sanktionen, Embargo).
  Art. 42: Militärische Maßnahmen (Autorisierung von Gewaltanwendung).

Kernaussagen:
- SR-Resolutionen unter Kapitel VII sind für alle UN-Mitglieder verbindlich (Art. 25 UN-Charta).
- Art. 103 UN-Charta: Charta-Pflichten haben Vorrang vor allen anderen Verträgen.
- Der IGH prüft NICHT die Rechtmäßigkeit von SR-Resolutionen (ultra vires-Problem bleibt offen).
- Kapitel-VII-Befugnis setzt Art. 39-Feststellung des SR voraus.

Relevanz: Leitfall zu Art. 24/25 UN-Charta (Sicherheitsratskompetenzen), Art. 103 UN-Charta,
Vorrang von SR-Resolutionen über Vertragspflichten.
"""},

# ─── Art. 51 UN-Charta / Selbstverteidigung ──────────────────────────────────

{
"id":   "steckbrief_igh_oil_platforms_art51",
"skill": SKILL,
"meta": {
    "source_type": "urteil",
    "gericht":     "IGH",
    "case_ref":    "Oil Platforms (Iran v USA) 2003",
},
"doc": """IGH, Urteil vom 06.11.2003 — Oil Platforms (Islamische Republik Iran v. USA)

Sachverhalt: Im Kontext des Iran-Irak-Kriegs 1980–1988 griffen US-Marineeinheiten 1987/1988
iranische Ölbohrplattformen an. Die USA beriefen sich auf Art. 51 UN-Charta
(Selbstverteidigung) und behaupteten, Iran habe zuvor durch Minen und Raketenattacken
US-Schiffe angegriffen. Iran klagte wegen Verletzung eines bilateralen Freundschaftsvertrags.

Rechtsfrage — Art. 51 UN-Charta (Selbstverteidigung):
Voraussetzungen nach Art. 51 UN-Charta (und Gewohnheitsvölkerrecht, Nicaragua-Urteil):
1. Bewaffneter Angriff (armed attack): Ein spezifisch dem Iran zurechenbarer,
   ausreichend gravierender bewaffneter Angriff muss vorgelegen haben.
   → Der IGH stellte fest: Die von den USA behaupteten iranischen Angriffe (Minen,
   Raketen) erreichten nicht die Schwelle eines „bewaffneten Angriffs" im Sinne von Art. 51.
2. Notwendigkeit (necessity): Kein alternatives, weniger eingreifendes Mittel.
3. Verhältnismäßigkeit (proportionality): Reaktion muss in Art und Umfang dem Angriff
   entsprechen. Zerstörung von Ölbohrplattformen als Reaktion auf Minenlegen war
   unverhältnismäßig.
→ Ergebnis: USA konnten sich nicht auf Art. 51 berufen; Selbstverteidigung scheiterte
  am Fehlen eines bewaffneten Angriffs.

Verhältnis Art. 2 Nr. 4 / Art. 51 UN-Charta:
Art. 2 Nr. 4 UN-Charta: Absolutes Gewaltverbot (jus cogens). Ausnahmen nur:
- Art. 51 UN-Charta: Individuelles/kollektives Selbstverteidigungsrecht bei bewaffnetem Angriff,
  bis Sicherheitsrat Maßnahmen ergreift. Pflicht zur Unterrichtung des SR (Art. 51 Satz 2).
- Kapitel VII: SR-autorisierte Gewalt (Kollektivsicherheitssystem).
- Keine dritte Ausnahme: Humanitäre Intervention ist völkerrechtlich umstritten (nicht anerkannt).

Voraussetzungen Selbstverteidigung nach Art. 51 / Gewohnheitsrecht:
(1) Bewaffneter Angriff (armed attack) eines Staates — bloße Grenzstreitigkeiten nicht ausreichend.
(2) Notwendigkeit: Militärische Reaktion als letztes Mittel.
(3) Verhältnismäßigkeit: Maßnahme muss dem Angriff angemessen sein.
(4) Sofortige Notifizierung des Sicherheitsrats (Art. 51 Satz 2 UN-Charta).

Caroline-Formel (1837, Gewohnheitsrecht):
Präventive Selbstverteidigung bei „instant, overwhelming necessity leaving no moment for
deliberation" — enger Standard, heute str. (anticipatory self-defense vs. preemptive war).

Kernaussagen:
- „Bewaffneter Angriff" (Art. 51) erfordert erhebliche Schwere; Provokationen oder
  Grenzzwischenfälle reichen nicht.
- Drei kumulative Voraussetzungen: armed attack + necessity + proportionality.
- Preemptive self-defense (ohne vorherigen Angriff) ist nach klassischem VR unzulässig.

Relevanz: Leitfall zu Art. 51 UN-Charta, Selbstverteidigung, Verhältnismäßigkeit,
„armed attack threshold".
"""},

{
"id":   "steckbrief_igh_wall_opinion_2004",
"skill": SKILL,
"meta": {
    "source_type": "urteil",
    "gericht":     "IGH",
    "case_ref":    "Legal Consequences of the Construction of a Wall in the OPT 2004",
},
"doc": """IGH, Gutachten vom 09.07.2004 — Rechtliche Konsequenzen des Baus einer Mauer
im besetzten palästinensischen Gebiet (Legal Consequences of the Construction of a
Wall in the Occupied Palestinian Territory)

Sachverhalt: Israel begann 2002 mit dem Bau einer Sperrmauer/Sperranlage im Westjordanland,
zum Teil auf besetztem palästinensischem Gebiet. Die UN-Generalversammlung bat den IGH
gemäß Art. 96 UN-Charta um ein Gutachten zu den völkerrechtlichen Konsequenzen.

Gutachtenkompetenz des IGH:
Der IGH bestätigte seine Zuständigkeit für Gutachten der Generalversammlung nach
Art. 96 UN-Charta. Er stellte klar: Gutachten haben keine bindende Wirkung, aber
hohe rechtliche Autorität.

Israelisches Argument — Art. 51 UN-Charta:
Israel berief sich auf sein Selbstverteidigungsrecht (Art. 51 UN-Charta) gegen
Terroranschläge aus dem Westjordanland. Der IGH lehnte dies ab: Art. 51 setzt einen
bewaffneten Angriff eines anderen Staates voraus. Da das Westjordanland von Israel
selbst kontrolliert wird (Besatzungsgebiet), könne Art. 51 auf diese Situation nicht
angewendet werden — die Bedrohung ist innerterritorial/internal, nicht ein Angriff
eines fremden Staates. Zudem müsste Art. 51 durch Art. 2 Nr. 4 + Kapitel VI als primäres
Instrument der Streitbeilegung flankiert werden.

Humanitäres Völkerrecht in besetzten Gebieten:
- IV. Genfer Konvention (1949): Anwendbar im besetzten Westjordanland.
- HLKO (Haager Landkriegsordnung): Bindend als Gewohnheitsrecht.
- Israel muss Pflichten des Besatzungsrechts einhalten (freie Bewegung der Zivilbevölkerung,
  keine Enteignung außer militärischer Notwendigkeit).
- EMRK und IPBPR: Gelten auch extraterritorial bei effektiver Kontrolle.

Kernaussagen:
- Bau der Mauer auf besetztem Gebiet verletzt: Art. 2 Nr. 4 UN-Charta, Genfer
  Konventionen, Recht auf Selbstbestimmung der Palästinenser.
- Art. 51 UN-Charta gilt nicht bei internem Aufstand / nicht-staatlichem Akteur im
  eigenen Besatzungsgebiet (str. nach 9/11-Debatten).
- Drittstaatenpflicht: Andere UN-Mitglieder dürfen die illegale Situation nicht anerkennen
  und müssen auf Beendigung hinwirken.

Relevanz: Leitfall zu Art. 51 (Grenzen), Selbstbestimmungsrecht, besetztes Gebiet,
Verhältnis EMRK/IPBPR zur UN-Charta, humanitäres Völkerrecht.
"""},

{
"id":   "steckbrief_igh_armed_activities_congo",
"skill": SKILL,
"meta": {
    "source_type": "urteil",
    "gericht":     "IGH",
    "case_ref":    "Armed Activities on the Territory of the Congo (DRC v Uganda) 2005",
},
"doc": """IGH, Urteil vom 19.12.2005 — Armed Activities on the Territory of the Congo
(Demokratische Republik Kongo v. Uganda)

Sachverhalt: Uganda stationierte Truppen im Osten des Kongo (DRC), unterstützte bewaffnete
Rebellengruppen und beutete kongolesische Ressourcen aus. Uganda berief sich auf
Selbstverteidigung nach Art. 51 UN-Charta gegen Angriffe irregulärter Gruppen (ADF),
die von kongolesischem Boden operierten.

Rechtsfrage 1 — Gewaltverbot Art. 2 Nr. 4 UN-Charta:
Uganda verletzte das Gewaltverbot, indem es Truppen ohne Einwilligung des Kongo
(nach Widerruf des Einverständnisses 1998) im Kongo stationierte und Rebellengruppen
unterstützte. Keine Rechtfertigung durch Art. 51.

Rechtsfrage 2 — Selbstverteidigung Art. 51 UN-Charta:
Ugandas Argument: ADF-Rebellen griffen von kongolesischem Boden aus ugandische
Interessen an → Selbstverteidigung gegen den Kongo (als „unable or unwilling").
IGH: Nein. Selbstverteidigung nach Art. 51 setzt (1) bewaffneten Angriff eines Staates
voraus (nicht-staatliche Akteure allein reichen nicht — str., vgl. Öl-Plattformen,
Wall-Gutachten); (2) das Kongo selbst hat Uganda nicht angegriffen; (3) Uganda unterrichtete
den Sicherheitsrat nicht (Art. 51 Satz 2 UN-Charta — Pflicht zur Notifizierung).

„Unable or Unwilling"-Doktrin:
Uganda verwies auf die Unfähigkeit des Kongo, ADF-Rebellen zu kontrollieren. Der IGH
lehnte dies als eigenständige Rechtfertigung ab — diese Doktrin findet im UN-Chartarecht
keine ausdrückliche Grundlage und ist im Gewohnheitsrecht umstritten.

Rechtsfrage 3 — Nichteinmischungsprinzip / Selbstbestimmung:
Uganda verletzte durch Unterstützung und Ermutigung von Rebellengruppen das Prinzip
der Nichteinmischung (non-intervention). Die Nichteinmischung ist gewohnheitsrechtlich
verankert (Nicaragua-Urteil 1986) und verbietet es, anderen Staaten die politische
Ordnung zu diktieren.

Reparationen:
Uganda muss dem Kongo Schadensersatz leisten (Reparationsurteil 2022: USD 325 Mio.).

Kernaussagen:
- Art. 51 setzt staatlichen armed attack voraus; nicht-staatliche Akteure aus fremdem
  Gebiet rechtfertigen keine Selbstverteidigung gegen den Gebietsstaat (außer bei
  zurechenbarer Verantwortung).
- Art. 51 Satz 2: Notifizierungspflicht an den SR ist materielle Voraussetzung, nicht
  nur Formalität.
- Nichteinmischung als erga-omnes-Pflicht (Nicaragua, Barcelona Traction).

Relevanz: Leitfall zu Art. 51 (non-state actors), Nichteinmischungsprinzip,
„unable or unwilling", Reparationspflichten.
"""},
]

# ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

def embed_batch(model, texts, batch_size=16):
    embs = []
    for i in range(0, len(texts), batch_size):
        embs.extend(model.encode(texts[i:i+batch_size], show_progress_bar=False).tolist())
    return embs

def add_if_new(col, id_, doc, meta):
    try:
        existing = col.get(ids=[id_])
        if existing['ids']:
            print(f"  SKIP (exists): {id_}")
            return False
    except Exception:
        pass
    return True  # needs adding

# ─── Hauptprogramm ────────────────────────────────────────────────────────────

print("Loading model …")
model = SentenceTransformer(MODEL_NAME)

print("Connecting to ChromaDB …")
client = chromadb.PersistentClient(CHROMADB_PATH)
col    = client.get_or_create_collection(COLLECTION,
         metadata={"hnsw:space": "cosine"})
print(f"Collection {COLLECTION}: {col.count()} docs")

to_add_ids, to_add_docs, to_add_metas = [], [], []

for sb in STECKBRIEFE:
    id_  = sb["id"]
    doc  = sb["doc"].strip()
    meta = {**sb["meta"], "skill": SKILL, "id": id_}
    if add_if_new(col, id_, doc, meta):
        to_add_ids.append(id_)
        to_add_docs.append(doc)
        to_add_metas.append(meta)
    else:
        pass  # already printed skip

if not to_add_ids:
    print("Nichts hinzuzufügen — alle Steckbriefe bereits vorhanden.")
else:
    print(f"Embedding {len(to_add_ids)} neue Steckbriefe …")
    embeddings = embed_batch(model, to_add_docs)
    col.add(ids=to_add_ids, documents=to_add_docs,
            metadatas=to_add_metas, embeddings=embeddings)
    print(f"✓ {len(to_add_ids)} Steckbriefe hinzugefügt.")
    print(f"  Collection jetzt: {col.count()} docs")
    for id_ in to_add_ids:
        print(f"  + {id_}")
