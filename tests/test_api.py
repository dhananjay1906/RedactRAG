import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)

# Every PII value planted in the policy docs (names, phones, emails, case numbers).
POLICY_PII = [v for d in json.loads(Path("data/policies/manifest.json").read_text(encoding="utf-8"))
              for v in d["pii"].values()]

def test_health():
    assert client.get("/health").json() == {"status": "ok"}

def test_search_is_masked():
    rows = client.get("/search", params={"q": "records request contact", "k": 20}).json()
    assert rows
    leaked = [v for r in rows for v in POLICY_PII if v in r["content"]]
    assert not leaked, leaked

def test_search_k_is_capped():
    assert client.get("/search", params={"q": "x", "k": 1000}).status_code == 422
    assert client.get("/search", params={"q": "x", "k": 0}).status_code == 422

def test_ask_rejects_bad_input():
    assert client.post("/ask", json={}).status_code == 422
