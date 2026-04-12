# Retrieval-Pipeline – OpenLex MVP

> Vollständige Dokumentation der Retrieval-Pipeline in `app.py`.
> Stand: 2026-04-10 (nach Fix 1–3: Pflicht-Chunk-Bug, MW-Chunks, Definition-Keywords)

---

## Übersicht

Die Pipeline transformiert eine Nutzerfrage in einen gerankt-gefilterten Chunk-Satz,
der als Kontext an das LLM übergeben wird. 16 Schritte in 4 Phasen:

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: RETRIEVAL                                             │
│                                                                 │
│  Frage → [1] Query Expansion (History-Kontext, <30 Wörter)     │
│       → [2] Synonym-Expansion (DE↔EN, Alltagsbegriffe)         │
│       → [3] Embedding (mxbai-embed-de-large-v1, 1024 dim)      │
│       → [4] Semantic Search (ChromaDB, n=40)                    │
│       → [5] Norm-Based Search (bis 5 Normen × 5 Ergebnisse)    │
│       → [6] Keyword Hybrid Search (Umlaut + Synonyme)          │
│                                                                 │
│  PHASE 2: RERANKING                                             │
│                                                                 │
│       → [7] Cross-Encoder Reranking (mMiniLMv2, Top 40)        │
│       → [8] Pre-DSGVO-Filter (vor 2018 / obsolete Normen)      │
│       → [9] MW-Priorisierung (CE>4.0 → Position 1-3)           │
│                                                                 │
│  PHASE 3: ANREICHERUNG & SELEKTION                              │
│                                                                 │
│       → [10] Pflicht-Chunk-Trigger (Themen-Keywords → Suchen)  │
│       → [11] Urteilsnamen-Suche (Kurzname → Segmente)          │
│       → [12] Dokument-Deduplizierung (MAX_PER_DOC=3)           │
│       → [13] Dynamischer Cutoff + Min/Max (3–15 Dokumente)     │
│       → [14] Source-Type-Diversifizierung                       │
│       → [15] Erwägungsgrund-Anreicherung (max 2 EG)            │
│                                                                 │
│  PHASE 4: GENERIERUNG & VALIDIERUNG                             │
│                                                                 │
│       → [16] Kontext-Aufbau → System-Prompt → LLM-Cascade      │
│       →      Validierung (Norm/AZ-Check)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Schlüsselparameter

| Parameter | Wert | Zeile | Zweck |
|-----------|------|-------|-------|
| `MIN_DOCS` | 3 | 37 | Mindest-Dokumente im Ergebnis |
| `MAX_DOCS` | 15 | 38 | Max-Dokumente im Ergebnis |
| `CE_CUTOFF` | 3.0 | 39 | Cross-Encoder-Schwelle |
| `DIST_CUTOFF` | 0.25 | 40 | Semantische Distanz-Schwelle |
| `MAX_PER_DOC` | 3 | 909 | Max Chunks pro Dokument |
| `n_results` (semantic) | 40 | 677 | Initiale Suchbreite |
| `n_results` (norm) | 5 | 712 | Pro-Norm-Ergebnisse |
| `n_results` (keyword) | 5 | 761 | Pro-Keyword-Ergebnisse |
| LLM `max_tokens` | 2048 | 1354 | Max Antwortlänge |
| LLM `temperature` | 0.3 | 1354 | Deterministische Generierung |

---

## Phase 1: Retrieval

### Schritt 1 — Query Expansion (Z. 666–671)

Bei Follow-up-Fragen (<30 Wörter) wird die letzte Nutzerfrage vorangestellt:

```python
if history and len(question.split()) < 30:
    last_user = history[-1][0]
    search_query = f"{last_user} – {question}"
```

### Schritt 2 — Synonym-Expansion (Z. 511–559)

`_SYNONYM_MAP`: 40+ Einträge, die Alltagsbegriffe auf Fachbegriffe expandieren.

**Deutsch → Fachbegriff:**
| Alltagsbegriff | Expansion |
|----------------|-----------|
| löschen | Löschung, Recht auf Vergessenwerden, Art. 17 |
| cookies | Cookie, Einwilligung, TDDDG, § 25 TDDDG |
| chef | Arbeitgeber, Beschäftigtendatenschutz |
| arzt | Gesundheitsdaten, Art. 9 DSGVO, besondere Kategorien |
| whatsapp | Messenger, Drittlandtransfer, US-Transfer |
| google | Drittlandtransfer, Auftragsverarbeitung, Analytics, DPF |

**Deutsch → Englisch (bidirektional):**
| DE | EN |
|----|-----|
| einwilligung | consent |
| auftragsverarbeiter | processor |
| betroffenenrechte | data subject rights |
| drittland | international transfer, third country |

### Schritt 3 — Embedding (Z. 674)

| Parameter | Wert |
|-----------|------|
| Modell | `mixedbread-ai/deepset-mxbai-embed-de-large-v1` |
| Dimension | 1024 |

### Schritt 4 — Semantic Search (Z. 673–704)

```python
results = col.query(query_embeddings=q_embedding, n_results=40)
```

**Segment-Boost-Gewichte** (Z. 159–168) — multipliziert auf Distanz:

| Segment | Faktor | Effekt |
|---------|--------|--------|
| methodenwissen | 0.70 | ↑↑ stark bevorzugt |
| leitsatz | 0.85 | ↑ bevorzugt |
| gesetz_granular | 0.92 | ↑ leicht bevorzugt |
| entscheidungsgruende | 0.92 | ↑ leicht bevorzugt |
| wuerdigung | 0.92 | ↑ leicht bevorzugt |
| tenor | 0.95 | ↑ leicht bevorzugt |
| tatbestand | 1.05 | ↓ leicht benachteiligt |
| sachverhalt | 1.05 | ↓ leicht benachteiligt |

### Schritt 5 — Norm-Based Search (Z. 706–732)

Regex-Extraktion von Normreferenzen (Art. X DSGVO, § Y BDSG, etc.).

- Max 5 Normen
- Pro Norm: `n_results=5`
- Filter: `source_type ∈ {gesetz_granular, gesetz}`
- Distanz-Gewichtung: × 0.85 (bevorzugt)

### Schritt 6 — Keyword Hybrid Search (Z. 734–807)

1. **Wort-Extraktion**: Alle Wörter ≥5 Zeichen
2. **Umlaut-Normalisierung**: ü→ue, ö→oe, ä→ae (bidirektional)
3. **Synonym-Expansion** aus `_SYNONYM_MAP` (max 10 Wörter total)
4. **Suche**: `where_document={"$contains": word}`, max 5 Ergebnisse/Keyword

**Merge-Logik:**
- Chunk bereits in Semantic-Ergebnissen → Distanz halbiert (×0.5) → "hybrid"
- Nur-Keyword-Chunks → synthetische Distanz 0.15 × Segment-Boost → "keyword"

---

## Phase 2: Reranking

### Schritt 7 — Cross-Encoder Reranking (Z. 809–880)

| Parameter | Wert |
|-----------|------|
| Modell | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` |
| Max Kandidaten | 40 |
| Text-Truncation | 500 Zeichen pro Chunk |
| Min-Score (keyword/hybrid) | 3.0 (Floor) |

**Recency-Boost** (Z. 827–832) — dividiert den CE-Score:

| Jahr | Faktor | Effektiver Multiplikator |
|------|--------|--------------------------|
| ≥ 2023 | 0.70 | Score × 1.43 |
| ≥ 2020 | 0.85 | Score × 1.18 |
| ≥ 2018 | 0.95 | Score × 1.05 |
| < 2018 | 1.10 | Score × 0.91 |

**Key-Judgment-Boost** (Z. 834–840):
Urteile mit Kurzname (aus `urteilsnamen.json`, 138 Einträge) → CE-Score × 1.5

**Lower-Court-Penalty** (Z. 842–854):
BSG, BFH, BAG, BVerwG, OLG, LG, VG, AG → CE-Score ÷ 1.3
(Nur wenn Frage keinen expliziten Gerichtsbezug hat)

### Schritt 8 — Pre-DSGVO-Filter (Z. 856–869)

Entfernt/bestraft veraltete Chunks:
- Vor-2018-Leitlinien
- Obsolete Normen: § 29 BDSG-alt, §§ 88–100 TKG

Logik:
- Bei ≥3 aktuelle Chunks → alte komplett entfernen
- Sonst → Penalty ÷ 3.0

### Schritt 9 — MW-Priorisierung (Z. 882–896)

Methodenwissen-Chunks mit CE-Score > 4.0 werden an den Anfang verschoben (max 3).

---

## Phase 3: Anreicherung & Selektion

### Schritt 10 — Pflicht-Chunk-Trigger (Z. 562–608)

Funktion `_find_pflicht_chunks()` — themenbasierte Pflicht-Dokumente.

**Mechanismus:**
1. Frage wird gegen `THEMEN_KEYWORDS_MAP` (30 Einträge) geprüft
2. Matchende Themen triggern Suchen aus `THEMEN_PFLICHT_SEARCHES` (25 Themen)
3. Suche per `where_document={"$contains": ...}` oder `id:`-Lookup
4. Max 5 Pflicht-Chunks, jeweils mit CE=10.0, distance=0.05

**THEMEN_KEYWORDS_MAP** (Z. 467–507) — Keyword → Thema:

| Keywords (Auswahl) | Thema | Pflicht-Suchen |
|--------------------|-------|----------------|
| usa, drittland, cloud, dpf, schrems | drittland | Art. 44–46, Schrems-II-Tenor (ID), DPF-MW |
| cookie, banner, tracking | cookie | § 25 TDDDG, Cookie-MW |
| einwilligung, consent, newsletter | einwilligung | Art. 7, § 25 TDDDG, § 7 UWG, Newsletter-MW |
| arbeitgeber, beschäftigte, mitarbeiter | beschaeftigt | Art. 88, § 26 BDSG, C-34/21 |
| personenbezogene daten, definition, definiert, begriff | definition | Art. 4-Index (MW), Breyer-Tenor (ID) |
| berechtigtes interesse, interessenabwägung | berechtigt | Art. 6(1)(f), EG 47, C-621/22, MW |
| schufa, scoring, bonitaet | scoring | Art. 6(1)(f), SCHUFA, Profiling-MW |
| auskunft, auskunftsrecht, art. 15 | auskunft | Art. 15, Betroffenenrechte-Leitlinie |
| dsfa, folgenabschätzung | dsfa | Art. 35, DSFA-MW, Blacklist-MW |
| datenpanne, breach, meldepflicht | datenpanne | Art. 33, Art. 34, EDPB-Leitlinie |
| auftragsverarbeiter, av-vertrag | auftragsverarbeitung | Art. 28, Art. 29, AV-MW |
| gemeinsame verantwortlichkeit, fanpage | gemeinsam | Art. 26, Art. 4 Nr. 7, C-210/16, MW |
| künstliche intelligenz, ki-tool | ki | KI-MW, Art. 28, Art. 35, AI-Act-MW |
| chatgpt, openai, llm | chatgpt | KI-MW, ChatGPT-Leitlinie |
| vertrag, vertragserfüllung | vertrag | Art. 6(1)(b), EDPB-Leitlinie Vertrag |
| rechenschaftspflicht, accountability | rechenschaft | Art. 5(2), Art. 24, MW |

**Wichtig**: `definition`-Trigger wurde eingeschränkt — "was ist/sind/bedeutet" entfernt (Fix 3, 2026-04-10). Nur noch bei echten Definitionsfragen aktiv.

**Wichtig**: Breyer-Suche umgestellt von `("C-582/14", "urteil")` auf `("id:seg_eugh_c_582_14_tenor", None)` (Fix 1, 2026-04-10) — verhindert Matching auf andere Urteile die C-582/14 zitieren.

### Schritt 11 — Urteilsnamen-Suche (Z. 611–658)

Funktion `_find_urteil_by_name()`:

1. Prüft ob Kurzname (z.B. "Schrems II") in der Frage vorkommt
2. Quelle: `urteilsnamen.json` (138 Einträge)
3. Lädt alle Segmente des Urteils (max 30)
4. Segment-Priorität: tenor (0) > wuerdigung (1) > vorlagefragen (2) > sachverhalt (3)
5. Nimmt Top 3 Segmente
6. CE=10.0, distance=0.05, source="urteil_name"

### Schritt 12 — Dokument-Deduplizierung (Z. 908–921)

```python
MAX_PER_DOC = 3  # Max Chunks pro Dokument-Schlüssel
```

Gruppiert nach `_doc_key()` (Gericht+AZ oder Leitlinien-Titel). Entfernt Duplikate jenseits von 3.

### Schritt 13 — Dynamischer Cutoff + Min/Max (Z. 923–959)

**Cutoff**: Chunk wird aufgenommen wenn:
- CE-Score ≥ 3.0 **ODER** Distanz < 0.25

**Min/Max-Enforcement**:
- < 3 Dokumente → nächstbeste Kandidaten auffüllen
- > 15 Dokumente → nur Top 15 nach Score

### Schritt 14 — Source-Type-Diversifizierung (Z. 965–981)

Erzwingt mindestens je 1 Chunk aus:
- **gesetz**: `{gesetz_granular}`
- **urteil**: `{urteil, urteil_segmentiert}`
- **leitlinie**: `{leitlinie, methodenwissen}`

### Schritt 15 — Erwägungsgrund-Anreicherung (Z. 989–1043)

Funktion `_enrich_with_erwaegungsgruende()`:
- Scannt Ergebnisse nach DSGVO-Artikeln mit `erwaegungsgruende`-Metadaten
- Lädt zugehörige EG per ID `dsgvo_eg_{nr}`
- Max 2 EG, sortiert nach Nummer (niedrigste zuerst)
- CE=5.0, distance=0.10

---

## Phase 4: Generierung & Validierung

### Schritt 16 — Kontext-Aufbau, LLM, Validierung

#### Kontext-Formatierung (Z. 1218–1242)

Chunks werden als nummerierte Quellen formatiert:
```
[Quelle 1 – Typ: gesetz_granular – Art. 5 DSGVO]
Art. 5 DSGVO – Grundsätze für die Verarbeitung...

[Quelle 2 – Typ: urteil_segmentiert – EuGH C-311/18 (Schrems II)]
Tenor: Aus diesen Gründen hat der Gerichtshof...
```

Max 3000 Zeichen pro Chunk-Text.

#### System-Prompt (Z. 90–117)

Kernregeln für das LLM:

1. **Quellenbindung**: Jede Aussage muss mit `[Quelle X]` belegt werden
2. **Keine Erfindungen**: Keine Normen, AZ oder Rechtsgrundlagen erfinden
3. **Ehrlichkeit**: Bei fehlenden Quellen: "Diese Information ist in den vorliegenden Quellen nicht enthalten"
4. **Definitionsregel**: Bei DSGVO-Begriffen immer mit Art. 4 DSGVO Legaldefinition beginnen (26 Definitionen in 4 Gruppen)
5. **TDDDG-Regel**: Immer "TDDDG" statt "TTDSG" verwenden (Umbenennung 2024)
6. **§ 29 BDSG-Warnung**: § 29 BDSG-alt ist aufgehoben (25.05.2018), Nachfolger ist § 31 BDSG-neu
7. **Urteilsnamen**: Kurzname in Klammern: "EuGH C-311/18 (Schrems II)"
8. **EDPB-Quellen**: Offizieller deutscher Titel + Randnummer
9. **Gutachtenstil**: Prüfungsreihenfolge: Anwendbarkeit → personenbezogene Daten → Verantwortlicher → Rechtsgrundlage → Grundsätze → Rechte → Pflichten

#### LLM-Provider-Kaskade (Z. 1480–1557)

| Priorität | Provider | Modell(e) |
|-----------|----------|-----------|
| 1 | HuggingFace | Qwen/Qwen3-235B-A22B → Mixtral-8x7B |
| 2 | OpenRouter | qwen3-235b → llama-3.3-70b → gemma-3-27b → mistral-small-3.1-24b |
| 3 | Mistral API | Mistral Large |
| 4 | Ollama (lokal) | gemma4:12b → qwen2.5:14b |

Parameter: `max_tokens=2048`, `temperature=0.3`, `timeout=120s`

Fallback-Logik: Versucht Provider der Reihe nach. Beim ersten erfolgreichen Token wird festgelegt. Nur bei komplettem Fehler → nächster Provider.

#### Validierung (Z. 1565–1662)

Prüft alle Norm-/AZ-Referenzen in der Antwort:
- **✅ Verifiziert**: In Quellen UND ChromaDB
- **⚠️ Nur in DB**: In ChromaDB aber nicht in übergebenen Quellen
- **❌ Fehlend**: Nicht in ChromaDB → wahrscheinliche Halluzination

---

## Hilfsfunktionen

| Funktion | Zeile | Zweck |
|----------|-------|-------|
| `extract_norms()` | 230 | Regex-Extraktion von Normreferenzen |
| `extract_aktenzeichen()` | 235 | Regex-Extraktion von Aktenzeichen |
| `_extract_year()` | 244 | Jahres-Extraktion aus Metadaten |
| `_recency_factor()` | 255 | Recency-Multiplikator |
| `_is_outdated_chunk()` | 279 | Pre-DSGVO / obsolete Norm-Erkennung |
| `_find_pflicht_chunks()` | 562 | Themenbasierte Pflicht-Chunks |
| `_find_urteil_by_name()` | 611 | Urteilssuche nach Kurzname |
| `_enrich_with_erwaegungsgruende()` | 989 | Erwägungsgrund-Nachladen |
| `group_chunks_to_docs()` | 1179 | Chunks → Dokument-Gruppierung |
| `format_context()` | 1218 | Chunk-Formatierung für LLM |
| `_build_llm_messages()` | 1250 | System-Prompt + Nachrichten-Aufbau |
| `stream_with_fallback()` | 1521 | LLM-Cascade mit Provider-Fallback |
| `validate_response()` | 1565 | Norm/AZ-Validierung der Antwort |
