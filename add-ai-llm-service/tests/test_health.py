import os
os.environ.setdefault("MISTRAL_API_KEY", "dummy")
os.environ.setdefault("MISTRAL_ENDPOINT", "https://api.mistral.ai/v1")
os.environ.setdefault("MISTRAL_MODEL", "mistral-large-latest")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
