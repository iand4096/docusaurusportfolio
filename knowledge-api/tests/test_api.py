from fastapi.testclient import TestClient
from app.api_schema import SearchResponse
from app.main import SearchRequest, app

def test_health():
    resp=TestClient(app).get('/health')
    assert resp.status_code==200 and 'index_loaded' in resp.json()


def test_exported_search_example_matches_request_and_response_models():
    operation = app.openapi()['paths']['/search']['post']
    request = operation['requestBody']['content']['application/json']['examples']['taxonomy-filter']
    response = operation['responses']['200']['content']['application/json']['examples']['taxonomy-filter']
    search = SearchRequest.model_validate(request['value'])
    result = SearchResponse.model_validate(response['value'])
    assert search.mode == result.mode
    assert 0 < len(result.results) <= search.top_k
    assert all(set(hit.facets['topics']) & set(search.filters['topics']) for hit in result.results)
