from collections.abc import Generator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import algo
from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_overrides() -> Generator[None, None, None]:
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


def test_info_uses_dependency_overrides(client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_name="Test Gateway",
        app_version="1.2.3",
        environment="test",
        allowed_algos=["fixed_window"],
    )

    response = client.get("/info")

    assert response.status_code == 200
    assert response.json() == {
        "app_name": "Test Gateway",
        "version": "1.2.3",
        "environment": "test",
    }


def test_check_success(monkeypatch, client: TestClient) -> None:
    async def fake_dispatch(key: str, algo_name: str) -> algo.RateLimitResult:
        assert key == "user-1"
        assert algo_name == "fixed_window"
        return algo.RateLimitResult(
            allowed=True,
            remaining=4,
            reset_at=datetime(2026, 1, 1, 0, 0, 0),
        )

    from app import main as main_module

    monkeypatch.setattr(main_module, "dispatch_algo", fake_dispatch)

    response = client.post("/check", json={"key": "user-1", "algo": "fixed_window"})

    assert response.status_code == 200
    assert response.json() == {
        "allowed": True,
        "remaining": 4,
        "reset_at": "2026-01-01T00:00:00",
    }


def test_check_returns_400_for_invalid_algorithm(monkeypatch, client: TestClient) -> None:
    async def fake_dispatch(key: str, algo_name: str) -> algo.RateLimitResult:
        raise ValueError("Algorithm 'unknown' is not enabled")

    from app import main as main_module

    monkeypatch.setattr(main_module, "dispatch_algo", fake_dispatch)

    response = client.post("/check", json={"key": "user-1", "algo": "unknown"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Algorithm 'unknown' is not enabled"}


def test_check_returns_422_for_missing_fields(client: TestClient) -> None:
    response = client.post("/check", json={})

    assert response.status_code == 422
