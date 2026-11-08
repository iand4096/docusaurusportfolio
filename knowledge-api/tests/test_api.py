from fastapi.testclient import TestClient
from app.main import app

def test_health():
    resp=TestClient(app).get('/health')
    assert resp.status_code==200 and 'index_loaded' in resp.json()
