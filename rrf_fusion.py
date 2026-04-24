"""
Reciprocal Rank Fusion (Cormack et al. 2009).
Standard k=60.
"""


def rrf_fuse(
    rankings: list,
    k: int = 60,
) -> dict:
    """
    Fusioniert mehrere geordnete ID-Listen via RRF.

    Args:
        rankings: Liste von geordneten chunk_id-Listen pro Retrieval-Pfad
        k: RRF-Konstante (Standard 60)

    Returns:
        dict chunk_id -> RRF-Score, sortiert absteigend
    """
    scores: dict = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            if chunk_id is None or chunk_id == "":
                continue
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    # Absteigend sortieren
    return dict(sorted(scores.items(), key=lambda x: -x[1]))


def rrf_top_k(
    rankings: list,
    top_k: int,
    k: int = 60,
) -> list:
    """Gibt Top-K der fusionierten Ergebnisse als Liste zurück."""
    fused = rrf_fuse(rankings, k=k)
    return list(fused.items())[:top_k]
