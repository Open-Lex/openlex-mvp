# OpenLex Pipeline Decisions

**Erstellt:** 2026-05-01  
**Auditor:** Pipeline-Audit via SSH + Trace-Run  
**Trace-Query:** „Wie hat der EuGH zu IP-Adressen entschieden?" (chunk_search: C-507/23)  
**Trace-Datei:** `/tmp/audit_trace.json`  
**Gesamtdauer Trace:** 9591 ms  

---

## Stage 1: Query-Eingang & Intent-Analyse / Klärungsfrage

**Was passiert hier (Funktional):**  
Die User-Query wird entgegengenommen. Eine explizite Intent-Analyse oder Klärungsfrage-Logik existiert **nicht** als eigenständige Stage im Code. Der System-Prompt enthält die Anweisung „Wenn die Frage zu unspezifisch ist, stelle maximal 3 gezielte Rückfragen" — das delegiert die Klärungsfrage an das LLM, nicht an die Retrieval-Pipeline. Die Query wird direkt an retrieve() übergeben.

**Quell-Code-Stelle:**  
app.py:2460–2464 (`chat_stream`), app.py:781–783 (`retrieve` Signatur), app.py:142–174 (SYSTEM_PROMPT)

**Eingabe:**  
Roher User-Text (str), optionale History (list[list[str]])

**Ausgabe:**  
Query-String (unverändert, bis Rewrite greift), history wird für Folgefragen-Erkennung genutzt

**Entscheidungen pro Chunk:**  
Keine — diese Stage erzeugt noch keine Chunks.

**Heute im Trace sichtbar (return_trace=True, trace_format=rich):**  
`query: "Wie hat der EuGH zu IP-Adressen entschieden?"` — die rohe Query ist im JSON-Root sichtbar.

**Heute im Trace NICHT sichtbar:**  
- Keine Intent-Kategorie (z.B. „Rechtsprechungsfrage", „Definitionsfrage")  
- Keine Klärungsfrage-Entscheidung (wird das LLM triggern oder nicht?)  
- Kein History-Kontext-Merge-Flag (ob search_query = question oder = history+question)

**Konsequenz für den Inspector:**  
NEIN — Intent-Analyse und Klärungsfrage-Weg sind nicht traceable. Fehlend: `intent_type`, `clarification_needed`, `search_query_augmented`

---

## Stage 2: Query-Rewrite (deaktiviert)

**Was passiert hier (Funktional):**  
Wenn `OPENLEX_REWRITE_ENABLED=true`, wird die Query via Mistral Medium (`mistral-medium-latest`) in juristische Fachsprache umgeschrieben. Nutzt SQLite-Cache (`/opt/openlex-mvp/cache/rewrite_cache.sqlite`). Drei Guards verhindern Halluzinationen: Aktenzeichen-Guard (C-/T-Muster), Gerichts-Guard (EuGH etc.), Eigenname-Guard. Bei ungültigem Rewrite Fallback auf Originalquery. Temperature=0.0, max_tokens=80.

**Quell-Code-Stelle:**  
app.py:795–820 (Rewrite-Block in `retrieve`), query_rewriter.py:1–309

**Eingabe:**  
Original-Query (str)

**Ausgabe:**  
RewriteResult(original, rewritten, from_cache, duration_ms, error)

**Entscheidungen pro Chunk:**  
Keine — beeinflusst aber alle nachfolgenden Embedding-Berechnungen.

**Heute im Trace sichtbar:**  
```json
"rewrite": {
  "used": false, "original": "...", "rewritten": "...",
  "from_cache": false, "error": null, "duration_ms": 0.0
}
```
Vollständig dokumentiert, da `used=false` → kein echter Aufruf.

**Heute im Trace NICHT sichtbar:**  
- Bei `used=true`: kein `cache_hit_key`, keine `guard_triggered` Flags, kein Mistral-Latenz-Aufschlüsselung

**Konsequenz für den Inspector:**  
NEIN für aktiven Fall — fehlend wenn aktiv: `guard_triggered` (welcher Guard hat ausgelöst), `cache_key`

---

## Stage 3: Norm-Validator (Regex / QU-Klassifikation)

**Was passiert hier (Funktional):**  
Zwei separate Extraktionen laufen **vor** dem Embedding:  
1. `extract_norms(question)` — Regex `NORM_RE` extrahiert Normreferenzen (Art. X DSGVO, § X BDSG etc.)  
2. `extract_aktenzeichen(question)` — Regex `AZ_RE` extrahiert EuGH/BGH-Aktenzeichen  
Diese werden für Norm-Lookup (Stage 5b) und Keyword-Suche (Stage 7) genutzt. Die Validierung der **Antwort** (nach LLM) ist davon getrennt (validate_response).

**Quell-Code-Stelle:**  
app.py:305–312 (`extract_norms`, `extract_aktenzeichen`), app.py:870 (Norm-Lookup Schleife), app.py:180–201 (NORM_RE, AZ_RE)

**Eingabe:**  
Query-String

**Ausgabe:**  
list[str] Normen (max 5 für Lookup), list[str] Aktenzeichen (für Keyword-Boost)

**Entscheidungen pro Chunk:**  
Keine direkt — Ergebnis bestimmt welche Norm-Lookup-Queries abgesetzt werden.

**Heute im Trace sichtbar:**  
Nur indirekt: Chunks mit `source=norm_lookup` zeigen ob Norm-Extraktion etwas gefunden hat. Im Trace dieser Query: `norm_lookup: count_out=None` (weil Per-Source aktiv, intern).

**Heute im Trace NICHT sichtbar:**  
- Welche Normen/AZ extrahiert wurden  
- Anzahl der extrahierten Normen  
- Welche Synonyme aus `_SYNONYM_MAP` expandiert wurden

**Konsequenz für den Inspector:**  
NEIN — fehlend: `extracted_norms: ["..."]`, `extracted_az: ["..."]`, `synonym_expansion: ["..."]`

---

## Stage 4: Norm-Hypothesizer

**Was passiert hier (Funktional):**  
`_expand_qu_norms(question)` und `_qu_get_chroma_ids(norms)` aus `query_understanding.py` führen eine deterministischen Norm-zu-Chunk-ID-Mapping durch (kein Embedding). Gibt bekannte ChromaDB-IDs für Normen zurück. Wird als „QU Injection" (Stage 8) in die Pipeline eingespeist. Derzeit in diesem Trace **nicht aktiv** (qu_injection count=0).

**Quell-Code-Stelle:**  
app.py:39–48 (Import-Versuch), app.py:899–922 (QU-Injection Block)

**Eingabe:**  
Query-String → norm-Liste → ChromaDB-IDs

**Ausgabe:**  
list[str] Chunk-IDs (direkt per `col.get()` ladbar)

**Entscheidungen pro Chunk:**  
Chunk erhält `adjusted_distance=0.15`, `source="qu_injection"` — qualifiziert sich für Top-40.

**Heute im Trace sichtbar:**  
`qu_injection: active=false, detail="intern"` in pipeline_stages.

**Heute im Trace NICHT sichtbar:**  
- Welche Normen `_expand_qu_norms` zurückgab  
- Warum QU nicht aktiv ist (module fehlt? keine Normen? leere ID-Liste?)  
- Mapping: Norm → Chunk-ID

**Konsequenz für den Inspector:**  
NEIN — fehlend: `qu_norms_expanded`, `qu_ids_injected`, `qu_module_available`

---

## Stage 5: Query-Embedding

**Was passiert hier (Funktional):**  
`model.encode([search_query])` erzeugt einen Dense-Vektor via SentenceTransformer `mixedbread-ai/deepset-mxbai-embed-de-large-v1`. Das Embedding wird für die Semantic-Suche (40 Ergebnisse) und alle Keyword-Suchen (`where_document` + `query_embeddings`) wiederverwendet. Bei Per-Source: das vorberechnete Embedding wird gecacht und als lambda an `per_source_query()` übergeben.

**Quell-Code-Stelle:**  
app.py:822–833 (Embedding-Berechnung), app.py:1092–1094 (Per-Source Embedding-Cache), per_source_retrieval.py:107–114

**Eingabe:**  
search_query (str, ggf. mit History-Augmentation)

**Ausgabe:**  
list[list[float]] — 1D-Liste mit Vektordimension des Modells

**Entscheidungen pro Chunk:**  
Kein direkter Effekt — Embedding bestimmt Ähnlichkeitsranking in ChromaDB.

**Heute im Trace sichtbar:**  
Nicht sichtbar. Embedding wird nirgends im Trace ausgegeben.

**Heute im Trace NICHT sichtbar:**  
- Embedding-Berechnung-Dauer (ms)  
- Modell-Name  
- Vektor-Dimension  
- History-Augmentation-Flag (wurde search_query erweitert?)

**Konsequenz für den Inspector:**  
NEIN — fehlend: `embedding_model`, `embedding_duration_ms`, `search_query_used`, `history_augmented`

---

## Stage 6: Semantic Top-K aus ChromaDB

**Was passiert hier (Funktional):**  
`col.query(query_embeddings, n_results=40)` — ein einziger ChromaDB-Call über alle Source-Types. Liefert 40 Chunks sortiert nach Kosinus-Distanz. Anschließend wird pro Chunk `adjusted_distance = distance * SEGMENT_BOOST[segment/source_type]` berechnet. Methodenwissen: ×0.70, leitsatz: ×0.85, gesetz_granular: ×0.92, tenor/wuerdigung: ×0.92–0.95, tatbestand/sachverhalt: ×1.05.

**Quell-Code-Stelle:**  
app.py:835–867 (Semantic-Suche Block), app.py:215–225 (SEGMENT_BOOST Tabelle)

**Eingabe:**  
query_embeddings (40-Call), n_results=40

**Ausgabe:**  
list[dict] mit text, meta, distance, adjusted_distance, source="semantic"

**Entscheidungen pro Chunk:**  
`adjusted_distance = distance × SEGMENT_BOOST` — bestimmt Position im Pre-CE-Sort.

**Heute im Trace sichtbar:**  
Nur indirekt wenn Per-Source **deaktiviert**. Mit Per-Source aktiv: `semantic: count_out=None, detail="ChromaDB top-40 → intern von Per-Source genutzt"`.

**Heute im Trace NICHT sichtbar:**  
- Rohe distance-Werte vor Boost  
- adjusted_distance nach Boost  
- Welcher SEGMENT_BOOST angewendet wurde  
- Anzahl tatsächlich zurückgegebener Chunks (n_results vs tatsächlich)

**Konsequenz für den Inspector:**  
NEIN (bei Per-Source aktiv) — fehlend: `raw_distances`, `segment_boost_applied`, `adjusted_distances`

---

## Stage 7: Per-Source-Retrieval mit Type-Budget

**Was passiert hier (Funktional):**  
`OPENLEX_PER_SOURCE_BUDGET_ACTIVE=true` → ersetzt den Single-Call durch 5 separate ChromaDB-Calls (je source_type). Budget: gesetz_granular max 4, urteil_segmentiert max 2, leitlinie max 2, methodenwissen max 1, erwaegungsgrund max 1. Alle Chunks werden nach Distance sortiert, dann Budget angewendet. Max 10 Chunks total. Das Single-Call-Embedding wird gecacht und wiederverwendet.

Shadow-Modus (`OPENLEX_PER_SOURCE_RETRIEVAL_ENABLED=true`, Budget inaktiv): läuft parallel, schreibt Telemetrie via `per_source_telemetry.log_per_source()`, Single-Call-Ergebnis bleibt aktiv.

**Quell-Code-Stelle:**  
app.py:1078–1175 (Per-Source Block), per_source_retrieval.py:82–219

**Eingabe:**  
query_text, embed_fn (gecachtes Embedding), DEFAULT_TOP_K={gesetz_granular:6, urteil_segmentiert:6, leitlinie:6, erwaegungsgrund:4, methodenwissen:4}

**Ausgabe:**  
list[dict] mit chunk_id, distance, source_type, metadata, document (max 10 nach Budget)

**Entscheidungen pro Chunk:**  
Budget `(min, max)` pro Typ — Chunk wird akzeptiert wenn `counts[type] < max`. Unbekannte Types immer genommen.

**Heute im Trace sichtbar:**  
`per_source: active=true, count_out=10, detail="10 Chunks nach Typ-Budget (ersetzt Single-Call)"`. Pro Chunk: `sources=["per_source"]`.

**Heute im Trace NICHT sichtbar:**  
- Wie viele Chunks **jeder Typ** vor Budget-Anwendung hatte  
- Welches Budget pro Typ angewendet wurde  
- Overlap-Wert zwischen Single-Call und Per-Source (wird nur in Telemetrie geloggt)  
- Per-Source-Dauer (ms)  
- Welche Chunks durch Budget abgeschnitten wurden

**Konsequenz für den Inspector:**  
TEILWEISE — fehlend: `per_source_budget_counts`, `per_source_overlap`, `per_source_duration_ms`

---

## Stage 8: QU-Injection

**Was passiert hier (Funktional):**  
`query_understanding.expand_query_to_norms(question)` → Norm-Namen → `get_chroma_ids_for_norms(norms)` → direkte `col.get(ids=[...])`. Kein Embedding-Roundtrip. Chunks werden mit `adjusted_distance=0.15` und `source="qu_injection"` in den Pool eingespeist. Soft-Injection: Cross-Encoder entscheidet final. Abhängig davon ob `query_understanding` importierbar ist.

**Quell-Code-Stelle:**  
app.py:899–922 (QU-Injection Block), app.py:39–48 (Import-Block)

**Eingabe:**  
Query-String → Norm-Mapping → ChromaDB-IDs

**Ausgabe:**  
Chunks mit source="qu_injection", adjusted_distance=0.15

**Entscheidungen pro Chunk:**  
Feste adjusted_distance=0.15 → landet in Top-40 vor CE.

**Heute im Trace sichtbar:**  
`qu_injection: active=false, detail="intern"` — keine QU-Chunks in diesem Trace.

**Heute im Trace NICHT sichtbar:**  
- Ob `query_understanding` Modul verfügbar ist  
- Welche Normen erkannt wurden  
- Warum keine Injection stattfand (kein Modul? Keine Normen? Leere ID-Liste?)

**Konsequenz für den Inspector:**  
NEIN — fehlend: `qu_module_available`, `qu_norms_found`, `qu_ids_count`

---

## Stage 9: Norm-Lookup-Injection + Urteilsname-Pfad

**Was passiert hier (Funktional):**  
**9a) Norm-Lookup:** Für bis zu 5 extrahierte Normen aus der Query: separater `col.query()` mit `where={"source_type": {"$in": ["gesetz_granular", "gesetz"]}}`, n_results=5. Ergebnisse mit `adjusted_distance = dist * 0.85` (10% Boost gegenüber raw).

**9b) Urteilsname-Pfad:** `_find_urteil_by_name(question, col)` — durchsucht `urteilsnamen.json` (lazy geladen). Wenn ein Kurzname (z.B. „Breyer", „Schrems II") in der Query gefunden wird: `col.get(where={"aktenzeichen": az})` lädt bis zu 30 Chunks, sortiert nach Segment-Priorität (tenor→wuerdigung→sachverhalt), max 3 Chunks. Source: `"urteil_name"`, ce_score=10.0 (Pflicht).

**Quell-Code-Stelle:**  
app.py:869–897 (Norm-Lookup), app.py:717–764 (`_find_urteil_by_name`), app.py:1310–1318 (Urteilsname-Merge in Pflicht-Slots)

**Eingabe:**  
Extrahierte Normen (list[str]), Query-String vs. urteilsnamen.json

**Ausgabe:**  
Norm-Lookup: Chunks source="norm_lookup", adjusted_distance=dist*0.85  
Urteilsname: Chunks source="urteil_name", ce_score=10.0

**Entscheidungen pro Chunk:**  
Norm-Lookup: 10% Distance-Boost. Urteilsname: feste ce_score=10.0 → immer in finale Auswahl.

**Heute im Trace sichtbar:**  
`norm_lookup: active=true, detail="intern (vor Per-Source)"` — aber count_in/count_out=None weil Per-Source aktiv. Keine Chunks mit source="norm_lookup" oder "urteil_name" in diesem Trace.

**Heute im Trace NICHT sichtbar:**  
- Welche Normen für Norm-Lookup verwendet wurden  
- Ob Urteilsname-Match stattfand (welcher Name gematcht)  
- Anzahl injizierter Norm-Chunks  
- Urteilsnamen-Datei-Status (geladen? Anzahl Einträge?)

**Konsequenz für den Inspector:**  
NEIN — fehlend: `norm_lookup_queries`, `urteilsname_matched`, `urteilsname_chunks_injected`

---

## Stage 10: BM25 + RRF (deaktiviert)

**Was passiert hier (Funktional):**  
Wenn `OPENLEX_BM25_ENABLED=true` und `bm25_index.retrieve` importierbar: BM25-Suche mit Snowball-Stemmer, persistierter Index, k=40 Treffer. Anschließend RRF-Fusion (`rrf_fuse(rankings, k=60)`) über semantic_ids + qu_ids + bm25_ids. Fehlende BM25-Chunks werden via `col.get()` nachgeladen (source="rrf_injected"). Sortierung nach RRF-Score, Top-80 für CE. Bei Fehler: Fallback auf Distance-Sort.

**Quell-Code-Stelle:**  
app.py:50–65 (Feature-Flags + Import), app.py:924–934 (BM25-Retrieval), app.py:1014–1063 (RRF-Fusion Block)

**Eingabe:**  
Query-String → BM25-Index, semantic_ids + qu_ids

**Ausgabe:**  
Fusionierte, RRF-sortierte Chunk-Liste (max 80)

**Entscheidungen pro Chunk:**  
RRF-Score = 1/(k+rank_i) für jedes Ranking-Signal. Chunks nur aus BM25: source="rrf_injected", distance=0.20.

**Heute im Trace sichtbar:**  
`bm25_rrf: active=false, detail="Deaktiviert"` in pipeline_stages.

**Heute im Trace NICHT sichtbar:**  
Da deaktiviert: alle BM25-internen Metriken. Wenn aktiv wären fehlend: BM25-Score pro Chunk, RRF-Score pro Chunk, Overlap BM25∩Semantic.

**Konsequenz für den Inspector:**  
NEIN (deaktiviert, kein Trace nötig) — wenn aktiviert fehlend: `bm25_score`, `rrf_score`, `bm25_rank`

---

## Stage 11: Pre-CE Filter

**Was passiert hier (Funktional):**  
Sortierung des gesamten Candidate-Pools nach `adjusted_distance`. Bei BM25+RRF aktiv: bereits nach RRF sortiert. Dann Slice auf `candidates[:40]` → max 40 Chunks als Cross-Encoder-Input. Wenn Per-Source aktiv: der Per-Source-Output (max 10) ist bereits der Pool — Pre-CE ist damit faktisch ein No-Op.

**Quell-Code-Stelle:**  
app.py:1068–1076 (Pre-CE Sort + Slice), app.py:1177 (`candidates = chunks[:40]`)

**Eingabe:**  
Gesamter Candidate-Pool (semantic + norm + qu + keyword + per_source)

**Ausgabe:**  
list[dict] max 40 Chunks, sortiert nach adjusted_distance

**Entscheidungen pro Chunk:**  
Chunks ab Position 41 werden verworfen (topk_slice).

**Heute im Trace sichtbar:**  
`pre_ce: active=true, count_out=10, detail="Top-10 nach Distanz → Cross-Encoder-Input"`. Im Trace erscheinen alle 10 Chunks mit rrf_rank.

**Heute im Trace NICHT sichtbar:**  
- adjusted_distance-Wert pro Chunk  
- Wie viele Chunks durch den Slice entfernt wurden  
- Ob MW-Priorisierung (Stage nach CE) schon hier angewendet wurde

**Konsequenz für den Inspector:**  
TEILWEISE — fehlend: `adjusted_distance` pro Chunk, `pre_ce_dropped_count`

---

## Stage 12: Cross-Encoder Scoring

**Was passiert hier (Funktional):**  
`reranker.predict(pairs)` — alle candidate-Chunks als (query, chunk_text[:500]) Paare in einem Batch. Modell: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (oder via `RERANKER_MODEL` Env-Var). Scores im Bereich ca. -5 bis +5 (mmarco) oder ×10 für BGE-reranker. Keyword/Hybrid-Chunks: Mindest-Score 3.0 (`if ce_score < 3.0: ce_score = 3.0`). Score wird in `chunk["ce_score"]` geschrieben.

**Quell-Code-Stelle:**  
app.py:1199–1215 (CE-Scoring Block), app.py:251–264 (`get_reranker`), app.py:252–257 (Modell + Scale)

**Eingabe:**  
list[(query, chunk_text[:500])] — max 40 Paare

**Ausgabe:**  
float ce_score pro Chunk (raw, vor Boosts)

**Entscheidungen pro Chunk:**  
Score bestimmt Ranking. Keyword-Chunks: floor(3.0). BGE-Modell: ×10 Skalierung.

**Heute im Trace sichtbar:**  
`ce_score_raw` pro Chunk im Trace. Beispiel: Chunk `seg_eugh_C-470_21_wuerdigung_7` = 2.215, `mw_personenbezug_ip_adressen` = 2.251. `cross_encoder: count_in=10, count_out=10, detail="10 gescort, CE_CUTOFF=3.0"`.

**Heute im Trace NICHT sichtbar:**  
- CE-Score **nach** Boosts (nur raw sichtbar, kein `ce_score_final`)  
- Welches Reranker-Modell aktiv ist  
- CE-Batch-Latenz  
- Ob Keyword-Floor (3.0) angewendet wurde

**Konsequenz für den Inspector:**  
TEILWEISE — ce_score_raw vorhanden, aber fehlend: `ce_score_final` (nach Boosts), `reranker_model`, `keyword_floor_applied`

---

## Stage 13: Boosts & Penalties (alle einzeln)

**Was passiert hier (Funktional):**  
Drei Modifikatoren werden sequenziell auf `chunk["ce_score"]` angewendet:

**13a) Aktualitäts-Boost/Penalty (Recency-Faktor):**  
`_extract_year(chunk)` aus Metadaten (datum/titel/chunk_id/thema). Dann `ce_score = ce_score / recency_factor`:  
- Jahr ≥ 2023: ÷0.70 (Boost, Score steigt)  
- Jahr ≥ 2020: ÷0.85  
- Jahr ≥ 2018: ÷0.95  
- Jahr < 2018: ÷1.10 (Penalty)  
- Kein Jahr: ÷1.0  

**13b) Schlüsselurteil-Boost:**  
Wenn `get_urteilsname(az)` einen Eintrag in `urteilsnamen.json` findet: `ce_score *= 1.5`. Gilt für alle Urteile mit bekanntem Kurznamen.

**13c) Instanzgerichts-Penalty:**  
Wenn die Query **kein** Gericht/AZ nennt und der Chunk von BSG/BFH/BAG/BVerwG/OLG/LG/VG/AG stammt: `ce_score /= 1.3`.

**13d) Pre-DSGVO-Filter/Penalty:**  
Veraltete Leitlinien (Datum < 2018) und Chunks mit aufgehobenen Normen (§ 29 BDSG-alt etc.): Wenn ≥3 aktuelle Chunks vorhanden → veraltete entfernt. Sonst: `ce_score /= 3.0`, `_pre_dsgvo=True`.

**13e) Methodenwissen-Priorisierung:**  
MW-Chunks mit ce_score > 4.0 (nach Boosts): max 3 an Position 1–3 gesetzt (`mw_top`). Kein numerischer Multiplier, nur Umordnung.

**Quell-Code-Stelle:**  
app.py:1218–1228 (Recency), app.py:1229–1239 (Schlüsselurteil), app.py:1241–1257 (Instanzgericht), app.py:1259–1281 (Pre-DSGVO), app.py:1294–1308 (MW-Priorisierung)

**Eingabe:**  
candidates list mit ce_score-Werten

**Ausgabe:**  
Modifizierte ce_score-Werte, ggf. Umordnung, ggf. entfernte Chunks

**Entscheidungen pro Chunk:**  
Jeder Chunk kann mehrere Boosts/Penalties erhalten.

**Heute im Trace sichtbar:**  
`boosts_applied` Liste pro Chunk. Im Trace:  
- `seg_eugh_C-470_21_wuerdigung_7`: `["aktualitaet_recency0.70", "schluesselurteil_x1.5"]`  
- `beh_18.01.2023_...`: `["aktualitaet_recency0.70"]`  
- MW-Chunks und gesetz-Chunks: `[]`  
Stage-Detail: `"aktualitaet_recency0.70, schluesselurteil_x1.5"`

**Heute im Trace NICHT sichtbar:**  
- ce_score_final (Score nach allen Boosts) — nur raw sichtbar  
- Ob Pre-DSGVO-Penalty angewendet wurde (fehlt in boosts_applied wenn entfernt)  
- Ob Instanzgerichts-Penalty angewendet wurde (kein `instanzgericht_div1.3` in diesem Trace)  
- Ob MW-Priorisierung durchgeführt wurde (kein Flag)  
- Jahres-Extraktion: welches Jahr wurde für Recency-Berechnung verwendet

**Konsequenz für den Inspector:**  
TEILWEISE — fehlend: `ce_score_final`, `year_extracted`, `pre_dsgvo_applied`, `mw_prioritized`

---

## Stage 14: Filter & Cutoff (Dedup, CE-Cutoff)

**Was passiert hier (Funktional):**  
Drei Filter sequenziell:

**14a) Document-Level Deduplication:**  
Max 3 Chunks pro Dokument (`MAX_PER_DOC=3`). Dokument-Key aus `_doc_key()`: AZ+Gericht (Urteile), Gesetz-Name, Titel, Thema. Überzählige Chunks: filter_reason="dedup".

**14b) CE-Cutoff:**  
`ce_score >= CE_CUTOFF (3.0) OR adjusted_distance < DIST_CUTOFF (0.25)` → accepted. Sonst: filter_reason="ce_cutoff". Pflicht-Chunks (aus Stage 9) werden davor eingefügt und sind cutoff-immun.

**14c) Min/Max-Dokument-Limit:**  
Min 3 Dokumente: wenn unter Min → auffüllen aus nächstbesten Candidates. Max 8 Dokumente (`MAX_DOCS`): wenn über Max → niedrigst-scorende Dokumente entfernen.

**14d) Source-Type-Diversifizierung:**  
Wenn keine gesetz_granular/gesetz, keine urteil/urteil_segmentiert, oder keine leitlinie/methodenwissen in selected: Nachladen aus candidates.

**Quell-Code-Stelle:**  
app.py:1320–1337 (Doc-Dedup), app.py:1339–1358 (CE-Cutoff), app.py:1360–1401 (Min/Max + Diversifizierung), app.py:88–92 (CE_CUTOFF, DIST_CUTOFF, MIN_DOCS, MAX_DOCS Konstanten)

**Eingabe:**  
Sortierte candidates nach ce_score + Pflicht-Chunks

**Ausgabe:**  
selected: list[dict] mit min 3, max 8 Dokumenten

**Entscheidungen pro Chunk:**  
filter_reason: "dedup" | "ce_cutoff" | "topk_slice" | None

**Heute im Trace sichtbar:**  
`filter: count_in=10, count_out=9, detail="dedup: 1"`. Ein Chunk hat `filter_reason="dedup"`: `gran_DDG_§_2_Abs.1_S.17`. `filter_reason="ce_cutoff"` kommt nicht vor (alle CE-Scores über 3.0 nach Boosts oder durch Distanz).

**Heute im Trace NICHT sichtbar:**  
- Ob Diversifizierung nachgeladen hat  
- Warum ein Chunk ce_cutoff erhält (score und threshold nicht direkt vergleichbar ohne ce_score_final)  
- adjusted_distance für dist-Cutoff-Entscheidung  
- Wie viele Chunks durch Min-Auffüllung kamen

**Konsequenz für den Inspector:**  
TEILWEISE — fehlend: `ce_score_final` für Cutoff-Entscheidung, `dist_at_cutoff`, `diversification_added`

---

## Stage 15: EG-Enrichment (`_enrich_with_erwaegungsgruende`)

**Was passiert hier (Funktional):**  
Für jeden DSGVO-Artikel in den Top-Ergebnissen: Metadaten-Feld `erwaegungsgruende` (kommagetrennte EG-Nummern) auslesen. Die niedrigste EG-Nummer zuerst. Direkte `col.get(ids=[f"dsgvo_eg_{nr}"])` — kein Embedding. Max 2 EGs pro Anfrage. Source="eg_enrichment", distance=0.10, ce_score=5.0 (fest).

**Quell-Code-Stelle:**  
app.py:1575–1629 (`_enrich_with_erwaegungsgruende`), app.py:1404 (Aufruf in `retrieve`)

**Eingabe:**  
selected list mit gesetz_granular-Chunks die DSGVO-Artikel enthalten

**Ausgabe:**  
selected + max 2 EG-Chunks (source="eg_enrichment")

**Entscheidungen pro Chunk:**  
EG-Nummer aus Metadaten → direkte ID-Suche. Fester ce_score=5.0.

**Heute im Trace sichtbar:**  
Im Trace erscheint `dsgvo_eg_30` als Chunk mit `source=["per_source"]` — dieser kam direkt über Per-Source, nicht über EG-Enrichment. Kein Chunk mit source="eg_enrichment" in diesem Trace.

**Heute im Trace NICHT sichtbar:**  
- Ob EG-Enrichment überhaupt ausgeführt wurde  
- Welche EG-Nummern in DSGVO-Artikel-Metadaten gefunden wurden  
- Warum kein Enrichment stattfand (keine DSGVO-Artikel in selected?)

**Konsequenz für den Inspector:**  
NEIN — fehlend: `eg_enrichment_attempted`, `eg_nrs_candidates`, `eg_nrs_added`

---

## Stage 16: Tenor-Enforce (`_ensure_tenor_chunks`)

**Was passiert hier (Funktional):**  
Feature-Flag: `OPENLEX_TENOR_ENFORCE=true` (Standard). Für jedes `urteil_segmentiert`-Chunk in selected: AZ sammeln, prüfen ob Tenor/Leitsatz bereits vorhanden. Falls nicht: `col.get(where={"$and": [{"aktenzeichen": az}, {"segment": "leitsatz"}]})` → dann "tenor" → dann "entscheidungsgruende". Max 3 Injektions-Slots. Injizierte Chunks: ce_score=best_score×0.90 (leitsatz/tenor) oder ×0.80 (Fallback). Misses werden in JSONL-Log geschrieben (`/opt/openlex-mvp/logs/tenor_enforce_misses.jsonl`).

**Quell-Code-Stelle:**  
app.py:1427–1545 (`_ensure_tenor_chunks`), app.py:1406–1407 (Aufruf), app.py:1432–1436 (Konstanten)

**Eingabe:**  
selected list nach EG-Enrichment

**Ausgabe:**  
(updated_selected, tenor_trace) — tenor_trace: {"injected": [...], "already_present": [...], "misses": [...]}

**Entscheidungen pro Chunk:**  
Injizierte Chunks: source="tenor_enforce" oder "tenor_enforce_fallback", `_tenor_injected=True`.

**Heute im Trace sichtbar:**  
`tenor_enforce: injected=[], already_present=[], misses=["C-470/21"]`. Stage-Detail: `"⚠ 1 AZ ohne Tenor verfügbar"`. C-470/21 hat keinen verfügbaren Tenor/Leitsatz in ChromaDB.

**Heute im Trace NICHT sichtbar:**  
- Welche Segmente für C-470/21 versucht wurden  
- Ob der entscheidungsgruende-Fallback auch fehlschlug  
- available_segments aus Tenor-Miss-Log (nur im JSONL)

**Konsequenz für den Inspector:**  
JA (tenor_enforce vorhanden) — teilweise fehlend: `tenor_tried_segments`, `tenor_miss_available_segments`

---

## Stage 17: Finale Auswahl

**Was passiert hier (Funktional):**  
`selected` nach Tenor-Enforce ist der finale Chunk-Pool. Für den LLM-Kontext: `format_context(chunks)` — Chunks werden via `group_chunks_to_docs()` nach Dokument gruppiert, innerhalb Dokument nach ce_score sortiert, Primärquellen vor Methodenwissen. Leitlinien-Deduplizierung via Jaccard-Ähnlichkeit (≥0.80 Titel-Ähnlichkeit → ältere Version entfernt). Ausgabe: nummerierte Quellen `[Quelle 1 – Typ: X – Label]` mit max 3000 Zeichen pro Chunk.

**Quell-Code-Stelle:**  
app.py:1409–1423 (Trace-Finalisierung in `retrieve`), app.py:1804–1828 (`format_context`), app.py:1765–1801 (`group_chunks_to_docs`), app.py:1714–1762 (`_dedup_leitlinien`)

**Eingabe:**  
selected list (post Tenor-Enforce)

**Ausgabe:**  
context str für LLM, final_rank pro Chunk gesetzt

**Entscheidungen pro Chunk:**  
final_rank > 0 = in Antwort. Docs sortiert: primary (nach best_score) vor MW (nach best_score). Chunks pro Doc: nach ce_score absteigend.

**Heute im Trace sichtbar:**  
`final: count_in=9, count_out=9`. Pro Chunk: `final_rank` 1–9. `final_results` Liste im Response enthält alle 9 Chunks mit vollständiger Trace-Info.

**Heute im Trace NICHT sichtbar:**  
- Ob Leitlinien-Dedup stattfand  
- Welche Formatierungsregel pro Chunk angewendet wurde (segment/volladresse/paragraph)  
- context-Länge (Zeichen)  
- Welche Chunks wegen topk_slice gefiltert wurden (kein Chunk mit topk_slice in diesem Trace)

**Konsequenz für den Inspector:**  
JA (final_rank sichtbar) — teilweise fehlend: `leitlinien_dedup_removed`, `context_length_chars`, `doc_ordering`

---

## Stage 18: LLM-Antwortgenerierung

**Was passiert hier (Funktional):**  
**System-Prompt:** DSGVO-Assistent, strikte Quellenbindung, juristische Nummerierung (I./1./a)/(1)), keine horizontalen Linien, URTEILSZITATE mit Urteilsname, EDPB-Zitate mit Randnummer, DEFINITIONSREGEL (Art. 4 DSGVO Legaldefinitionen), Verbot veralteter Normen (§ 29 BDSG-alt), TTDSG→TDDDG-Umbenennung. Ca. 1400 Zeichen langer System-Prompt.

**Modell-Cascading (Priorität):**  
1. **Mistral API** — `mistral-medium-latest`, URL: `https://api.mistral.ai/v1/chat/completions`  
2. **OpenRouter** — Modelle in Reihenfolge: `qwen/qwen3-235b-a22b`, `meta-llama/llama-3.3-70b-instruct`, `google/gemma-3-27b-it`, `mistralai/mistral-small-3.1-24b-instruct`  
3. **Ollama lokal** — `gemma4:e4b` bevorzugt, fallback auf erstes verfügbares Modell

**Streaming:** SSE via `stream_with_fallback()`, yields (token, provider_display). Gradio `.stream()`.

**Token-Limits:** max_tokens=2048, bei Ollama: num_ctx=8192, think=False.  
**Temperature:** 0.3 (OpenAI-kompatible Provider), Mistral: 0.3, Ollama: default.  
**History:** Letzte 6 Nachrichten (`history[-6:]`) in messages eingefügt.

**Quellen-Attribution:** Validierung nach komplettem Stream via `validate_response()` (NORM_RE + AZ_RE → 3-Stufen: verified/in_db_only/missing). Missing-Referenzen werden inline mit ⚠️-Warnung markiert. Antwort-Footer: `*Modell: X | N Dokumente (M Chunks) | K Referenzen validiert*`.

**Quell-Code-Stelle:**  
app.py:2459–2523 (`chat_stream`), app.py:1836–1847 (`_build_llm_messages`), app.py:142–174 (SYSTEM_PROMPT), app.py:1872–1935 (OpenRouter + Mistral), app.py:1960–2008 (Ollama), app.py:2015–2034 (PROVIDERS)

**Eingabe:**  
context (format_context output), messages (system + history + user), llm_history

**Ausgabe:**  
Streaming tokens → full_response str, validations list, sources_md HTML

**Entscheidungen pro Chunk:**  
Quellen-Attribution via Nummern [Quelle N] im LLM-Output.

**Heute im Trace sichtbar:**  
Im Inspector-Trace (API/inspect) **keine** LLM-Stage — der Inspector ruft nur `retrieve()` auf, nicht `chat_stream()`.

**Heute im Trace NICHT sichtbar:**  
- Welcher Provider verwendet wurde  
- Anzahl generierter Tokens  
- LLM-Latenz  
- Validierungs-Ergebnis (verified/in_db_only/missing counts)  
- Ob Antwort abgeschnitten wurde (truncation detection)

**Konsequenz für den Inspector:**  
NEIN — der Inspector schließt die LLM-Stage komplett aus. Fehlend: `llm_provider_used`, `llm_tokens`, `llm_duration_ms`, `validation_counts`

---

## Summary-Tabelle

| Stage | Im Code aktiv? | Im Trace vollständig? | Lücken |
|-------|---------------|----------------------|--------|
| 1: Query-Eingang & Intent | Ja (kein eigenst. Intent) | Nein | intent_type, search_query_used, history_augmented |
| 2: Query-Rewrite | Nein (disabled) | Ja (deaktiviert-Zustand) | guard_triggered wenn aktiv |
| 3: Norm-Validator (Regex) | Ja | Nein | extracted_norms, extracted_az, synonym_expansion |
| 4: Norm-Hypothesizer (QU) | Nein (module?) | Nein | qu_module_available, qu_norms_found |
| 5: Query-Embedding | Ja | Nein | embedding_model, embedding_duration_ms, search_query_used |
| 6: Semantic Top-K | Ja (intern via Per-Source) | Nein (intern) | raw_distances, segment_boost_applied |
| 7: Per-Source Budget | Ja (aktiv) | Teilweise | per_source_budget_counts, overlap, duration_ms |
| 8: QU-Injection | Nein (inaktiv) | Nein | qu_module_available, qu_norms_found |
| 9: Norm-Lookup + Urteilsname | Ja | Nein | norm_lookup_queries, urteilsname_matched |
| 10: BM25 + RRF | Nein (disabled) | Ja (deaktiviert-Zustand) | bm25_score wenn aktiv |
| 11: Pre-CE Filter | Ja | Teilweise | adjusted_distance, pre_ce_dropped |
| 12: Cross-Encoder | Ja | Teilweise | ce_score_final, reranker_model, latency |
| 13: Boosts & Penalties | Ja | Teilweise | ce_score_final, year_extracted, pre_dsgvo_applied |
| 14: Filter & Cutoff | Ja | Teilweise | ce_score_final für Cutoff-Entscheidung, dist_at_cutoff |
| 15: EG-Enrichment | Ja | Nein | eg_enrichment_attempted, eg_nrs_added |
| 16: Tenor-Enforce | Ja | Ja (tenor_enforce dict) | tenor_tried_segments |
| 17: Finale Auswahl | Ja | Ja (final_rank) | leitlinien_dedup, context_length |
| 18: LLM-Generierung | Ja | Nein (außerhalb Scope) | llm_provider, tokens, validation_counts |

---

## Vorgeschlagene Trace-Erweiterungen

| Lücke | Datei | Felder | Aufwand | Risiko |
|-------|-------|--------|---------|--------|
| **ce_score_final** fehlt (nur raw sichtbar) | app.py:1218–1281 | Trace-Eintrag nach letztem Boost-Schritt: `ce_score_final` | S | Niedrig — nur dict-Schreiben |
| **adjusted_distance** pro Chunk | app.py:1184–1197 (Trace-Init) + inspector/main.py:120–136 | `adjusted_distance` in _trace beim Pre-CE-Init; im Inspector aus results auslesen | S | Niedrig |
| **extracted_norms / extracted_az** im Trace | app.py:870, app.py:939 | Neue Trace-Felder im return-dict: `"norm_extract": {"norms": [...], "az": [...], "synonyms": [...]}` | S | Niedrig |
| **per_source_budget_counts** | app.py:1120, per_source_retrieval.py | Budget-Counts aus `_ps_result.per_source` in Trace schreiben | S | Niedrig |
| **embedding_duration_ms + search_query_used** | app.py:834, 826 | `"embedding": {"model": ..., "duration_ms": ..., "search_query": ...}` in rich_trace | S | Niedrig |
| **EG-Enrichment-Trace** | app.py:1575–1629 | Return-value `_enrich_with_erwaegungsgruende` mit `{"eg_attempted": [...], "eg_added": [...]}` + in rich_trace | M | Niedrig |
| **QU-Modul-Status** | app.py:39–48, 899–922 | `"qu_status": {"available": bool, "norms_found": [...], "ids_injected": int}` in rich_trace | M | Niedrig |
| **LLM-Stage im Inspector** | inspector/main.py, app.py:2459 | Zweiter Inspector-Endpoint `/api/full` der auch `chat_stream` aufruft und LLM-Metriken zurückgibt | L | Mittel (LLM-Kosten, Latenz) |
| **Urteilsname-Match-Trace** | app.py:717–764 | `"urteilsname_hits": [{"az": ..., "name": ..., "chunks_loaded": int}]` in rich_trace | S | Niedrig |
| **Tenor-Enforce tried_segments** | app.py:1484–1506 | `"tried_segments": ["leitsatz", "tenor"]` in `tenor_trace["misses"]` Eintrag | S | Niedrig |

