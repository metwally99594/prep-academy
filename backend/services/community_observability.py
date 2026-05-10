"""
Community Observability — timing metrics, correlation IDs, structured logging helpers.

No external dependencies (no Redis, no OpenTelemetry). Uses Python's logging
with structured key=value format for log aggregation tools.
"""
import time
import uuid
import logging
from contextvars import ContextVar
from typing import Optional, Callable
from functools import wraps

_logger = logging.getLogger(__name__)

# ── Correlation ID ──

_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> Optional[str]:
    return _correlation_id.get()


def set_correlation_id(cid: Optional[str] = None) -> str:
    if not cid:
        cid = uuid.uuid4().hex[:12]
    _correlation_id.set(cid)
    return cid


def reset_correlation_id():
    _correlation_id.set(None)


def with_correlation_id(func: Callable) -> Callable:
    """Decorator that ensures a correlation ID is set during function execution."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        cid = get_correlation_id()
        if not cid:
            set_correlation_id()
        try:
            return await func(*args, **kwargs)
        finally:
            pass

    return wrapper


# ── Timing context manager ──


class Timer:
    """Simple timer for measuring operation duration.

    Usage:
        timer = Timer()
        with timer:
            await some_operation()
        logger.info("op=duration ms=%.1f", timer.ms)
    """

    def __init__(self):
        self.start: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self.start

    @property
    def ms(self) -> float:
        return round(self.elapsed * 1000, 2)

    @property
    def sec(self) -> float:
        return round(self.elapsed, 4)


def timed(logger_override=None):
    """Decorator that logs function duration.

    Usage:
        @timed()
        async def my_func(...):
            ...

    Logs: "func=my_func duration_ms=42.0"
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            log = logger_override or _logger
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = (time.perf_counter() - start) * 1000
                cid = get_correlation_id() or "-"
                log.info("func=%s duration_ms=%.1f correlation_id=%s", func.__name__, elapsed, cid)
        return wrapper
    return decorator


# ── Structured logging helpers ──


def log_moderation_action(
    logger_obj: logging.Logger,
    action: str,
    target_type: str,
    target_id: str,
    admin_id: Optional[str] = None,
    severity: Optional[str] = None,
    duration_ms: Optional[float] = None,
    correlation_id: Optional[str] = None,
    **extra,
):
    """Emit a structured log line for moderation actions."""
    parts = [
        f"mod_action={action}",
        f"target_type={target_type}",
        f"target_id={target_id[:8] if target_id else '-'}",
    ]
    if admin_id:
        parts.append(f"admin_id={admin_id[:8]}")
    if severity:
        parts.append(f"severity={severity}")
    if duration_ms is not None:
        parts.append(f"duration_ms={duration_ms:.1f}")
    if correlation_id:
        parts.append(f"correlation_id={correlation_id}")
    for k, v in extra.items():
        parts.append(f"{k}={v}")
    logger_obj.info(" ".join(parts))


def log_notification_event(
    logger_obj: logging.Logger,
    event: str,
    user_id: Optional[str] = None,
    notification_type: Optional[str] = None,
    count: Optional[int] = None,
    duration_ms: Optional[float] = None,
    correlation_id: Optional[str] = None,
    **extra,
):
    """Emit a structured log line for notification events."""
    parts = [f"notif_event={event}"]
    if user_id:
        parts.append(f"user_id={user_id[:8]}")
    if notification_type:
        parts.append(f"type={notification_type}")
    if count is not None:
        parts.append(f"count={count}")
    if duration_ms is not None:
        parts.append(f"duration_ms={duration_ms:.1f}")
    if correlation_id:
        parts.append(f"correlation_id={correlation_id}")
    for k, v in extra.items():
        parts.append(f"{k}={v}")
    logger_obj.info(" ".join(parts))


def log_cache_event(
    logger_obj: logging.Logger,
    event: str,
    cache_key: Optional[str] = None,
    duration_ms: Optional[float] = None,
    correlation_id: Optional[str] = None,
    **extra,
):
    """Emit a structured log line for cache events."""
    parts = [f"cache_event={event}"]
    if cache_key:
        parts.append(f"key={cache_key[:60]}")
    if duration_ms is not None:
        parts.append(f"duration_ms={duration_ms:.1f}")
    if correlation_id:
        parts.append(f"correlation_id={correlation_id}")
    for k, v in extra.items():
        parts.append(f"{k}={v}")
    logger_obj.info(" ".join(parts))


def log_feed_event(
    logger_obj: logging.Logger,
    event: str,
    sort: Optional[str] = None,
    page_size: Optional[int] = None,
    result_count: Optional[int] = None,
    duration_ms: Optional[float] = None,
    cached: Optional[bool] = None,
    correlation_id: Optional[str] = None,
    **extra,
):
    """Emit a structured log line for feed building."""
    parts = [f"feed_event={event}"]
    if sort:
        parts.append(f"sort={sort}")
    if page_size is not None:
        parts.append(f"page_size={page_size}")
    if result_count is not None:
        parts.append(f"result_count={result_count}")
    if duration_ms is not None:
        parts.append(f"duration_ms={duration_ms:.1f}")
    if cached is not None:
        parts.append(f"cached={cached}")
    if correlation_id:
        parts.append(f"correlation_id={correlation_id}")
    for k, v in extra.items():
        parts.append(f"{k}={v}")
    logger_obj.info(" ".join(parts))
