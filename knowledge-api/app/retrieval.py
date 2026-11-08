"""Governed BM25, FAISS and RRF hybrid retrieval over an immutable local index.

The optional mode argument is last for backwards compatibility with the MVP.
"""
from __future__ import annotations
import re
from typing import Any, Literal

RetrievalMode = Literal['bm25', 'semantic', 'hybrid']


def tokenize(text: str) -> list[str]:
    return re.findall(r'[a-z0-9][a-z0-9+_.-]*', text.lower())


def matches(row: dict, filters: dict[str, list[str]], include_archived: bool) -> bool:
    facets = row.get('facets') or {}
    lifecycle = facets.get('lifecycle') or []
    explicit = filters.get('lifecycle', [])
    # Explicit lifecycle filter is authoritative; opt-in to archived in search UI.
    if not (include_archived or 'archived' in explicit) and 'archived' in lifecycle:
        return False
    # OR within each facet; AND across different facets.
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
        # Fallback for unit tests only. Docker installs rank-bm25.
        terms = set(tokenize(query))
        return [float(sum(tokens.count(term) for term in terms)) for tokens in corpus]


def rrf(keyword_indices: list[int], semantic_indices: list[int], k: int = 60) -> dict[int, float]:
    fused: dict[int, float] = {}
    for ranking in (keyword_indices, semantic_indices):
        for rank, ix in enumerate(ranking, 1):
            fused[ix] = fused.get(ix, 0.0) + 1.0 / (k + rank)
    return fused


def search(records: list[dict], question: str, filters: dict[str, list[str]] | None = None,
           include_archived: bool = False, top_k: int = 5, semantic_index: Any = None,
           embedding_model: Any = None, mode: RetrievalMode = 'hybrid') -> list[dict]:
    if mode not in ('bm25', 'semantic', 'hybrid'):
        raise ValueError(f'Unknown retrieval mode: {mode}')
    if mode == 'semantic' and (semantic_index is None or embedding_model is None):
        raise ValueError('Semantic index unavailable')
    filters = filters or {}
    eligible = [i for i, row in enumerate(records) if matches(row, filters, include_archived)]
    if not eligible:
        return []
    kw_rank: list[int] = []
    sem_rank: list[int] = []
    if mode in ('bm25', 'hybrid'):
        scores = keyword_scores(question, records)
        # BM25 may give zero or negative scores for real matches in a tiny corpus.
        # Detect lexical hits by token overlap; use BM25 only for their ranking.
        query_terms = set(tokenize(question))
        kw_rank = sorted(
            (i for i in eligible if query_terms.intersection(
                tokenize(records[i]['title'] + ' ' + records[i]['heading'] + ' ' + records[i]['text'])
            )),
            key=lambda i: (-scores[i], i),
        )[:40]
    if mode in ('semantic', 'hybrid') and semantic_index is not None and embedding_model is not None:
        import numpy as np
        vec = np.asarray(embedding_model.encode([question], normalize_embeddings=True), dtype='float32')
        # Search the whole small index, then filter all candidate ranks before top_k.
        _, ids = semantic_index.search(vec, len(records))
        allowed = set(eligible)
        sem_rank = [int(i) for i in ids[0] if int(i) in allowed][:40]
    fused = rrf(kw_rank, sem_rank)
    ranked = sorted(fused, key=lambda i: (-fused[i], i))[:top_k]
    return [{**records[i], 'score': round(fused[i], 6)} for i in ranked]
