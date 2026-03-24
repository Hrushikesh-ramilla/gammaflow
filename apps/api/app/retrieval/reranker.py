"""Cross-encoder reranker for top-k Qdrant results.

Uses sentence-transformers cross-encoder/ms-marco-MiniLM-L-6-v2 to rerank
the initial vector search results by relevance to the query.

Why reranking?
  Vector search retrieves candidates by embedding similarity — fast but imprecise.
  Cross-encoders jointly encode query+document and produce precise relevance scores.
  We retrieve top-20 from Qdrant, rerank, return top-5 for the LLM prompt.
"""

from typing import List

import structlog

log = structlog.get_logger()

# Lazy-loaded cross-encoder model
_cross_encoder = None
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _get_cross_encoder():
    """Load the cross-encoder model lazily (only on first call)."""
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder

            log.info("reranker.loading_model", model=CROSS_ENCODER_MODEL)
            _cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL, max_length=512)
            log.info("reranker.model_ready")
        except ImportError:
            log.warning("reranker.cross_encoder_unavailable_fallback_to_score_sort")
            _cross_encoder = None
    return _cross_encoder


def rerank(query: str, results: List[dict], top_k: int = 5) -> List[dict]:
    """Rerank search results using cross-encoder scores.

    Args:
        query: The user's question.
        results: List of result dicts with at minimum a "text" key.
        top_k: Number of top-ranked results to return.

    Returns:
        Top-k results sorted by rerank_score descending, with "rerank_score" added.
    """
    if not results:
        return results

    model = _get_cross_encoder()
    if model is None:
        # Fallback: sort by existing Qdrant score
        log.debug("reranker.using_fallback_score_sort")
        sorted_results = sorted(results, key=lambda r: r.get("score", 0), reverse=True)
        for r in sorted_results:
            r["rerank_score"] = r.get("score")
        return sorted_results[:top_k]

    # Build (query, passage) pairs for the cross-encoder
    pairs = [(query, r.get("text", "")) for r in results]

    try:
        scores = model.predict(pairs)
        for result, score in zip(results, scores):
            result["rerank_score"] = float(score)

        reranked = sorted(results, key=lambda r: r["rerank_score"], reverse=True)
        log.debug(
            "reranker.complete",
            candidates=len(results),
            returned=min(top_k, len(reranked)),
        )
        return reranked[:top_k]

    except Exception as exc:
        log.warning("reranker.prediction_failed", error=str(exc))
        # Graceful degradation: return original results unsorted
        for r in results:
            r["rerank_score"] = r.get("score")
        return results[:top_k]
