from __future__ import annotations

from typing import Callable

from tenacity import AsyncRetrying, RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_exponential


def retry_on_exception(max_attempts: int = 3, wait_multiplier: float = 1.0):
    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=wait_multiplier, min=1, max=10),
        retry=retry_if_exception_type(Exception),
    )


async def execute_with_retry(fn: Callable[..., Any], *args, **kwargs):
    try:
        async for attempt in AsyncRetrying(
            reraise=True,
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(Exception),
        ):
            return await fn(*args, **kwargs)
    except RetryError as exc:
        raise exc.last_attempt.exception() from exc
