import os, tempfile
os.environ["BM25_CACHE_DIR"] = tempfile.mkdtemp()

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
