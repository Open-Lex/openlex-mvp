# OpenLex Pipeline – Struktur & Telemetrie-Mapping

Analysiert: 2026-04-30  
Quellen: app.py (3385 Zeilen), per_source_retrieval.py, per_source_telemetry.py

## Zentrale Funktion

```python
retrieve(
    question: str,
    history: list | None = None,
    _candidates_only: bool = False,
    _candidates_top_k: int = 150,
    return_trace: bool = False,      # ← bereits vorhanden
    trace_format: str = "flat"       # "flat" oder "rich"
)
```

Aufruf mit `return_trace=True, trace_format="rich"` gibt zurück:
```python
(selected_chunks, {
    "chunks": {chunk_id: {
        "sources": list[str],        # ["semantic", "hybrid", ...]
        "rrf_rank": int,             # Rang vor Cross-Encoder (1-40)
        "ce_score_raw": float|None,  # CE-Score (nach Scale)
        "ce_rank": int,              # Rang nach CE (1-40)
        "boosts_applied": list[str], # z.B. ["schluesselurteil_x1.5"]
        "final_rank": int,           # -1 = nicht in Ergebnissen
        "filter_reason": str|None,   # "dedup", "ce_cutoff", "pre_dsgvo", "topk_slice"
    }},
    "rewrite": {
        "used": bool,
        "original": str,
        "rewritten": str,
        "from_cache": bool,
        "error": str|None,
        "duration_ms": float,
    }
})
```

## Pipeline-Stages (12)

| # | Name | Quelle im Trace | Chunks rein | Chunks raus |
|---|------|-----------------|-------------|-------------|
| 0 | Query Rewriting | rewrite_info.used | 1 Query | 1 Query |
| 1 | Semantic Search | source="semantic" | — | ≤40 |
| 2 | Norm Lookup | source="norm_lookup" | — | +≤25 |
| 3 | QU Injection | source="qu_injection" | — | +N |
| 4 | BM25 + RRF | source="rrf_injected" | — | +M |
| 5 | Keyword Search | source="keyword"/"hybrid" | — | +K |
| 6 | Per-Source Budget | source="per_source" | ersetzt 1 | ≤10 |
| 7 | Pre-CE Filter | rrf_rank ≤ 40 | Pool | 40 Kandidaten |
| 8 | Cross-Encoder | ce_score_raw != null | 40 | 40 (scored) |
| 9 | Boosts & Penalties | boosts_applied | 40 | 40 (modifiziert) |
| 10 | Deduplication | filter_reason="dedup" | 40 | <40 |
| 11 | Cutoff + Selection | filter_reason="ce_cutoff" | — | ≥3, ≤8 |
| 12 | EG-Anreicherung | source="eg_enrichment" | — | +≤2 |

## Kein Trace-Mechanismus notwendig – `return_trace` existiert bereits!

`retrieve()` ab Zeile 781 in app.py hat bereits vollständigen Trace-Support.
`retrieve_candidates_only()` (Zeile 767) gibt Pre-CE-Pool zurück (nützlich für Stage 7).

## Geplantes Inspector-Backend

```
/opt/openlex-mvp/inspector/
    main.py       FastAPI-App, Port 7862
    index.html    React+Tailwind CDN (Single File)
```

Systemd: openlex-inspector.service
Nginx: inspect.open-lex.cloud → Port 7862

## Röttler-Diagnose

EuGH C-34/10 (Röttler) — Aktenzeichen: C-34/10 oder "C‑34/10"
Chunk-IDs beginnen mit "seg_eugh_c-34/10_" oder "eugh_c_34_10_"
Suchstring für Chunk-Search: "C-34/10" oder "Röttler"
