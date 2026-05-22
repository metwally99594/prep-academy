import asyncio
import logging
import random
from typing import TypeVar, Callable, Awaitable, Optional
from functools import wraps
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_status: tuple = (429, 500, 502, 503, 504)


OPENROUTER_RETRY = RetryConfig(max_attempts=3, initial_delay=2.0, max_delay=20.0)
WIKIMEDIA_RETRY = RetryConfig(max_attempts=2, initial_delay=1.0, max_delay=5.0)
OPENVERSE_RETRY = RetryConfig(max_attempts=2, initial_delay=1.0, max_delay=5.0)
PUBMED_RETRY = RetryConfig(max_attempts=3, initial_delay=1.0, max_delay=10.0)


async def retry_async(
    func: Callable[[], Awaitable[T]],
    config: Optional[RetryConfig] = None,
    operation_name: str = "operation",
) -> Optional[T]:
    config = config or RetryConfig()
    for attempt in range(1, config.max_attempts + 1):
        try:
            result = await func()
            if attempt > 1:
                logger.info(f"{operation_name} succeeded on attempt {attempt}")
            return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code not in config.retry_on_status:
                logger.warning(f"{operation_name} got non-retryable {e.response.status_code}, giving up")
                return None
            logger.warning(f"{operation_name} attempt {attempt}/{config.max_attempts} got {e.response.status_code}")
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
            logger.warning(f"{operation_name} attempt {attempt}/{config.max_attempts} network error: {e}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"{operation_name} attempt {attempt}/{config.max_attempts} failed: {e}")
        if attempt == config.max_attempts:
            break
        delay = min(
            config.initial_delay * (config.exponential_base ** (attempt - 1)),
            config.max_delay
        )
        if config.jitter:
            delay *= (0.5 + random.random())
        await asyncio.sleep(delay)
    logger.error(f"{operation_name} failed after {config.max_attempts} attempts")
    return None


def with_retry(config: Optional[RetryConfig] = None, name: Optional[str] = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            op_name = name or func.__name__
            return await retry_async(
                lambda: func(*args, **kwargs),
                config=config,
                operation_name=op_name,
            )
        return wrapper
    return decorator
