"""Local keyword + optional FAISS retrieval; explicit faceted governance."""
from __future__ import annotations
import math
import re
from typing import Any


def tokenize(text: str) -> list[str]:
    return re.findall(r'[a-z0-9][a-z0-9+_.-]*', text.lower())


def matches(row: dict, filters: dict[str, list[str]], include_archived: bool) -> bool:
    """Enforce lifecycle eligibility and canonical facet filtering.

    Lifecycle is special: an explicit lifecycle filter containing 'archived'
    opts the caller into archived results, even if include_archived is false.
    An explicit 'current' filter never leaks archived content just because
    include_archived was set.
    """
    facets = row.get('facets') or {}
    explicit_lifecycle = filters.get('lifecycle', [])
    archived_requested = 'archived' in explicit_lifecycle
    if not (include_archived or archived_requested):
        if 'archived' in facets.get('lifecycle', []):
            return False
    return all(bool(set(facets.get(field, [])) & set(values))
               for field, values in filters.items())


def keyword_scores(query: str, records: list[dict]) -> list[float]:
    corpus = [tokenize(r['title']+' '+r['heading']+' '+r['text']) for r in records]
    if not corpus:
        return []
    try:
        from rank_bm25 import BM25Okapi
        return list(map(float, BM25Okapi(corpus).get_scores(tokenize(query))))
    except ImportError:
        # Deterministic dependency-free test/development fallback.
        terms = set(tokenize(query))
        return [float(sum(tokens.count(term) for term in terms)) for tokens in corpus]


def rrf(keyword_indices: list[int], semantic_indices: list[int], k: int = 60) -> dict[int, float]:
    scores: dict[int,float] = {}
    for ranked in (keyword_indices, semantic_indices):
        for rank, ix in enumerate(ranked, start=1):
            scores[ix] = scores.get(ix, 0.0) + 1.0/(k + rank)
    return scores


def search(records: list[dict], question: str, filters: dict[str, list[str]] | None = None,
           include_archived: bool = False, top_k: int = 5, semantic_index: Any = None,
           embedding_model: Any = None) -> list[dict]:
    filters = filters or {}
    candidates = [i for i,r in enumerate(records) if matches(r,filters,include_archived)]
    if not candidates:
        return []
    scores = keyword_scores(question, records)
    kw_rank = sorted(candidates, key=lambda i: scores[i], reverse=True)
    kw_rank = [i for i in kw_rank if scores[i] > 0][:40]
    sem_rank = []
    if semantic_index is not None and embedding_model is not None:
        import numpy as np
        vec = np.asarray(embedding_model.encode([question], normalize_embeddings=True), dtype='float32')
        # Search complete index; filter results below. Enough for <= 100 pages.
        _, idx = semantic_index.search(vec, len(records))
        allowed = set(candidates)
        sem_rank = [int(i) for i in idx[0] if int(i) in allowed][:40]
    fused = rrf(kw_rank, sem_rank)
    ranked = sorted(fused, key=lambda i:fused[i], reverse=True)[:top_k]
    return [{**records[i], 'score':round(fused[i],6)} for i in ranked]
