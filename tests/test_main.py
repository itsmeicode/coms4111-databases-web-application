import pytest

# `fastapi.testclient` (Starlette TestClient) depends on `httpx`.
# If `httpx` isn't installed yet, skip tests instead of failing collection.
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_root() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Hello from FastAPI"}


def test_echo() -> None:
    resp = client.post("/echo", json={"message": "hi"})
    assert resp.status_code == 200
    assert resp.json() == {"message": "hi"}
