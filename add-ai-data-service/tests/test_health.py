# NOTE: importing app.main opens a real DB connection, so this test
# needs `docker compose up postgres` running (or DATABASE_URL pointed at
# any reachable Postgres) before `pytest` is run.
import os
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/add_ai")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
