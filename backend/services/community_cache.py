"""In-memory TTL cache for community endpoints. No Redis dependency."""
import time
from typing import Any, Optional

_cache: dict[str, tuple[float, Any]] = {}
DEFAULT_TTL = 45


def cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.time() > expires_at:
        del _cache[key]
        return None
    return value


def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL):
    _cache[key] = (time.time() + ttl, value)


def cache_invalidate(pattern: Optional[str] = None):
    if pattern is None:
        _cache.clear()
        return
    to_delete = [k for k in _cache if pattern in k]
    for k in to_delete:
        del _cache[k]


def build_cache_key(prefix: str, **params) -> str:
    parts = [prefix]
    for k, v in sorted(params.items()):
        if v is not None:
            parts.append(f"{k}={v}")
    return ":".join(parts)
