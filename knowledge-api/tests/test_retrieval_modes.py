"""Mode-switch regression tests; no live DeepSeek or FAISS model required."""
from __future__ import annotations
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from app.retrieval import matches, search

ROWS = [
    {'id': 'a', 'title': 'Python onboarding', 'heading': 'Guide', 'text': 'Python documentation',
     'url': '/a', 'facets': {'technologies': ['python'], 'lifecycle': ['current']}},
    {'id': 'b', 'title': 'OpenAPI docs', 'heading': 'Specs', 'text': 'OpenAPI documentation',
     'url': '/b', 'facets': {'technologies': ['openapi'], 'lifecycle': ['current']}},
    {'id': 'c', 'title': 'Retired REST API', 'heading': 'Deprecated', 'text': 'OpenAPI documentation',
     'url': '/c', 'facets': {'technologies': ['openapi'], 'lifecycle': ['archived']}},
]
TAXONOMY = {'version': 2, 'dimensions': {
    'technologies': {'metadata_field': 'technologies', 'terms': {
        'python': {'label': 'Python', 'governance': {'status': 'active'}},
        'openapi': {'label': 'OpenAPI', 'governance': {'status': 'active'}}}},
    'lifecycle': {'metadata_field': 'lifecycle', 'terms': {
        'current': {'label': 'Current', 'governance': {'status': 'active'}},
        'archived': {'label': 'Archived', 'governance': {'status': 'active'}}}},
}}

class FakeEncoder:
    def encode(self, values, normalize_embeddings=False):
        assert normalize_embeddings is True
        return [[1.0, 0.0]]

class FakeFaiss:
    def search(self, vec, size):
        assert size == len(ROWS)
        return [[0.99, 0.7, 0.4]], [[1, 0, 2]]


def test_modes_only_use_relevant_retrievers(monkeypatch):
    # BM25 works even when no FAISS components are installed / loaded.
    assert search(ROWS, 'Python', mode='bm25')[0]['id'] == 'a'
    # Semantic picks FakeFaiss ordering, excludes archived by policy.
    assert [r['id'] for r in search(ROWS, 'Python', semantic_index=FakeFaiss(),
                                      embedding_model=FakeEncoder(), mode='semantic')] == ['b', 'a']
    assert search(ROWS, 'Python', semantic_index=FakeFaiss(),
                  embedding_model=FakeEncoder(), mode='hybrid')
    with pytest.raises(ValueError, match='unavailable'):
        search(ROWS, 'Python', mode='semantic')


def test_lifecycle_and_explicit_facets_remain_enforced_for_modes():
    for mode in ('bm25', 'semantic', 'hybrid'):
        kwargs = {'semantic_index': FakeFaiss(), 'embedding_model': FakeEncoder()} if mode != 'bm25' else {}
        found = search(ROWS, 'OpenAPI', filters={'technologies': ['openapi']}, mode=mode, **kwargs)
        assert all('openapi' in r['facets']['technologies'] for r in found)
        assert not any('archived' in r['facets']['lifecycle'] for r in found)
    assert matches(ROWS[2], {'lifecycle': ['archived']}, False)


def client_with_state(monkeypatch, semantic=True):
    from app import main
    monkeypatch.setattr(main, 'taxonomy', lambda _repo: TAXONOMY)
    monkeypatch.setattr(main, 'snapshot', lambda: (
        {'source_hash': 'abcde1234500000', 'semantic_enabled': semantic},
        ROWS, FakeFaiss() if semantic else None, FakeEncoder() if semantic else None))
    return TestClient(main.app)


def test_api_explicit_modes_and_failures(monkeypatch):
    client = client_with_state(monkeypatch)
    for mode in ('bm25', 'semantic', 'hybrid'):
        res = client.post('/search', json={'query': 'Python', 'mode': mode})
        assert res.status_code == 200, res.text
        assert res.json()['mode'] == mode
    assert client.post('/search', json={'query': 'Python', 'mode': 'wrong'}).status_code == 422
    assert client.post('/search', json={'query': 'Python', 'filters': {
        'technologies': ['made-up']}}).status_code == 422
    client_no_semantic = client_with_state(monkeypatch, semantic=False)
    unavailable = client_no_semantic.post('/search', json={'query': 'Python', 'mode': 'semantic'})
    assert unavailable.status_code == 409
    fallback = client_no_semantic.post('/search', json={'query': 'Python', 'mode': 'hybrid'})
    assert fallback.status_code == 200
    assert fallback.json()['mode'] == 'bm25'


def test_chat_no_key_and_mocked_deepseek(monkeypatch):
    from app import main
    client = client_with_state(monkeypatch)
    monkeypatch.setattr(main.cfg, 'deepseek_api_key', '')
    denied = client.post('/chat', json={'query': 'Python experience', 'mode': 'bm25'})
    assert denied.status_code == 503
    calls = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            assert kwargs['api_key'] == 'test-key'

            class Completion:
                def create(self, **payload):
                    calls.append(payload)
                    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                        content='Python is discussed in the portfolio [1].'))])
            self.chat = SimpleNamespace(completions=Completion())

    monkeypatch.setitem(sys.modules, 'openai', SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setattr(main.cfg, 'deepseek_api_key', 'test-key')
    response = client.post('/chat', json={'query': 'Python experience', 'mode': 'bm25'})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['mode'] == 'bm25'
    assert body['sources'][0]['id'] == 1
    assert '[1]' in body['answer']
    assert calls and 'Python experience' in calls[0]['messages'][1]['content']
