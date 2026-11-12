from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_synthesize_rejects_empty_text():
    r = client.post("/synthesize", json={"text": "   "})
    assert r.status_code == 422
