# Per-Source-Retrieval Test — 2026-04-27_17-57

Test-Queries: 10

## Pro Query: Top-Chunks pro Source-Type + Budget-Resultat

### 1. Darf mein Arbeitgeber meine E-Mails lesen?

Embedding: 132ms · Retrieval: 360ms · Chunks total: 26

**gesetz_granular** (179ms, 6 chunks):

- `gran_DDG_§_6_Abs.1_S.4` | dist=0.220 | DDG § 6 Abs. 1 S. 4 DDG
  > (2) Werden kommerzielle Kommunikationen per elektronischer Post versandt, darf in der Kopf- und in der Betreffzeile wede
- `gran_BDSG_§_58_Abs.1_S.13` | dist=0.226 | BDSG § 58 Abs. 1 S. 13 BDSG
  > Der Empfänger hat die Daten zu berichtigen, zu löschen oder ihre Verarbeitung einzuschränken.
- `gran_BDSG_§_26_Abs.1_S.6` | dist=0.227 | BDSG § 26 Abs. 1 S. 6 BDSG
  > Der Arbeitgeber hat die beschäftigte Person über den Zweck der Datenverarbeitung und über ihr Widerrufsrecht nach Artike

**urteil_segmentiert** (32ms, 6 chunks):

- `seg_BAG_9._Senat_9_AZR_383_19_entscheidungsgruende_6` | dist=0.224 |  BAG 9. Senat 9 AZR 383/19
  > sächlich - verarbeitet werden sollen. Dies eröffnet ihm im Hinblick auf die Verwendung der Daten einen erheblichen Entsc
- `BGH_2._Zivilsenat_II_ZR_132_24_leitsatz` | dist=0.224 |  BGH 2. Zivilsenat II ZR 132/24
  > Leitsatz Ein Vereinsmitglied hat ein berechtigtes Interesse an der Mitteilung der E-Mail-Adressen der anderen Vereinsmit
- `seg_BGH_2._Zivilsenat_II_ZR_132_24_leitsatz` | dist=0.224 |  BGH 2. Zivilsenat II ZR 132/24
  > Leitsatz Ein Vereinsmitglied hat ein berechtigtes Interesse an der Mitteilung der E-Mail-Adressen der anderen Vereinsmit

**leitlinie** (49ms, 6 chunks):

- `beh_Januar_2016-_Orientierungshilfe_der_Date_22` | dist=0.144 |  Januar 2016- Orientierungshilfe der Datenschutzaufsichtsbehörden zur datenschutzgerechten Nutzung von E-Mail und anderen Internetdiensten am Arbeitsplatz
  > 2.  Der Arbeitgeber kann die Erlaubnis zur privaten Nutzung des betrieblichen E-Mail-Postfachs an  Bedingungen knüpfen: 
- `beh_Januar_2016-_Orientierungshilfe_der_Date_141` | dist=0.152 |  Januar 2016- Orientierungshilfe der Datenschutzaufsichtsbehörden zur datenschutzgerechten Nutzung von E-Mail und anderen Internetdiensten am Arbeitsplatz
  > Arbeitgebers auf mein E-Mail Postfach ermöglicht wird,
- `beh_Januar_2016-_Orientierungshilfe_der_Date_7` | dist=0.157 |  Januar 2016- Orientierungshilfe der Datenschutzaufsichtsbehörden zur datenschutzgerechten Nutzung von E-Mail und anderen Internetdiensten am Arbeitsplatz
  > Soweit der Arbeitgeber Hardware bzw. Software zur Verfügung stellt, dürfen die betrieblichen In- ternet- und E-Mail-Dien

**erwaegungsgrund** (44ms, 4 chunks):

- `dsgvo_eg_164` | dist=0.250 | DSGVO Berufsgeheimnisse und andere Geheimhaltungsvorschriften*
  > Erwägungsgrund 164 DSGVO – Berufsgeheimnisse und andere Geheimhaltungsvorschriften*  1 Hinsichtlich der Befugnisse der A
- `dsgvo_eg_155` | dist=0.252 | DSGVO Verarbeitung im Beschäftigungskontext*
  > Erwägungsgrund 155 DSGVO – Verarbeitung im Beschäftigungskontext*  Im Recht der Mitgliedstaaten oder in Kollektivvereinb
- `dsgvo_eg_154` | dist=0.257 | DSGVO Zugang der Öffentlichkeit zu amtlichen Dokumenten*
  > Erwägungsgrund 154 DSGVO – Zugang der Öffentlichkeit zu amtlichen Dokumenten*  1 Diese Verordnung ermöglicht es, dass be

**methodenwissen** (56ms, 4 chunks):

- `mw_beschaeftigtendatenschutz_email_it` | dist=0.137 |  Beschäftigtendatenschutz – E-Mail- und IT-Privatnutzung am Arbeitsplatz
  > Darf der Arbeitgeber E-Mails der Beschäftigten lesen? Die Antwort hängt davon ab, ob die Privatnutzung erlaubt ist oder 
- `mw_newsletter_einwilligung_dreistufig` | dist=0.253 |  Newsletter-Einwilligung: Dreistufige Prüfung (UWG / TDDDG / DSGVO)
  > Bei der rechtlichen Bewertung von Newsletter-Versand und E-Mail-Marketing müssen drei Regelungsebenen kumulativ geprüft 
- `mw_eugh_c_65_23_betriebsvereinbarungen_muessen_dsgvo_konform_se` | dist=0.255 |  EuGH C-65/23 – Betriebsvereinbarungen müssen DSGVO-konform sein
  > EuGH C-65/23 (K GmbH): Kernaussage: Betriebsvereinbarungen im Sinne von Art. 88 Abs. 1 DSGVO i.V.m. § 26 Abs. 4 BDSG müs

**Nach Typ-Budget (14 Chunks):**

- erwaegungsgrund: 2
- gesetz_granular: 4
- leitlinie: 3
- methodenwissen: 2
- urteil_segmentiert: 3

Top-8 nach Distance:
- `mw_beschaeftigtendatenschutz_email_it` [methodenwissen] | dist=0.137 |  Beschäftigtendatenschutz – E-Mail- und IT-Privatnutzung am Arbeitsplatz
- `beh_Januar_2016-_Orientierungshilfe_der_Date_22` [leitlinie] | dist=0.144 |  Januar 2016- Orientierungshilfe der Datenschutzaufsichtsbehörden zur datenschutzgerechten Nutzung von E-Mail und anderen Internetdiensten am Arbeitsplatz
- `beh_Januar_2016-_Orientierungshilfe_der_Date_141` [leitlinie] | dist=0.152 |  Januar 2016- Orientierungshilfe der Datenschutzaufsichtsbehörden zur datenschutzgerechten Nutzung von E-Mail und anderen Internetdiensten am Arbeitsplatz
- `beh_Januar_2016-_Orientierungshilfe_der_Date_7` [leitlinie] | dist=0.157 |  Januar 2016- Orientierungshilfe der Datenschutzaufsichtsbehörden zur datenschutzgerechten Nutzung von E-Mail und anderen Internetdiensten am Arbeitsplatz
- `gran_DDG_§_6_Abs.1_S.4` [gesetz_granular] | dist=0.220 | DDG § 6 Abs. 1 S. 4 DDG
- `seg_BAG_9._Senat_9_AZR_383_19_entscheidungsgruende_6` [urteil_segmentiert] | dist=0.224 |  BAG 9. Senat 9 AZR 383/19
- `BGH_2._Zivilsenat_II_ZR_132_24_leitsatz` [urteil_segmentiert] | dist=0.224 |  BGH 2. Zivilsenat II ZR 132/24
- `seg_BGH_2._Zivilsenat_II_ZR_132_24_leitsatz` [urteil_segmentiert] | dist=0.224 |  BGH 2. Zivilsenat II ZR 132/24

**Bewertung:**
- [ ] ✅ Pro Source sinnvolle Top-Chunks UND Budget liefert gute Mischung
- [ ] ⚠️ Pro Source OK, aber Budget verdrängt wichtige Chunks
- [ ] ❌ Pro Source zeigt schon falsche Chunks

---

### 2. Was ist eine Auftragsverarbeitung?

Embedding: 111ms · Retrieval: 216ms · Chunks total: 26

**gesetz_granular** (24ms, 6 chunks):

- `gran_BDSG_§_62_Abs.1_S.9` | dist=0.164 | BDSG § 62 Abs. 1 S. 9 BDSG
  > (5) Die Verarbeitung durch einen Auftragsverarbeiter hat auf der Grundlage eines Vertrags oder eines anderen Rechtsinstr
- `gran_BDSG_§_62_Abs.1_S.13` | dist=0.173 | BDSG § 62 Abs. 1 S. 13 BDSG
  > (7) Ein Auftragsverarbeiter, der die Zwecke und Mittel der Verarbeitung unter Verstoß gegen diese Vorschrift bestimmt, g
- `gran_BDSG_§_62_Abs.1_S.3` | dist=0.175 | BDSG § 62 Abs. 1 S. 3 BDSG
  > (2) Ein Verantwortlicher darf nur solche Auftragsverarbeiter mit der Verarbeitung personenbezogener Daten beauftragen, d

**urteil_segmentiert** (30ms, 6 chunks):

- `seg_eugh_C-60_22_rechtsrahmen_1` | dist=0.219 |  EuGH C-60/22
  > Dabei sollte er die Art, den Umfang, die Umstände und die Zwecke der Verarbeitung und das Risiko für die Rechte und Frei
- `BGH_6._Zivilsenat_VI_ZR_396_24_leitsatz` | dist=0.227 |  BGH 6. Zivilsenat VI ZR 396/24
  > Leitsatz 1. Der Verantwortliche hat auch im Zusammenhang mit der Beendigung einer Auftragsverarbeitung den Schutz der Re
- `seg_BGH_6._Zivilsenat_VI_ZR_396_24_leitsatz` | dist=0.231 |  BGH 6. Zivilsenat VI ZR 396/24
  > Leitsatz 1. Der Verantwortliche hat auch im Zusammenhang mit der Beendigung einer Auftragsverarbeitung den Schutz der Re

**leitlinie** (59ms, 6 chunks):

- `beh_13Auftragsverarbeitung,_Art._28_DS-GVOin_2` | dist=0.121 |  13Auftragsverarbeitung, Art. 28 DS-GVOin Überarbeitung
  > eine Stelle, die personenbezogene Daten im Auftrag  des Verantwortlichen verarbeitet. Der Begriff des
- `beh_13Auftragsverarbeitung,_Art._28_DS-GVOin_63` | dist=0.141 |  13Auftragsverarbeitung, Art. 28 DS-GVOin Überarbeitung
  > spruchnahme fremder Fachleistungen bei einem ei- genständig Verantwortlichen, für die bei der Verar- beitung (einschließ
- `beh_13Auftragsverarbeitung,_Art._28_DS-GVOin_28` | dist=0.146 |  13Auftragsverarbeitung, Art. 28 DS-GVOin Überarbeitung
  > ger von Daten müssen im Verzeichnis von Verarbei- tungstätigkeiten (vgl. Art. 30 Abs. 1 lit. d DS-GVO)  geführt werden.

**erwaegungsgrund** (45ms, 4 chunks):

- `dsgvo_eg_81` | dist=0.216 | DSGVO Heranziehung eines Auftragsverarbeiters*
  > Erwägungsgrund 81 DSGVO – Heranziehung eines Auftragsverarbeiters*  1 Damit die Anforderungen dieser Verordnung in Bezug
- `dsgvo_eg_95` | dist=0.224 | DSGVO Unterstützung durch den Auftragsverarbeiter*
  > Erwägungsgrund 95 DSGVO – Unterstützung durch den Auftragsverarbeiter*  Der Auftragsverarbeiter sollte erforderlichenfal
- `dsgvo_eg_82` | dist=0.239 | DSGVO Verzeichnis der Verarbeitungstätigkeiten*
  > Erwägungsgrund 82 DSGVO – Verzeichnis der Verarbeitungstätigkeiten*  1 Zum Nachweis der Einhaltung dieser Verordnung sol

**methodenwissen** (58ms, 4 chunks):

- `mw_auftragsverarbeitung_cloud` | dist=0.200 |  Auftragsverarbeitung vs. Funktionsübertragung – Abgrenzung und Prüfung
  > Auftragsverarbeitung (Art. 28 DSGVO) vs. Funktionsübertragung – Abgrenzung und Prüfung:  Abgrenzung (entscheidend für Re
- `mw_vorlageverfahren_art_267_aeuv_und_one_stop_shop_mechanismus` | dist=0.255 |  Vorlageverfahren Art. 267 AEUV und One-Stop-Shop-Mechanismus
  > Zentrale EU-Verfahrensinstrumente für die DSGVO-Durchsetzung: 1. Vorlageverfahren (Art. 267 AEUV): Nationale Gerichte kö
- `mw_art_5_abs_2_dsgvo_rechenschaftspflicht_accountability` | dist=0.257 |  Art. 5 Abs. 2 DSGVO – Rechenschaftspflicht (Accountability)
  > Art. 5 Abs. 2 DSGVO – Rechenschaftspflicht (Accountability): Der Verantwortliche ist für die Einhaltung der Grundsätze n

**Nach Typ-Budget (14 Chunks):**

- erwaegungsgrund: 2
- gesetz_granular: 4
- leitlinie: 3
- methodenwissen: 2
- urteil_segmentiert: 3

Top-8 nach Distance:
- `beh_13Auftragsverarbeitung,_Art._28_DS-GVOin_2` [leitlinie] | dist=0.121 |  13Auftragsverarbeitung, Art. 28 DS-GVOin Überarbeitung
- `beh_13Auftragsverarbeitung,_Art._28_DS-GVOin_63` [leitlinie] | dist=0.141 |  13Auftragsverarbeitung, Art. 28 DS-GVOin Überarbeitung
- `beh_13Auftragsverarbeitung,_Art._28_DS-GVOin_28` [leitlinie] | dist=0.146 |  13Auftragsverarbeitung, Art. 28 DS-GVOin Überarbeitung
- `gran_BDSG_§_62_Abs.1_S.9` [gesetz_granular] | dist=0.164 | BDSG § 62 Abs. 1 S. 9 BDSG
- `gran_BDSG_§_62_Abs.1_S.13` [gesetz_granular] | dist=0.173 | BDSG § 62 Abs. 1 S. 13 BDSG
- `gran_BDSG_§_62_Abs.1_S.3` [gesetz_granular] | dist=0.175 | BDSG § 62 Abs. 1 S. 3 BDSG
- `gran_BDSG_§_70_Abs.1_S.4` [gesetz_granular] | dist=0.185 | BDSG § 70 Abs. 1 S. 4 BDSG
- `mw_auftragsverarbeitung_cloud` [methodenwissen] | dist=0.200 |  Auftragsverarbeitung vs. Funktionsübertragung – Abgrenzung und Prüfung

**Bewertung:**
- [ ] ✅ Pro Source sinnvolle Top-Chunks UND Budget liefert gute Mischung
- [ ] ⚠️ Pro Source OK, aber Budget verdrängt wichtige Chunks
- [ ] ❌ Pro Source zeigt schon falsche Chunks

---

### 3. Sind Cookies ohne Einwilligung erlaubt?

Embedding: 79ms · Retrieval: 203ms · Chunks total: 26

**gesetz_granular** (28ms, 6 chunks):

- `gran_BDSG_§_51_Abs.1_S.7` | dist=0.222 | BDSG § 51 Abs. 1 S. 7 BDSG
  > Bei der Beurteilung, ob die Einwilligung freiwillig erteilt wurde, müssen die Umstände der Erteilung berücksichtigt werd
- `gran_BDSG_§_51_Abs.1_S.6` | dist=0.222 | BDSG § 51 Abs. 1 S. 6 BDSG
  > (4) Die Einwilligung ist nur wirksam, wenn sie auf der freien Entscheidung der betroffenen Person beruht.
- `gran_DDG_§_7_Abs.1_S.3` | dist=0.223 | DDG § 7 Abs. 1 S. 3 DDG
  > Diensteanbieter können jedoch auf freiwilliger Basis die Nutzer identifizieren, eine Passworteingabe verlangen oder ande

**urteil_segmentiert** (30ms, 6 chunks):

- `seg_eugh_C-673_17_vorlagefragen_3` | dist=0.182 |  EuGH C-673/17
  > Es kann nämlich nicht ausgeschlossen werden, dass der Nutzer die dem voreingestellten Ankreuzkästchen beigefügte Informa
- `seg_eugh_C-673_17_vorlagefragen_4` | dist=0.191 |  EuGH C-673/17
  > Die Verordnung 2016/679 sieht mithin nunmehr ausdrücklich eine aktive Einwilligung vor. Hierzu ist festzustellen, dass n
- `seg_eugh_C-673_17_vf_2_0` | dist=0.192 |  EuGH C-673/17
  > Mit seiner zweiten Frage möchte das vorlegende Gericht wissen, ob Art. 5 Abs. 3 der Richtlinie 2002/58 dahin auszulegen 

**leitlinie** (52ms, 6 chunks):

- `beh_05.02.2015-_Keine_Cookies_ohne_Einwillig_2` | dist=0.116 |  05.02.2015- Keine Cookies ohne Einwilligung der Internetnutzer
  > Nutzerverhaltens im Internet. Sie werden immer häufiger zur Bildung von anbieter- übergreifenden Nutzungsprofilen verwen
- `beh_05.02.2015-_Keine_Cookies_ohne_Einwillig_1` | dist=0.123 |  05.02.2015- Keine Cookies ohne Einwilligung der Internetnutzer
  > Keine Cookies ohne Einwilligung der Internetnutzer
- `beh_05.02.2015-_Keine_Cookies_ohne_Einwillig_6` | dist=0.129 |  05.02.2015- Keine Cookies ohne Einwilligung der Internetnutzer
  > ente Regelungen zum Schutz der Privatsphäre der Nutzer unabdingbar.

**erwaegungsgrund** (40ms, 4 chunks):

- `dsgvo_eg_43` | dist=0.231 | DSGVO Zwanglose Einwilligung*
  > Erwägungsgrund 43 DSGVO – Zwanglose Einwilligung*  1 Um sicherzustellen, dass die Einwilligung freiwillig erfolgt ist, s
- `dsgvo_eg_30` | dist=0.233 | DSGVO Online-Kennungen zur Profilerstellung und Identifizierung*
  > Erwägungsgrund 30 DSGVO – Online-Kennungen zur Profilerstellung und Identifizierung*  1 Natürlichen Personen werden unte
- `dsgvo_eg_32` | dist=0.247 | DSGVO Einwilligung*
  > Erwägungsgrund 32 DSGVO – Einwilligung*  1 Die Einwilligung sollte durch eine eindeutige bestätigende Handlung erfolgen,

**methodenwissen** (53ms, 4 chunks):

- `mw_pruefungsschema_cookies_tracking` | dist=0.159 |  Prüfungsschema Cookies und Online-Tracking
  > Prüfungsschema Cookies und Online-Tracking:  (1) Handelt es sich um einen Zugriff auf Informationen im Endgerät des Nutz
- `mw_verhaeltnis_dsgvo_zu_eprivacy_ttdsg_lex_specialis` | dist=0.218 |  Verhältnis DSGVO zu ePrivacy/TTDSG (lex specialis)
  > Das TTDSG (Telekommunikation-Telemedien-Datenschutz-Gesetz) setzt die ePrivacy-Richtlinie (2002/58/EG) um. Im Verhältnis
- `mw_verhaeltnis_dsgvo_ttdsg_uwg_werbung` | dist=0.222 |  Verhältnis DSGVO – TTDSG – § 7 UWG bei Werbung und Direktmarketing
  > Bei Direktmarketing und Werbung greifen drei Regelungsebenen ineinander, die jeweils eigenständig geprüft werden müssen:

**Nach Typ-Budget (14 Chunks):**

- erwaegungsgrund: 2
- gesetz_granular: 4
- leitlinie: 3
- methodenwissen: 2
- urteil_segmentiert: 3

Top-8 nach Distance:
- `beh_05.02.2015-_Keine_Cookies_ohne_Einwillig_2` [leitlinie] | dist=0.116 |  05.02.2015- Keine Cookies ohne Einwilligung der Internetnutzer
- `beh_05.02.2015-_Keine_Cookies_ohne_Einwillig_1` [leitlinie] | dist=0.123 |  05.02.2015- Keine Cookies ohne Einwilligung der Internetnutzer
- `beh_05.02.2015-_Keine_Cookies_ohne_Einwillig_6` [leitlinie] | dist=0.129 |  05.02.2015- Keine Cookies ohne Einwilligung der Internetnutzer
- `mw_pruefungsschema_cookies_tracking` [methodenwissen] | dist=0.159 |  Prüfungsschema Cookies und Online-Tracking
- `seg_eugh_C-673_17_vorlagefragen_3` [urteil_segmentiert] | dist=0.182 |  EuGH C-673/17
- `seg_eugh_C-673_17_vorlagefragen_4` [urteil_segmentiert] | dist=0.191 |  EuGH C-673/17
- `seg_eugh_C-673_17_vf_2_0` [urteil_segmentiert] | dist=0.192 |  EuGH C-673/17
- `mw_verhaeltnis_dsgvo_zu_eprivacy_ttdsg_lex_specialis` [methodenwissen] | dist=0.218 |  Verhältnis DSGVO zu ePrivacy/TTDSG (lex specialis)

**Bewertung:**
- [ ] ✅ Pro Source sinnvolle Top-Chunks UND Budget liefert gute Mischung
- [ ] ⚠️ Pro Source OK, aber Budget verdrängt wichtige Chunks
- [ ] ❌ Pro Source zeigt schon falsche Chunks

---

### 4. Kann ich Schadensersatz nach SCHUFA-Urteil verlangen?

Embedding: 127ms · Retrieval: 206ms · Chunks total: 26

**gesetz_granular** (32ms, 6 chunks):

- `gran_BDSG_§_83_Abs.1_S.3` | dist=0.189 | BDSG § 83 Abs. 1 S. 3 BDSG
  > (2) Wegen eines Schadens, der nicht Vermögensschaden ist, kann die betroffene Person eine angemessene Entschädigung in G
- `gran_DDG_§_26_Abs.1_S.4` | dist=0.225 | DDG § 26 Abs. 1 S. 4 DDG
  > (2) Der Betroffene kann jederzeit eine gerichtliche Entscheidung beantragen.
- `gran_BDSG_§_83_Abs.1_S.1` | dist=0.226 | BDSG § 83 Abs. 1 S. 1 BDSG
  > Hat ein Verantwortlicher einer betroffenen Person durch eine Verarbeitung personenbezogener Daten, die nach diesem Geset

**urteil_segmentiert** (28ms, 6 chunks):

- `seg_eugh_C-634_21_sachverhalt_0` | dist=0.195 |  EuGH C-634/21
  > Ausgangsverfahren und Vorlagefragen 14 Die SCHUFA ist eine private Gesellschaft deutschen Rechts, die ihre Vertragspartn
- `BGH_1._Zivilsenat_I_ZR_97_25_entscheidungsgruende_5` | dist=0.200 |  BGH 1. Zivilsenat I ZR 97/25
  > Rn. 94] - SCHUFA Holding [Restschuldbefreiung]). 20 b) Die Folgen für die Interessen und das Privatleben der betroffenen
- `seg_BGH_1._Zivilsenat_I_ZR_97_25_entscheidungsgruende_5` | dist=0.201 |  BGH 1. Zivilsenat I ZR 97/25
  > Rn. 94] - SCHUFA Holding [Restschuldbefreiung]). 20 b) Die Folgen für die Interessen und das Privatleben der betroffenen

**leitlinie** (54ms, 6 chunks):

- `beh_18.01.2023â_Stellungnahme_zu_Grundsatz_170` | dist=0.224 |  18.01.2023– Stellungnahme zu Grundsatzfragen zur Sanktionierung von Datenschutzverstößen von Unternehmen - EuGH-Rechtssache C-807/21
  > dieser gemäß Art. 82 Abs. 3 DSGVO nicht nachweist, dass er in keinerlei Hinsicht für  den Umstand, durch den der Schaden
- `beh_22.06.2022-_FAQ_zu_Facebook-Fanpages_37` | dist=0.230 |  22.06.2022- FAQ zu Facebook-Fanpages
  > die Verantwortlichen geltend zu machen.
- `beh_Januar_2016-_Orientierungshilfe_der_Date_87` | dist=0.234 |  Januar 2016- Orientierungshilfe der Datenschutzaufsichtsbehörden zur datenschutzgerechten Nutzung von E-Mail und anderen Internetdiensten am Arbeitsplatz
  > Verstoß zivilrechtliche Schadensersatzpflichten auslösen kann.

**erwaegungsgrund** (41ms, 4 chunks):

- `dsgvo_eg_146` | dist=0.239 | DSGVO Schadenersatz*
  > Erwägungsgrund 146 DSGVO – Schadenersatz*  1 Der Verantwortliche oder der Auftragsverarbeiter sollte Schäden, die einer 
- `dsgvo_eg_142` | dist=0.249 | DSGVO Vertretung von Betroffenen durch Einrichtungen, Organisationen und Verbände*
  > Erwägungsgrund 142 DSGVO – Vertretung von Betroffenen durch Einrichtungen, Organisationen und Verbände*  1 Betroffene Pe
- `dsgvo_eg_141` | dist=0.259 | DSGVO Recht auf Beschwerde*
  > Erwägungsgrund 141 DSGVO – Recht auf Beschwerde*  1 Jede betroffene Person sollte das Recht haben, bei einer einzigen Au

**methodenwissen** (51ms, 4 chunks):

- `mw_eugh_c_507_23_entschuldigung_als_schadensausgleich_t_354_22_` | dist=0.215 |  EuGH C-507/23 – Entschuldigung als Schadensausgleich; T-354/22 Bindl – 400 EUR für Drittlandtransfer
  > EuGH C-507/23 (Patērētāju tiesību aizsardzības centrs): Kernaussage: Eine aufrichtige Entschuldigung des Verantwortliche
- `mw_haftungssystem_dsgvo_national` | dist=0.216 |  Haftungssystem bei Datenschutzverstößen – DSGVO und nationales Recht
  > Haftungssystem bei Datenschutzverstößen – Zusammenspiel DSGVO und nationales Recht:  1. Art. 82 DSGVO (eigenständige Ans
- `mw_eugh_c_634_21_schufa_scoring_als_automatisierte_entscheidung` | dist=0.219 |  EuGH C-634/21 SCHUFA – Scoring als automatisierte Entscheidung
  > EuGH C-634/21 (SCHUFA Holding – Scoring): Kernaussage: Scoring (Bonitätsbewertung) durch die SCHUFA stellt eine 'automat

**Nach Typ-Budget (14 Chunks):**

- erwaegungsgrund: 2
- gesetz_granular: 4
- leitlinie: 3
- methodenwissen: 2
- urteil_segmentiert: 3

Top-8 nach Distance:
- `gran_BDSG_§_83_Abs.1_S.3` [gesetz_granular] | dist=0.189 | BDSG § 83 Abs. 1 S. 3 BDSG
- `seg_eugh_C-634_21_sachverhalt_0` [urteil_segmentiert] | dist=0.195 |  EuGH C-634/21
- `BGH_1._Zivilsenat_I_ZR_97_25_entscheidungsgruende_5` [urteil_segmentiert] | dist=0.200 |  BGH 1. Zivilsenat I ZR 97/25
- `seg_BGH_1._Zivilsenat_I_ZR_97_25_entscheidungsgruende_5` [urteil_segmentiert] | dist=0.201 |  BGH 1. Zivilsenat I ZR 97/25
- `mw_eugh_c_507_23_entschuldigung_als_schadensausgleich_t_354_22_` [methodenwissen] | dist=0.215 |  EuGH C-507/23 – Entschuldigung als Schadensausgleich; T-354/22 Bindl – 400 EUR für Drittlandtransfer
- `mw_haftungssystem_dsgvo_national` [methodenwissen] | dist=0.216 |  Haftungssystem bei Datenschutzverstößen – DSGVO und nationales Recht
- `beh_18.01.2023â_Stellungnahme_zu_Grundsatz_170` [leitlinie] | dist=0.224 |  18.01.2023– Stellungnahme zu Grundsatzfragen zur Sanktionierung von Datenschutzverstößen von Unternehmen - EuGH-Rechtssache C-807/21
- `gran_DDG_§_26_Abs.1_S.4` [gesetz_granular] | dist=0.225 | DDG § 26 Abs. 1 S. 4 DDG

**Bewertung:**
- [ ] ✅ Pro Source sinnvolle Top-Chunks UND Budget liefert gute Mischung
- [ ] ⚠️ Pro Source OK, aber Budget verdrängt wichtige Chunks
- [ ] ❌ Pro Source zeigt schon falsche Chunks

---

### 5. Welche Rechte habe ich nach DSGVO?

Embedding: 87ms · Retrieval: 152ms · Chunks total: 26

**gesetz_granular** (20ms, 6 chunks):

- `dsgvo_art_20` | dist=0.140 | DSGVO Art. 20 DSGVO
  > Art. 20 DSGVO – Recht auf Datenübertragbarkeit  Die betroffene Person hat das Recht, die sie betreffenden personenbezoge
- `dsgvo_art_16` | dist=0.143 | DSGVO Art. 16 DSGVO
  > Art. 16 DSGVO – Recht auf Berichtigung  1 Die betroffene Person hat das Recht, von dem Verantwortlichen unverzüglich die
- `dsgvo_art_17` | dist=0.146 | DSGVO Art. 17 DSGVO
  > Art. 17 DSGVO – Recht auf Löschung ("Recht auf Vergessenwerden")  Die betroffene Person hat das Recht, von dem Verantwor

**urteil_segmentiert** (27ms, 6 chunks):

- `seg_eugh_C-579_21_rechtsrahmen_3` | dist=0.149 |  EuGH C-579/21
  > Der Verantwortliche hat den Nachweis für den offenkundig unbegründeten oder exzessiven Charakter des Antrags zu erbringe
- `seg_eugh_C-129_21_rechtsrahmen_4` | dist=0.150 |  EuGH C-129/21
  > Der Widerruf der Einwilligung muss so einfach wie die Erteilung der Einwilligung sein. …“ 13 Art. 16 („Recht auf Bericht
- `seg_eugh_C-655_23_rechtsrahmen_3` | dist=0.153 |  EuGH C-655/23
  > n legt gemäß Artikel 21 Absatz 1 Widerspruch gegen die Verarbeitung ein und es liegen keine vorrangigen berechtigten Grü

**leitlinie** (43ms, 6 chunks):

- `beh_Juni_2020_-_LfDI_BW_-_Orientierungshilfe_18` | dist=0.146 |  Juni 2020 - LfDI BW - Orientierungshilfe Datenschutz im Verein nach der DSGVO
  > land und in allen anderen Mitgliedstaaten der Europäischen Union geltendes Recht.
- `beh_Juni_2020_-_LfDI_BW_-_Orientierungshilfe_28` | dist=0.150 |  Juni 2020 - LfDI BW - Orientierungshilfe Datenschutz im Verein nach der DSGVO
  > Art. 6 Abs. 1 DS-GVO. Damit eine Verarbeitung rechtmäßig ist, müssen personenbe- zogene Daten mit Einwilligung der betro
- `beh_Leitlinien_3_2019_zur_Verarbeitung_43` | dist=0.151 |  Leitlinien 3/2019 zur Verarbeitung
  > 6 RECHTE DER BETROFFENEN PERSON 91. Obwohl alle Betroffenenrechte der DSGVO auch im Rahmen der Verarbeitung personenbezo

**erwaegungsgrund** (14ms, 4 chunks):

- `dsgvo_eg_1` | dist=0.143 | DSGVO Datenschutz als Grundrecht*
  > Erwägungsgrund 1 DSGVO – Datenschutz als Grundrecht*  1 Der Schutz natürlicher Personen bei der Verarbeitung personenbez
- `dsgvo_eg_11` | dist=0.156 | DSGVO Gleiche Befugnisse und Sanktionen*
  > Erwägungsgrund 11 DSGVO – Gleiche Befugnisse und Sanktionen*  Ein unionsweiter wirksamer Schutz personenbezogener Daten 
- `dsgvo_eg_4` | dist=0.158 | DSGVO Einklang mit anderen Rechten*
  > Erwägungsgrund 4 DSGVO – Einklang mit anderen Rechten*  1 Die Verarbeitung personenbezogener Daten sollte im Dienste der

**methodenwissen** (49ms, 4 chunks):

- `mw_art_5_abs_1_lit_d_dsgvo_richtigkeit` | dist=0.149 |  Art. 5 Abs. 1 lit. d DSGVO – Richtigkeit
  > Art. 5 Abs. 1 lit. d DSGVO – Grundsatz der Richtigkeit: Personenbezogene Daten müssen sachlich richtig und erforderliche
- `mw_verbot_mit_erlaubnisvorbehalt` | dist=0.160 |  mw_verbot_mit_erlaubnisvorbehalt
  > Verbot mit Erlaubnisvorbehalt (Art. 6 Abs. 1 DSGVO): Die Verarbeitung personenbezogener Daten ist grundsätzlich verboten
- `mw_unmittelbare_geltung_dsgvo` | dist=0.167 |  mw_unmittelbare_geltung_dsgvo
  > Unmittelbare Geltung der DSGVO: Als EU-Verordnung (Art. 288 Abs. 2 AEUV) gilt die DSGVO unmittelbar in allen Mitgliedsta

**Nach Typ-Budget (14 Chunks):**

- erwaegungsgrund: 2
- gesetz_granular: 4
- leitlinie: 3
- methodenwissen: 2
- urteil_segmentiert: 3

Top-8 nach Distance:
- `dsgvo_art_20` [gesetz_granular] | dist=0.140 | DSGVO Art. 20 DSGVO
- `dsgvo_art_16` [gesetz_granular] | dist=0.143 | DSGVO Art. 16 DSGVO
- `dsgvo_eg_1` [erwaegungsgrund] | dist=0.143 | DSGVO Datenschutz als Grundrecht*
- `beh_Juni_2020_-_LfDI_BW_-_Orientierungshilfe_18` [leitlinie] | dist=0.146 |  Juni 2020 - LfDI BW - Orientierungshilfe Datenschutz im Verein nach der DSGVO
- `dsgvo_art_17` [gesetz_granular] | dist=0.146 | DSGVO Art. 17 DSGVO
- `seg_eugh_C-579_21_rechtsrahmen_3` [urteil_segmentiert] | dist=0.149 |  EuGH C-579/21
- `mw_art_5_abs_1_lit_d_dsgvo_richtigkeit` [methodenwissen] | dist=0.149 |  Art. 5 Abs. 1 lit. d DSGVO – Richtigkeit
- `dsgvo_art_15` [gesetz_granular] | dist=0.150 | DSGVO Art. 15 DSGVO

**Bewertung:**
- [ ] ✅ Pro Source sinnvolle Top-Chunks UND Budget liefert gute Mischung
- [ ] ⚠️ Pro Source OK, aber Budget verdrängt wichtige Chunks
- [ ] ❌ Pro Source zeigt schon falsche Chunks

---

### 6. Wann ist eine DSFA verpflichtend?

Embedding: 109ms · Retrieval: 183ms · Chunks total: 26

**gesetz_granular** (27ms, 6 chunks):

- `dsgvo_art_54` | dist=0.224 | DSGVO Art. 54 DSGVO
  > Art. 54 DSGVO – Errichtung der Aufsichtsbehörde  Jeder Mitgliedstaat sieht durch Rechtsvorschriften Folgendes vor: die E
- `gran_BDSG_§_38_Abs.1_S.3` | dist=0.227 | BDSG § 38 Abs. 1 S. 3 BDSG
  > (2) § 6 Absatz 4, 5 Satz 2 und Absatz 6 finden Anwendung, § 6 Absatz 4 jedoch nur, wenn die Benennung einer oder eines D
- `gran_DDG_§_12_Abs.1_S.3` | dist=0.230 | DDG § 12 Abs. 1 S. 3 DDG
  > Dezember 2021 betreffen.

**urteil_segmentiert** (36ms, 6 chunks):

- `BFH_9._Senat_IX_R_6_23_leitsatz` | dist=0.222 |  BFH 9. Senat IX R 6/23
  > Leitsatz 1. Die Anforderung unter anderem von Mietverträgen durch das Finanzamt (FA) beim Vermieter (Steuerpflichtigen) 
- `seg_BFH_9._Senat_IX_R_6_23_leitsatz` | dist=0.223 |  BFH 9. Senat IX R 6/23
  > Leitsatz 1. Die Anforderung unter anderem von Mietverträgen durch das Finanzamt (FA) beim Vermieter (Steuerpflichtigen) 
- `seg_eugh_C-654_23_rechtsrahmen_4` | dist=0.233 |  EuGH C-654/23
  > Teile der Erklärung sind dann nicht verbindlich, wenn sie einen Verstoß gegen diese Verordnung darstellen. … (4)   Bei d

**leitlinie** (43ms, 6 chunks):

- `beh_5Datenschutz-FolgenabschÃ¤tzung_nach_Art_23` | dist=0.145 |  5Datenschutz-Folgenabschätzung nach Art. 35 DS-GVO
  > den Verarbeitungsvorgänge durchzuführen. Auch  bereits bestehende Verarbeitungsvorgänge können  unter die Pflicht einer 
- `beh_5Datenschutz-FolgenabschÃ¤tzung_nach_Art_17` | dist=0.158 |  5Datenschutz-Folgenabschätzung nach Art. 35 DS-GVO
  > einer Abschätzung der Risiken der Verarbeitungs- vorgänge („Schwellwertanalyse“). Ergibt diese ein  voraussichtlich hohe
- `beh_5Datenschutz-FolgenabschÃ¤tzung_nach_Art_6` | dist=0.159 |  5Datenschutz-Folgenabschätzung nach Art. 35 DS-GVO
  > Daten. Die DSFA ist durchzuführen, wenn die Form  der Verarbeitung, insbesondere bei der Verwen- dung neuer Technologien

**erwaegungsgrund** (28ms, 4 chunks):

- `dsgvo_eg_138` | dist=0.232 | DSGVO Dringlichkeitsverfahren*
  > Erwägungsgrund 138 DSGVO – Dringlichkeitsverfahren*  1 Die Anwendung dieses Verfahrens sollte in den Fällen, in denen si
- `dsgvo_eg_169` | dist=0.236 | DSGVO Sofort geltende Durchführungsrechtsakte*
  > Erwägungsgrund 169 DSGVO – Sofort geltende Durchführungsrechtsakte*  Die Kommission sollte sofort geltende Durchführungs
- `dsgvo_eg_44` | dist=0.239 | DSGVO Vertragserfüllung oder -abschluss*
  > Erwägungsgrund 44 DSGVO – Vertragserfüllung oder -abschluss*  Die Verarbeitung von Daten sollte als rechtmäßig gelten, w

**methodenwissen** (49ms, 4 chunks):

- `mw_wp_248_2_aus_9_regel_fuer_dsfa_pflicht` | dist=0.156 |  WP 248 – 2-aus-9-Regel für DSFA-Pflicht
  > Art.-29-Datenschutzgruppe WP 248 (jetzt EDPB) – 9 Kriterien für die DSFA-Pflicht: Eine DSFA ist in der Regel erforderlic
- `mw_pruefungsschema_datenschutz_folgenabschaetzung_dsfa_art_35_d` | dist=0.157 |  Prüfungsschema Datenschutz-Folgenabschätzung (DSFA, Art. 35 DSGVO)
  > Art. 35 DSGVO – Datenschutz-Folgenabschätzung (DSFA): Wann erforderlich: Wenn eine Verarbeitung voraussichtlich ein hohe
- `mw_dsk_blacklist_17_dsfa_pflichtige_verarbeitungen` | dist=0.188 |  DSK-Blacklist – 17 DSFA-pflichtige Verarbeitungen
  > Die DSK (Datenschutzkonferenz) hat gemäß Art. 35 Abs. 4 DSGVO eine Liste von 17 Verarbeitungstätigkeiten erstellt, die s

**Nach Typ-Budget (14 Chunks):**

- erwaegungsgrund: 2
- gesetz_granular: 4
- leitlinie: 3
- methodenwissen: 2
- urteil_segmentiert: 3

Top-8 nach Distance:
- `beh_5Datenschutz-FolgenabschÃ¤tzung_nach_Art_23` [leitlinie] | dist=0.145 |  5Datenschutz-Folgenabschätzung nach Art. 35 DS-GVO
- `mw_wp_248_2_aus_9_regel_fuer_dsfa_pflicht` [methodenwissen] | dist=0.156 |  WP 248 – 2-aus-9-Regel für DSFA-Pflicht
- `mw_pruefungsschema_datenschutz_folgenabschaetzung_dsfa_art_35_d` [methodenwissen] | dist=0.157 |  Prüfungsschema Datenschutz-Folgenabschätzung (DSFA, Art. 35 DSGVO)
- `beh_5Datenschutz-FolgenabschÃ¤tzung_nach_Art_17` [leitlinie] | dist=0.158 |  5Datenschutz-Folgenabschätzung nach Art. 35 DS-GVO
- `beh_5Datenschutz-FolgenabschÃ¤tzung_nach_Art_6` [leitlinie] | dist=0.159 |  5Datenschutz-Folgenabschätzung nach Art. 35 DS-GVO
- `BFH_9._Senat_IX_R_6_23_leitsatz` [urteil_segmentiert] | dist=0.222 |  BFH 9. Senat IX R 6/23
- `seg_BFH_9._Senat_IX_R_6_23_leitsatz` [urteil_segmentiert] | dist=0.223 |  BFH 9. Senat IX R 6/23
- `dsgvo_art_54` [gesetz_granular] | dist=0.224 | DSGVO Art. 54 DSGVO

**Bewertung:**
- [ ] ✅ Pro Source sinnvolle Top-Chunks UND Budget liefert gute Mischung
- [ ] ⚠️ Pro Source OK, aber Budget verdrängt wichtige Chunks
- [ ] ❌ Pro Source zeigt schon falsche Chunks

---

### 7. Datenschutz im Verein

Embedding: 68ms · Retrieval: 179ms · Chunks total: 26

**gesetz_granular** (20ms, 6 chunks):

- `dsgvo_art_91` | dist=0.209 | DSGVO Art. 91 DSGVO
  > Art. 91 DSGVO – Bestehende Datenschutzvorschriften von Kirchen und religiösen Vereinigungen oder Gemeinschaften  Wendet 
- `dsgvo_art_76` | dist=0.213 | DSGVO Art. 76 DSGVO
  > Art. 76 DSGVO – Vertraulichkeit  Die Beratungen des Ausschusses sind gemäß seiner Geschäftsordnung vertraulich, wenn der
- `gran_BDSG_§_26_Abs.1_S.9` | dist=0.223 | BDSG § 26 Abs. 1 S. 9 BDSG
  > (4) Die Verarbeitung personenbezogener Daten, einschließlich besonderer Kategorien personenbezogener Daten von Beschäfti

**urteil_segmentiert** (29ms, 6 chunks):

- `seg_BGH_2._Zivilsenat_II_ZR_132_24_leitsatz` | dist=0.190 |  BGH 2. Zivilsenat II ZR 132/24
  > Leitsatz Ein Vereinsmitglied hat ein berechtigtes Interesse an der Mitteilung der E-Mail-Adressen der anderen Vereinsmit
- `BGH_2._Zivilsenat_II_ZR_132_24_leitsatz` | dist=0.191 |  BGH 2. Zivilsenat II ZR 132/24
  > Leitsatz Ein Vereinsmitglied hat ein berechtigtes Interesse an der Mitteilung der E-Mail-Adressen der anderen Vereinsmit
- `BGH_2._Zivilsenat_II_ZR_132_24_entscheidungsgruende_5` | dist=0.196 |  BGH 2. Zivilsenat II ZR 132/24
  > abs. lit. b DSGVO zulässig. 26 Ein milderes Mittel gleicher Eignung bestand entgegen der Auffassung der Revision auch ni

**leitlinie** (51ms, 6 chunks):

- `beh_Juni_2020_-_LfDI_BW_-_Orientierungshilfe_58` | dist=0.118 |  Juni 2020 - LfDI BW - Orientierungshilfe Datenschutz im Verein nach der DSGVO
  > Aus dem vertraglichen Vertrauensverhältnis zwischen den Vereinsmitgliedern und  dem Verein folgt jedoch, dass der Verein
- `beh_Juni_2020_-_LfDI_BW_-_Orientierungshilfe_117` | dist=0.125 |  Juni 2020 - LfDI BW - Orientierungshilfe Datenschutz im Verein nach der DSGVO
  > denwerbung, um einen ausreichenden Mitgliederbestand und genügend finanzielle  Mittel sicherzustellen. Die Daten seiner 
- `beh_Juni_2020_-_LfDI_BW_-_Orientierungshilfe_151` | dist=0.125 |  Juni 2020 - LfDI BW - Orientierungshilfe Datenschutz im Verein nach der DSGVO
  > Überzeugungen, Gewerkschaftszugehörigkeit, Gesundheitsdaten etc.). Oft ergibt  sich das Geheimhaltungsinteresse der Mitg

**erwaegungsgrund** (29ms, 4 chunks):

- `dsgvo_eg_165` | dist=0.220 | DSGVO Keine Beeinträchtigung des Status der Kirchen und religiösen Vereinigungen*
  > Erwägungsgrund 165 DSGVO – Keine Beeinträchtigung des Status der Kirchen und religiösen Vereinigungen*  Im Einklang mit 
- `dsgvo_eg_55` | dist=0.230 | DSGVO Öffentliches Interesse bei Verarbeitung durch staatliche Stellen für Ziele anerkannter Religionsgemeinschaften*
  > Erwägungsgrund 55 DSGVO – Öffentliches Interesse bei Verarbeitung durch staatliche Stellen für Ziele anerkannter Religio
- `dsgvo_eg_48` | dist=0.232 | DSGVO Überwiegende berechtigte Interessen in der Unternehmensgruppe*
  > Erwägungsgrund 48 DSGVO – Überwiegende berechtigte Interessen in der Unternehmensgruppe*  1 Verantwortliche, die Teil ei

**methodenwissen** (50ms, 4 chunks):

- `mw_art_5_abs_1_lit_f_dsgvo_integritaet_und_vertraulichkeit` | dist=0.231 |  Art. 5 Abs. 1 lit. f DSGVO – Integrität und Vertraulichkeit
  > Art. 5 Abs. 1 lit. f DSGVO – Grundsatz der Integrität und Vertraulichkeit: Personenbezogene Daten müssen durch geeignete
- `mw_bcr_verbindliche_interne_vorschriften` | dist=0.232 |  mw_bcr_verbindliche_interne_vorschriften
  > Verbindliche interne Datenschutzvorschriften (BCR) nach Art. 47 DSGVO: Konzerninterne Regelungen für den internationalen
- `mw_verbot_mit_erlaubnisvorbehalt` | dist=0.235 |  mw_verbot_mit_erlaubnisvorbehalt
  > Verbot mit Erlaubnisvorbehalt (Art. 6 Abs. 1 DSGVO): Die Verarbeitung personenbezogener Daten ist grundsätzlich verboten

**Nach Typ-Budget (14 Chunks):**

- erwaegungsgrund: 2
- gesetz_granular: 4
- leitlinie: 3
- methodenwissen: 2
- urteil_segmentiert: 3

Top-8 nach Distance:
- `beh_Juni_2020_-_LfDI_BW_-_Orientierungshilfe_58` [leitlinie] | dist=0.118 |  Juni 2020 - LfDI BW - Orientierungshilfe Datenschutz im Verein nach der DSGVO
- `beh_Juni_2020_-_LfDI_BW_-_Orientierungshilfe_117` [leitlinie] | dist=0.125 |  Juni 2020 - LfDI BW - Orientierungshilfe Datenschutz im Verein nach der DSGVO
- `beh_Juni_2020_-_LfDI_BW_-_Orientierungshilfe_151` [leitlinie] | dist=0.125 |  Juni 2020 - LfDI BW - Orientierungshilfe Datenschutz im Verein nach der DSGVO
- `seg_BGH_2._Zivilsenat_II_ZR_132_24_leitsatz` [urteil_segmentiert] | dist=0.190 |  BGH 2. Zivilsenat II ZR 132/24
- `BGH_2._Zivilsenat_II_ZR_132_24_leitsatz` [urteil_segmentiert] | dist=0.191 |  BGH 2. Zivilsenat II ZR 132/24
- `BGH_2._Zivilsenat_II_ZR_132_24_entscheidungsgruende_5` [urteil_segmentiert] | dist=0.196 |  BGH 2. Zivilsenat II ZR 132/24
- `dsgvo_art_91` [gesetz_granular] | dist=0.209 | DSGVO Art. 91 DSGVO
- `dsgvo_art_76` [gesetz_granular] | dist=0.213 | DSGVO Art. 76 DSGVO

**Bewertung:**
- [ ] ✅ Pro Source sinnvolle Top-Chunks UND Budget liefert gute Mischung
- [ ] ⚠️ Pro Source OK, aber Budget verdrängt wichtige Chunks
- [ ] ❌ Pro Source zeigt schon falsche Chunks

---

### 8. Wie lange darf eine Bewerbung gespeichert werden?

Embedding: 97ms · Retrieval: 187ms · Chunks total: 26

**gesetz_granular** (25ms, 6 chunks):

- `gran_BDSG_§_17_Abs.1_S.3` | dist=0.224 | BDSG § 17 Abs. 1 S. 3 BDSG
  > Die Wahl erfolgt für fünf Jahre.
- `gran_BDSG_§_27_Abs.1_S.6` | dist=0.225 | BDSG § 27 Abs. 1 S. 6 BDSG
  > Bis dahin sind die Merkmale gesondert zu speichern, mit denen Einzelangaben über persönliche oder sachliche Verhältnisse
- `gran_BDSG_§_69_Abs.1_S.9` | dist=0.226 | BDSG § 69 Abs. 1 S. 9 BDSG
  > Die oder der Bundesbeauftragte kann diese Frist um einen Monat verlängern, wenn die geplante Verarbeitung besonders komp

**urteil_segmentiert** (28ms, 6 chunks):

- `seg_eugh_C-61_22_wuerdigung_30` | dist=0.217 |  EuGH C-61/22
  > Insoweit stellt der 21. Erwägungsgrund der Verordnung ausdrücklich klar, dass diese „keine Rechtsgrundlage für die Einri
- `seg_eugh_c_307_22_rechtsrahmen_4` | dist=0.223 |  EuGH C-307/22
  > Der Verantwortliche verarbeitet die personenbezogenen Daten nicht mehr, es sei denn, er kann zwingende schutzwürdige Grü
- `seg_eugh_c_461_10_rechtsrahmen_9` | dist=0.224 |  EuGH C-461/10
  > b)                                                                       zur Identifizierung des Adressaten einer Nachri

**leitlinie** (47ms, 6 chunks):

- `beh_20.12.2021-_HÃ¤ufige_Fragestellungen_neb_49` | dist=0.156 |  20.12.2021- Häufige Fragestellungen nebst Antworten zur Verarbeitung von Beschäftigtendaten im Zusammenhang mit der Corona-Pandemie
  > legt sind, dürfen Eintragungen regelmäßig nicht länger als zwei Wochen  nach dem Kontakt gespeichert und sollten nach ei
- `beh_Leitlinien_01_2020_zur_Verarbeitung_pers_85` | dist=0.183 |  Leitlinien 01/2020 zur Verarbeitung personenbezogener
  > 3.1.2.3 Speicherfrist 126. Daten sollten nur so lange gespeichert werden, wie zur Erfüllung des Parkvertrags oder anderw
- `beh_Stand_Februar_2018_-_Hinweise_zum_Verzei_11` | dist=0.190 |  Stand Februar 2018 - Hinweise zum Verzeichnis von Verarbeitungstätigkeiten, Art. 30 DS-GVO
  > Um Änderungen der Eintragungen im Verzeichnis nachvollziehen zu können (z. B. wer war wann  Verantwortlicher, Datenschut

**erwaegungsgrund** (36ms, 4 chunks):

- `dsgvo_eg_158` | dist=0.248 | DSGVO Verarbeitung zu Archivzwecken*
  > Erwägungsgrund 158 DSGVO – Verarbeitung zu Archivzwecken*  1 Diese Verordnung sollte auch für die Verarbeitung personenb
- `dsgvo_eg_155` | dist=0.251 | DSGVO Verarbeitung im Beschäftigungskontext*
  > Erwägungsgrund 155 DSGVO – Verarbeitung im Beschäftigungskontext*  Im Recht der Mitgliedstaaten oder in Kollektivvereinb
- `dsgvo_eg_171` | dist=0.253 | DSGVO Aufhebung der RL 95/46/EG und Übergangsbestimmungen*
  > Erwägungsgrund 171 DSGVO – Aufhebung der RL 95/46/EG und Übergangsbestimmungen*  1 Die Richtlinie 95/46/EG sollte durch 

**methodenwissen** (51ms, 4 chunks):

- `mw_art_5_abs_1_lit_e_dsgvo_speicherbegrenzung` | dist=0.218 |  Art. 5 Abs. 1 lit. e DSGVO – Speicherbegrenzung
  > Art. 5 Abs. 1 lit. e DSGVO – Grundsatz der Speicherbegrenzung: Personenbezogene Daten dürfen nur so lange in identifizie
- `mw_recht_auf_vergessenwerden_pruefungsschema` | dist=0.250 |  Recht auf Vergessenwerden – Prüfungsschema
  > Das Recht auf Löschung (Art. 17 DSGVO), auch bekannt als Recht auf Vergessenwerden, wurde grundlegend durch das EuGH-Urt
- `mw_verbot_mit_erlaubnisvorbehalt` | dist=0.256 |  mw_verbot_mit_erlaubnisvorbehalt
  > Verbot mit Erlaubnisvorbehalt (Art. 6 Abs. 1 DSGVO): Die Verarbeitung personenbezogener Daten ist grundsätzlich verboten

**Nach Typ-Budget (14 Chunks):**

- erwaegungsgrund: 2
- gesetz_granular: 4
- leitlinie: 3
- methodenwissen: 2
- urteil_segmentiert: 3

Top-8 nach Distance:
- `beh_20.12.2021-_HÃ¤ufige_Fragestellungen_neb_49` [leitlinie] | dist=0.156 |  20.12.2021- Häufige Fragestellungen nebst Antworten zur Verarbeitung von Beschäftigtendaten im Zusammenhang mit der Corona-Pandemie
- `beh_Leitlinien_01_2020_zur_Verarbeitung_pers_85` [leitlinie] | dist=0.183 |  Leitlinien 01/2020 zur Verarbeitung personenbezogener
- `beh_Stand_Februar_2018_-_Hinweise_zum_Verzei_11` [leitlinie] | dist=0.190 |  Stand Februar 2018 - Hinweise zum Verzeichnis von Verarbeitungstätigkeiten, Art. 30 DS-GVO
- `seg_eugh_C-61_22_wuerdigung_30` [urteil_segmentiert] | dist=0.217 |  EuGH C-61/22
- `mw_art_5_abs_1_lit_e_dsgvo_speicherbegrenzung` [methodenwissen] | dist=0.218 |  Art. 5 Abs. 1 lit. e DSGVO – Speicherbegrenzung
- `seg_eugh_c_307_22_rechtsrahmen_4` [urteil_segmentiert] | dist=0.223 |  EuGH C-307/22
- `seg_eugh_c_461_10_rechtsrahmen_9` [urteil_segmentiert] | dist=0.224 |  EuGH C-461/10
- `gran_BDSG_§_17_Abs.1_S.3` [gesetz_granular] | dist=0.224 | BDSG § 17 Abs. 1 S. 3 BDSG

**Bewertung:**
- [ ] ✅ Pro Source sinnvolle Top-Chunks UND Budget liefert gute Mischung
- [ ] ⚠️ Pro Source OK, aber Budget verdrängt wichtige Chunks
- [ ] ❌ Pro Source zeigt schon falsche Chunks

---

### 9. Was hat der EuGH zu Schrems II entschieden?

Embedding: 121ms · Retrieval: 191ms · Chunks total: 26

**gesetz_granular** (31ms, 6 chunks):

- `gran_BDSG_§_21_Abs.1_S.8` | dist=0.250 | BDSG § 21 Abs. 1 S. 8 BDSG
  > (5) Ist ein Verfahren zur Überprüfung der Gültigkeit eines Beschlusses der Europäischen Kommission nach Absatz 1 bei dem
- `gran_BDSG_§_21_Abs.1_S.1` | dist=0.254 | BDSG § 21 Abs. 1 S. 1 BDSG
  > Hält eine Aufsichtsbehörde einen Angemessenheitsbeschluss der Europäischen Kommission, einen Beschluss über die Anerkenn
- `gran_BDSG_§_21_Abs.1_S.10` | dist=0.256 | BDSG § 21 Abs. 1 S. 10 BDSG
  > Kommt das Bundesverwaltungsgericht zu der Überzeugung, dass der Beschluss der Europäischen Kommission nach Absatz 1 gült

**urteil_segmentiert** (24ms, 6 chunks):

- `seg_eugh_T-553_23_header_17` | dist=0.189 |  EuG T-553/23
  > rde einzuholen. 93 Die Kommission, unterstützt durch Irland und die Vereinigten Staaten von Amerika, tritt der Argumenta
- `seg_eugh_T-553_23_header_20` | dist=0.190 |  EuG T-553/23
  > die vorherige Genehmigung einer Justiz- oder Verwaltungsbehörde einzuholen. 95 Festzustellen ist, ob dieses Fehlen einer
- `seg_eugh_T-553_23_header_8` | dist=0.195 |  EuG T-553/23
  > Die besagte Vorschrift ist in Kapitel V der Verordnung enthalten, das, worauf der Gerichtshof hingewiesen hat, den Fortb

**leitlinie** (50ms, 6 chunks):

- `beh_Ãbermittlung_personenbezogener_Daten_au_32` | dist=0.177 |  Übermittlung personenbezogener Daten aus Europa an die USA
  > 16  EuGH, Urt. v. 16. Juli 2020, Rs. C‐311/18 (sog. Schrems II).
- `beh_Ãbermittlung_personenbezogener_Daten_au_31` | dist=0.180 |  Übermittlung personenbezogener Daten aus Europa an die USA
  > 14  EuGH, Urt. v. 6. Oktober 2015, Rs. C‐362/14 (sog. Schrems I).  15  Durchführungsbeschluss (EU) 2016/1250 der Kommiss
- `beh_Ãbermittlung_personenbezogener_Daten_au_70` | dist=0.185 |  Übermittlung personenbezogener Daten aus Europa an die USA
  > 38  EuGH, Urt. v. 16. Juli 2020, Rs. C‐311/18 (sog. Schrems II).  39  S. Annex I., Section III.6.d und e des Angemessenh

**erwaegungsgrund** (35ms, 4 chunks):

- `dsgvo_eg_143` | dist=0.272 | DSGVO Gerichtliche Rechtsbehelfe*
  > Erwägungsgrund 143 DSGVO – Gerichtliche Rechtsbehelfe*  1 Jede natürliche oder juristische Person hat das Recht, unter d
- `dsgvo_eg_149` | dist=0.273 | DSGVO Sanktionen für Verstöße gegen nationale Vorschriften*
  > Erwägungsgrund 149 DSGVO – Sanktionen für Verstöße gegen nationale Vorschriften*  1 Die Mitgliedstaaten sollten die stra
- `dsgvo_eg_152` | dist=0.275 | DSGVO Sanktionsbefugnis der Mitgliedsstaaten*
  > Erwägungsgrund 152 DSGVO – Sanktionsbefugnis der Mitgliedsstaaten*  1 Soweit diese Verordnung verwaltungsrechtliche Sank

**methodenwissen** (51ms, 4 chunks):

- `mw_eugh_c_446_21_schrems_meta_datenminimierung_begrenzt_werbenu` | dist=0.214 |  EuGH C-446/21 Schrems/Meta – Datenminimierung begrenzt Werbenutzung
  > EuGH C-446/21 (Schrems v Meta Platforms Ireland): Kernaussage: Der Grundsatz der Datenminimierung (Art. 5 Abs. 1 lit. c 
- `mw_eugh_c_687_21_mediamarktsaturn_ausgleichsfunktion_des_schade` | dist=0.237 |  EuGH C-687/21 MediaMarktSaturn – Ausgleichsfunktion des Schadensersatzes
  > EuGH C-687/21 (MediaMarktSaturn/Saturn Electro, Urteil): Kernaussage: Der Schadensersatzanspruch nach Art. 82 DSGVO hat 
- `mw_anwendungsvorrang_des_eu_rechts_costa_enel_simmenthal` | dist=0.244 |  Anwendungsvorrang des EU-Rechts (Costa/ENEL, Simmenthal)
  > Der Anwendungsvorrang des EU-Rechts ist ein fundamentales Prinzip: Steht nationales Recht im Widerspruch zu EU-Recht, mu

**Nach Typ-Budget (14 Chunks):**

- erwaegungsgrund: 2
- gesetz_granular: 4
- leitlinie: 3
- methodenwissen: 2
- urteil_segmentiert: 3

Top-8 nach Distance:
- `beh_Ãbermittlung_personenbezogener_Daten_au_32` [leitlinie] | dist=0.177 |  Übermittlung personenbezogener Daten aus Europa an die USA
- `beh_Ãbermittlung_personenbezogener_Daten_au_31` [leitlinie] | dist=0.180 |  Übermittlung personenbezogener Daten aus Europa an die USA
- `beh_Ãbermittlung_personenbezogener_Daten_au_70` [leitlinie] | dist=0.185 |  Übermittlung personenbezogener Daten aus Europa an die USA
- `seg_eugh_T-553_23_header_17` [urteil_segmentiert] | dist=0.189 |  EuG T-553/23
- `seg_eugh_T-553_23_header_20` [urteil_segmentiert] | dist=0.190 |  EuG T-553/23
- `seg_eugh_T-553_23_header_8` [urteil_segmentiert] | dist=0.195 |  EuG T-553/23
- `mw_eugh_c_446_21_schrems_meta_datenminimierung_begrenzt_werbenu` [methodenwissen] | dist=0.214 |  EuGH C-446/21 Schrems/Meta – Datenminimierung begrenzt Werbenutzung
- `mw_eugh_c_687_21_mediamarktsaturn_ausgleichsfunktion_des_schade` [methodenwissen] | dist=0.237 |  EuGH C-687/21 MediaMarktSaturn – Ausgleichsfunktion des Schadensersatzes

**Bewertung:**
- [ ] ✅ Pro Source sinnvolle Top-Chunks UND Budget liefert gute Mischung
- [ ] ⚠️ Pro Source OK, aber Budget verdrängt wichtige Chunks
- [ ] ❌ Pro Source zeigt schon falsche Chunks

---

### 10. Welche rechtlichen Anforderungen gelten für biometrische Daten?

Embedding: 111ms · Retrieval: 211ms · Chunks total: 26

**gesetz_granular** (24ms, 6 chunks):

- `dsgvo_art4_daten_identitaet` | dist=0.179 | DSGVO Art. 4 DSGVO (Daten und Identität)
  > Art. 4 DSGVO – Begriffsbestimmungen: Daten und Identität  Nr. 1 „personenbezogene Daten": alle Informationen, die sich a
- `gran_BDSG_§_47_Abs.1` | dist=0.192 | BDSG § 47 Abs. 1 BDSG
  > Personenbezogene Daten müssen  1. auf rechtmäßige Weise und nach Treu und Glauben verarbeitet werden, 2. für festgelegte
- `dsgvo_art_9_part0` | dist=0.197 | DSGVO Art. 9 DSGVO (Teil 1)
  > Art. 9 DSGVO – Verarbeitung besonderer Kategorien personenbezogener Daten  Die Verarbeitung personenbezogener Daten, aus

**urteil_segmentiert** (30ms, 6 chunks):

- `seg_eugh_C-252_21_rechtsrahmen_5` | dist=0.154 |  EuGH C-252/21
  > ng vorvertraglicher Maßnahmen erforderlich, die auf Anfrage der betroffenen Person erfolgen; c) die Verarbeitung ist zur
- `seg_eugh_C-205_21_vf_3_14` | dist=0.155 |  EuGH C-205/21
  > Jedoch kann der bloße Umstand, dass eine Person einer vorsätzlichen Offizialstraftat beschuldigt wird, nicht als ein Fak
- `seg_eugh_C-61_22_wuerdigung_7` | dist=0.155 |  EuGH C-61/22
  > Um die Übereinstimmung der biometrischen Identifikatoren mit der Identität des Antragstellers zu gewährleisten, muss der

**leitlinie** (60ms, 6 chunks):

- `beh_03.04.2019-_Positionspapier_zur_biometri_152` | dist=0.135 |  03.04.2019- Positionspapier zur biometrischen Analyse
  > Verifikation.  Biometrische Daten fallen somit erst unter den Begriff der „besonderen Kategorien  personenbezogener Date
- `beh_03.04.2019-_Positionspapier_zur_biometri_127` | dist=0.140 |  03.04.2019- Positionspapier zur biometrischen Analyse
  > 6.1 Begriff der biometrischen Daten nach Art. 4 Nr. 14 DS-GVO  Biometrische Daten sind nach der Definition in Art. 4 Nr.
- `beh_03.04.2019-_Positionspapier_zur_biometri_126` | dist=0.142 |  03.04.2019- Positionspapier zur biometrischen Analyse
  > 6 Rechtliche Bewertung  Nach Art. 9 Abs. 1 DS-GVO ist die Verarbeitung biometrischer Daten zur eindeutigen Identifizieru

**erwaegungsgrund** (40ms, 4 chunks):

- `dsgvo_eg_34` | dist=0.190 | DSGVO Genetische Daten*
  > Erwägungsgrund 34 DSGVO – Genetische Daten*  Genetische Daten sollten als personenbezogene Daten über die ererbten oder 
- `dsgvo_eg_53` | dist=0.191 | DSGVO Verarbeitung sensibler Daten im Gesundheits- und Sozialbereich*
  > Erwägungsgrund 53 DSGVO – Verarbeitung sensibler Daten im Gesundheits- und Sozialbereich*  1 Besondere Kategorien person
- `dsgvo_eg_51` | dist=0.195 | DSGVO Besonderer Schutz sensibler Daten*
  > Erwägungsgrund 51 DSGVO – Besonderer Schutz sensibler Daten*  1 Personenbezogene Daten, die ihrem Wesen nach hinsichtlic

**methodenwissen** (57ms, 4 chunks):

- `mw_art4_index` | dist=0.197 | DSGVO Art. 4
  > Art. 4 DSGVO – Begriffsbestimmungen (Übersicht)  Art. 4 DSGVO definiert die zentralen Begriffe der Verordnung. Jeder Beg
- `mw_personenbezug_ip_adressen_bestimmbarkeit` | dist=0.207 |  Personenbezogene Daten – Personenbezug und Bestimmbarkeit
  > Personenbezogene Daten (Art. 4 Nr. 1 DSGVO) – Personenbezug und Bestimmbarkeit:  Definition: Alle Informationen, die sic
- `mw_informationelle_selbstbestimmung_bverfg_volkszaehlung_1983_u` | dist=0.209 |  Informationelle Selbstbestimmung (BVerfG Volkszählung 1983) und IT-Grundrecht
  > Die verfassungsrechtlichen Grundlagen des deutschen Datenschutzrechts: 1. BVerfG, Urteil vom 15.12.1983, 1 BvR 209/83 (V

**Nach Typ-Budget (14 Chunks):**

- erwaegungsgrund: 2
- gesetz_granular: 4
- leitlinie: 3
- methodenwissen: 2
- urteil_segmentiert: 3

Top-8 nach Distance:
- `beh_03.04.2019-_Positionspapier_zur_biometri_152` [leitlinie] | dist=0.135 |  03.04.2019- Positionspapier zur biometrischen Analyse
- `beh_03.04.2019-_Positionspapier_zur_biometri_127` [leitlinie] | dist=0.140 |  03.04.2019- Positionspapier zur biometrischen Analyse
- `beh_03.04.2019-_Positionspapier_zur_biometri_126` [leitlinie] | dist=0.142 |  03.04.2019- Positionspapier zur biometrischen Analyse
- `seg_eugh_C-252_21_rechtsrahmen_5` [urteil_segmentiert] | dist=0.154 |  EuGH C-252/21
- `seg_eugh_C-205_21_vf_3_14` [urteil_segmentiert] | dist=0.155 |  EuGH C-205/21
- `seg_eugh_C-61_22_wuerdigung_7` [urteil_segmentiert] | dist=0.155 |  EuGH C-61/22
- `dsgvo_art4_daten_identitaet` [gesetz_granular] | dist=0.179 | DSGVO Art. 4 DSGVO (Daten und Identität)
- `dsgvo_eg_34` [erwaegungsgrund] | dist=0.190 | DSGVO Genetische Daten*

**Bewertung:**
- [ ] ✅ Pro Source sinnvolle Top-Chunks UND Budget liefert gute Mischung
- [ ] ⚠️ Pro Source OK, aber Budget verdrängt wichtige Chunks
- [ ] ❌ Pro Source zeigt schon falsche Chunks

---

## Aggregierte Bewertung (von Hendrik auszufüllen)

Nach Sichtprüfung der 10 Fälle:
- Anteil ✅: ___ / 10
- Anteil ⚠️: ___ / 10
- Anteil ❌: ___ / 10

**Performance:**
- Avg Embedding: 104ms
- Avg Retrieval (5 Calls): 209ms
- Avg Total: 313ms

**Entscheidung:**
- [ ] Per-Source-Retrieval funktioniert gut → weiter mit Schritt 2.2
- [ ] Probleme bei bestimmten Source-Types (welche?): ___
- [ ] Performance zu langsam, Optimierung nötig