import time
import hashlib
import threading
from collections import defaultdict, deque
from typing import Optional, Set, Tuple
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.core.config import settings


class RateLimiter:
    """
    In-memory Sliding Window Rate Limiter.
    Tracks requests per client identifier (API Key / Bearer token or Client IP)
    over a rolling time window (default 60 seconds).
    """

    def __init__(
        self,
        requests_per_minute: Optional[int] = None,
        window_seconds: int = 60,
        enabled: Optional[bool] = None,
    ):
        self._requests_per_minute = (
            requests_per_minute
            if requests_per_minute is not None
            else getattr(settings, "rate_limit_requests_per_minute", 60)
        )
        self.window_seconds = window_seconds
        self._enabled = (
            enabled
            if enabled is not None
            else getattr(settings, "rate_limit_enabled", True)
        )
        self._clients = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Run garbage collection every 5 minutes

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    @property
    def requests_per_minute(self) -> int:
        return self._requests_per_minute

    @requests_per_minute.setter
    def requests_per_minute(self, value: int):
        self._requests_per_minute = max(1, value)

    def extract_client_identifier(self, request: Request) -> str:
        """
        Derives client identifier from authentication token or client IP.
        Prioritizes X-API-Key and Bearer token over IP to prevent shared IP throttling
        for distinct authenticated users.
        """
        # 1. API Key Header
        api_key = request.headers.get("x-api-key")
        if api_key:
            hashed = hashlib.sha256(api_key.strip().encode()).hexdigest()[:16]
            return f"key:{hashed}"

        # 2. Bearer Token Header
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            if token:
                hashed = hashlib.sha256(token.encode()).hexdigest()[:16]
                return f"token:{hashed}"

        # 3. Client IP (accounts for reverse proxies / CDNs like Cloudflare, Render, AWS ALB)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # First IP in chain is the original client IP
            client_ip = forwarded_for.split(",")[0].strip()
            return f"ip:{client_ip}"

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return f"ip:{real_ip.strip()}"

        client_host = request.client.host if request.client else "127.0.0.1"
        return f"ip:{client_host}"

    def is_allowed(self, key: str) -> Tuple[bool, int, int, int]:
        """
        Checks whether the key is permitted to make a request.
        Returns:
            (allowed: bool, remaining: int, retry_after: int, reset_epoch: int)
        """
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            # Run periodic cleanup to prevent unbounded dictionary growth
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup_expired(now)

            timestamps = self._clients[key]

            # Evict timestamps outside rolling window
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            current_count = len(timestamps)

            if current_count >= self._requests_per_minute:
                # Rate limit exceeded
                oldest_timestamp = timestamps[0]
                retry_after = max(1, int(oldest_timestamp + self.window_seconds - now) + 1)
                reset_epoch = int(oldest_timestamp + self.window_seconds)
                return False, 0, retry_after, reset_epoch

            # Request allowed: register timestamp
            timestamps.append(now)
            remaining = max(0, self._requests_per_minute - (current_count + 1))
            reset_epoch = int(now + self.window_seconds)
            return True, remaining, 0, reset_epoch

    def reset(self, key: Optional[str] = None):
        """Clears request history for a specific key or all keys (useful in tests)."""
        with self._lock:
            if key is not None:
                self._clients.pop(key, None)
            else:
                self._clients.clear()

    def _cleanup_expired(self, now: float):
        """Evicts client entries with no activity within the window."""
        cutoff = now - self.window_seconds
        expired_keys = [
            k for k, q in self._clients.items()
            if not q or q[-1] <= cutoff
        ]
        for k in expired_keys:
            del self._clients[k]
        self._last_cleanup = now


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI / Starlette middleware enforcing rolling window rate limits.
    Injects standard rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
    and returns HTTP 429 Too Many Requests with Retry-After when exceeded.
    """

    EXEMPT_PATHS: Set[str] = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    }

    def __init__(self, app, limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.limiter = limiter or rate_limiter

    async def dispatch(self, request: Request, call_next):
        # 1. Skip if rate limiting is globally disabled
        if not self.limiter.enabled:
            return await call_next(request)

        # 2. Skip exempt HTTP methods (CORS preflight OPTIONS requests)
        if request.method == "OPTIONS":
            return await call_next(request)

        # 3. Skip exempt paths (e.g. liveness probes, documentation)
        path = request.url.path
        if path in self.EXEMPT_PATHS or any(path.startswith(f"{ep}/") for ep in self.EXEMPT_PATHS):
            return await call_next(request)

        # 4. Resolve client identifier and evaluate rate limit
        client_key = self.limiter.extract_client_identifier(request)
        allowed, remaining, retry_after, reset_epoch = self.limiter.is_allowed(client_key)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Maximum {self.limiter.requests_per_minute} requests per minute allowed.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.limiter.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_epoch),
                },
            )

        # 5. Process request and attach rate limit telemetry headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_epoch)
        return response
