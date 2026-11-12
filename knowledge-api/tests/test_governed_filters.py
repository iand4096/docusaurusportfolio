"""Regressions for canonical facet validation and lifecycle behavior."""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.governance_filters import taxonomy_dimensions, validate_filters
from app.retrieval import matches, search

TAXONOMY = {
    'version': 2,
    'dimensions': {
        'content_types': {'metadata_field': 'type', 'terms': {
            'case-study': {'label': 'Case study', 'governance': {'status': 'active'}}}},
        'audiences': {'metadata_field': 'audiences', 'terms': {
            'developers': {'label': 'Developers', 'governance': {'status': 'active'}}}},
        'topics': {'metadata_field': 'topics', 'terms': {
            'taxonomy': {'label': 'Taxonomy', 'governance': {'status': 'active'}},
            'retired-term': {'label': 'Retired', 'governance': {'status': 'deprecated'}}}},
        'technologies': {'metadata_field': 'technologies', 'terms': {
            'openapi': {'label': 'OpenAPI', 'governance': {'status': 'active'}},
            'python': {'label': 'Python', 'governance': {'status': 'active'}}}},
        'lifecycle': {'metadata_field': 'lifecycle', 'terms': {
            'current': {'label': 'Current', 'governance': {'status': 'active'}},
            'historical': {'label': 'Historical', 'governance': {'status': 'active'}},
            'archived': {'label': 'Archived', 'governance': {'status': 'active'}}}},
    },
}
DIMS = taxonomy_dimensions(TAXONOMY)

ROWS = [
    {'id': 'a', 'title': 'API taxonomy', 'heading': 'Governance',
     'text': 'OpenAPI taxonomy governance documentation', 'url': '/docs/a',
     'facets': {'type': ['case-study'], 'audiences': ['developers'],
                'topics': ['taxonomy'], 'technologies': ['openapi'], 'lifecycle': ['current']}},
    {'id': 'b', 'title': 'Old API taxonomy', 'heading': 'Governance',
     'text': 'OpenAPI taxonomy governance documentation', 'url': '/docs/b',
     'facets': {'type': ['case-study'], 'audiences': ['developers'],
                'topics': ['taxonomy'], 'technologies': ['openapi'], 'lifecycle': ['archived']}},
    {'id': 'c', 'title': 'Python API', 'heading': '',
     'text': 'Python documentation without OpenAPI', 'url': '/docs/c',
     'facets': {'type': ['case-study'], 'audiences': ['developers'],
                'topics': ['taxonomy'], 'technologies': ['python'], 'lifecycle': ['historical']}},
]


def test_dimensions_use_metadata_field_and_active_ids():
    assert sorted(DIMS) == ['audiences', 'lifecycle', 'technologies', 'topics', 'type']
    assert 'retired-term' not in DIMS['topics']['terms']


@pytest.mark.parametrize('filters', [
    {'made_up': ['openapi']}, {'technologies': ['OpenAPI']},
    {'technologies': ['not-a-term']}, {'technologies': []},
    {'topics': ['retired-term']},
])
def test_rejects_invalid_filters(filters):
    with pytest.raises(HTTPException) as info:
        validate_filters(filters, DIMS)
    assert info.value.status_code == 422


def test_valid_filters_deduplicated():
    assert validate_filters({'technologies': ['openapi', 'openapi']}, DIMS) == {'technologies': ['openapi']}


def test_or_within_and_between_facets():
    filters = validate_filters({'technologies': ['openapi', 'python'], 'lifecycle': ['current']}, DIMS)
    assert [r['id'] for r in search(ROWS, 'documentation taxonomy', filters=filters)] == ['a']


def test_filter_applied_before_top_k():
    filters = validate_filters({'technologies': ['python']}, DIMS)
    assert [r['id'] for r in search(ROWS, 'documentation', filters=filters, top_k=1)] == ['c']


def test_archived_excluded_by_default_but_explicitly_available():
    assert not matches(ROWS[1], {}, False)
    assert matches(ROWS[1], {'lifecycle': ['archived']}, False)
    assert [r['id'] for r in search(ROWS, 'OpenAPI', filters={'lifecycle': ['archived']})] == ['b']
    assert [r['id'] for r in search(ROWS, 'OpenAPI', filters={'lifecycle': ['current']}, include_archived=True)] == ['a']
    assert set(r['id'] for r in search(ROWS, 'OpenAPI', include_archived=True)) == {'a', 'b', 'c'}


def test_api_returns_422_and_filtered_results(monkeypatch):
    from app import main
    monkeypatch.setattr(main, 'taxonomy', lambda _repo: TAXONOMY)
    monkeypatch.setattr(main, 'snapshot', lambda: (
        {'source_hash': 'abcdef1234567890', 'semantic_enabled': False}, ROWS, None, None))
    client = TestClient(main.app)
    r = client.get('/taxonomy')
    assert r.status_code == 200
    assert 'openapi' in r.json()['dimensions']['technologies']['terms']
    bad = client.post('/search', json={'query': 'OpenAPI', 'filters': {'technologies': ['invalid']}})
    assert bad.status_code == 422
    ok = client.post('/search', json={'query': 'OpenAPI', 'filters': {
        'technologies': ['openapi'], 'lifecycle': ['current']}, 'top_k': 5})
    assert ok.status_code == 200
    assert [x['id'] for x in ok.json()['results']] == ['a']
    archived = client.post('/search', json={'query': 'OpenAPI', 'filters': {'lifecycle': ['archived']}})
    assert archived.status_code == 200
    assert [x['id'] for x in archived.json()['results']] == ['b']


def test_api_exclusions_are_validated_and_applied(monkeypatch):
    from app import main
    monkeypatch.setattr(main, 'taxonomy', lambda _repo: TAXONOMY)
    monkeypatch.setattr(main, 'snapshot', lambda: (
        {'source_hash': 'abcdef1234567890', 'semantic_enabled': False}, ROWS, None, None))
    client = TestClient(main.app)
    bad = client.post('/search', json={'query': 'OpenAPI',
        'exclude_filters': {'lifecycle': ['invalid']}})
    assert bad.status_code == 422
    ok = client.post('/search', json={'query': 'OpenAPI', 'include_archived': True,
        'exclude_filters': {'lifecycle': ['archived']}})
    assert ok.status_code == 200
    assert [row['id'] for row in ok.json()['results']] == ['a']
