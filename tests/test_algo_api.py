import asyncio
from datetime import datetime

import pytest

from app import algo



@pytest.fixture
def algo_registry_fixture(monkeypatch) -> list[str]:
	called: list[str] = []

	async def fixed_handler(key: str) -> algo.RateLimitResult:
		called.append(f"fixed:{key}")
		return algo.RateLimitResult(True, 10, datetime.now())

	async def sliding_handler(key: str) -> algo.RateLimitResult:
		called.append(f"sliding:{key}")
		return algo.RateLimitResult(True, 10, datetime.now())

	async def token_handler(key: str) -> algo.RateLimitResult:
		called.append(f"token:{key}")
		return algo.RateLimitResult(True, 10, datetime.now())

	monkeypatch.setattr(
		algo,
		"ALGO_REGISTRY",
		{
			"fixed_window": fixed_handler,
			"sliding_window": sliding_handler,
			"token_bucket": token_handler,
		},
	)
	monkeypatch.setattr(
		algo.settings,
		"allowed_algos",
		["fixed_window", "sliding_window", "token_bucket"],
	)

	return called


def test_algo_routes_to_correct_keys(algo_registry_fixture: list[str]) -> None:

	asyncio.run(algo.dispatch_algo("k1", "fixed_window"))
	asyncio.run(algo.dispatch_algo("k2", " sliding_window "))
	asyncio.run(algo.dispatch_algo("k3", "TOKEN_BUCKET"))

	assert algo_registry_fixture == ["fixed:k1", "sliding:k2", "token:k3"]
