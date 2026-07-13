import asyncio
from datetime import datetime as RealDateTime

import pytest

from app import algo


class FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str):
        return self.kv.get(key)

    async def set(self, key: str, value, ex: int | None = None):
        self.kv[key] = str(value)
        if ex is not None:
            self.ttls[key] = int(ex)
        return True

    async def incr(self, key: str):
        value = int(self.kv.get(key, "0")) + 1
        self.kv[key] = str(value)
        return value

    async def ttl(self, key: str):
        if key not in self.kv and key not in self.hashes:
            return -2
        return self.ttls.get(key, -1)

    async def expire(self, key: str, seconds: int):
        self.ttls[key] = int(seconds)
        return True

    async def hgetall(self, key: str):
        return self.hashes.get(key, {}).copy()

    async def hset(self, key: str, mapping: dict[str, str]):
        bucket = self.hashes.setdefault(key, {})
        bucket.update(mapping)
        return len(mapping)


class FrozenDateTime(RealDateTime):
    current = RealDateTime(2026, 1, 1, 0, 0, 0)

    @classmethod
    def now(cls, tz=None):
        if tz is not None:
            return cls.current.astimezone(tz)
        return cls.current


@pytest.fixture
def fake_env(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(algo, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(algo, "datetime", FrozenDateTime)
    monkeypatch.setattr(
        algo.settings,
        "allowed_algos",
        ["fixed_window", "sliding_window", "token_bucket"],
    )
    monkeypatch.setattr(algo.settings, "fixed_window_length", 10)
    monkeypatch.setattr(algo.settings, "fixed_window_limit", 2)
    monkeypatch.setattr(algo.settings, "sliding_window_length", 10)
    monkeypatch.setattr(algo.settings, "sliding_window_threshold", 2)
    monkeypatch.setattr(algo.settings, "token_bucket_burst_capacity", 2)
    monkeypatch.setattr(algo.settings, "token_bucket_refill_rate", 1.0)
    yield fake_redis


def test_fixed_window_allows_then_blocks(fake_env):
    r1 = asyncio.run(algo.fixed_window("user-a"))
    r2 = asyncio.run(algo.fixed_window("user-a"))
    r3 = asyncio.run(algo.fixed_window("user-a"))

    assert r1.allowed is True
    assert r2.allowed is True
    assert r3.allowed is False
    assert r1.remaining == 1
    assert r2.remaining == 0
    assert r3.remaining == 0


def test_fixed_window_isolated_per_key(fake_env):
    r1 = asyncio.run(algo.fixed_window("user-a"))
    r2 = asyncio.run(algo.fixed_window("user-b"))

    assert r1.allowed is True
    assert r2.allowed is True
    assert r1.remaining == 1
    assert r2.remaining == 1


def test_sliding_window_blocks_at_threshold(fake_env):
    FrozenDateTime.current = RealDateTime(2026, 1, 1, 0, 0, 0)

    r1 = asyncio.run(algo.sliding_window("user-a"))
    r2 = asyncio.run(algo.sliding_window("user-a"))
    r3 = asyncio.run(algo.sliding_window("user-a"))

    assert r1.allowed is True
    assert r2.allowed is True
    assert r3.allowed is False
    assert r3.remaining == 0


def test_token_bucket_consumes_and_denies_when_empty(fake_env):
    FrozenDateTime.current = RealDateTime(2026, 1, 1, 0, 0, 0)

    r1 = asyncio.run(algo.token_bucket_algo("user-a"))
    r2 = asyncio.run(algo.token_bucket_algo("user-a"))
    r3 = asyncio.run(algo.token_bucket_algo("user-a"))

    assert r1.allowed is True
    assert r2.allowed is True
    assert r3.allowed is False
    assert r2.remaining == 0
    assert r3.remaining == 0


def test_token_bucket_refills_over_time(fake_env):
    FrozenDateTime.current = RealDateTime(2026, 1, 1, 0, 0, 0)
    asyncio.run(algo.token_bucket_algo("user-a"))
    asyncio.run(algo.token_bucket_algo("user-a"))

    FrozenDateTime.current = RealDateTime(2026, 1, 1, 0, 0, 2)
    r = asyncio.run(algo.token_bucket_algo("user-a"))

    assert r.allowed is True
    assert r.remaining == 1


def test_dispatch_rejects_unknown_algorithm(fake_env):
    with pytest.raises(ValueError, match="not enabled"):
        asyncio.run(algo.dispatch_algo("user-a", "unknown"))


def test_token_bucket_invalid_stored_datetime_raises(fake_env):
    fake_env.hashes["token-bucket:user-a"] = {
        "tokens": "1",
        "last_refill": "not-a-date",
    }

    with pytest.raises(ValueError):
        asyncio.run(algo.token_bucket_algo("user-a"))
