from __future__ import annotations

from typing import Optional

import redis

from app.shared.config import settings

_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.REDIS_URL.strip(),
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis_client


def redis_available() -> bool:
    if not settings.REDIS_URL.strip():
        return False
    try:
        return bool(get_redis().ping())
    except Exception:
        return False


def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None
