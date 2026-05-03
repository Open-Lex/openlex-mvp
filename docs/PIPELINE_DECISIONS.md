# OpenLex Pipeline Decisions

**Erstellt:** 2026-05-01  
**Zuletzt aktualisiert:** 2026-05-03  
**Auditor:** Pipeline-Audit via SSH + Trace-Run  
**Trace-Query:** „Was ist ein personenbezogenes Datum nach Art. 4 DSGVO?"  
**Trace-Datei:** `/tmp/doku_reference.json`  
**Branch:** `feature/inspector-trace-completion`  
**Paket-Stand:** Paket 1 + Patch 1.1 + Patch 1.1b  

---

## Überblick: 18 Stages in `trace_format="full"`

Der Trace liefert 18 explizite Stages im `full_trace.stages`-Array. Jede Stage hat:
- `id`, `label`, `kind` (`injector` / `filter` / `transformer`)
- `active` (bool) — ob die Stage in diesem Aufruf aktiv war
- `count_in`, `count_out`, `count_injected` oder `count_filtered` (wo zutreffend)
- `decisions` — Array mit chunk-level Entscheidungen (nur bei `trace_format="full"`)
- `flow_boundary` (nur Stage 1: `embedding`) — Query-Level-Stage, nicht Teil des Chunk-Flusses
- `flow_isolated` (nur Stage 13: `pflicht_urteilsname_injection`) — paralleler Fork, kein Continuity-Check

**Consistency-Check** (`full_trace.consistency`):  
`_validate_full_trace()` (app.py:1885) prüft `count_out[n] == count_in[n+1]` zwischen allen Stages, überspringt dabei `flow_boundary`- und `flow_isolated`-Stages. Bei `valid=true` und leeren `issues`/`warnings` ist der Trace konsistent.

---

## Stage 1: embedding

**Was passiert hier:**  
`model.encode([search_query])` erzeugt einen Dense-Vektor mit SentenceTransformer `mixedbread-ai/deepset-mxbai-embed-de-large-v1`. Das resultierende Embedding wird für alle nachgelagerten ChromaDB-Abfragen (Semantic, Norm-Lookup, Keyword) wiederverwendet. Das Modell läuft lokal, kein API-Call.

**Code-Stelle:** app.py:855–871

**kind:** `transformer` | `flow_boundary=True` (Query-Level-Stage, zählt nicht in Chunk-Continuity)

**count-Felder:** `count_in=1` (die Query), `count_out=1`

**decisions:** Keine (leeres Array) — das Embedding-Ergebnis wird nicht als Chunk-Entscheidung gelogged.

**Live-Trace-Werte:**
```json
{
  "id": "embedding",
  "flow_boundary": true,
  "label": "Query Embedding",
  "active": true,
  "duration_ms": 127.8,
  "model": "mixedbread-ai/deepset-mxbai-embed-de-large-v1",
  "input_text": "Was ist ein personenbezogenes Datum nach Art. 4 DSGVO?",
  "kind": "transformer",
  "count_in": 1,
  "count_out": 1,
  "decisions": []
}
```

**Verbleibende Lücken:**  
- Vektor-Dimension nicht im Trace  
- History-Augmentation-Flag fehlt (ob `search_query` mit History erweitert wurde)

---

## Stage 2: semantic

**Was passiert hier:**  
`col.query(query_embeddings, n_results=40)` — ein ChromaDB-Call über alle Source-Types. Pro Chunk wird `adjusted_distance = distance × SEGMENT_BOOST[segment|source_type]` berechnet (Methodenwissen: ×0.70, leitsatz: ×0.85, gesetz_granular: ×0.92, tenor/wuerdigung: ×0.92–0.95, tatbestand/sachverhalt: ×1.05). Ergebnis: Chunks mit `source="semantic"`.

**Code-Stelle:** app.py:919–933

**kind:** `injector` (fügt Chunks in den leeren Pool ein)

**count-Felder:** `count_in=0`, `count_injected=N`, `count_out=N`

**decisions in `trace_format="full"`:** Ja — ein Eintrag pro injiziertem Chunk.

**Decisions-Schema:**
```json
{
  "chunk_id": "mw_art4_index",
  "raw_distance": 0.1438,
  "segment_boost_factor": 0.7,
  "segment_boost_delta": -0.0431,
  "boosted_distance": 0.1006
}
```

**Live-Trace-Werte:** `count_in=0`, `count_out=39`, `count_injected=39`, `dec=39`

**Verbleibende Lücken:** Keine wesentlichen — `raw_distance`, `segment_boost_factor`, `boosted_distance` sind vollständig dokumentiert.

---

## Stage 3: norm_lookup_injection

**Was passiert hier:**  
Für bis zu 5 Normen, die `extract_norms(question)` aus der Query extrahiert (Regex `NORM_RE`): je ein ChromaDB-Query mit `where={"source_type": {"$in": ["gesetz_granular", "gesetz"]}}`, n_results=5. `adjusted_distance = dist × 0.85` (10% Boost). Bei aktiver Query — z.B. „Art. 4 DSGVO" — werden passende Gesetzs-Chunks injiziert. Bei keiner erkannten Norm ist `active=false` und `count_injected=0`.

**Code-Stelle:** app.py:935–964

**kind:** `injector`

**count-Felder:** `count_in` (Pool-Größe nach Semantic), `count_injected`, `count_out`

**decisions in `trace_format="full"`:** Ja — ein Eintrag pro injiziertem Chunk.

**Decisions-Schema:**
```json
{
  "chunk_id": "gran_BDSG_§_14_Abs.1_S.4",
  "action": "injected",
  "norm": "§ 14 Abs. 1 S. 4 BDSG"
}
```

**Live-Trace-Werte:** `count_in=39`, `count_out=44`, `count_injected=5`, `dec=5`

**Verbleibende Lücken:**  
- Welche Normen `extract_norms` aus der Query extrahiert hat, steht nicht separat im Trace  
- Synonym-Expansion (`_SYNONYM_MAP`) nicht sichtbar

---

## Stage 4: qu_injection

**Was passiert hier:**  
`_expand_qu_norms(question)` + `_qu_get_chroma_ids(norms)` — deterministisches Norm-zu-Chunk-ID-Mapping ohne Embedding-Roundtrip. Direkte `col.get(ids=[...])`. Chunks werden mit `adjusted_distance=0.15` und `source="qu_injection"` injiziert. Läuft immer, aber injiziert nur wenn das QU-Modul verfügbar ist und Normen gefunden werden. In diesem Trace: kein Treffer, `count_injected=0`.

**Code-Stelle:** app.py:977–1018

**kind:** `injector`

**count-Felder:** `count_in`, `count_injected`, `count_out`

**decisions in `trace_format="full"`:** Ja (wenn injected) — Schema analog norm_lookup_injection mit `source="qu_injection"`.

**Live-Trace-Werte:** `count_in=44`, `count_out=44`, `count_injected=0`, `dec=0`

```json
{
  "id": "qu_injection",
  "label": "QU-Injection",
  "kind": "injector",
  "active": true,
  "count_in": 44,
  "count_injected": 0,
  "count_out": 44,
  "decisions": []
}
```

**Verbleibende Lücken:**  
- Warum keine Injection stattfand (kein Modul? keine Normen? leere ID-Liste?) nicht explizit geloggt  
- `qu_module_available` Flag fehlt

---

## Stage 5: keyword_injection

**Was passiert hier:**  
Für jedes relevante Wort aus der Query (min. 5 Zeichen, inkl. Umlaut-Varianten und Synonym-Expansion via `_SYNONYM_MAP`, max 10 Keywords): `col.query(..., where_document={"$contains": word})`, n_results=5. **Bereits vorhandene** Chunks: `adjusted_distance *= 0.5` (starker Boost), `source="hybrid"`. Neue Chunks: `adjusted_distance=0.15×SEGMENT_BOOST`, `source="keyword"`. `count_boosted_existing` zählt Hybrid-Boosts separat.

**Code-Stelle:** app.py:1115–1162

**kind:** `injector`

**count-Felder:** `count_in`, `count_injected` (nur neue), `count_out`, `count_boosted_existing`

**decisions in `trace_format="full"`:** Ja — Einträge für alle neu injizierten und alle hybrid-geboosteten Chunks.

**Decisions-Schema (injected):**
```json
{
  "chunk_id": "beh_Juni_2020_-_LfDI_BW_-_Orientierungshilfe_171",
  "action": "injected",
  "source": "keyword"
}
```

**Live-Trace-Werte:** `count_in=44`, `count_out=45`, `count_injected=1`, `dec=9` (9 Entscheidungen: 1 injected + 8 boosted)

**Verbleibende Lücken:** Welche Keywords tatsächlich Treffer hatten, nicht einzeln gelistet.

---

## Stage 6: bm25_rrf

**Was passiert hier:**  
BM25-Suche mit Snowball-Stemmer + RRF-Fusion (Reciprocal Rank Fusion, k=60) über semantic, QU und BM25-Rankings. Fehlende BM25-Chunks werden via `col.get()` nachgeladen (`source="rrf_injected"`, distance=0.20). Nur aktiv wenn `OPENLEX_BM25_ENABLED=true` und BM25-Modul importierbar. In diesem Trace: **inaktiv** (`active=false`).

**Code-Stelle:** app.py:1201–1230

**kind:** `injector`

**count-Felder:** `count_in`, `count_injected`, `count_out`

**decisions in `trace_format="full"`:** Ja (wenn aktiv) — Einträge für `rrf_injected`-Chunks.

**Live-Trace-Werte:** `active=false`, `count_in=45`, `count_out=45`, `count_injected=0`, `dec=0`

**Verbleibende Lücken:** Da inaktiv kein Trace nötig. Wenn aktiv wären fehlend: BM25-Score pro Chunk, RRF-Score pro Chunk, Overlap BM25∩Semantic.

---

## Stage 7: per_source

**Was passiert hier:**  
Wenn `OPENLEX_PER_SOURCE_BUDGET_ACTIVE=true`: 5 separate ChromaDB-Calls je source_type ersetzen den Single-Call-Pool. Budget: gesetz_granular max 4, urteil_segmentiert max 2, leitlinie max 2, methodenwissen max 1, erwaegungsgrund max 1. Chunks sortiert nach Distance, dann Budget angewendet. Unbekannte Types immer genommen. Max 10 Chunks total. Das Embedding wird gecacht und wiederverwendet. Die Stage fungiert auch als Pre-CE-Slice (≤40 Kandidaten).

**Code-Stelle:** app.py:1325–1352

**kind:** `filter`

**count-Felder:** `count_in` (Pool nach bm25_rrf), `count_filtered` (durch Budget/Slice verworfen), `count_out`

**decisions in `trace_format="full"`:** Ja — `action="kept"` für alle Candidates, `action="filtered"/"beyond_top40"` für verworfene.

**Decisions-Schema:**
```json
{
  "chunk_id": "mw_art4_index",
  "action": "kept",
  "source_type": "methodenwissen",
  "source": "per_source",
  "adjusted_distance": 0.1006
}
```

**Live-Trace-Werte:** `count_in=45`, `count_out=10`, `count_filtered=35`, `dec=10`

**Verbleibende Lücken:**  
- Per-Typ-Counts (wie viele je source_type vor/nach Budget) nicht im Trace  
- Per-Source-Latenz (ms) nicht gelogged

---

## Stage 8: cross_encoder

**Was passiert hier:**  
`reranker.predict(pairs)` — alle Candidates als `(query, chunk_text[:500])` Paare in einem Batch. Modell: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (oder via `RERANKER_MODEL`). Scores im Bereich ca. −5 bis +5 (mmarco) oder ×10 für BGE-reranker (`_CE_SCORE_SCALE`). Keyword/Hybrid-Chunks erhalten Mindest-Score 3.0 (`floor`). Score wird in `chunk["ce_score"]` geschrieben (raw, vor Boosts).

**Code-Stelle:** app.py:1401–1455

**kind:** `transformer`

**count-Felder:** `count_in=N`, `count_out=N` (keine Filterung hier)

**decisions in `trace_format="full"`:** Ja — ein Eintrag pro Chunk.

**Decisions-Schema:**
```json
{
  "chunk_id": "mw_art4_index",
  "ce_score_raw": 0.8522,
  "rank_by_distance": 1
}
```

**Live-Trace-Werte:** `count_in=10`, `count_out=10`, `dec=10`

**Verbleibende Lücken:**  
- CE-Batch-Latenz (ms) nicht gelogged  
- Welches Reranker-Modell aktiv ist, steht zwar in `model`-Feld des Stage-Eintrags, aber nicht im Root-Response

---

## Stage 9: pre_dsgvo_filter

**Was passiert hier:**  
Entfernt veraltete Leitlinien (Datum < 2018) und Chunks mit aufgehobenen Normen (§ 29 BDSG-alt etc.) aus dem Candidate-Pool, wenn mindestens 3 aktuelle Chunks vorhanden sind. Andernfalls: `ce_score /= 3.0` als Penalty + `_pre_dsgvo=True`. In typischen DSGVO-Anfragen greift dieser Filter selten, daher häufig `active=false` und `count_filtered=0`.

**Code-Stelle:** app.py:1519–1528 (Stage-Eintrag), ~app.py:1480–1519 (Filter-Logik)

**kind:** `filter`

**count-Felder:** `count_in`, `count_filtered`, `count_out`

**decisions in `trace_format="full"`:** Ja (wenn gefiltert) — `{"chunk_id": ..., "filtered": true, "reason": "pre_dsgvo"}` für entfernte Chunks.

**Live-Trace-Werte:** `active=false`, `count_in=10`, `count_out=10`, `count_filtered=0`, `dec=0`

**Verbleibende Lücken:**  
- Welche Chunks als „pre_dsgvo" markiert wurden (penalty statt removal) nicht im Trace  
- Entscheidungsregel (≥3 aktuelle Chunks) nicht im Trace dokumentiert

---

## Stage 10: boosts

**Was passiert hier:**  
Drei Modifikatoren werden sequenziell auf `chunk["ce_score"]` angewendet und vollständig gelogged:  
**a) Aktualitäts-Boost/Penalty (Recency):** Jahr aus Metadaten extrahieren → `ce_score /= recency_factor` (≥2023: ÷0.70 = Boost; ≥2020: ÷0.85; ≥2018: ÷0.95; <2018: ÷1.10 = Penalty).  
**b) Schlüsselurteil-Boost:** Wenn Urteil in `urteilsnamen.json` → `ce_score *= 1.5`.  
**c) Instanzgerichts-Penalty:** Wenn Query kein Gericht/AZ nennt und Chunk von BSG/BFH/BAG/BVerwG/OLG/LG/VG/AG stammt: `ce_score /= 1.3`.  
Nach allen Boosts: Sortierung nach `ce_score` (+ SEGMENT_BOOST als Tie-Breaker).

**Code-Stelle:** app.py:1555–1581

**kind:** `transformer`

**count-Felder:** `count_in=N`, `count_out=N`

**decisions in `trace_format="full"`:** Ja — vollständiges Before/After/Delta pro Chunk.

**Decisions-Schema:**
```json
{
  "chunk_id": "seg_eugh_C-247_23_rechtsrahmen_1",
  "ce_score_before": 1.4742,
  "ce_score_after": 3.1591,
  "ce_score_delta": 1.6849,
  "boosts_applied": [
    {"name": "aktualitaet_recency", "factor": 1.4286},
    {"name": "schluesselurteil", "factor": 1.5}
  ]
}
```

**Live-Trace-Werte:** `count_in=10`, `count_out=10`, `dec=10`

**Verbleibende Lücken:**  
- Welches Jahr für Recency-Berechnung extrahiert wurde, nicht im Trace  
- Instanzgerichts-Penalty wird nicht im `boosts_applied`-Array erscheinen wenn es nicht angewendet wurde (korrekt), aber kein explizites `instanzgericht_checked=true`-Flag

---

## Stage 11: mw_priorization

**Was passiert hier:**  
MW-Chunks mit `ce_score > 4.0` (nach Boosts) werden an Positionen 1–3 gesetzt (max 3). Kein numerischer Multiplier, nur Umordnung. `active=false` wenn kein MW-Chunk den Schwellenwert überschreitet (typisch für viele Anfragen).

**Code-Stelle:** app.py:1586–1605

**kind:** `transformer`

**count-Felder:** `count_in=N`, `count_out=N`, `count_mw_promoted`

**decisions in `trace_format="full"`:** Ja (wenn aktiv) — `{"chunk_id": ..., "action": "promoted_to_front"}` für jeden promovierten MW-Chunk.

**Live-Trace-Werte:** `active=false`, `count_in=10`, `count_out=10`, `count_mw_promoted=0`, `dec=0`

**Verbleibende Lücken:** Keine wesentlichen — der Stage-Eintrag dokumentiert `count_mw_promoted` vollständig.

---

## Stage 12: dedup

**Was passiert hier:**  
Document-Level Deduplication: max 3 Chunks pro Dokument (`MAX_PER_DOC=3`). Dokument-Key via `_doc_key()`: AZ+Gericht (Urteile), Gesetz-Name, Titel, Thema. Überzählige Chunks werden entfernt. Der Stage-Eintrag enthält sowohl die gefilterten als auch die behaltenen Chunks in `decisions`.

**Code-Stelle:** app.py:1632–1668

**kind:** `filter`

**count-Felder:** `count_in`, `count_filtered`, `count_out`

**decisions in `trace_format="full"`:** Ja — alle Chunks mit `action="filtered"` oder `action="kept"`.

**Decisions-Schema (filtered):**
```json
{
  "chunk_id": "dsgvo_art_11",
  "action": "filtered",
  "reason": "dedup_max_per_doc",
  "doc_key": "DSGVO"
}
```

**Live-Trace-Werte:** `count_in=10`, `count_out=8`, `count_filtered=2`, `dec=10`

**Verbleibende Lücken:** Keine — vollständig dokumentiert mit `doc_key` und Reason.

---

## Stage 13: pflicht_urteilsname_injection

**Was passiert hier:**  
Paralleler Fork: `_find_pflicht_chunks(question, col)` und `_find_urteil_by_name(question, col)` laden Pflicht-Chunks und Urteilsname-Chunks direkt via `col.get()`. Diese bypassen den CE-Cutoff und werden direkt in `selected` eingefügt (ce_score=10.0 bei Urteilsnamen). `flow_isolated=True` bedeutet: die Continuity-Prüfung überspringt diese Stage — sie speist keinen fortlaufenden Chunk-Fluss, sondern einen parallelen Fork.

**Code-Stelle:** app.py:1676–1700

**kind:** `injector` | `flow_isolated=True`

**count-Felder:** `count_in=0`, `count_injected=N_pflicht`, `count_out=N_pflicht`

**decisions in `trace_format="full"`:** Ja (wenn injected) — `{"chunk_id": ..., "action": "injected", "source": ..., "bypass_ce": true}`.

**Live-Trace-Werte:** `active=false` (kein Pflicht/Urteilsname-Match), `count_in=0`, `count_out=0`, `count_injected=0`, `dec=0`

**Verbleibende Lücken:**  
- Welche Urteilsnamen aus `urteilsnamen.json` geprüft wurden, nicht im Trace  
- Warum kein Match stattfand, nicht explizit gelogged

---

## Stage 14: ce_cutoff

**Was passiert hier:**  
Filtert deduplizierte Candidates nach `ce_score >= CE_CUTOFF (3.0)` ODER `adjusted_distance < DIST_CUTOFF (0.25)`. Chunks die keines der Kriterien erfüllen werden verworfen. Pflicht-Chunks (aus Stage 13) sind immun — sie werden nicht in die `deduped`-Liste einbezogen, sondern separat in `selected` eingefügt. `ce_score_final` im Decisions-Eintrag ist der boosted Score (nach Stage 10), nicht raw.

**Code-Stelle:** app.py:1702–1726

**kind:** `filter`

**count-Felder:** `count_in` (deduped), `count_filtered`, `count_out`

**decisions in `trace_format="full"`:** Ja — `action="kept"` oder `action="filtered"` mit `ce_score_final` und `reason`.

**Decisions-Schema (kept):**
```json
{
  "chunk_id": "seg_eugh_C-247_23_rechtsrahmen_1",
  "action": "kept",
  "ce_score_final": 3.1591,
  "reason": "above_cutoff"
}
```

**Live-Trace-Werte:** `count_in=8`, `count_out=8`, `count_filtered=0`, `dec=8`

**Verbleibende Lücken:**  
- `dist_cutoff_threshold` und `ce_cutoff_threshold` stehen zwar im Stage-Eintrag als Extra-Felder, aber nicht in jedem Decision-Eintrag für Grenzfälle

---

## Stage 15: selected_merge

**Was passiert hier:**  
Kombiniert Pflicht-Chunks (aus Stage 13, `flow_isolated`) mit den CE-gefilterten Candidates (aus Stage 14) zu `selected`. Keine Filterung, reines Merge. `count_in` = CE-gefilterte Chunks, `count_injected` = Pflicht-Chunks, `count_out` = Summe. Dieser Stage-Eintrag stellt die Continuity nach dem parallelen Fork wieder her.

**Code-Stelle:** app.py:1727–1787

**kind:** `injector`

**count-Felder:** `count_in` (CE-passed), `count_injected` (Pflicht), `count_out`

**decisions in `trace_format="full"`:** Keine (leeres Array / kein `decisions`-Feld im Stage-Eintrag).

**Live-Trace-Werte:** `count_in=8`, `count_out=8`, `count_injected=0`, `dec=0`

**Verbleibende Lücken:** Keine — der Merge-Schritt ist durch die benachbarten Stages vollständig dokumentiert.

---

## Stage 16: min_max_diversification

**Was passiert hier:**  
Drei Regeln sequenziell:  
**a) Min-Docs-Auffüllung:** Wenn `len(docs) < MIN_DOCS (3)` → Nachladen aus Candidates bis Minimum erreicht.  
**b) Max-Docs-Limit:** Wenn `len(docs) > MAX_DOCS (8)` → niedrigst-scorende Dokumente entfernen.  
**c) Source-Type-Diversifizierung:** Prüft ob gesetz_granular, urteil/urteil_segmentiert, leitlinie/methodenwissen vertreten sind. Falls Gruppe fehlt → ein Chunk nachschieben.  
`kind` wird dynamisch gesetzt: `"injector"` wenn Chunks hinzugefügt, `"filter"` wenn entfernt, `"transformer"` wenn unverändert.

**Code-Stelle:** app.py:1788–1808

**kind:** `filter` / `injector` / `transformer` (dynamisch)

**count-Felder:** `count_in` (post selected_merge), `count_injected`, `count_filtered`, `count_out`, `min_docs`, `max_docs`

**decisions in `trace_format="full"`:** Keine (leeres `decisions`-Array in dieser Implementierung).

**Live-Trace-Werte:** `count_in=8`, `count_out=6`, `count_filtered=2`, `min_docs=3`, `max_docs=8`, `dec=0`

**Verbleibende Lücken:**  
- Welche Chunks konkret durch Max-Docs entfernt wurden, nicht in `decisions` gelistet  
- Ob Diversifizierung nachgeladen hat und welcher Chunk, nicht gelogged

---

## Stage 17: eg_enrichment

**Was passiert hier:**  
Für jeden DSGVO-Artikel in den selektierten Chunks: Metadaten-Feld `erwaegungsgruende` (kommagetrennte EG-Nummern) auslesen. Direkte `col.get(ids=[f"dsgvo_eg_{nr}"])` — kein Embedding. Max 2 EGs pro Anfrage. `source="eg_enrichment"`, `distance=0.10`, `ce_score=5.0` (fest). EG-Chunks die bereits im Pool sind werden nicht doppelt eingefügt.

**Code-Stelle:** app.py:1809–1832

**kind:** `injector`

**count-Felder:** `count_in`, `count_injected`, `count_out`

**decisions in `trace_format="full"`:** Ja (wenn injected) — `{"chunk_id": ..., "source": "eg_enrichment"}`.

**Decisions-Schema:**
```json
{
  "chunk_id": "",
  "source": "eg_enrichment"
}
```

**Live-Trace-Werte:** `count_in=6`, `count_out=8`, `count_injected=2`, `dec=2`

**Verbleibende Lücken:**  
- `chunk_id` im Decision-Eintrag ist leer wenn die EG-ID nicht im `id`-Feld des Chunks gesetzt ist — bekannte Gap  
- Welche EG-Nummern aus den Artikel-Metadaten extrahiert wurden, nicht im Trace

---

## Stage 18: tenor_enforce

**Was passiert hier:**  
Feature-Flag: `OPENLEX_TENOR_ENFORCE=true` (Standard). Für jedes `urteil_segmentiert`-Chunk in `selected`: AZ sammeln, prüfen ob Tenor/Leitsatz bereits vorhanden. Falls nicht: `col.get(where={"$and": [{"aktenzeichen": az}, {"segment": "leitsatz"}]})` → dann "tenor" → dann "entscheidungsgruende" (Fallback). Max 3 Injektions-Slots. Injizierte Chunks: `ce_score = best_score × 0.90` (leitsatz/tenor) oder `× 0.80` (Fallback). Misses werden in `tenor_enforce_misses.jsonl` gelogged.

**Code-Stelle:** app.py:1832–1865 (Stage-Eintrag), app.py:1427–1545 (`_ensure_tenor_chunks`)

**kind:** `injector`

**count-Felder:** `count_in`, `count_injected`, `count_out`

**decisions in `trace_format="full"`:** Ja — `action="injected"` / `action="already_present"` / `action="miss"` pro AZ.

**Decisions-Schema (injected):**
```json
{
  "action": "injected",
  "az": "C-247/23",
  "chunk_id": "seg_eugh_C-247_23_tenor",
  "segment": "tenor"
}
```

**Live-Trace-Werte:** `count_in=8`, `count_out=10`, `count_injected=2`, `dec=2`

**Verbleibende Lücken:**  
- Welche Segmente für ein `miss`-AZ versucht wurden, fehlt im Decision-Eintrag  
- `available_segments` aus Tenor-Miss-Log nur im JSONL, nicht im API-Response

---

## Stages außerhalb des `full_trace.stages`-Arrays

### Query-Rewrite (vor Stage 1)

Wenn `OPENLEX_REWRITE_ENABLED=true`: Mistral-Medium-Call zur juristischen Umformulierung. Im Response-Root als `rewrite`-Objekt dokumentiert.

**Live-Trace-Werte:**
```json
{
  "rewrite": {
    "used": false,
    "original": "Was ist ein personenbezogenes Datum nach Art. 4 DSGVO?",
    "rewritten": "Was ist ein personenbezogenes Datum nach Art. 4 DSGVO?",
    "from_cache": false,
    "error": null,
    "duration_ms": 0.0
  }
}
```

**Verbleibende Lücken (wenn aktiv):** `guard_triggered`-Flag (welcher Guard hat ausgelöst), `cache_key`.

### LLM-Generierung (nach Stage 18)

Der `/api/inspect`-Endpoint ruft nur `retrieve()` auf, nicht `chat_stream()`. Die LLM-Stage (Mistral/OpenRouter/Ollama-Cascading, Streaming, Quellen-Attribution via `validate_response()`) ist bewusst nicht Teil des Trace. Geplant für Paket 3.

---

## Consistency-Validator

`_validate_full_trace()` (app.py:1885–1930) prüft nach dem Aufbau aller 18 Stages:

1. `count_out[n] == count_in[n+1]` für alle benachbarten Stages
2. Überspringt Übergänge bei `flow_boundary=True` (Stage 1: embedding)
3. Überspringt Übergänge bei `flow_isolated=True` (Stage 13: pflicht_urteilsname_injection) und deren Vorgänger

Ergebnis in `full_trace.consistency`:
```json
{
  "valid": true,
  "issues": [],
  "warnings": []
}
```

Bei `valid=false` mit `issues` → Dokumentation darf nicht aktualisiert werden (STOP-Bedingung).

---

## Summary-Tabelle: Alle 18 Stages

| # | Stage ID | Label | kind | active | flow flags | decisions in full trace | verbleibende Lücken |
|---|----------|-------|------|--------|------------|------------------------|---------------------|
| 1 | `embedding` | Query Embedding | transformer | true | flow_boundary | Nein (kein chunk-level) | vektor-dim, history_augmented |
| 2 | `semantic` | Semantic Top-40 | injector | true | — | Ja (raw_distance, boost, boosted_distance) | — |
| 3 | `norm_lookup_injection` | Norm-Lookup Injection | injector | true (wenn Normen) | — | Ja (chunk_id, action, norm) | extracted_norms nicht separiert |
| 4 | `qu_injection` | QU-Injection | injector | true | — | Ja (wenn injected) | qu_module_available, warum kein match |
| 5 | `keyword_injection` | Keyword-Injection | injector | true | — | Ja (injected + boosted) | welche Keywords Treffer hatten |
| 6 | `bm25_rrf` | BM25 + RRF Fusion | injector | false | — | Ja (wenn aktiv) | bm25_score, rrf_score wenn aktiv |
| 7 | `per_source` | Per-Source Budget | filter | true | — | Ja (kept + filtered/beyond_top40) | per-typ budget counts |
| 8 | `cross_encoder` | Cross-Encoder | transformer | true | — | Ja (ce_score_raw, rank_by_distance) | ce_batch_latency |
| 9 | `pre_dsgvo_filter` | Pre-DSGVO Filter | filter | false | — | Ja (wenn filtered) | penalty vs. removal nicht unterschieden |
| 10 | `boosts` | Boosts & Penalties | transformer | true | — | Ja (before/after/delta/boosts_applied) | year_extracted |
| 11 | `mw_priorization` | MW-Priorisierung | transformer | false | — | Ja (wenn aktiv) | — |
| 12 | `dedup` | Doc-Dedup (max 3/Dokument) | filter | true | — | Ja (filtered+kept mit doc_key) | — |
| 13 | `pflicht_urteilsname_injection` | Pflicht + Urteilsname Injection | injector | false | flow_isolated | Ja (wenn injected) | warum kein match |
| 14 | `ce_cutoff` | CE-Cutoff Filter | filter | true | — | Ja (kept+filtered mit ce_score_final) | — |
| 15 | `selected_merge` | Selected-Merge (Pflicht + CE-Passed) | injector | true | — | Nein (kein decisions-Array) | — |
| 16 | `min_max_diversification` | Min-Docs / Max-Docs / Diversification | filter/injector/transformer | true | — | Nein | welche Chunks entfernt/hinzugefügt |
| 17 | `eg_enrichment` | EG-Enrichment | injector | true | — | Ja (chunk_id, source) | chunk_id leer-Bug, welche EG-Nummern |
| 18 | `tenor_enforce` | Tenor-Enforce | injector | true | — | Ja (injected/already_present/miss) | tried_segments bei miss |

---

## Offene Lücken (Stand 2026-05-03)

### Geschlossen durch Paket 1 + Patch 1.1 + 1.1b (12 von 14 originalen Gaps)

- `ce_score_final` nach Boosts → jetzt vollständig in Stage `boosts` (ce_score_before/after/delta) und in `ce_cutoff` decisions
- `adjusted_distance` pro Chunk → jetzt in Stage `per_source` decisions
- `extracted_norms` / `extracted_az` → teilweise sichtbar via Stage `norm_lookup_injection` decisions (norm-Feld)
- `per_source_budget_counts` → Stage `per_source` existiert jetzt explizit
- `embedding_duration_ms` + `model` → in Stage `embedding` vollständig
- EG-Enrichment-Trace → Stage `eg_enrichment` mit decisions
- QU-Injection-Trace → Stage `qu_injection` explizit
- Norm-Lookup-Trace → Stage `norm_lookup_injection` explizit
- Doc-Dedup-Trace → Stage `dedup` explizit mit doc_key
- CE-Cutoff-Trace → Stage `ce_cutoff` explizit mit ce_score_final
- Pflicht/Urteilsname-Fork → Stage `pflicht_urteilsname_injection` mit `flow_isolated`
- Consistency-Validator → `full_trace.consistency` mit `valid`, `issues`, `warnings`

### Verbleibende Lücken (Stand 2026-05-03)

1. **LLM-Stage** (Generierung, Streaming, Quellen-Attribution) — geplant Paket 3
2. **eg_enrichment chunk_id leer**: Wenn `c.get("id")` und `c.get("meta", {}).get("chunk_id", "")` beide leer sind, wird leerer String im Decision-Eintrag gesetzt. Fix: EG-Chunks beim Laden mit `id` aus der ChromaDB-ID belegen.
3. **min_max_diversification decisions**: Kein `decisions`-Array — es ist nicht nachvollziehbar welche Chunks konkret entfernt oder nachgeschoben wurden.
4. **year_extracted im boosts-Trace**: Welches Jahr `_extract_year()` für den Recency-Faktor verwendet hat, fehlt im `boosts_applied`-Array.
5. **qu_module_available / warum QU kein Match**: Stage `qu_injection` liefert zwar count=0, aber nicht ob das Modul fehlt oder die Normen-Extraktion leer war.
6. **tried_segments bei tenor_enforce miss**: Im `decisions`-Eintrag `action="miss"` fehlt welche Segmente versucht wurden (nur im JSONL-Log).
7. **per_source per-typ budget counts**: Wie viele Chunks je source_type vor und nach Budget-Anwendung vorhanden waren, ist nicht im Trace.

---

## Audit-Historie

### 2026-04-30/05-01 — Initial-Audit

Erster Trace-Audit via SSH + `return_trace=True` (altes Format). Query: „Wie hat der EuGH zu IP-Adressen entschieden?" 14 Lücken identifiziert. Dokument mit 18 funktionalen Stages (ohne explizite Stage-IDs) erstellt.

Hauptbefunde:
- Keine expliziten Stage-Objekte mit ID/kind/count
- `ce_score_final` nur als `ce_score` in Chunk-Metadaten, nicht trace-explizit
- Norm-Lookup, QU-Injection, Keyword-Injection nur als Seiteneffekte sichtbar
- EG-Enrichment, Dedup, CE-Cutoff nicht als Trace-Stages dokumentiert
- Kein Consistency-Validator

### 2026-05-02 — Paket 1: trace_format="full"

Implementierung des `trace_format="full"` Modus: `full_trace["stages"]`-Array mit expliziten Stage-Objekten für alle aktiven Stages. Commit: `a04a03f feat(trace): implement trace_format="full" – per-stage decisions for all active stages`.

Neu hinzugefügt:
- Stages `embedding`, `semantic`, `per_source`, `cross_encoder`, `boosts`, `eg_enrichment`, `tenor_enforce`
- Per-Chunk `decisions`-Arrays mit chunk-level Entscheidungsfeldern
- `count_in`/`count_out`/`count_injected`/`count_filtered` Felder

### 2026-05-03 — Patch 1.1 + 1.1b

Patch 1.1: 8 neue explizite Stages für bisher implizite Pipeline-Schritte. Patch 1.1b: 3 Flow-Gap-Fixes im Consistency-Validator.

Commit 1: `a04a03f` — trace_format=full Basisimplementierung  
Commit 2: `eb79467 feat(trace): Patch 1.1b — fix 3 flow-gap issues in consistency validator`

Neu hinzugefügt:
- Stages `norm_lookup_injection`, `qu_injection`, `keyword_injection` (Injektions-Pfade)
- Stages `pre_dsgvo_filter`, `dedup` (Filter-Schritte)
- Stages `pflicht_urteilsname_injection` (mit `flow_isolated=True`), `ce_cutoff`, `selected_merge`
- Stage `min_max_diversification` (Min/Max/Diversifizierung als expliziter Block)
- Stage `mw_priorization` (bisher undokumentiert)
- Consistency-Validator `_validate_full_trace()` mit `flow_boundary`/`flow_isolated`-Semantik
- `full_trace.consistency`: `{valid, issues, warnings}`

Ergebnis: 18 explizite Stages, `consistency.valid=true`, 12 von 14 ursprünglichen Lücken geschlossen.

### Offene Lücken (Stand 2026-05-03)

- LLM-Stage (Generierung, Streaming, Quellen-Attribution) — geplant Paket 3
- `eg_enrichment` chunk_id leer-Bug — kleiner Fix in `_enrich_with_erwaegungsgruende`
- `min_max_diversification` ohne `decisions`-Array
- `year_extracted` im boosts-Trace fehlt
- `qu_module_available` / Gründe für QU-Nicht-Match fehlen
- `tried_segments` bei `tenor_enforce miss` fehlt
- Per-source per-typ budget counts fehlen
