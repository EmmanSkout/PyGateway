from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from app.config import get_settings


@dataclass
class BucketConf:
    counter: int
    timestamp: datetime
    
@dataclass
class BucketPair:
    old_bucket: BucketConf
    current_bucket: BucketConf
    


settings = get_settings()
fixed_bucket: dict[str, BucketConf] = {}
sliding_bucket: dict[str,BucketPair] = {}

@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_at: datetime


AlgoHandler = Callable[[str], RateLimitResult]


def dispatch_algo(key: str, algo_name: str) -> RateLimitResult:
    normalized_algo = algo_name.strip().lower()
    enabled_algos = {algo.strip().lower() for algo in settings.allowed_algos}

    if normalized_algo not in enabled_algos:
        raise ValueError(f"Algorithm '{algo_name}' is not enabled")

    handler = ALGO_REGISTRY.get(normalized_algo)
    if handler is None:
        raise ValueError(f"Algorithm '{algo_name}' is enabled but not implemented")

    return handler(key)


def fixed_window(key: str) -> RateLimitResult:
    now = datetime.now()
    bucket = fixed_bucket.get(key)

    if bucket is None:
        bucket = BucketConf(counter=1, timestamp=now)
        fixed_bucket[key] = bucket
    else:
        elapsed = (now - bucket.timestamp).total_seconds()
        if elapsed >= settings.fixed_window_length:
            bucket.counter = 1
            bucket.timestamp = now
        else:
            bucket.counter += 1

    allowed = bucket.counter <= settings.fixed_window_limit
    remaining_requests = max(0, settings.fixed_window_limit - bucket.counter)
    reset_at = bucket.timestamp + timedelta(seconds=settings.fixed_window_length)

    return RateLimitResult(allowed=allowed, remaining=remaining_requests, reset_at=reset_at)


def sliding_window(key: str) -> RateLimitResult:
    now = datetime.now()
    buckets = sliding_bucket.get(key)
    elapsed: float = 0
    if(buckets is None):
        cur = BucketConf(counter=1, timestamp=now)
        buckets = BucketPair(old_bucket=BucketConf(counter=0, timestamp=now), current_bucket=cur)
        sliding_bucket[key] = buckets
    else:
        currentBucket = buckets.current_bucket
        oldBucket = buckets.old_bucket
        elapsed = (now - currentBucket.timestamp).total_seconds()
        if elapsed >= settings.sliding_window_length:
            oldBucket.counter = currentBucket.counter
            oldBucket.timestamp = currentBucket.timestamp
            currentBucket.counter = 1
            currentBucket.timestamp = now
            elapsed = 0
        else:
            currentBucket.counter += 1

    effective = buckets.current_bucket.counter + buckets.old_bucket.counter * (
        1 - elapsed / settings.sliding_window_length
    )
    allowed = effective <= settings.sliding_window_threshold
    remaining_requests = max(0, int(settings.sliding_window_threshold - effective))
    reset_at = buckets.current_bucket.timestamp + timedelta(seconds=settings.sliding_window_length)
    return RateLimitResult(allowed, remaining_requests, reset_at)
        
            
        

def token_bucket(key: str) -> RateLimitResult:
    return RateLimitResult(True,0,datetime.now())
    


ALGO_REGISTRY: dict[str, AlgoHandler] = {
    "fixed_window": fixed_window,
    "sliding_window": sliding_window,
}






