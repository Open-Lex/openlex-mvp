"""
OpenLex Pipeline Inspector — Backend
Port 7862, FastAPI + statisches HTML

Nutzt retrieve(return_trace=True, trace_format="rich") aus app.py.
Kein Änderungsbedarf in app.py — der Trace-Hook existiert bereits.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

# app.py liegt eine Ebene über diesem Verzeichnis
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Lazy imports — schwere Modelle erst beim ersten Request laden
_retrieve = None
_get_collection = None
_is_initialized = False
_init_error: Optional[str] = None


def _initialize():
    global _retrieve, _get_collection, _is_initialized, _init_error
    if _is_initialized:
        return
    try:
        import app as _app
        _retrieve = _app.retrieve
        _get_collection = _app.get_collection
        _is_initialized = True
    except Exception as e:
        _init_error = str(e)
        _is_initialized = True  # Nicht nochmal versuchen


from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="OpenLex Pipeline Inspector", version="1.0.0")


class InspectRequest(BaseModel):
    query: str
    chunk_search: Optional[str] = None  # AZ, Chunk-ID oder Keyword


class InspectResponse(BaseModel):
    query: str
    rewrite: dict
    pipeline_stages: list[dict]  # Eine Zeile pro Stage
    chunks: list[dict]           # Alle Chunks mit Trace-Info
    tracked_chunks: list[str]    # IDs der gesuchten Chunks (für Röttler etc.)
    final_results: list[dict]    # Die ausgewählten Chunks (final_rank > 0)
    duration_ms: float


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    html_path = Path(__file__).resolve().parent / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>index.html nicht gefunden</h1>", status_code=404)


@app.get("/api/health")
async def health():
    _initialize()
    return {
        "status": "ok" if _is_initialized and not _init_error else "error",
        "initialized": _is_initialized,
        "error": _init_error,
    }


@app.post("/api/inspect")
async def inspect_pipeline(req: InspectRequest):
    _initialize()
    if _init_error:
        raise HTTPException(500, f"Pipeline-Init fehlgeschlagen: {_init_error}")
    if not _retrieve:
        raise HTTPException(500, "retrieve() nicht verfügbar")

    t0 = time.time()
    try:
        results, rich_trace = _retrieve(
            req.query,
            return_trace=True,
            trace_format="rich",
        )
    except Exception as e:
        raise HTTPException(500, f"retrieve() Fehler: {e}")

    duration_ms = (time.time() - t0) * 1000

    chunks_trace: dict = rich_trace.get("chunks", {})
    rewrite_info: dict = rich_trace.get("rewrite", {})

    # ── Alle Chunks als flache Liste aufbauen ──
    all_chunks = []
    for cid, info in chunks_trace.items():
        # Metadaten aus den Ergebnissen holen, falls vorhanden
        meta = {}
        doc_preview = ""
        for r in results:
            rid = r.get("id") or r.get("meta", {}).get("chunk_id", "")
            if rid == cid:
                meta = r.get("meta", {})
                doc_preview = (r.get("text") or r.get("document", ""))[:200]
                break

        all_chunks.append({
            "id": cid,
            "sources": info.get("sources", []),
            "rrf_rank": info.get("rrf_rank", -1),
            "ce_score_raw": info.get("ce_score_raw"),
            "ce_rank": info.get("ce_rank", -1),
            "boosts_applied": info.get("boosts_applied", []),
            "final_rank": info.get("final_rank", -1),
            "filter_reason": info.get("filter_reason"),
            "source_type": meta.get("source_type", ""),
            "gericht": meta.get("gericht", ""),
            "aktenzeichen": meta.get("aktenzeichen", ""),
            "gesetz": meta.get("gesetz", ""),
            "titel": meta.get("titel", ""),
            "segment": meta.get("segment", ""),
            "doc_preview": doc_preview,
        })

    # ── Pipeline-Stages berechnen ──
    stages = _compute_stages(all_chunks, rewrite_info)

    # ── Chunk-Suche (für Röttler-Diagnose) ──
    tracked_ids = []
    if req.chunk_search:
        search_lower = req.chunk_search.lower()
        for c in all_chunks:
            cid_lower = c["id"].lower()
            az_lower = c["aktenzeichen"].lower()
            if (search_lower in cid_lower
                    or search_lower in az_lower
                    or search_lower in c["doc_preview"].lower()
                    or search_lower in c["titel"].lower()):
                tracked_ids.append(c["id"])

    # ── Final Results ──
    final = sorted(
        [c for c in all_chunks if c["final_rank"] > 0],
        key=lambda x: x["final_rank"]
    )

    return {
        "query": req.query,
        "rewrite": rewrite_info,
        "pipeline_stages": stages,
        "chunks": all_chunks,
        "tracked_chunks": tracked_ids,
        "final_results": final,
        "duration_ms": round(duration_ms, 1),
    }


@app.get("/api/search-chunk")
async def search_chunk_in_db(q: str, limit: int = 10):
    """Sucht direkt in ChromaDB nach Chunks (unabhängig von einer Query)."""
    _initialize()
    if _init_error or not _get_collection:
        raise HTTPException(500, "ChromaDB nicht verfügbar")

    try:
        col = _get_collection()
        # Suche per get mit where-Filter auf Aktenzeichen
        r = col.get(
            where={"aktenzeichen": {"$contains": q}} if len(q) > 3 else None,
            include=["metadatas", "documents"],
            limit=limit,
        )
        items = []
        for cid, meta, doc in zip(r["ids"], r["metadatas"], r["documents"]):
            items.append({
                "id": cid,
                "meta": meta,
                "doc_preview": (doc or "")[:200],
            })
        return {"query": q, "results": items}
    except Exception as e:
        # Fallback: kein where-Filter
        try:
            col = _get_collection()
            # Direkte ID-Suche
            try:
                r = col.get(ids=[q], include=["metadatas", "documents"])
                items = [{"id": r["ids"][0], "meta": r["metadatas"][0], "doc_preview": (r["documents"][0] or "")[:200]}]
                return {"query": q, "results": items}
            except Exception:
                pass
        except Exception:
            pass
        raise HTTPException(500, f"Suche fehlgeschlagen: {e}")


def _compute_stages(chunks: list[dict], rewrite_info: dict) -> list[dict]:
    """Berechnet die Chunk-Anzahl pro Pipeline-Stage."""

    def count_by_source(*src_names):
        return len([c for c in chunks if any(s in c["sources"] for s in src_names)])

    n_semantic = count_by_source("semantic")
    n_norm = count_by_source("norm_lookup")
    n_qu = count_by_source("qu_injection")
    n_bm25_rrf = count_by_source("rrf_injected")
    n_keyword = count_by_source("keyword", "hybrid")
    n_per_source = count_by_source("per_source")
    n_pre_ce = len([c for c in chunks if c["rrf_rank"] > 0])
    n_ce_scored = len([c for c in chunks if c["ce_score_raw"] is not None])
    n_after_filter = len([c for c in chunks
                          if c["ce_score_raw"] is not None and c["filter_reason"] is None])
    n_final = len([c for c in chunks if c["final_rank"] > 0])

    # Filter-Breakdown
    by_filter: dict[str, int] = {}
    for c in chunks:
        fr = c.get("filter_reason")
        if fr:
            by_filter[fr] = by_filter.get(fr, 0) + 1

    ps_active = n_per_source > 0

    stages = [
        {
            "id": "rewrite",
            "label": "Query Rewriting",
            "active": rewrite_info.get("used", False),
            "count_in": 1,
            "count_out": 1,
            "detail": (
                f"'{rewrite_info.get('original', '')}' → '{rewrite_info.get('rewritten', '')}'"
                if rewrite_info.get("used") else "Deaktiviert"
            ),
        },
        {
            "id": "semantic",
            "label": "Semantische Suche",
            "active": True,
            "count_in": 0,
            "count_out": n_semantic if not ps_active else None,
            "detail": ("ChromaDB top-40 → intern von Per-Source genutzt" if ps_active
                       else f"ChromaDB top-40, {n_semantic} Chunks"),
        },
        {
            "id": "norm_lookup",
            "label": "Norm-Lookup",
            "active": n_norm > 0 or ps_active,
            "count_in": None if ps_active else n_semantic,
            "count_out": None if ps_active else n_semantic + n_norm,
            "detail": ("intern (vor Per-Source)" if ps_active
                       else f"+{n_norm} normbasierte Chunks"),
        },
        {
            "id": "qu_injection",
            "label": "QU Injection",
            "active": n_qu > 0,
            "count_in": None if ps_active else n_semantic + n_norm,
            "count_out": None if ps_active else n_semantic + n_norm + n_qu,
            "detail": ("intern" if ps_active else f"+{n_qu} deterministisch"),
        },
        {
            "id": "bm25_rrf",
            "label": "BM25 + RRF",
            "active": n_bm25_rrf > 0,
            "count_in": None if ps_active else n_semantic + n_norm + n_qu,
            "count_out": None if ps_active else n_semantic + n_norm + n_qu + n_bm25_rrf,
            "detail": f"+{n_bm25_rrf} via BM25/RRF" if n_bm25_rrf else "Deaktiviert",
        },
        {
            "id": "keyword",
            "label": "Keyword-Suche",
            "active": n_keyword > 0,
            "count_in": None if ps_active else n_semantic + n_norm + n_qu + n_bm25_rrf,
            "count_out": None if ps_active else n_semantic + n_norm + n_qu + n_bm25_rrf + n_keyword,
            "detail": (f"+{n_keyword} Keyword/Hybrid-Treffer" if n_keyword else "Kein Keyword-Treffer"),
        },
        {
            "id": "per_source",
            "label": "Per-Source Budget",
            "active": ps_active,
            "count_in": None,
            "count_out": n_per_source if ps_active else n_semantic + n_norm + n_qu + n_bm25_rrf + n_keyword,
            "detail": (f"{n_per_source} Chunks nach Typ-Budget (ersetzt Single-Call)"
                       if ps_active else "Deaktiviert — Single-Call aktiv"),
        },
        {
            "id": "pre_ce",
            "label": "Pre-CE Filter",
            "active": True,
            "count_in": None,
            "count_out": n_pre_ce,
            "detail": f"Top-{n_pre_ce} nach Distanz → Cross-Encoder-Input",
        },
        {
            "id": "cross_encoder",
            "label": "Cross-Encoder",
            "active": True,
            "count_in": n_pre_ce,
            "count_out": n_ce_scored,
            "detail": f"{n_ce_scored} gescort, CE_CUTOFF=3.0",
        },
        {
            "id": "boosts",
            "label": "Boosts & Penalties",
            "active": any(c["boosts_applied"] for c in chunks),
            "count_in": n_ce_scored,
            "count_out": n_ce_scored,
            "detail": ", ".join(sorted({b for c in chunks for b in c["boosts_applied"]})) or "–",
        },
        {
            "id": "filter",
            "label": "Filter & Cutoff",
            "active": True,
            "count_in": n_ce_scored,
            "count_out": n_after_filter,
            "detail": " | ".join(f"{k}: {v}" for k, v in by_filter.items()) or "Kein Filter",
        },
        {
            "id": "final",
            "label": "Finale Auswahl",
            "active": True,
            "count_in": n_after_filter,
            "count_out": n_final,
            "detail": f"{n_final} Chunks in Antwort (min=3, max=8)",
        },
    ]
    return stages


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7862, reload=False)
