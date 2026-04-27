#!/usr/bin/env python3
"""
Performance: per-Source-Retrieval (5 Calls) vs. Single-Call (1 Call mit k=20).
"""
import sys, time
sys.path.insert(0, "/opt/openlex-mvp")
from per_source_retrieval import per_source_query

QUERIES = [
    "Darf mein Arbeitgeber meine E-Mails lesen?",
    "Was ist eine Auftragsverarbeitung?",
    "Sind Cookies ohne Einwilligung erlaubt?",
    "Welche Rechte habe ich nach DSGVO?",
    "Wann ist eine DSFA verpflichtend?",
]


def single_call_retrieval(query_embedding, col, k=20):
    """Misst nur den Retrieval-Call (ohne Embedding)."""
    t = time.time()
    col.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["metadatas", "distances"],
    )
    return (time.time() - t) * 1000


def main():
    from sentence_transformers import SentenceTransformer
    print("Loading model...")
    model = SentenceTransformer(
        "mixedbread-ai/deepset-mxbai-embed-de-large-v1",
        prompts={"query": "query: "},
        default_prompt_name="query",
    )
    embed_fn = lambda t: model.encode(t)

    import chromadb
    col = chromadb.PersistentClient("/opt/openlex-mvp/chromadb").get_collection("openlex_datenschutz")

    print(f"\n{'Query':<55} {'Emb(ms)':<9} {'Single(ms)':<12} {'5-Calls(ms)':<13} {'Ratio'}")
    print("-" * 100)

    single_total = per_total = emb_total = 0.0

    for q in QUERIES:
        # Embedding (einmal, für beide Methoden identisch)
        t_emb = time.time()
        emb = embed_fn(q)
        emb_ms = (time.time() - t_emb) * 1000
        emb_list = emb.tolist()

        # Single-Call (nur Retrieval, kein Embedding)
        single_ms = single_call_retrieval(emb_list, col)

        # Per-Source (nutzt eigenes Embedding intern → erneut messen ohne Emb-Zeit)
        # Embedding separat übergeben über Wrapper
        cached_emb = emb_list[:]
        embed_cached = lambda _: cached_emb
        ps = per_source_query(q, embed_cached)
        per_ms = ps.total_duration_ms   # nur Retrieval, Embedding ~0ms da cached

        ratio = per_ms / single_ms if single_ms > 0 else 0.0
        emb_total += emb_ms
        single_total += single_ms
        per_total += per_ms

        print(f"{q[:53]:<55} {emb_ms:>6.0f}   {single_ms:>9.0f}   {per_ms:>10.0f}   {ratio:>5.2f}x")

    n = len(QUERIES)
    print("-" * 100)
    print(f"{'AVG':<55} {emb_total/n:>6.0f}   {single_total/n:>9.0f}   {per_total/n:>10.0f}   {per_total/single_total:>5.2f}x")
    print()
    print(f"Gesamtlatenz Single:    Emb {emb_total/n:.0f}ms + Retrieval {single_total/n:.0f}ms = {(emb_total+single_total)/n:.0f}ms")
    print(f"Gesamtlatenz Per-Source: Emb {emb_total/n:.0f}ms + Retrieval {per_total/n:.0f}ms = {(emb_total+per_total)/n:.0f}ms")


if __name__ == "__main__":
    main()
