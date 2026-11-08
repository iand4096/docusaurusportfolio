"""Regression: BM25 IDF may be nonpositive on tiny corpora."""
from app import retrieval

ROWS = [
    {'id': 'a', 'title': 'OpenAPI', 'heading': 'Guide', 'text': 'API governance',
     'facets': {'lifecycle': ['current']}},
    {'id': 'b', 'title': 'API basics', 'heading': 'OpenAPI', 'text': 'Overview',
     'facets': {'lifecycle': ['current']}},
    {'id': 'c', 'title': 'Python', 'heading': 'Tutorial', 'text': 'Testing',
     'facets': {'lifecycle': ['current']}},
]


def test_zero_and_negative_bm25_scores_do_not_discard_real_matches(monkeypatch):
    monkeypatch.setattr(retrieval, 'keyword_scores', lambda *_: [0.0, -0.25, 10.0])
    results = retrieval.search(ROWS, 'OpenAPI', mode='bm25')
    assert [r['id'] for r in results] == ['a', 'b']


def test_hybrid_without_semantic_index_uses_lexical_matches(monkeypatch):
    monkeypatch.setattr(retrieval, 'keyword_scores', lambda *_: [0.0, -0.25, 10.0])
    assert [r['id'] for r in retrieval.search(ROWS, 'OpenAPI', mode='hybrid')] == ['a', 'b']


def test_no_keyword_overlap_means_no_bm25_result(monkeypatch):
    monkeypatch.setattr(retrieval, 'keyword_scores', lambda *_: [12.0, 13.0, 14.0])
    assert retrieval.search(ROWS, 'kubernetes', mode='bm25') == []
