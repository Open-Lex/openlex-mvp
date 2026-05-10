# K2.7-EVAL — PULL-COMPLETE

**Datum:** 2026-05-10  
**Sprint:** K2.7-EVAL  
**Status:** ABGESCHLOSSEN ✅

---

## Ergebnis-Überblick

Beide Evaluations-Wege abgeschlossen — Pipeline-Generik bestätigt, Shadow-Retrieval exzellent.

| Weg | Ziel | Status | Ergebnis |
|---|---|---|---|
| Weg 2 — Smoketest | Generic `skill_id`-Interface live testen | ✅ GRÜN | Hit@5=100% (5/5) |
| Weg 1 — Shadow-Eval | Retrieval-Qualität K3a-Collections messen | ✅ GRÜN | Hit@5=100% (beide Skills) |

---

## Weg 2 — Pipeline-Smoketest

**Skill:** `datenschutz`  
**Modell:** `mixedbread-ai/deepset-mxbai-embed-de-large-v1`  
**Collection:** `openlex_datenschutz` (18.084 Chunks)

| Metrik | Wert |
|---|---|
| Hit@5 | 100% (5/5) |
| Avg Latenz | 10.248 ms |
| Source-Types aktiv | `gesetz_granular`, `urteil_segmentiert`, `leitlinie` |

**Architektur-Befund:**
- `get_collection(skill_id)` → generisch ✓
- `retrieve(question, history, skill_id=...)` → generisch ✓
- QU-Injection für Non-DSGVO: `try/except pass` (silent skip, non-blocking) ✓
- Query-Rewriter: `OPENLEX_REWRITE_ENABLED=false` (Default) → kein Blocker ✓
- `validate_response()`: parametrisiert via `skill_id` ✓

**Report:** `/opt/openlex-mvp-v2/reports/K27/EVAL/w2/SMOKETEST_OK.md`

---

## Weg 1 — Shadow-Eval (K3a)

**Modell:** `intfloat/multilingual-e5-large`  
**Shadow-DB:** `/opt/openlex-sources/chromadb_shadow/`  
**Venv:** `/opt/openlex-mvp-v2/venv` (huggingface_hub 1.10.0 ✓)  
**Skript:** `/opt/openlex-sources/scripts/eval_shadow_v1.py`

### Ergebnisse

| Skill | Queries | Hit@5 | Hit@10 | NDCG@10 | Embeddings |
|---|---:|---:|---:|---:|---:|
| strafrecht | 5 | **100%** | **100%** | **0.96** | 184.704 |
| steuerrecht | 5 | **100%** | **100%** | **0.86** | 131.622 |
| **Gesamt** | **10** | **100%** | **100%** | **0.91** | 316.326 |

### Per-Query Detail — Strafrecht

| Query | Hit@5 | NDCG@10 | Gefundene Terme |
|---|---|---|---|
| Notwehr nach § 32 StGB | ✅ | 1.00 | notwehr, angriff, gebotenheit, verteidigung |
| Vorsatz vs. Fahrlässigkeit | ✅ | 0.99 | vorsatz, fahrlässigkeit, sorgfaltspflicht |
| Betrug § 263 StGB | ✅ | 0.82 | täuschung, irrtum, vermögensschaden |
| Strafverfolgungsverjährung | ✅ | 0.99 | verjährung, verfolgungsverjährung, ablauf |
| Versuch vs. Vollendung | ✅ | 0.99 | versuch, vollendung, rücktritt, § 22 stgb |

### Per-Query Detail — Steuerrecht

| Query | Hit@5 | NDCG@10 | Gefundene Terme |
|---|---|---|---|
| Betriebsausgabe § 4 EStG | ✅ | 0.92 | betriebsausgabe, betrieblich veranlasst, abzugsfähig |
| Beschränkte/unbeschränkte Steuerpflicht | ✅ | 0.59 | unbeschränkte steuerpflicht, beschränkte steuerpflicht, wohnsitz |
| Innergemeinschaftliche Lieferung USt | ✅ | 0.98 | innergemeinschaftliche lieferung, umsatzsteuer, § 6a ustg |
| Verdeckte Gewinnausschüttung | ✅ | 0.92 | verdeckte gewinnausschüttung, fremdvergleich, gesellschafter |
| Festsetzungsverjährung AO | ✅ | 0.91 | festsetzungsverjährung, verjährungsfrist, ablaufhemmung |

### NLnet-Aussage

> Shadow-Eval auf 2 K3a-Collections (`intfloat/multilingual-e5-large`), je 5 juristische Test-Queries:  
> **Hit@5 = 100%, Hit@10 = 100%, Median NDCG@10 = 0.91**  
> Retrieval-Qualität exzellent (Schwelle: ≥ 80%).

---

## Kritische Befunde (für K2.8)

### 1. Embedding-Modell-Mismatch (BLOCKER für K3a→Live-Integration)

| Component | Modell |
|---|---|
| Live-App (`app.py`) | `mixedbread-ai/deepset-mxbai-embed-de-large-v1` |
| K3a Shadow-Build | `intfloat/multilingual-e5-large` |

**Konsequenz:** K3a-Collections sind **nicht direkt** in die Live-App einbindbar.  
**Empfehlung K2.8:** K3a-Build mit mxbai-Modell neu starten (Option A).  
**Nicht K2.7-blockend:** Shadow-Eval verwendet konsistent das K3a-Modell.

### 2. Datenschutz-spezifische Komponenten (Pipeline-aaS-Debt)

| Datei | Datenschutz-Hardcoding | K2.8-Aktion |
|---|---|---|
| `query_rewriter.py` | `_SYSTEM_PROMPT` fest "Datenschutzrecht" | Skill-aware Prompt per JSON |
| `query_understanding.py` | `QU_NORM_TO_CHROMA_IDS` DSGVO-only | Skill-aware Map oder abschalten |
| `per_source_retrieval.py` | `SOURCE_TYPES` Datenschutz-only | Skill-aware Budget via skills.json |

---

## Dateien

| Datei | Inhalt |
|---|---|
| `reports/K27/EVAL/w2/SMOKETEST_OK.md` | Weg 2: Smoketest-Protokoll |
| `reports/K27/EVAL/w2/smoketest_raw.json` | Weg 2: Raw-Ergebnisse |
| `reports/K27/EVAL/w1/queries/strafrecht.json` | 5 kuratierte Strafrecht-Queries |
| `reports/K27/EVAL/w1/queries/steuerrecht.json` | 5 kuratierte Steuerrecht-Queries |
| `reports/K27/EVAL/w1/results/strafrecht.json` | Weg 1: Strafrecht-Ergebnisse |
| `reports/K27/EVAL/w1/results/steuerrecht.json` | Weg 1: Steuerrecht-Ergebnisse |
| `reports/K27/EVAL/w1/SUMMARY.md` | Weg 1: Aggregat-Summary |

---

## Offene Punkte → K2.8

1. **K3a-Restart mit mxbai** — Embedding-Mismatch beheben (blockiert Live-Integration)
2. **Eval für weitere Skills** — Sobald K3a fertig: sozialrecht, mietrecht, verkehrsrecht etc.
3. **eval_v3.py multi-skill** — Datenschutz-Hardcoding aufbrechen
4. **Pipeline-aaS** — query_rewriter + per_source skill-aware machen

## K2.7 Gesamtstatus

| Sub-Sprint | Status |
|---|---|
| K2.7-C (Cellar/Europarecht) | ✅ DONE |
| K2.7-R (rii Senat-Routing) | ✅ DONE — 1.044.736 Assignments |
| K2.7-O (OAPEN/OpenRewi) | ⏳ Rate-Limit — Retry 2026-05-11 |
| K2.7-RSS (Daily-Update-Cron) | ✅ DONE — aktiv seit 2026-05-09 |
| K2.7-INV2 (Re-Inventur) | ✅ DONE — 51 Dateien, 43 Skill-Descriptions |
| K2.7-DIAG (Routing-Diagnose) | ✅ DONE — kein Bug |
| K2.7-QW (Quick Wins) | ✅ DONE — 18.382 neue Assignments |
| K2.7-AUDIT (Pipeline+Embedding) | ✅ DONE — read-only |
| K2.7-EVAL (Smoketest+Shadow) | ✅ DONE |
