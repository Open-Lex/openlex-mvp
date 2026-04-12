# Grundlagen-Check – OpenLex Retrieval-Qualität

> 15 Kernfragen des Datenschutzrechts durch `retrieve()` geprüft.
> Stand: 2026-04-10 (nach Fix 1–3: Pflicht-Chunk-Bug, MW-Chunks, Definition-Keywords)
> Laufzeit: ~25s gesamt (Ø 1.2s/Frage, Erststart 10.5s wegen Modell-Laden)

---

## Zusammenfassung

| # | Frage (verkürzt) | Chunks | Pflicht-Quellen | Bewertung |
|---|------------------|--------|-----------------|-----------|
| F01 | Art. 5 DSGVO Grundsätze | 21 | Art. 5 ✅ EG 39 ✅ | ✅ Gut |
| F02 | DSGVO unmittelbare Geltung | 24 | Anwendungsvorrang ✅ Art. 288 AEUV ❌ | ⚠️ Lücke |
| F03 | Verbot mit Erlaubnisvorbehalt | 24 | Art. 6 Abs. 1 ❌ | ⚠️ Lücke |
| F04 | Art. 6 Rechtsgrundlagen | 23 | Art. 6 ✅ | ✅ Sehr gut |
| F05 | EU-US Data Privacy Framework | 18 | DPF ✅ Angemessenheitsbeschluss ✅ | ✅ Gut |
| F06 | Drittlandübermittlung | 22 | Art. 44–46 ✅ C-311/18 ✅ | ✅ Sehr gut |
| F07 | Schrems II | 34 | C-311/18 ✅ Privacy Shield ✅ | ✅ Sehr gut |
| F08 | § 26 BDSG Beschäftigtendatenschutz | 23 | § 26 BDSG ✅ Art. 88 ✅ | ✅ Gut |
| F09 | § 26 BDSG europarechtswidrig | 17 | § 26 BDSG ✅ Art. 88 ✅ | ✅ Gut |
| F10 | SCCs + Drittlandtransfer | 35 | Art. 46 ✅ C-311/18 ✅ | ✅ Gut |
| F11 | Einwilligung | 30 | Art. 7 ✅ | ✅ Gut |
| F12 | Berechtigtes Interesse | 32 | Art. 6(1)(f) ✅ | ✅ Sehr gut |
| F13 | BCRs | 15 | Art. 47 ✅ | ✅ Sehr gut |
| F14 | Öffnungsklauseln | 25 | Art. 88 ❌ | ⚠️ Lücke |
| F15 | Strengere nationale Regeln | 15 | Vollharmonisierung ❌ | ⚠️ Lücke |

**Gesamtbewertung: 11/15 vollständig, 4/15 mit Lücken**
(Vorher: 9/15 — +2 durch Fix 1–3)

---

## Vergleich: Vor und nach Fix 1–3

| Frage | Vorher (pre-Fix) | Nachher (post-Fix) | Veränderung |
|-------|------------------|---------------------|-------------|
| F01 | ✅ (aber BGH-Pflicht Rang 2-3) | ✅ Art. 5 auf Rang 1 | **↑ sauberer** |
| F03 | ⚠️ (BGH-Pflicht Rang 1-2) | ⚠️ (MW-Chunk stattdessen) | **↑ BGH weg** |
| F05 | ⚠️ (kein DPF-Chunk) | ✅ DPF-MW auf Rang 1 | **↑ gefixt** |
| F10 | ⚠️ (kein SCC-Chunk) | ✅ Art. 46 + C-311/18 | **↑ gefixt** |
| F12 | ⚠️ (BGH-Pflicht, kaum BCR) | ✅ Pflicht + EuGH C-621/22 | **↑ gefixt** |
| F13 | ⚠️ (BGH-Pflicht, CE=-0.3) | ✅ BCR-MW Rang 1, Art. 47 Rang 2 | **↑ gefixt** |

**BGH I ZR 115/25 erscheint in 0/15 Fragen** (vorher: 10/15). Fix 1 war erfolgreich.

---

## Einzelanalyse

### F01: Art. 5 DSGVO – Grundsätze ✅

| # | Source-Type | CE | Quelle | Chunk | Relevanz |
|---|-------------|-----|--------|-------|----------|
| 1 | gesetz_granular | 10.7 | hybrid | Art. 5 DSGVO | ✅ Exakt |
| 2 | leitlinie | 10.5 | hybrid | EDPB Leitlinien 3/2020 Grundsätze | ✅ Exakt |
| 3 | leitlinie | 8.4 | semantic | EDPB Leitlinien 03/2022 Art. 5 | ✅ |
| 4 | leitlinie | 8.0 | hybrid | Hambacher Erklärung Art. 5 | ✅ |
| 5 | urteil_seg | 6.5 | semantic | EuGH C-655/23 Rechtsrahmen | ⚠️ |

**Bewertung**: Hervorragend. Art. 5 DSGVO direkt auf Rang 1 (statt vorher Rang 5). EG 39 über Erwägungsgrund-Anreicherung nachgeladen.

---

### F02: Unmittelbare Geltung der DSGVO ⚠️

| # | Source-Type | CE | Quelle | Chunk | Relevanz |
|---|-------------|-----|--------|-------|----------|
| 1 | urteil_seg | 6.4 | keyword | EuGH C-252/21 | ⚠️ Befugnisse |
| 2 | urteil_seg | 6.4 | keyword | EuGH C-634/21 | ⚠️ Mitgliedstaat |
| 3 | urteil_seg | 6.4 | keyword | EuGH C-65/23 | ✅ EG 155 |
| 4 | urteil_seg | 6.4 | keyword | EuGH C-659/22 | ⚠️ EG 1 |
| 5 | urteil_seg | 6.4 | keyword | EuGH C-200/23 | ⚠️ |

**Lücke**: Art. 288 AEUV fehlt — ist kein DSGVO-Artikel und daher nicht im `gesetz_granular`-Bestand. MW-Chunk `mw_unmittelbare_geltung_dsgvo` erscheint NICHT in Top 5 (enthält den Text, wird aber durch die vielen EuGH-Keyword-Treffer verdrängt).

**Analyse**: MW-Chunk ist vorhanden und korrekt, wird aber nicht priorisiert weil:
1. Kein Pflicht-Trigger für "unmittelbare Geltung" oder "Verordnung"
2. MW-Priorisierung greift nur bei CE > 4.0 — der MW-Chunk hat vermutlich CE < 4.0 für diese Frage

**Empfehlung**: Pflicht-Trigger hinzufügen: `(["unmittelbar", "verordnung", "anwendungsvorrang", "art. 288"], "unmittelbar")` mit Suche nach `("id:mw_unmittelbare_geltung_dsgvo", None)`.

---

### F03: Verbot mit Erlaubnisvorbehalt ⚠️

| # | Source-Type | CE | Quelle | Chunk | Relevanz |
|---|-------------|-----|--------|-------|----------|
| 1 | leitlinie | 3.5 | keyword | LfDI BW Orientierungshilfe | ✅ Erlaubnisvorbehalt |
| 2 | leitlinie | 3.5 | keyword | LfDI BW Verein | ⚠️ Tangential |
| 3 | leitlinie | 3.2 | hybrid | Orientierungshilfe Datenschutzrecht | ✅ Rechtsgrundlagen |
| 4 | gesetz_granular | -0.5 | semantic | § 6 BDSG | ❌ Irrelevant |
| 5 | leitlinie | -0.6 | semantic | Einwilligung DS-GVO | ⚠️ |

**Lücke**: Art. 6 Abs. 1 DSGVO fehlt in den Chunks (als Textstring). Der MW-Chunk `mw_verbot_mit_erlaubnisvorbehalt` ist vorhanden und enthält "Art. 6 Abs. 1 DSGVO", wird aber nicht in den Top-Ergebnissen geliefert.

**Analyse**: CE-Scores generell niedrig (max 3.5). MW-Chunk wird nicht priorisiert weil:
1. "verbot" und "erlaubnisvorbehalt" triggern keinen Pflicht-Themen-Match
2. MW-Priorisierung greift nur bei CE > 4.0

**Empfehlung**: Entweder (a) Pflicht-Trigger für Verbot mit Erlaubnisvorbehalt oder (b) den MW-Chunk-Text als Synonym in die Keyword-Suche einbauen.

---

### F04: Art. 6 DSGVO – Rechtsgrundlagen ✅✅

| # | Source-Type | CE | Quelle | Chunk |
|---|-------------|-----|--------|-------|
| 1 | urteil_seg | 20.8 | semantic | EuGH C-268/21 Art. 6(1)(e) |
| 2 | leitlinie | 9.7 | hybrid | EDPB Einwilligung + Rechtsgrundlagen |
| 3 | leitlinie | 9.7 | semantic | LfDI BW Art. 6(1) |
| 4 | urteil | 9.2 | semantic | Art. 6(1)(f) Rechtfertigung |
| 5 | leitlinie | 8.8 | hybrid | EDPB Zusammenspiel Art. 6/Art. 9 |

**Bewertung**: Exzellent. Höchster CE-Score (20.8). Gute Diversität. Art. 6 DSGVO granular auf Rang 6.

---

### F05: EU-US Data Privacy Framework ✅

| # | Source-Type | CE | Quelle | Chunk |
|---|-------------|-----|--------|-------|
| 1 | methodenwissen | 5.2 | hybrid | mw_dpf_data_privacy_framework |
| 2 | urteil_seg | 8.4 | semantic | EuGH T-553/23 Angemessenheit USA |
| 3 | urteil_seg | 6.4 | keyword | EuGH C-659/22 |
| 4 | urteil_seg | 6.4 | keyword | EuGH C-638/23 |
| 5 | urteil_seg | 6.4 | keyword | EuGH C-487/21 |

**Bewertung**: Gut. MW-Chunk auf Rang 1 (MW-Priorisierung). EuGH T-553/23 (DPF-Urteil) auf Rang 2. Verbesserung gegenüber vorher (kein DPF-Chunk).

---

### F06: Drittlandübermittlung ✅✅

| # | Source-Type | CE | Quelle | Chunk |
|---|-------------|-----|--------|-------|
| 1 | gesetz_granular | 10.0 | pflicht | Art. 44 DSGVO |
| 2 | gesetz_granular | 10.0 | pflicht | Art. 45 DSGVO (Teil 1) |
| 3 | gesetz_granular | 10.0 | pflicht | Art. 45 DSGVO (Teil 2) |
| 4 | gesetz_granular | 10.0 | pflicht | Art. 46 DSGVO |
| 5 | urteil_seg | 10.0 | pflicht | Schrems-II-Tenor |

**Bewertung**: Perfekt. Alle vier Pflicht-Quellen + Schrems-II-Tenor. "drittland"-Trigger greift korrekt.

---

### F07: Schrems II ✅✅

| # | Source-Type | CE | Quelle | Chunk |
|---|-------------|-----|--------|-------|
| 1-4 | gesetz_granular | 10.0 | pflicht | Art. 44–46 DSGVO |
| 5 | urteil_seg | 10.0 | pflicht | Schrems-II-Tenor |
| 6-8 | urteil_seg | 10.0 | urteil_name | Schrems-II-Sachverhalt |

**Bewertung**: Perfekt. Drittland-Pflicht + Urteilsname-Lookup → 34 Chunks, davon 8 direkt Schrems-II. Auch Schrems I (C-362/14) geladen.

---

### F08: § 26 BDSG Beschäftigtendatenschutz ✅

| # | Source-Type | CE | Quelle | Chunk |
|---|-------------|-----|--------|-------|
| 1 | gesetz_granular | 10.0 | pflicht | Art. 88 DSGVO |
| 2-3 | gesetz_granular | 10.0 | pflicht | Art. 6 DSGVO |
| 6 | methodenwissen | 8.4 | hybrid | MW C-34/21 § 26 BDSG |
| 7 | methodenwissen | 6.8 | semantic | MW BDSG-Öffnungsklauseln |
| 8 | urteil_seg | 15.5 | semantic | EuGH C-65/23 § 26 BDSG |

**Bewertung**: Gut. Art. 88 auf Rang 1, § 26 BDSG im MW und EuGH-Urteil. "beschaeftigt"-Trigger greift.

---

### F09: EuGH zu § 26 BDSG europarechtswidrig ✅

| # | Source-Type | CE | Quelle | Chunk |
|---|-------------|-----|--------|-------|
| 1 | methodenwissen | 4.9 | semantic | MW C-34/21 § 26 BDSG |
| 2 | leitlinie | 4.3 | semantic | DSK Stellungnahme § 26 BDSG |
| 3 | urteil_seg | 4.1 | keyword | EuGH C-288/12 |
| 5 | leitlinie | 3.9 | keyword | DSK Beschäftigtendatenschutz |
| 7 | methodenwissen | 3.0 | hybrid | MW Anwendungsvorrang |

**Bewertung**: Gut. Alle relevanten Quellen gefunden — MW-Chunk, DSK-Stellungnahme, EuGH-Urteil.

---

### F10: Standardvertragsklauseln ✅

| # | Source-Type | CE | Quelle | Chunk |
|---|-------------|-----|--------|-------|
| 1-4 | gesetz_granular | 10.0 | pflicht | Art. 44–46 DSGVO |
| 5 | urteil_seg | 10.0 | pflicht | Schrems-II-Tenor |
| 6 | urteil_seg | 5.3 | hybrid | Schrems II Art. 46(2)(c) |

**Bewertung**: Gut. "drittland"-Trigger greift via "transfer" im Synonym. Art. 46 und C-311/18 gefunden.

---

### F11: Einwilligung ✅

| # | Source-Type | CE | Quelle | Chunk |
|---|-------------|-----|--------|-------|
| 1 | gesetz_granular | 10.0 | pflicht | Art. 7 DSGVO |
| 3 | gesetz_granular | 10.0 | pflicht | § 25 TDDDG |
| 5 | methodenwissen | 10.0 | pflicht | MW Newsletter Einwilligung |
| 8 | leitlinie | 3.5 | hybrid | EDPB Einwilligung Art. 4 Nr. 11 |

**Bewertung**: Gut. "einwilligung"-Trigger greift. Art. 7 auf Rang 1. 30 Chunks.

---

### F12: Berechtigtes Interesse ✅✅

| # | Source-Type | CE | Quelle | Chunk |
|---|-------------|-----|--------|-------|
| 1-4 | urteil | 10.0 | pflicht | Art. 6(1)(f)-Urteile |
| 5 | urteil_seg | 20.3 | semantic | EuGH C-621/22 Würdigung |
| 6 | leitlinie | 11.8 | hybrid | Orientierungshilfe Art. 6(1)(f) |
| 7 | leitlinie | 9.2 | hybrid | EDPB Berechtigtes Interesse 2024 |

**Bewertung**: Hervorragend. "berechtigt"-Trigger greift. C-621/22 mit CE=20.3 auf Rang 5. EDPB-Leitlinie 2024 auf Rang 7.

---

### F13: BCRs ✅✅

| # | Source-Type | CE | Quelle | Chunk |
|---|-------------|-----|--------|-------|
| 1 | methodenwissen | 10.9 | hybrid | mw_bcr_verbindliche_interne_vorschriften |
| 2 | gesetz_granular | 6.6 | hybrid | Art. 47 DSGVO |
| 3 | erwaegungsgrund | 4.1 | semantic | EG 110 (BCRs) |
| 4 | leitlinie | 4.0 | hybrid | Datenübermittlung BCRs |

**Bewertung**: Hervorragend. BCR-MW auf Rang 1, Art. 47 auf Rang 2, EG 110 auf Rang 3. Massive Verbesserung gegenüber vorher (CE=-0.3).

---

### F14: Öffnungsklauseln ⚠️

| # | Source-Type | CE | Quelle | Chunk |
|---|-------------|-----|--------|-------|
| 1 | leitlinie | 8.6 | semantic | DSK Stellungnahme nationale Verfahren |
| 2 | urteil_seg | 6.4 | hybrid | EuGH C-65/23 Art. 88 |
| 3 | urteil_seg | 6.4 | hybrid | EuGH C-65/23 EG 8, 10, 155 |
| 5 | leitlinie | 5.6 | semantic | Orientierungshilfe Öffnungsklausel |
| 7 | leitlinie | 3.7 | keyword | LfDI BW DS-GVO unmittelbar anwendbar |

**Lücke**: Art. 88 DSGVO als Chunk-Text im Gesetzestext wird gefunden (EuGH-Zitat), aber der Suchbegriff "Art. 88" erscheint nicht exakt in den Chunk-Texten der Top-Ergebnisse (nur in Meta/EuGH-Kontext). MW-Chunk `mw_vollharmonisierung_oeffnungsklauseln` nicht in Top 8.

**Analyse**: "Öffnungsklausel" triggert keinen Pflicht-Match, da kein entsprechendes Keyword in THEMEN_KEYWORDS_MAP. Der MW-Chunk ist vorhanden, wird aber semantisch nicht hoch genug gerankt.

**Empfehlung**: Pflicht-Trigger: `(["öffnungsklausel", "oeffnungsklausel", "spielraum"], "oeffnungsklausel")` mit Suche `("id:mw_vollharmonisierung_oeffnungsklauseln", None)`.

---

### F15: Strengere nationale Regeln ⚠️

| # | Source-Type | CE | Quelle | Chunk |
|---|-------------|-----|--------|-------|
| 1 | methodenwissen | 4.1 | hybrid | mw_unmittelbare_geltung_dsgvo |
| 2 | urteil_seg | 6.4 | hybrid | EuGH C-65/23 EG 8, 10, 155 |
| 3 | urteil_seg | 6.4 | hybrid | EuGH C-340/21 |
| 5 | methodenwissen | 3.0 | hybrid | MW Normenhierarchie |

**Lücke**: Das Wort "Vollharmonisierung" kommt in keinem der gelieferten Chunks vor (nur im MW-Chunk `mw_vollharmonisierung_oeffnungsklauseln`, der nicht in den Top 8 ist).

**Analyse**: Der MW-Chunk `mw_unmittelbare_geltung_dsgvo` auf Rang 1 enthält "Anwendungsvorrang" und "Öffnungsklauseln", aber nicht den exakten String "Vollharmonisierung". Der MW-Chunk `mw_vollharmonisierung_oeffnungsklauseln` wird semantisch nicht hoch genug gerankt für diese Frage.

**Empfehlung**: Gleicher Pflicht-Trigger wie F14 → löst beide Probleme gleichzeitig.

---

## Verbleibende Lücken & Empfohlene Maßnahmen

### 1. Pflicht-Trigger für Öffnungsklauseln/Vollharmonisierung (löst F14 + F15)

```python
# In THEMEN_PFLICHT_SEARCHES:
"oeffnungsklausel": [
    ("id:mw_vollharmonisierung_oeffnungsklauseln", None),
    ("Art. 88", "gesetz_granular"),
],

# In THEMEN_KEYWORDS_MAP:
(["öffnungsklausel", "oeffnungsklausel", "vollharmonisierung",
  "spielraum", "nationales recht"], "oeffnungsklausel"),
```

### 2. Pflicht-Trigger für Unmittelbare Geltung (löst F02)

```python
# In THEMEN_PFLICHT_SEARCHES:
"unmittelbar": [
    ("id:mw_unmittelbare_geltung_dsgvo", None),
],

# In THEMEN_KEYWORDS_MAP:
(["unmittelbar", "anwendungsvorrang", "verordnung richtlinie",
  "vorrang"], "unmittelbar"),
```

### 3. Pflicht-Trigger für Verbot mit Erlaubnisvorbehalt (verbessert F03)

```python
# In THEMEN_PFLICHT_SEARCHES:
"erlaubnisvorbehalt": [
    ("id:mw_verbot_mit_erlaubnisvorbehalt", None),
    ("Verarbeitung ist nur rechtmäßig", "gesetz_granular"),
],

# In THEMEN_KEYWORDS_MAP:
(["erlaubnisvorbehalt", "grundsätzlich verboten",
  "verarbeitungsverbot"], "erlaubnisvorbehalt"),
```

### Priorisierung

| # | Fix | Betroffene Fragen | Aufwand |
|---|-----|-------------------|---------|
| 1 | 🔴 Öffnungsklausel-Trigger | F14, F15 | 5 Zeilen Code |
| 2 | 🟡 Unmittelbar-Trigger | F02 | 5 Zeilen Code |
| 3 | 🟢 Erlaubnisvorbehalt-Trigger | F03 | 5 Zeilen Code |

Alle drei Fixes sind ~15 Zeilen Code in app.py und erfordern keine neuen Daten — die MW-Chunks existieren bereits.
