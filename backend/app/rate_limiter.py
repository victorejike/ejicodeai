import asyncio
import time
from collections import defaultdict

from fastapi.responses import JSONResponse
from fastapi.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.config import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple IP-based rate limiting middleware."""

    def __init__(self, app, max_requests: int, window_seconds: int):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        key = f"{client_ip}:{request.url.path}"

        async with self.lock:
            timestamps = self.requests[key]
            while timestamps and timestamps[0] <= now - self.window_seconds:
                timestamps.pop(0)
            if len(timestamps) >= self.max_requests:
                return JSONResponse(
                    {"detail": "Rate limit exceeded. Please try again later."},
                    status_code=429,
                )
            timestamps.append(now)
            self.requests[key] = timestamps

        return await call_next(request)
