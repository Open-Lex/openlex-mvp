# OpenLex Eval v3 – Report

**Timestamp:** 2026-04-23 18:34  
**Fragen:** 78  
**Dauer:** 155.0s  
**Modus:** Retrieval-only

## Retrieval-Metriken

| Metrik | Wert |
|--------|------|
| Hit@3 | 0.322 |
| nDCG@3 | 0.226 |
| ForbiddenHit@3 | 0.000 |
| Hit@5 | 0.341 |
| nDCG@5 | 0.204 |
| ForbiddenHit@5 | 0.000 |
| Hit@10 | 0.341 |
| nDCG@10 | 0.205 |
| ForbiddenHit@10 | 0.000 |
| MRR | 0.317 |

## MRR pro Kategorie

| Kategorie | MRR |
|-----------|-----|
| pruefungsschemata | 0.727 |
| behoerden | 0.500 |
| beschaeftigtendatenschutz | 0.500 |
| cookies_tracking | 0.500 |
| rechtsprechung | 0.500 |
| methodenwissen | 0.250 |
| rechtsgrundlagen | 0.192 |
| drittlandtransfer | 0.188 |
| allgemein | 0.105 |
| auftragsverarbeitung | 0.000 |
| betroffenenrechte | 0.000 |

## Latenz

_(Warmup=3 Queries exkl., n=75)_

| Messung | mean | median | p95 |
|---------|------|--------|-----|
| Reranker | 406 ms | 381 ms | 672 ms |
| Total Retrieve | 1459 ms | 1441 ms | 1855 ms |

## Einzelergebnisse

### canonical_001
**Frage:** Wie ist die Rangfolge der Rechtsnormen im europäischen Datenschutzrecht strukturiert und welche konkreten Rechtsquellen sind auf den jeweiligen Ebenen zu beachten?  
**Kategorie:** methodenwissen  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=0.00  
**Gold-IDs:**   
**Retrieved Top-5:** eugh_C-416_23_rechtsrahmen_0, eugh_C-638_23_rechtsrahmen_0, eugh_C-768_21_rechtsrahmen_0, eugh_C-446_21_rechtsrahmen_0, eugh_C-487_21_rechtsrahmen_0  

### canonical_002
**Frage:** Unter welchen Voraussetzungen müssen nationale Gerichte Vorschriften des Bundesdatenschutzgesetzes unangewendet lassen, wenn diese mit der Datenschutz-Grundverordnung in Konflikt stehen?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_88  
**Retrieved Top-5:** eugh_C-60_22_sachverhalt_1, eugh_C-65_23_vf_2_0, eugh_C-34_21_vf_2_0, eugh_C-203_22_wuerdigung_7, eugh_C-487_21_wuerdigung_4  

### canonical_003
**Frage:** Welche spezifischen Öffnungsklauseln der DSGVO ermöglichen es den Mitgliedstaaten, nationale Regelungen für die Verarbeitung besonderer Kategorien personenbezogener Daten im Arbeitsrecht zu erlassen?  
**Kategorie:** methodenwissen  
**Retrieval:** Hit@3=0.25 | Hit@5=0.25 | Hit@10=0.25 | MRR=1.00  
**Gold-IDs:** dsgvo_art_9_part0, dsgvo_art_9_part1, dsgvo_art_88, gran_BDSG_§_26_Abs.1  
**Retrieved Top-5:** Art. 88 DSGVO, eugh_C-34_21_vf_1_1, eugh_C-34_21_vorlagefragen_3, eugh_C-65_23_vf_1_0, eugh_C-34_21_vf_2_0  

### canonical_004
**Frage:** Welche konkreten Vorschriften des BDSG setzen die Öffnungsklauseln der DSGVO um und welche besonderen Anforderungen oder Einschränkungen ergeben sich dabei insbesondere im Beschäftigtendatenschutz?  
**Kategorie:** methodenwissen  
**Retrieval:** Hit@3=0.25 | Hit@5=0.25 | Hit@10=0.25 | MRR=1.00  
**Gold-IDs:** dsgvo_art_88, gran_BDSG_§_26_Abs.1, dsgvo_art_89, dsgvo_art_23  
**Retrieved Top-5:** Art. 88 DSGVO, Art. 6 DSGVO (Teil 1), Art. 6 DSGVO (Teil 2), dd8676b5fa6eb84d, 8c5a57d49b9a3646  

### canonical_005
**Frage:** Welche spezifischen Regelungen des TTDSG sind bei der Verwendung von Cookies auf einer Website zu beachten und wie verhält sich diese Regelung zur DSGVO?  
**Kategorie:** cookies_tracking  
**Retrieval:** Hit@3=0.25 | Hit@5=0.25 | Hit@10=0.25 | MRR=1.00  
**Gold-IDs:** dsgvo_art_95, gran_TDDDG_§_25, dsgvo_art_6_part0, dsgvo_art_6_part1  
**Retrieved Top-5:** gran_TDDDG_§_25, gran_TDDDG_§_29, Verhältnis DSGVO zu ePrivacy/TTDSG (lex specialis), Verhältnis DSGVO – TTDSG – § 7 UWG bei Werbung und Direktmarketing, eugh_C-65_23_vf_1_3  

### canonical_006
**Frage:** Welche spezifischen Regelungen des sektorspezifischen Datenschutzrechts sind bei der Verarbeitung von Sozialdaten und Steuerdaten zu beachten und wie verhalten sich diese zu den allgemeinen Bestimmungen der DSGVO?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1, dsgvo_art_85  
**Retrieved Top-5:** eugh_C-34_21_vf_1_3, eugh_C-667_21_rechtsrahmen_5, eugh_C-667_21_vf_1_3, eugh_C-61_22_wuerdigung_9, eugh_C-205_21_vf_2_1  

### canonical_007
**Frage:** Welche Hierarchie der Rechtsquellen und Autoritäten ist bei der juristischen Analyse im Datenschutzrecht zu beachten und welche praktische Relevanz haben die Leitlinien des Europäischen Datenschutzausschusses?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=0.00  
**Gold-IDs:**   
**Retrieved Top-5:** eugh_C-340_21_rechtsrahmen_0, eugh_C-132_21_rechtsrahmen_0, eugh_C-638_23_rechtsrahmen_0, eugh_C-65_23_rechtsrahmen_0, eugh_C-710_23_rechtsrahmen_0  

### canonical_008
**Frage:** Wie ist bei ungeklärten Rechtsfragen im Datenschutzrecht vorzugehen, wenn die EuGH-Rechtsprechung noch keine klare Linie aufweist?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=0.00  
**Gold-IDs:**   
**Retrieved Top-5:** eugh_C-470_21_wuerdigung_18, eugh_c_97_23_rechtsrahmen_0, eugh_c_333_22_vf_2b_2, eugh_C-203_22_sachverhalt_3, eugh_C-21_23_vf_1_7  

### canonical_009
**Frage:** Wie ist bei der Auslegung der DSGVO mit unterschiedlichen Formulierungen in den verschiedenen Sprachfassungen umzugehen und welche Rolle spielt dabei der EuGH?  
**Kategorie:** methodenwissen  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=0.00  
**Gold-IDs:**   
**Retrieved Top-5:** eugh_C-34_21_vf_1_0, eugh_C-252_21_rechtsrahmen_8, eugh_C-667_21_vf_5_0, eugh_C-203_22_wuerdigung_0, eugh_C-422_24_sachverhalt_4  

### canonical_010
**Frage:** Wie sind die Erwägungsgründe der DSGVO bei der Auslegung von Art. 6 Abs. 1 lit. f DSGVO zu berücksichtigen?  
**Kategorie:** methodenwissen  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1, dsgvo_art_5  
**Retrieved Top-5:** Systematische Auslegung der DSGVO (Erwägungsgründe als Kontext), beh_29.03.2019-_Orientierungshilfe_der_Aufsi_36, Erwägungsgrund 6 DSGVO – Gewährleistung eines hohen Datensch, eugh_C-252_21_vf_6b_0, Art. 35 DSGVO (Teil 2)  

### canonical_011
**Frage:** Wie lässt sich das Spannungsverhältnis zwischen dem Schutz natürlicher Personen bei der Verarbeitung personenbezogener Daten und dem freien Datenverkehr innerhalb der Europäischen Union nach der Datenschutz-Grundverordnung in der Praxis auflösen?  
**Kategorie:** methodenwissen  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_1  
**Retrieved Top-5:** eugh_C-46_23_rechtsrahmen_0, eugh_C-638_23_rechtsrahmen_0, eugh_C-655_23_rechtsrahmen_0, eugh_C-154_21_rechtsrahmen_0, eugh_C-34_21_rechtsrahmen_1  

### canonical_012
**Frage:** Welche historischen Rechtsquellen und Dokumente sind bei der Auslegung von Begriffen der Datenschutz-Grundverordnung (DSGVO) heranzuziehen, wenn der Europäische Gerichtshof (EuGH) hierzu noch keine Rechtsprechung entwickelt hat?  
**Kategorie:** methodenwissen  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=0.00  
**Gold-IDs:**   
**Retrieved Top-5:** eugh_c_582_14_tenor, eugh_C-487_21_wuerdigung_5, eugh_C-710_23_vf_2_1, eugh_C-487_21_wuerdigung_0, eugh_C-33_22_vf_3_0  

### canonical_013
**Frage:** Welche spezifischen Auslegungsmethoden wendet der EuGH bei der Interpretation der DSGVO an und wie beeinflussen diese die praktische Anwendung des Datenschutzrechts?  
**Kategorie:** methodenwissen  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=0.00  
**Gold-IDs:**   
**Retrieved Top-5:** eugh_C-659_22_rechtsrahmen_0, eugh_C-807_21_vf_1_3, eugh_c_621_22_wuerdigung_1, eugh_C-203_22_sachverhalt_3, eugh_C-203_22_sachverhalt_2  

### canonical_014
**Frage:** Welche Voraussetzungen müssen erfüllt sein, damit die Verarbeitung personenbezogener Daten, insbesondere besonderer Kategorien, nach der Datenschutz-Grundverordnung rechtmäßig ist?  
**Kategorie:** rechtsgrundlagen  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1, dsgvo_art_9_part0, dsgvo_art_9_part1  
**Retrieved Top-5:** eugh_C-634_21_rechtsrahmen_3, eugh_C-34_21_rechtsrahmen_5, BDSG_§_24_Abs.1_S.2, BDSG_§_23_Abs.1_S.3, eugh_C-654_23_rechtsrahmen_3  

### canonical_015
**Frage:** Welche verfassungsrechtlichen Grundlagen sind für das deutsche Datenschutzrecht maßgeblich und welche Kernaussagen treffen die entsprechenden Urteile des Bundesverfassungsgerichts?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=0.00  
**Gold-IDs:**   
**Retrieved Top-5:** eugh_c_621_22_wuerdigung_1, eugh_C-710_23_rechtsrahmen_0, eugh_C-446_21_rechtsrahmen_0, eugh_C-252_21_vf_6_5, eugh_c_140_20_vorlagefragen_3  

### canonical_016
**Frage:** Welche konkreten Anforderungen stellt der Grundsatz der Rechtmäßigkeit, Verarbeitung nach Treu und Glauben sowie Transparenz gemäß Art. 5 Abs. 1 lit. a DSGVO an die Datenverarbeitung und welche Rechtsfolgen drohen bei einem Verstoß?  
**Kategorie:** rechtsgrundlagen  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_5, dsgvo_art_6_part0, dsgvo_art_6_part1, dsgvo_art_83_part0, dsgvo_art_83_part1  
**Retrieved Top-5:** eugh_C-492_23_vorlagefragen_8, beh_Leitlinien_03_2022_zu_119, eugh_C-654_23_rechtsrahmen_3, eugh_C-154_21_rechtsrahmen_1, eugh_C-34_21_rechtsrahmen_5  

### canonical_017
**Frage:** Unter welchen Voraussetzungen ist eine Weiterverarbeitung personenbezogener Daten zu einem anderen Zweck als dem ursprünglichen Erhebungszweck nach der Datenschutz-Grundverordnung zulässig?  
**Kategorie:** rechtsgrundlagen  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_5, dsgvo_art_6_part0, dsgvo_art_6_part1  
**Retrieved Top-5:** eugh_C-77_21_rechtsrahmen_1, Erwägungsgrund 50 DSGVO – Weiterverarbeitung*

1
Die Verarbe, beh_Leitlinien_06_2020_zum_Zusammenspiel_zwi_24, BDSG_§_49_Abs.1_S.1, BDSG_§_24_Abs.1_S.2  

### canonical_018
**Frage:** Welche konkreten Anforderungen stellt der Grundsatz der Datenminimierung nach Art. 5 Abs. 1 lit. c DSGVO an die Verarbeitung personenbezogener Daten für Werbezwecke und welche technischen Maßnahmen sind zur Umsetzung dieses Prinzips erforderlich?  
**Kategorie:** rechtsgrundlagen  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_5, dsgvo_art_25  
**Retrieved Top-5:** beh_Leitlinien_06_2020_zum_Zusammenspiel_zwi_51, beh_September_2025-_Anwendungshinweise_zu_de_13, eugh_C-446_21_vf_2b_2, beh_Stand_April_2018_-_Standard-Datenschutzm_31, beh_September_2025-_Anwendungshinweise_zu_de_14  

### canonical_019
**Frage:** Welche konkreten Maßnahmen muss ein Verantwortlicher ergreifen, um den Grundsatz der Richtigkeit personenbezogener Daten gemäß den Vorgaben der DSGVO zu gewährleisten?  
**Kategorie:** rechtsgrundlagen  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_5, dsgvo_art_16, dsgvo_art_17  
**Retrieved Top-5:** eugh_C-741_21_rechtsrahmen_2, eugh_C-34_21_rechtsrahmen_5, BDSG_§_26_Abs.1_S.11, beh_LfDI_BW_Diskussionspapier_Rechtsgrundlag_24, BDSG_§_74_Abs.1_S.1  

### canonical_020
**Frage:** Welche Anforderungen stellt der Grundsatz der Speicherbegrenzung nach der DSGVO an die Aufbewahrung von personenbezogenen Daten in Sicherungskopien und welche Ausnahmen gelten dabei?  
**Kategorie:** rechtsgrundlagen  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_5, dsgvo_art_89  
**Retrieved Top-5:** Art. 15 DSGVO, beh_02.03.2021-_Stellungnahme_der_DSK_zur_Ev_27, beh_10.03.2026-_Stellungnahme_zum_Digital_Fi_27, eugh_C-61_22_wuerdigung_23, eugh_c_307_22_rechtsrahmen_4  

### canonical_021
**Frage:** Welche konkreten Maßnahmen müssen gemäß DSGVO ergriffen werden, um die Integrität und Vertraulichkeit personenbezogener Daten zu gewährleisten, und welche Meldepflichten bestehen bei einer Verletzung dieser Prinzipien?  
**Kategorie:** rechtsgrundlagen  
**Retrieval:** Hit@3=0.33 | Hit@5=0.33 | Hit@10=0.33 | MRR=1.00  
**Gold-IDs:** dsgvo_art_5, dsgvo_art_32, dsgvo_art_33  
**Retrieved Top-5:** Art. 33 DSGVO, Art. 34 DSGVO, beh_Anforderungen_an_datenschutzrechtliche_Z_0, beh_Anforderungen_an_datenschutzrechtliche_Z_398, eugh_C-741_21_rechtsrahmen_2  

### canonical_022
**Frage:** Welche konkreten Maßnahmen muss ein Unternehmen ergreifen, um die Rechenschaftspflicht nach Art. 5 Abs. 2 DSGVO zu erfüllen und die Einhaltung der Datenschutzgrundsätze nachweisen zu können?  
**Kategorie:** rechtsgrundlagen  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_5, dsgvo_art_30, dsgvo_art_35_part0, dsgvo_art_35_part1  
**Retrieved Top-5:** Art. 24 DSGVO, eugh_C-340_21_vf_2_1, eugh_C-46_23_vf_1_1, eugh_C-203_22_sachverhalt_2, eugh_C-203_22_sachverhalt_3  

### canonical_023
**Frage:** Welche rechtlichen Schritte sind bei der Prüfung der Zulässigkeit einer Datenverarbeitung nach der Datenschutz-Grundverordnung zu beachten und welche Normen sind dabei insbesondere zu berücksichtigen?  
**Kategorie:** pruefungsschemata  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1, dsgvo_art_5  
**Retrieved Top-5:** eugh_C-492_23_rechtsrahmen_4, eugh_C-654_23_rechtsrahmen_3, eugh_C-340_21_vf_2_0, beh_06.05.2024-_Orientierungshilfe_der_DSK_z_86, beh_Juni_2025-_Orientierungshilfe_zu_empfohl_49  

### canonical_024
**Frage:** Welche rechtlichen Anforderungen müssen erfüllt sein, damit eine Einwilligung nach den Vorgaben der Datenschutz-Grundverordnung als wirksam angesehen werden kann?  
**Kategorie:** rechtsgrundlagen  
**Retrieval:** Hit@3=0.50 | Hit@5=0.50 | Hit@10=0.50 | MRR=1.00  
**Gold-IDs:** dsgvo_art_7, dsgvo_art_8  
**Retrieved Top-5:** Art. 7 DSGVO, Art. 70 DSGVO (Teil 1), gran_TDDDG_§_25, gran_TDDDG_§_29, eugh_C-492_23_rechtsrahmen_4  

### canonical_025
**Frage:** Welche Kriterien müssen bei der Prüfung eines berechtigten Interesses gemäß Art. 6 Abs. 1 lit. f DSGVO im Rahmen des dreistufigen Tests berücksichtigt werden?  
**Kategorie:** rechtsgrundlagen  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1  
**Retrieved Top-5:** eugh_c_621_22_wuerdigung_5, eugh_C-203_22_sachverhalt_2, eugh_C-683_21_vf_4_1, eugh_C-659_22_rechtsrahmen_0, beh_Leitlinien_3_2019_zur_Verarbeitung_18  

### canonical_026
**Frage:** Unter welchen Voraussetzungen ist eine Datenschutz-Folgenabschätzung nach der Datenschutz-Grundverordnung durchzuführen und welche inhaltlichen Anforderungen sind dabei zu beachten?  
**Kategorie:** pruefungsschemata  
**Retrieval:** Hit@3=0.40 | Hit@5=0.40 | Hit@10=0.40 | MRR=1.00  
**Gold-IDs:** dsgvo_art_35_part0, dsgvo_art_35_part1, dsgvo_art_36, dsgvo_art_9_part0, dsgvo_art_9_part1  
**Retrieved Top-5:** Art. 35 DSGVO (Teil 1), Art. 35 DSGVO (Teil 2), Prüfungsschema Datenschutz-Folgenabschätzung (DSFA, Art. 35 DSGVO), beh_23.10.2020-_Videokonferenzsysteme_45, eugh_C-492_23_rechtsrahmen_4  

### canonical_027
**Frage:** Unter welchen Voraussetzungen kann ein Betroffener nach Art. 82 DSGVO Schadensersatz für einen immateriellen Schaden geltend machen, und welche Kriterien hat der EuGH hierfür aufgestellt?  
**Kategorie:** pruefungsschemata  
**Retrieval:** Hit@3=0.33 | Hit@5=0.33 | Hit@10=0.33 | MRR=1.00  
**Gold-IDs:** dsgvo_art_82, dsgvo_art_28_part0, dsgvo_art_28_part1  
**Retrieved Top-5:** Art. 82 DSGVO, eugh_c_182_22_vf_5b_1, eugh_C-741_21_sachverhalt_1, eugh_C-590_22_vf_1_2_1, eugh_C-655_23_sachverhalt_2  

### canonical_028
**Frage:** Welche zentralen Verfahrensinstrumente auf EU-Ebene stehen den nationalen Gerichten und Aufsichtsbehörden zur Verfügung, um eine einheitliche Anwendung und Auslegung der DSGVO in grenzüberschreitenden Fällen sicherzustellen?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_56, dsgvo_art_65  
**Retrieved Top-5:** eugh_C-252_21_rechtsrahmen_8, eugh_c_97_23_rechtsrahmen_9, eugh_C-132_21_rechtsrahmen_0, eugh_C-200_23_vf_8_2, eugh_C-645_19_wuerdigung_9  

### canonical_029
**Frage:** Welche Funktion hat der Schadensersatzanspruch nach Art. 82 DSGVO und welche Kriterien sind für die Bemessung des Schadensersatzes maßgeblich?  
**Kategorie:** rechtsprechung  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=1.00  
**Gold-IDs:** dsgvo_art_82  
**Retrieved Top-5:** Art. 82 DSGVO, eugh_C-667_21_vf_4_0, eugh_C-590_22_vf_4_5_0, eugh_c_507_23_wuerdigung_10, eugh_C-741_21_vf_3_4_0  

### canonical_030
**Frage:** Unter welchen Voraussetzungen kann die bloße Befürchtung eines Datenmissbrauchs als immaterieller Schaden im Sinne der DSGVO anerkannt werden?  
**Kategorie:** rechtsprechung  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=1.00  
**Gold-IDs:** dsgvo_art_82  
**Retrieved Top-5:** Art. 82 DSGVO, eugh_C-655_23_vf_4_2, eugh_C-340_21_vf_5_0, eugh_c_182_22_vf_5b_1, eugh_C-590_22_vf_3  

### canonical_031
**Frage:** Unter welchen Voraussetzungen kann ein Identitätsdiebstahl nach einem Datenleck als ersatzfähiger immaterieller Schaden im Sinne der DSGVO geltend gemacht werden?  
**Kategorie:** rechtsprechung  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=1.00  
**Gold-IDs:** dsgvo_art_82  
**Retrieved Top-5:** Art. 82 DSGVO, eugh_c_182_22_vf_5b_1, eugh_c_182_22_vf_5b_0, eugh_c_182_22_tenor, eugh_C-655_23_sachverhalt_3  

### canonical_032
**Frage:** Unter welchen Voraussetzungen kann der bloße Kontrollverlust über personenbezogene Daten als immaterieller Schaden im Sinne der Datenschutz-Grundverordnung angesehen werden?  
**Kategorie:** rechtsprechung  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=1.00  
**Gold-IDs:** dsgvo_art_82  
**Retrieved Top-5:** Art. 82 DSGVO, Art. 4 DSGVO – Begriffsbestimmungen (Übersicht)

Art. 4 DSGV, eugh_c_582_14_tenor, eugh_c_182_22_vf_5b_1, eugh_C-655_23_vf_4_0  

### canonical_033
**Frage:** Unter welchen Voraussetzungen kann eine Entschuldigung des Verantwortlichen als ausreichender Ausgleich für immaterielle Schäden im Sinne der DSGVO angesehen werden?  
**Kategorie:** rechtsprechung  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_82  
**Retrieved Top-5:** eugh_C-655_23_vf_5_3, eugh_c_507_23_wuerdigung_9, eugh_c_507_23_tenor, eugh_C-655_23_sachverhalt_3, eugh_C-741_21_sachverhalt_1  

### canonical_034
**Frage:** Unter welchen Voraussetzungen können kommerzielle Interessen als berechtigtes Interesse im Sinne von Art. 6 Abs. 1 lit. f DSGVO gewertet werden?  
**Kategorie:** rechtsprechung  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1  
**Retrieved Top-5:** 0c2f81f4f1a2edac, BVerwG_6._Senat_6_C_3_23_tatbestand_5, 9c6462dd1332d694, 13b123df401a7579, eugh_c_621_22_wuerdigung_5  

### canonical_035
**Frage:** Welche Einschränkungen ergeben sich aus dem Grundsatz der Datenminimierung für die Zusammenführung personenbezogener Daten zu Werbezwecken, insbesondere im Hinblick auf die Entscheidung des EuGH in der Rechtssache C-446/21?  
**Kategorie:** rechtsprechung  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_5  
**Retrieved Top-5:** Art. 44 DSGVO, Art. 45 DSGVO (Teil 1), Art. 45 DSGVO (Teil 2), Art. 46 DSGVO, eugh_C-311_18_tenor  

### canonical_036
**Frage:** Unter welchen Voraussetzungen können Bußgelder nach der DSGVO gegen ein Unternehmen verhängt werden, und welche Rolle spielt dabei das Verschuldensprinzip?  
**Kategorie:** rechtsprechung  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_83_part0, dsgvo_art_83_part1  
**Retrieved Top-5:** beh_18.01.2023–_Stellungnahme_zu_Grundsatz_13, EuGH C-807/21 Deutsche Wohnen – Bußgelder und Verschuldensprinzip, Art. 83 DSGVO (Teil 1), beh_18.01.2023–_Stellungnahme_zu_Grundsatz_177, beh_18.01.2023–_Stellungnahme_zu_Grundsatz_52  

### canonical_037
**Frage:** Wie ist die Bußgeldobergrenze bei einem Datenschutzverstoß innerhalb eines Konzerns zu berechnen und welche Kriterien sind dabei maßgeblich?  
**Kategorie:** rechtsprechung  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_83_part0, dsgvo_art_83_part1  
**Retrieved Top-5:** eugh_C-654_23_rechtsrahmen_5, eugh_C-383_23_rechtsrahmen_1, eugh_C-383_23_wuerdigung_1, eugh_C-807_21_sachverhalt_2, eugh_C-768_21_sachverhalt_1  

### canonical_038
**Frage:** Welche konkreten Anforderungen stellt der EuGH in seinem Urteil C-34/21 an nationale Vorschriften zum Beschäftigtendatenschutz und welche Konsequenzen ergeben sich daraus für die Anwendung des § 26 BDSG?  
**Kategorie:** rechtsprechung  
**Retrieval:** Hit@3=0.75 | Hit@5=0.75 | Hit@10=0.75 | MRR=1.00  
**Gold-IDs:** dsgvo_art_88, dsgvo_art_6_part0, dsgvo_art_6_part1, gran_BDSG_§_26_Abs.1  
**Retrieved Top-5:** Art. 88 DSGVO, Art. 6 DSGVO (Teil 1), Art. 6 DSGVO (Teil 2), dd8676b5fa6eb84d, 8c5a57d49b9a3646  

### canonical_039
**Frage:** Welche Anforderungen müssen Betriebsvereinbarungen nach der Rechtsprechung des EuGH in der Sache C-65/23 erfüllen, um als Rechtsgrundlage für die Datenverarbeitung nach der DSGVO zu gelten?  
**Kategorie:** rechtsprechung  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=1.00  
**Gold-IDs:** dsgvo_art_88  
**Retrieved Top-5:** Art. 88 DSGVO, Art. 6 DSGVO (Teil 1), Art. 6 DSGVO (Teil 2), dd8676b5fa6eb84d, 8c5a57d49b9a3646  

### canonical_040
**Frage:** Welche spezifischen Anforderungen ergeben sich aus dem Zusammenspiel von DSGVO und AI Act bei der Verarbeitung besonderer Kategorien personenbezogener Daten für die Entwicklung von Hochrisiko-KI-Systemen?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_35_part0, dsgvo_art_35_part1  
**Retrieved Top-5:** Art. 44 DSGVO, Art. 45 DSGVO (Teil 1), Art. 45 DSGVO (Teil 2), Art. 46 DSGVO, eugh_C-311_18_tenor  

### canonical_041
**Frage:** Welche rechtlichen Anforderungen sind bei der Verarbeitung personenbezogener Daten im Rahmen des Digital Services Act zusätzlich zu beachten, und welche Rolle spielt dabei Art. 6 Abs. 1 DSGVO?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1  
**Retrieved Top-5:** eugh_C-252_21_vf_3_4, eugh_C-252_21_vf_5, beh_November_2024-_Orientierungshilfe_der_Au_74, beh_November_2024-_Orientierungshilfe_der_Au_71, eugh_C-710_23_vf_2_0  

### canonical_042
**Frage:** Welche rechtlichen Konsequenzen ergeben sich für die Verantwortlichkeit nach der Datenschutz-Grundverordnung, wenn personenbezogene Daten gemäß den Bestimmungen des Data Act weitergegeben werden?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=0.00  
**Gold-IDs:**   
**Retrieved Top-5:** eugh_c_582_14_tenor, eugh_c_307_22_rechtsrahmen_3, eugh_C-768_21_rechtsrahmen_1, eugh_C-492_23_rechtsrahmen_4, eugh_C-340_21_rechtsrahmen_1  

### canonical_043
**Frage:** Welche Verarbeitungstätigkeiten sind gemäß den Vorgaben der Datenschutzkonferenz zwingend einer Datenschutz-Folgenabschätzung zu unterziehen?  
**Kategorie:** behoerden  
**Retrieval:** Hit@3=0.33 | Hit@5=0.33 | Hit@10=0.33 | MRR=1.00  
**Gold-IDs:** dsgvo_art_35_part0, dsgvo_art_35_part1, dsgvo_art_9_part0, dsgvo_art_9_part1, dsgvo_art_10, dsgvo_art_22  
**Retrieved Top-5:** Art. 35 DSGVO (Teil 1), Art. 35 DSGVO (Teil 2), eugh_C-203_22_sachverhalt_2, eugh_C-492_23_rechtsrahmen_4, Erwägungsgrund 91 DSGVO – Erforderlichkeit einer Datenschutz  

### canonical_044
**Frage:** Unter welchen Voraussetzungen ist gemäß den Leitlinien des Europäischen Datenschutzausschusses eine Datenschutz-Folgenabschätzung durchzuführen?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=0.67 | Hit@5=0.67 | Hit@10=0.67 | MRR=1.00  
**Gold-IDs:** dsgvo_art_35_part0, dsgvo_art_35_part1, dsgvo_art_36  
**Retrieved Top-5:** Art. 35 DSGVO (Teil 1), Art. 35 DSGVO (Teil 2), eugh_C-492_23_rechtsrahmen_4, Erwägungsgrund 90 DSGVO – Datenschutz-Folgenabschätzung*

1, beh_06.05.2024-_Orientierungshilfe_der_DSK_z_86  

### canonical_045
**Frage:** Unter welchen Voraussetzungen stellt die Bonitätsbewertung durch die SCHUFA eine automatisierte Entscheidung im Sinne der DSGVO dar und welche Rechte haben Betroffene in diesem Zusammenhang?  
**Kategorie:** rechtsprechung  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_22, dsgvo_art_15  
**Retrieved Top-5:** Art. 44 DSGVO, Art. 45 DSGVO (Teil 1), Art. 45 DSGVO (Teil 2), Art. 46 DSGVO, eugh_C-311_18_tenor  

### canonical_046
**Frage:** Welche konkreten Informationen über die Logik eines automatisierten Entscheidungsprozesses muss ein Verantwortlicher gemäß der Rechtsprechung des EuGH im Fall C-203/22 (Dun & Bradstreet Austria) den betroffenen Personen bereitstellen, ohne dabei den genauen Algorithmus offenlegen zu müssen?  
**Kategorie:** betroffenenrechte  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_15  
**Retrieved Top-5:** Art. 13 DSGVO, Art. 14 DSGVO (Teil 1), Art. 14 DSGVO (Teil 2), eugh_C-203_22_wuerdigung_5, eugh_C-203_22_rechtsrahmen_2  

### canonical_047
**Frage:** Unter welchen Voraussetzungen ist das Verbot der Doppelbestrafung (ne bis in idem) im Datenschutzrecht anwendbar, insbesondere bei parallelen Sanktionen nach der DSGVO und nationalen Vorschriften?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_83_part0, dsgvo_art_83_part1  
**Retrieved Top-5:** eugh_c_151_20_vf_1_3b_1, eugh_c_151_20_vf_1_3b_0, eugh_c_27_22_vf_1b_0, eugh_C-205_21_sachverhalt_1, eugh_c_27_22_sachverhalt_3  

### canonical_048
**Frage:** Welche Kriterien müssen bei der Prüfung der Verhältnismäßigkeit einer datenschutzrechtlichen Maßnahme nach Art. 52 Abs. 1 GRCh berücksichtigt werden?  
**Kategorie:** rechtsgrundlagen  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1, dsgvo_art_5  
**Retrieved Top-5:** eugh_C-340_21_vf_2_0, eugh_C-340_21_vf_2_1, eugh_C-654_23_rechtsrahmen_3, eugh_C-741_21_rechtsrahmen_2, eugh_C-340_21_vf_1_1  

### canonical_049
**Frage:** Welche rechtlichen Voraussetzungen müssen erfüllt sein, um E-Mail-Werbung an Bestandskunden ohne deren ausdrückliche Einwilligung versenden zu dürfen?  
**Kategorie:** cookies_tracking  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1, dsgvo_art_21  
**Retrieved Top-5:** Art. 7 DSGVO, Art. 70 DSGVO (Teil 1), gran_TDDDG_§_25, gran_TDDDG_§_29, mw_newsletter_einwilligung_dreistufig  

### canonical_050
**Frage:** Welche Länder haben derzeit einen gültigen Angemessenheitsbeschluss der EU-Kommission gemäß Art. 45 DSGVO, der einen Datentransfer ohne zusätzliche Garantien ermöglicht?  
**Kategorie:** drittlandtransfer  
**Retrieval:** Hit@3=0.50 | Hit@5=0.75 | Hit@10=0.75 | MRR=0.50  
**Gold-IDs:** dsgvo_art_45_part0, dsgvo_art_45_part1, dsgvo_art_5, dsgvo_art_46  
**Retrieved Top-5:** Art. 44 DSGVO, Art. 45 DSGVO (Teil 1), Art. 45 DSGVO (Teil 2), Art. 46 DSGVO, eugh_C-311_18_tenor  

### canonical_051
**Frage:** Welche rechtlichen Anforderungen müssen bei der Versendung von Newslettern kumulativ erfüllt werden, insbesondere im Hinblick auf die Einwilligung und die Verwendung von Tracking-Technologien?  
**Kategorie:** pruefungsschemata  
**Retrieval:** Hit@3=0.33 | Hit@5=0.33 | Hit@10=0.33 | MRR=1.00  
**Gold-IDs:** gran_TDDDG_§_25, dsgvo_art_6_part0, dsgvo_art_6_part1  
**Retrieved Top-5:** gran_TDDDG_§_25, gran_TDDDG_§_29, Art. 7 DSGVO, eugh_C-741_21_sachverhalt_0, eugh_C-654_23_wuerdigung_0  

### canonical_052
**Frage:** Welche rechtlichen Grundlagen und Grenzen sind bei der Kontrolle von E-Mails durch den Arbeitgeber zu beachten, wenn die Privatnutzung der betrieblichen IT-Infrastruktur verboten ist?  
**Kategorie:** beschaeftigtendatenschutz  
**Retrieval:** Hit@3=0.67 | Hit@5=0.67 | Hit@10=0.67 | MRR=0.50  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1, gran_BDSG_§_26_Abs.1  
**Retrieved Top-5:** Art. 88 DSGVO, Art. 6 DSGVO (Teil 1), Art. 6 DSGVO (Teil 2), dd8676b5fa6eb84d, 8c5a57d49b9a3646  

### canonical_053
**Frage:** Welche spezifischen Angaben müssen in einer Datenschutzerklärung enthalten sein, wenn personenbezogene Daten direkt beim Betroffenen erhoben werden, und welche zusätzlichen Informationen sind erforderlich, wenn die Daten aus anderen Quellen stammen?  
**Kategorie:** betroffenenrechte  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_13, dsgvo_art_14_part0, dsgvo_art_14_part1, dsgvo_art_6_part0, dsgvo_art_6_part1  
**Retrieved Top-5:** eugh_c_582_14_tenor, eugh_c_97_23_rechtsrahmen_3, eugh_C-422_24_rechtsrahmen_1, eugh_C-200_23_vf_5_1, eugh_C-422_24_rechtsrahmen_3  

### canonical_054
**Frage:** Welche datenschutzrechtlichen Voraussetzungen müssen bei der Verwendung personenbezogener Daten für das Training von KI-Modellen erfüllt sein, insbesondere im Hinblick auf die Zweckbindung und die Rechtsgrundlagen?  
**Kategorie:** pruefungsschemata  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_5, dsgvo_art_6_part0, dsgvo_art_6_part1, dsgvo_art_89  
**Retrieved Top-5:** mw_dsk_ki_positionen, mw_ki_datenschutz_pruefungsschema, mw_ki_training_zweckbindung, beh_Juni_2025-_Orientierungshilfe_zu_empfohl_21, beh_12.12.2025-_DSGVO-Reform_Rechtssicherhe_2  

### canonical_055
**Frage:** Welche Kriterien müssen erfüllt sein, damit eine gemeinsame Verantwortlichkeit nach der Datenschutz-Grundverordnung vorliegt, und welche rechtlichen Konsequenzen ergeben sich daraus?  
**Kategorie:** pruefungsschemata  
**Retrieval:** Hit@3=0.50 | Hit@5=0.50 | Hit@10=0.50 | MRR=1.00  
**Gold-IDs:** dsgvo_art_26, dsgvo_art_82  
**Retrieved Top-5:** Art. 26 DSGVO, eugh_C-683_21_vf_5, eugh_C-46_23_rechtsrahmen_1, eugh_C-231_22_vf_2_1, beh_06.05.2024-_Orientierungshilfe_der_DSK_z_62  

### canonical_056
**Frage:** Welche datenschutzrechtlichen Anforderungen sind bei der Nutzung von KI-Tools wie ChatGPT zu beachten, insbesondere hinsichtlich der Rechtsgrundlage, der Auftragsverarbeitung und der Datenübermittlung in Drittländer?  
**Kategorie:** pruefungsschemata  
**Retrieval:** Hit@3=0.29 | Hit@5=0.29 | Hit@10=0.29 | MRR=1.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1, dsgvo_art_28_part0, dsgvo_art_28_part1, dsgvo_art_44, dsgvo_art_35_part0, dsgvo_art_35_part1  
**Retrieved Top-5:** Art. 28 DSGVO (Teil 1), Art. 28 DSGVO (Teil 2), Art. 29 DSGVO, Prüfungsschema Datenschutzrecht – 9-Schritte-Standardprüfung, mw_gemeinsame_verantwortlichkeit_art26  

### canonical_057
**Frage:** Welche Rechtsgrundlagen sind bei der Videoüberwachung von öffentlich zugänglichen Räumen durch nicht-öffentliche Stellen zu beachten und welche spezifischen Anforderungen ergeben sich daraus?  
**Kategorie:** rechtsgrundlagen  
**Retrieval:** Hit@3=0.67 | Hit@5=0.67 | Hit@10=0.67 | MRR=0.50  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1, gran_BDSG_§_4_Abs.1  
**Retrieved Top-5:** Art. 88 DSGVO, Art. 6 DSGVO (Teil 1), Art. 6 DSGVO (Teil 2), Prüfungsschema Datenschutz-Folgenabschätzung (DSFA, Art. 35 DSGVO), DSK-Blacklist – 17 DSFA-pflichtige Verarbeitungen  

### canonical_058
**Frage:** Welche rechtlichen Schritte und Abwägungen sind erforderlich, um einen Anspruch auf Löschung von Suchergebnissen gemäß dem Recht auf Vergessenwerden durchzusetzen?  
**Kategorie:** pruefungsschemata  
**Retrieval:** Hit@3=0.33 | Hit@5=0.33 | Hit@10=0.33 | MRR=1.00  
**Gold-IDs:** dsgvo_art_17, dsgvo_art_21, dsgvo_art_19  
**Retrieved Top-5:** Art. 17 DSGVO, beh_08.10.2014-_Zum_Recht_auf_Sperrung_von_S_1, beh_Leitlinien_8_2020_über_die_gezielte_Ansp_82, beh_Leitlinien_8_2020_über_die_gezielte_Ansp_81, eugh_C-203_22_sachverhalt_3  

### canonical_059
**Frage:** Welche rechtlichen Schritte sind erforderlich, um personenbezogene Daten in die USA zu übermitteln, wenn der Empfänger nicht unter dem Data Privacy Framework zertifiziert ist?  
**Kategorie:** pruefungsschemata  
**Retrieval:** Hit@3=0.75 | Hit@5=1.00 | Hit@10=1.00 | MRR=1.00  
**Gold-IDs:** dsgvo_art_45_part0, dsgvo_art_45_part1, dsgvo_art_46, dsgvo_art_44  
**Retrieved Top-5:** Art. 44 DSGVO, Art. 45 DSGVO (Teil 1), Art. 45 DSGVO (Teil 2), Art. 46 DSGVO, eugh_C-311_18_tenor  

### canonical_060
**Frage:** Welche rechtlichen Anforderungen müssen erfüllt sein, um Cookies und Tracking-Tools auf einer Website datenschutzkonform einzusetzen?  
**Kategorie:** pruefungsschemata  
**Retrieval:** Hit@3=0.25 | Hit@5=0.25 | Hit@10=0.25 | MRR=1.00  
**Gold-IDs:** gran_TDDDG_§_25, dsgvo_art_6_part0, dsgvo_art_6_part1, dsgvo_art_7  
**Retrieved Top-5:** gran_TDDDG_§_25, gran_TDDDG_§_29, beh_November_2024-_Orientierungshilfe_der_Au_66, beh_November_2024-_Orientierungshilfe_der_Au_46, beh_November_2024-_Orientierungshilfe_der_Au_65  

### canonical_061
**Frage:** Welche zentralen datenschutzrechtlichen Anforderungen stellen die Aufsichtsbehörden an den Einsatz von KI-Systemen, die personenbezogene Daten verarbeiten?  
**Kategorie:** behoerden  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_35_part0, dsgvo_art_35_part1, dsgvo_art_5, dsgvo_art_6_part0, dsgvo_art_6_part1  
**Retrieved Top-5:** Art. 4 DSGVO – Begriffsbestimmungen (Übersicht)

Art. 4 DSGV, eugh_c_582_14_tenor, mw_dsk_ki_positionen, beh_Juni_2025-_Orientierungshilfe_zu_empfohl_2, beh_12.12.2025-_DSGVO-Reform_Rechtssicherhe_2  

### canonical_062
**Frage:** Welche Orientierungshilfen hat die Datenschutzkonferenz für die Videoüberwachung durch nicht-öffentliche Stellen veröffentlicht und wann wurden diese zuletzt aktualisiert?  
**Kategorie:** behoerden  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=0.00  
**Gold-IDs:**   
**Retrieved Top-5:** Art. 88 DSGVO, Art. 6 DSGVO (Teil 1), Art. 6 DSGVO (Teil 2), beh_11.11.2020-_Checkliste_Datenschutz_in_Vi_66, beh_20.12.2021-_Orientierungshilfe_der_Aufsi_179  

### canonical_063
**Frage:** Welche Kriterien sind entscheidend, um zu bestimmen, ob ein Cloud-Dienstleister als Auftragsverarbeiter nach Art. 28 DSGVO oder als eigenständiger Verantwortlicher einzustufen ist?  
**Kategorie:** auftragsverarbeitung  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_28_part0, dsgvo_art_28_part1, dsgvo_art_6_part0, dsgvo_art_6_part1, dsgvo_art_32  
**Retrieved Top-5:** Art. 44 DSGVO, Art. 45 DSGVO (Teil 1), Art. 45 DSGVO (Teil 2), Art. 46 DSGVO, eugh_C-311_18_tenor  

### canonical_064
**Frage:** Unter welchen Voraussetzungen sind dynamische IP-Adressen als personenbezogene Daten im Sinne der DSGVO zu qualifizieren?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1  
**Retrieved Top-5:** eugh_c_582_14_tenor, eugh_C-683_21_vf_4_1, eugh_C-200_23_vf_6, eugh_C-604_22_vf_1_3, eugh_C-604_22_vf_1_2  

### canonical_065
**Frage:** Welche Voraussetzungen müssen erfüllt sein, damit eine automatisierte Entscheidungsfindung nach Art. 22 DSGVO zulässig ist, und welche Schutzmaßnahmen sind in diesem Fall zu ergreifen?  
**Kategorie:** pruefungsschemata  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_22, dsgvo_art_9_part0, dsgvo_art_9_part1, gran_BDSG_§_31_Abs.1  
**Retrieved Top-5:** eugh_C-634_21_vf_1_5, eugh_T-553_23_header_40, eugh_C-634_21_vf_1_4, eugh_C-634_21_vf_1_2, eugh_C-203_22_wuerdigung_4  

### canonical_066
**Frage:** Unter welchen Voraussetzungen können Nutzer ihre in einem sozialen Netzwerk generierten Daten in einem maschinenlesbaren Format anfordern und welche technischen Anforderungen sind dabei zu beachten?  
**Kategorie:** betroffenenrechte  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_20, dsgvo_art_6_part0, dsgvo_art_6_part1  
**Retrieved Top-5:** eugh_C-252_21_vf_3_4, eugh_C-200_23_vf_4_1, eugh_C-252_21_vf_6b_2, eugh_C-252_21_tenor_1, eugh_c_140_20_vorlagefragen_7  

### canonical_067
**Frage:** Welche Anforderungen stellt die DSGVO an die Einwilligungsfähigkeit von Minderjährigen bei der Nutzung von Diensten der Informationsgesellschaft und welche Pflichten ergeben sich daraus für die Anbieter solcher Dienste?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_8, dsgvo_art_12_part0, dsgvo_art_12_part1, dsgvo_art_6_part0, dsgvo_art_6_part1  
**Retrieved Top-5:** Art. 7 DSGVO, Art. 70 DSGVO (Teil 1), gran_TDDDG_§_25, gran_TDDDG_§_29, mw_newsletter_einwilligung_dreistufig  

### canonical_068
**Frage:** Welche Anspruchsgrundlagen kommen bei einem Datenschutzverstoß im deutschen Recht in Betracht und wie verhalten sich diese zu den Regelungen der DSGVO?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_82  
**Retrieved Top-5:** eugh_C-590_22_rechtsrahmen_0, eugh_C-741_21_rechtsrahmen_0, eugh_C-300_21_vf_1_1, eugh_C-456_22_rechtsrahmen, eugh_c_507_23_wuerdigung_2  

### canonical_069
**Frage:** Welche konkreten Kritikpunkte wurden von der Datenschutzkonferenz (DSK) im November 2022 an der Auftragsverarbeitung von Microsoft 365 im Hinblick auf die Einhaltung der Anforderungen des Art. 28 DSGVO festgestellt?  
**Kategorie:** behoerden  
**Retrieval:** Hit@3=0.50 | Hit@5=0.50 | Hit@10=0.50 | MRR=1.00  
**Gold-IDs:** dsgvo_art_28_part0, dsgvo_art_28_part1, dsgvo_art_35_part0, dsgvo_art_35_part1  
**Retrieved Top-5:** Art. 28 DSGVO (Teil 1), Art. 28 DSGVO (Teil 2), Art. 29 DSGVO, beh_10.03.2026-_Stellungnahme_zum_Digital_Fi_24, beh_06.05.2024-_Orientierungshilfe_der_DSK_z_61  

### canonical_070
**Frage:** Welche Definitionen von zentralen Begriffen wie 'personenbezogene Daten', 'Verantwortlicher' und 'Auftragsverarbeiter' sind in der Datenschutz-Grundverordnung verbindlich festgelegt?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=0.00  
**Gold-IDs:**   
**Retrieved Top-5:** eugh_c_582_14_tenor, beh_Leitlinien_07_2020_zu_den_Begriffen_„Ver_80, beh_Leitlinien_07_2020_zu_den_Begriffen_„Ver_4, eugh_C-180_21_rechtsrahmen_4, eugh_C-180_21_vf_2_1  

### canonical_071
**Frage:** Welche Voraussetzungen müssen erfüllt sein, damit die Verarbeitung personenbezogener Daten nach der DSGVO rechtmäßig ist?  
**Kategorie:** rechtsgrundlagen  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1, dsgvo_art_5  
**Retrieved Top-5:** eugh_C-492_23_vorlagefragen_8, eugh_C-34_21_rechtsrahmen_5, Art. 6 DSGVO (Teil 1), eugh_C-654_23_rechtsrahmen_3, Erwägungsgrund 40 DSGVO – Rechtmäßigkeit der Datenverarbeitu  

### canonical_072
**Frage:** Welche Schritte sind erforderlich, um die Zulässigkeit einer Datenübermittlung an ein US-Unternehmen im Rahmen des EU-US Data Privacy Framework zu prüfen?  
**Kategorie:** drittlandtransfer  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_45_part0, dsgvo_art_45_part1  
**Retrieved Top-5:** mw_dpf_data_privacy_framework, eugh_C-311_18_sachverhalt_5, beh_16.08.2024-_Datenverarbeitung_im_Zusamme_216, beh_Stand_April_2018_-_Standard-Datenschutzm_154, Prüfungsschema Datenschutzrecht – 9-Schritte-Standardprüfung  

### canonical_073
**Frage:** Welche zusätzlichen Maßnahmen müssen neben den Standardvertragsklauseln ergriffen werden, um einen datenschutzkonformen Drittlandtransfer gemäß den Vorgaben des EuGH-Urteils Schrems II zu gewährleisten?  
**Kategorie:** drittlandtransfer  
**Retrieval:** Hit@3=0.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=0.25  
**Gold-IDs:** dsgvo_art_46  
**Retrieved Top-5:** Art. 44 DSGVO, Art. 45 DSGVO (Teil 1), Art. 45 DSGVO (Teil 2), Art. 46 DSGVO, eugh_C-311_18_tenor  

### canonical_074
**Frage:** Welche inhaltlichen Anforderungen müssen verbindliche interne Datenschutzvorschriften nach der Datenschutz-Grundverordnung erfüllen und welches Verfahren ist für deren Genehmigung vorgesehen?  
**Kategorie:** drittlandtransfer  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_47_part0, dsgvo_art_47_part1  
**Retrieved Top-5:** eugh_C-492_23_rechtsrahmen_4, beh_06.05.2024-_Orientierungshilfe_der_DSK_z_86, Art. 47 DSGVO (Teil 1), beh_Leitlinien_05_2020_zur_Einwilligung_gemä_6, beh_Anforderungen_zur_Akkreditierung_gemäß_139  

### canonical_075
**Frage:** In welchen Fällen darf das Bundesdatenschutzgesetz (BDSG) strengere Regelungen als die Datenschutz-Grundverordnung (DSGVO) vorsehen und welche rechtlichen Grundlagen sind dabei zu beachten?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1  
**Retrieved Top-5:** eugh_C-34_21_vf_1_3, eugh_C-492_23_rechtsrahmen_4, beh_11.05.2023-_Notwendigkeit_spezifischer_R_6, beh_06.05.2024-_Orientierungshilfe_der_DSK_z_86, beh_18.01.2023–_Stellungnahme_zu_Grundsatz_2  

### canonical_076
**Frage:** In welchen Bereichen der Datenschutz-Grundverordnung haben die Mitgliedstaaten die Möglichkeit, durch nationale Regelungen vom grundsätzlichen Prinzip der Vollharmonisierung abzuweichen?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=0.25 | Hit@5=0.25 | Hit@10=0.25 | MRR=1.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1, dsgvo_art_88, gran_BDSG_§_26_Abs.1  
**Retrieved Top-5:** Art. 88 DSGVO, eugh_C-34_21_vf_1_3, eugh_C-65_23_rechtsrahmen_0, eugh_C-65_23_vf_1_0, eugh_C-34_21_vf_1_2  

### canonical_077
**Frage:** Welche Rechtsgrundlagen sind für die Anonymisierung personenbezogener Daten erforderlich und unter welchen Bedingungen fallen die Daten nach der Anonymisierung nicht mehr unter den Anwendungsbereich der DSGVO?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=0.00 | Hit@5=0.00 | Hit@10=0.00 | MRR=0.00  
**Gold-IDs:** dsgvo_art_6_part0, dsgvo_art_6_part1  
**Retrieved Top-5:** Art. 25 DSGVO, Art. 89 DSGVO, eugh_C-268_21_vf_2_3, eugh_C-683_21_vf_4_1, eugh_C-268_21_rechtsrahmen_0  

### canonical_078
**Frage:** Unter welchen Voraussetzungen stellt eine dynamische IP-Adresse ein personenbezogenes Datum im Sinne der DSGVO dar?  
**Kategorie:** allgemein  
**Retrieval:** Hit@3=1.00 | Hit@5=1.00 | Hit@10=1.00 | MRR=0.00  
**Gold-IDs:**   
**Retrieved Top-5:** eugh_c_582_14_vf_1b_0, eugh_C-604_22_vf_1_3, eugh_C-200_23_vf_6, eugh_C-638_23_sachverhalt_5, eugh_C-252_21_vf_3_4  
