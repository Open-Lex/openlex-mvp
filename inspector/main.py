"""
OpenLex Pipeline Inspector — Backend
Port 7862, FastAPI + statisches HTML

Nutzt retrieve(return_trace=True, trace_format="rich") aus app.py.
Kein Änderungsbedarf in app.py — der Trace-Hook existiert bereits.
"""
from __future__ import annotations

import json
import os
import re as _re
import sys
import time
from pathlib import Path
from typing import Optional

# app.py liegt eine Ebene über diesem Verzeichnis
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Lazy imports — schwere Modelle erst beim ersten Request laden
_retrieve          = None
_get_collection    = None
_format_context    = None
_build_llm_messages  = None
_stream_with_fallback = None
_group_chunks_to_docs = None
_SYSTEM_PROMPT_TEXT = None
_MISTRAL_MODEL_NAME = None
_is_initialized    = False
_init_error: Optional[str] = None


def _initialize():
    global _retrieve, _get_collection, _format_context, _build_llm_messages
    global _stream_with_fallback, _group_chunks_to_docs, _is_initialized, _init_error
    global _SYSTEM_PROMPT_TEXT, _MISTRAL_MODEL_NAME
    if _is_initialized:
        return
    try:
        import app as _app
        _retrieve             = _app.retrieve
        _get_collection       = _app.get_collection
        _format_context       = _app.format_context
        _build_llm_messages   = _app._build_llm_messages
        _stream_with_fallback = _app.stream_with_fallback
        _group_chunks_to_docs = _app.group_chunks_to_docs
        _SYSTEM_PROMPT_TEXT   = _app.SYSTEM_PROMPT
        _MISTRAL_MODEL_NAME   = getattr(_app, '_MISTRAL_MODEL', 'mistral-medium-latest')
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
    trace_format: Optional[str] = "rich"  # "rich" (default) oder "full"


class FullRunRequest(BaseModel):
    query: str
    chunk_search: Optional[str] = None
    trace_format: Optional[str] = "full"


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


# ═══════════════════════════════════════════════════════════════════════
# GROUNDING HELPERS (Paket 3)
# ═══════════════════════════════════════════════════════════════════════

_QUELLE_PAT = _re.compile(r'\[Quellen?\s+([\d][,\d\s]*)\]', _re.IGNORECASE)


def _approx_tokens(text: str) -> int:
    """Rough token estimate: words × 1.33 (German words avg 1.33 tok)."""
    return int(len(text.split()) * 1.33)


def _compute_grounding(answer: str, chunks: list[dict]) -> dict:
    """Parse [Quelle X] citations from LLM answer, check against provided context.

    Returns grounding summary dict.
    """
    if not _group_chunks_to_docs:
        return {"grounding_score": 1.0, "cited_in_context": [], "cited_not_in_context": [], "cited_nums": [], "total_docs": 0}

    docs = _group_chunks_to_docs(chunks)
    # Map 1-based doc index → list of chunk IDs in that doc
    doc_chunk_ids: dict[str, list[str]] = {}
    for i, doc in enumerate(docs, 1):
        doc_chunk_ids[str(i)] = [
            c.get("id") or c.get("meta", {}).get("chunk_id", "")
            for c in doc["chunks"]
        ]

    # Extract all cited Quelle numbers from answer
    cited_nums: set[str] = set()
    for m in _QUELLE_PAT.finditer(answer):
        for num in _re.findall(r'\d+', m.group(0)):
            cited_nums.add(num)

    cited_in_context: list[str] = []
    cited_not_in_context: list[str] = []

    for num in sorted(cited_nums, key=lambda x: int(x)):
        if num in doc_chunk_ids:
            cited_in_context.extend(doc_chunk_ids[num])
        else:
            cited_not_in_context.append(num)

    total = len(cited_nums)
    in_ctx = len([n for n in cited_nums if n in doc_chunk_ids])

    return {
        "cited_nums":            sorted(cited_nums, key=lambda x: int(x)),
        "cited_in_context":      cited_in_context,
        "cited_not_in_context":  cited_not_in_context,
        "grounding_score":       in_ctx / total if total > 0 else 1.0,
        "total_docs":            len(docs),
    }


def _run_llm_with_trace(query: str, chunks: list[dict]) -> dict:
    """Run LLM synchronously (blocking). Returns answer + grounding + timing trace."""
    t0 = time.time()

    _EMPTY_GROUNDING = {
        "grounding_score": 0.0, "cited_in_context": [],
        "cited_not_in_context": [], "cited_nums": [], "total_docs": 0,
    }

    if not _format_context or not _build_llm_messages or not _stream_with_fallback:
        return {
            "answer": "LLM-Funktionen nicht initialisiert.",
            "provider": "n/a", "model": "n/a",
            "approx_tokens": 0, "duration_ms": 0, "first_token_ms": None,
            "tokens_per_second": None, "error": "not_initialized",
            "input_tokens": {"system_prompt": 0, "query": 0, "context": 0, "total": 0},
            "grounding": _EMPTY_GROUNDING,
        }

    try:
        context  = _format_context(chunks)
        messages = _build_llm_messages(query, context, [])
    except Exception as e:
        return {
            "answer": f"Kontext-Aufbau fehlgeschlagen: {e}",
            "provider": "n/a", "model": "n/a",
            "approx_tokens": 0,
            "duration_ms": round((time.time() - t0) * 1000, 1),
            "first_token_ms": None, "tokens_per_second": None,
            "error": str(e),
            "input_tokens": {"system_prompt": 0, "query": 0, "context": 0, "total": 0},
            "grounding": _EMPTY_GROUNDING,
        }

    # Token-Schätzung für Input-Sektion
    sys_txt  = _SYSTEM_PROMPT_TEXT or ""
    sp_tok   = _approx_tokens(sys_txt)
    q_tok    = _approx_tokens(query)
    ctx_tok  = _approx_tokens(context)

    tokens: list[str] = []
    provider_used   = "unknown"
    error_msg: Optional[str] = None
    t_first_token: Optional[float] = None

    try:
        for token, provider in _stream_with_fallback(messages):
            if t_first_token is None:
                t_first_token = time.time()
            tokens.append(token)
            provider_used = provider
    except Exception as e:
        error_msg = str(e)

    answer      = "".join(tokens)
    duration_ms = round((time.time() - t0) * 1000, 1)
    first_ms    = round((t_first_token - t0) * 1000, 1) if t_first_token else None
    out_tok     = _approx_tokens(answer)
    tok_per_s   = round(out_tok / (duration_ms / 1000), 1) if duration_ms > 0 else None

    grounding: dict = _EMPTY_GROUNDING.copy()
    if answer and not error_msg:
        try:
            grounding = _compute_grounding(answer, chunks)
        except Exception:
            pass

    model_name = _MISTRAL_MODEL_NAME or "unknown"
    # Strip to base model if provider gives full string
    if "via " in provider_used:
        model_name = provider_used.split("via")[0].strip()

    return {
        "answer":           answer,
        "provider":         provider_used,
        "model":            model_name,
        "approx_tokens":    out_tok,
        "duration_ms":      duration_ms,
        "first_token_ms":   first_ms,
        "tokens_per_second": tok_per_s,
        "error":            error_msg,
        "input_tokens": {
            "system_prompt": sp_tok,
            "query":         q_tok,
            "context":       ctx_tok,
            "total":         sp_tok + q_tok + ctx_tok,
        },
        "grounding":        grounding,
    }



def _build_final_context(results: list[dict]) -> dict:
    """Build per-chunk context summary for the final_context stage visualization."""
    context_chunks = []
    for i, r in enumerate(results, 1):
        text = r.get("text") or r.get("document", "")
        meta = r.get("meta", {})
        approx_tok = _approx_tokens(text)
        context_chunks.append({
            "rank":              i,
            "chunk_id":          r.get("id") or meta.get("chunk_id", ""),
            "source_type":       meta.get("source_type", ""),
            "segment":           meta.get("segment", ""),
            "aktenzeichen":      meta.get("aktenzeichen", ""),
            "gesetz":            meta.get("gesetz", ""),
            "titel":             meta.get("titel", ""),
            "ce_score":          r.get("ce_score"),
            "approx_tokens":     approx_tok,
            "doc_preview":       text[:200],
            "is_tenor_injected": bool(
                r.get("_tenor_injected") or r.get("source") == "tenor_enforce"
            ),
        })
    total_tok = sum(c["approx_tokens"] for c in context_chunks)
    return {
        "chunks":               context_chunks,
        "total_chunks":         len(context_chunks),
        "total_context_tokens": total_tok,
    }

# ═══════════════════════════════════════════════════════════════════════
# SHARED RETRIEVE RESULT PROCESSOR
# ═══════════════════════════════════════════════════════════════════════

def _process_retrieve_result(query: str, chunk_search: Optional[str],
                              results: list, rich_trace: dict,
                              duration_ms: float) -> dict:
    """Converts retrieve() output into inspect API response dict."""
    chunks_trace: dict   = rich_trace.get("chunks", {})
    rewrite_info: dict   = rich_trace.get("rewrite", {})
    tenor_enforce: dict  = rich_trace.get("tenor_enforce", {})

    # ── Alle Chunks als flache Liste aufbauen ──
    all_chunks = []
    for cid, info in chunks_trace.items():
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

    # ── Chunks aus results die nicht im _trace sind nachladen ──
    injected_ids = {e["chunk_id"] for e in tenor_enforce.get("injected", [])}
    trace_ids    = {c["id"] for c in all_chunks}
    for i, res in enumerate(results, start=1):
        rid = res.get("id") or res.get("meta", {}).get("chunk_id", "")
        if not rid or rid in trace_ids:
            continue
        meta = res.get("meta", {})
        src  = res.get("source", "urteilsname") or "injected"
        is_tenor_chunk = rid in injected_ids
        all_chunks.append({
            "id":             rid,
            "sources":        [src],
            "rrf_rank":       -1,
            "ce_score_raw":   res.get("ce_score"),
            "ce_rank":        -1,
            "boosts_applied": ["tenor_enforced"] if is_tenor_chunk else [],
            "final_rank":     i,
            "filter_reason":  None,
            "source_type":    meta.get("source_type", ""),
            "gericht":        meta.get("gericht", ""),
            "aktenzeichen":   meta.get("aktenzeichen", ""),
            "gesetz":         meta.get("gesetz", ""),
            "titel":          meta.get("titel", ""),
            "segment":        meta.get("segment", ""),
            "doc_preview":    (res.get("text") or res.get("document", ""))[:200],
            "_tenor_injected": is_tenor_chunk,
        })
        trace_ids.add(rid)

    # Final-Rank für trace-Chunks die noch keinen Rank haben
    for i, res in enumerate(results, start=1):
        rid = res.get("id") or res.get("meta", {}).get("chunk_id", "")
        for c in all_chunks:
            if c["id"] == rid and c["final_rank"] == -1:
                c["final_rank"] = i
                break

    stages = _compute_stages(all_chunks, rewrite_info, tenor_enforce)

    # ── Chunk-Suche ──
    tracked_ids = []
    if chunk_search:
        search_lower = chunk_search.lower()
        for c in all_chunks:
            cid_lower = c["id"].lower()
            az_lower = c["aktenzeichen"].lower()
            if (search_lower in cid_lower
                    or search_lower in az_lower
                    or search_lower in c["doc_preview"].lower()
                    or search_lower in c["titel"].lower()):
                tracked_ids.append(c["id"])

    final = sorted(
        [c for c in all_chunks if c["final_rank"] > 0],
        key=lambda x: x["final_rank"]
    )

    return {
        "query":           query,
        "rewrite":         rewrite_info,
        "pipeline_stages": stages,
        "chunks":          all_chunks,
        "tracked_chunks":  tracked_ids,
        "final_results":   final,
        "tenor_enforce":   tenor_enforce,
        "duration_ms":     round(duration_ms, 1),
        "full_trace":      rich_trace.get("full"),
    }


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

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
            trace_format=req.trace_format or "rich",
        )
    except Exception as e:
        raise HTTPException(500, f"retrieve() Fehler: {e}")

    duration_ms = (time.time() - t0) * 1000
    return _process_retrieve_result(req.query, req.chunk_search, results, rich_trace, duration_ms)


@app.post("/api/full")
async def full_run(req: FullRunRequest):
    """Full pipeline: Retrieval + LLM generation with grounding trace."""
    _initialize()
    if _init_error:
        raise HTTPException(500, f"Pipeline-Init fehlgeschlagen: {_init_error}")
    if not _retrieve:
        raise HTTPException(500, "retrieve() nicht verfügbar")

    t0 = time.time()

    # Step 1: Retrieval
    try:
        results, rich_trace = _retrieve(
            req.query,
            return_trace=True,
            trace_format=req.trace_format or "full",
        )
    except Exception as e:
        raise HTTPException(500, f"retrieve() Fehler: {e}")

    retrieval_ms = (time.time() - t0) * 1000

    # Step 2: LLM generation (sync, run in thread to not block event loop)
    import asyncio
    loop = asyncio.get_event_loop()
    llm_result = await loop.run_in_executor(None, _run_llm_with_trace, req.query, results)

    total_ms = (time.time() - t0) * 1000

    response = _process_retrieve_result(req.query, req.chunk_search, results, rich_trace, retrieval_ms)
    response["llm"]           = llm_result
    response["final_context"] = _build_final_context(results)
    response["duration_ms"]   = round(total_ms, 1)
    response["retrieval_ms"]  = round(retrieval_ms, 1)
    return response


@app.get("/api/search-chunk")
async def search_chunk_in_db(q: str, limit: int = 10):
    """Sucht direkt in ChromaDB nach Chunks (unabhängig von einer Query)."""
    _initialize()
    if _init_error or not _get_collection:
        raise HTTPException(500, "ChromaDB nicht verfügbar")

    try:
        col = _get_collection()
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
        try:
            col = _get_collection()
            try:
                r = col.get(ids=[q], include=["metadatas", "documents"])
                items = [{"id": r["ids"][0], "meta": r["metadatas"][0], "doc_preview": (r["documents"][0] or "")[:200]}]
                return {"query": q, "results": items}
            except Exception:
                pass
        except Exception:
            pass
        raise HTTPException(500, f"Suche fehlgeschlagen: {e}")


def _compute_stages(chunks: list[dict], rewrite_info: dict, tenor_enforce: dict | None = None) -> list[dict]:
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

    # Tenor-Enforce Stage anhängen
    if tenor_enforce is not None:
        n_injected = len(tenor_enforce.get("injected", []))
        n_misses   = len(tenor_enforce.get("misses", []))
        already    = tenor_enforce.get("already_present", [])
        te_ran     = bool(n_injected or n_misses or already)
        detail_parts = []
        if n_injected:
            segs = [e["segment"] for e in tenor_enforce.get("injected", [])]
            detail_parts.append(f"+{n_injected} injiziert ({', '.join(segs)})")
        if already:
            detail_parts.append(f"{len(already)} AZ bereits mit Tenor")
        if n_misses:
            detail_parts.append(f"⚠ {n_misses} AZ ohne Tenor verfügbar")
        stages.append({
            "id": "tenor_enforce",
            "label": "Tenor-Enforce",
            "active": te_ran,
            "count_in": n_final,
            "count_out": n_final + n_injected,
            "detail": " | ".join(detail_parts) if detail_parts else "Kein Urteil in Ergebnissen",
        })

    return stages


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7862, reload=False)
