from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_redis_health() -> None:
    class HealthyRedisClient:
        async def ping(self) -> bool:
            return True

    app.dependency_overrides = {}
    from app import main as main_module

    main_module.get_redis_client = lambda: HealthyRedisClient()

    response = client.get("/redis-health")
    assert response.status_code == 200
    assert response.json() == {"status": "Redis is reachable"}


def test_redis_health_negative() -> None:
    class FailingRedisClient:
        async def ping(self) -> bool:
            raise RuntimeError("connection refused")

    app.dependency_overrides = {}
    from app import main as main_module

    main_module.get_redis_client = lambda: FailingRedisClient()

    response = client.get("/redis-health")
    assert response.status_code == 500
    assert "Redis connection error" in response.json()["detail"]
