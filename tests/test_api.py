"""API tests with FastAPI's TestClient. Run: python -m pytest  (needs requirements.txt installed)"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_ingest_sample_file():
    data = (ROOT / "sample_data" / "client_packaging_export.csv").read_bytes()
    res = client.post("/ingest", files={"file": ("export.csv", data, "text/csv")})
    assert res.status_code == 200
    body = res.json()
    assert len(body["products"]) == 4
    assert len(body["rejected"]) == 5
    assert body["products"][0]["country"] == "DE"


def test_unknown_client_returns_404():
    res = client.post("/ingest?client=unknown", files={"file": ("x.csv", b"a;b\n1;2\n", "text/csv")})
    assert res.status_code == 404


def test_empty_file_returns_400():
    res = client.post("/ingest", files={"file": ("x.csv", b"", "text/csv")})
    assert res.status_code == 400
