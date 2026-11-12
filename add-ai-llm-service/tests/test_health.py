import os

# The service builds its provider client at import time.
os.environ.setdefault("LLM_PROVIDER", "anthropic")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-not-a-real-key")
os.environ.setdefault("ANTHROPIC_MODEL", "claude-opus-5-5")

from fastapi.testclient import TestClient
import app.main as main

client = TestClient(main.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
