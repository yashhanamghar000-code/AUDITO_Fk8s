# NOTE: importing app.main boots a real QdrantClient connection, so this
# test needs `docker compose up qdrant` running, or QDRANT_URL pointed at
# any reachable Qdrant instance, before `pytest` is run.
import os
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
