from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil, floor
from typing import Awaitable, Callable

from app.config import get_settings
from app.redis import get_redis_client


@dataclass
class BucketConf:
    counter: int | float
    timestamp: datetime


@dataclass
class BucketPair:
    old_bucket: BucketConf
    current_bucket: BucketConf


settings = get_settings()
fixed_bucket: dict[str, BucketConf] = {}
sliding_bucket: dict[str, BucketPair] = {}
token_bucket: dict[str, BucketConf] = {}


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int | float
    reset_at: datetime


AlgoHandler = Callable[[str], Awaitable[RateLimitResult]]


async def dispatch_algo(key: str, algo_name: str) -> RateLimitResult:
    normalized_algo = algo_name.strip().lower()
    enabled_algos = {algo.strip().lower() for algo in settings.allowed_algos}

    if normalized_algo not in enabled_algos:
        raise ValueError(f"Algorithm '{algo_name}' is not enabled")

    handler = ALGO_REGISTRY.get(normalized_algo)
    if handler is None:
        raise ValueError(f"Algorithm '{algo_name}' is enabled but not implemented")

    return await handler(key)


async def fixed_window(key: str) -> RateLimitResult:
    now = datetime.now()
    redis = get_redis_client()
    redis_key = f"fixed-window:{key}"
    counter = await redis.get(redis_key)
    ttl = await redis.ttl(redis_key)

    if counter is None:
        await redis.set(redis_key, 1, ex=settings.fixed_window_length)
    else:
        counter = await redis.incr(redis_key)
    allowed = (counter is None) or (int(counter) <= settings.fixed_window_limit)
    remaining_requests = max(
        0, settings.fixed_window_limit - int(counter if counter is not None else 1)
    )
    reset_at = now + timedelta(seconds=ttl if ttl > 0 else settings.fixed_window_length)

    return RateLimitResult(allowed=allowed, remaining=remaining_requests, reset_at=reset_at)


async def sliding_window(key: str) -> RateLimitResult:
    now = datetime.now()
    redis = get_redis_client()
    window_size = settings.sliding_window_length
    current_window = floor(now.timestamp() / window_size)
    old_window = current_window - 1
    current_key = f"sliding-window:{key}:{current_window}"
    old_key = f"sliding-window:{key}:{old_window}"
    elapsed = (now.timestamp() % window_size) / window_size
    reset_at = datetime.fromtimestamp((current_window + 1) * window_size)

    prev = await redis.get(old_key) or 0
    cur = await redis.get(current_key) or 0

    weighted_prev = (int(prev) if prev is not None else 0) * (1 - elapsed)
    estimated = weighted_prev + (int(cur) if cur is not None else 0)
    if estimated >= settings.sliding_window_threshold:
        allowed = False
        remaining_requests = 0
        return RateLimitResult(allowed=allowed, remaining=remaining_requests, reset_at=reset_at)
    new_count = await redis.incr(current_key)
    if new_count == 1:
        await redis.expire(current_key, window_size * 2)
    new_estimate = weighted_prev + new_count
    remaining_requests = max(0, floor(settings.sliding_window_threshold - new_estimate))
    allowed = True
    return RateLimitResult(allowed, remaining_requests, reset_at)


async def token_bucket_algo(key: str) -> RateLimitResult:
    now = datetime.now()
    redis = get_redis_client()
    redis_key = f"token-bucket:{key}"
    max_tokens = settings.token_bucket_burst_capacity
    refill_rate = settings.token_bucket_refill_rate
    tokens = max_tokens
    last_refill = now

    data = await redis.hgetall(redis_key)
    if data:
        tokens = float(data.get("tokens", max_tokens))
        raw_last_refill = data.get("last_refill")
        if raw_last_refill:
            if isinstance(raw_last_refill, bytes):
                raw_last_refill = raw_last_refill.decode()
            elif isinstance(raw_last_refill, (bytearray, memoryview)):
                raw_last_refill = bytes(raw_last_refill).decode()
            last_refill = datetime.fromisoformat(raw_last_refill)

    elapsed = (now - last_refill).total_seconds()
    new_tokens = elapsed * refill_rate
    tokens = min(max_tokens, tokens + new_tokens)

    allowed = False
    remaining_request = tokens

    if remaining_request >= 1:
        remaining_request -= 1
        allowed = True
    await redis.hset(
        redis_key, mapping={"tokens": str(remaining_request), "last_refill": str(now.isoformat())}
    )
    await redis.expire(redis_key, ceil(max_tokens / refill_rate) + 1)
    reset_at = now + timedelta(seconds=(max_tokens - remaining_request) / refill_rate)
    return RateLimitResult(allowed, remaining_request, reset_at)


ALGO_REGISTRY: dict[str, AlgoHandler] = {
    "fixed_window": fixed_window,
    "sliding_window": sliding_window,
    "token_bucket": token_bucket_algo,
}
