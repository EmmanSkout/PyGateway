from functools import lru_cache

import redis.asyncio as redis

from app.config import get_settings


async def close_redis_client(client: redis.Redis) -> None:
    """
    Close the Redis client connection.

    Args:
        client (redis.Redis): The Redis client instance to close.
    """
    await client.aclose()


@lru_cache()
def get_redis_client() -> redis.Redis:
    """
    Get a Redis client instance with caching.

    Returns:
        redis.Redis: An instance of the Redis client.
    """
    redis_settings = get_settings()
    return redis.Redis(
        host=redis_settings.redis_host,
        port=redis_settings.redis_port,
        decode_responses=True,
    )
