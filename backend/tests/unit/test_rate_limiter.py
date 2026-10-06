import time
import pytest
from starlette.requests import Request
from starlette.datastructures import Headers
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.rate_limiter import RateLimiter, rate_limiter


def create_mock_request(
    path: str = "/api/test",
    method: str = "GET",
    headers: dict = None,
    client_host: str = "192.168.1.100"
) -> Request:
    raw_headers = []
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": raw_headers,
        "client": (client_host, 12345),
    }
    return Request(scope)


def test_rate_limiter_unit_basic_allowing_and_blocking():
    limiter = RateLimiter(requests_per_minute=3, window_seconds=60, enabled=True)
    key = "ip:10.0.0.1"

    # Request 1
    allowed, remaining, retry_after, reset_epoch = limiter.is_allowed(key)
    assert allowed is True
    assert remaining == 2
    assert retry_after == 0

    # Request 2
    allowed, remaining, retry_after, reset_epoch = limiter.is_allowed(key)
    assert allowed is True
    assert remaining == 1

    # Request 3
    allowed, remaining, retry_after, reset_epoch = limiter.is_allowed(key)
    assert allowed is True
    assert remaining == 0

    # Request 4 -> should be rejected with 429 conditions
    allowed, remaining, retry_after, reset_epoch = limiter.is_allowed(key)
    assert allowed is False
    assert remaining == 0
    assert retry_after >= 1
    assert reset_epoch > time.time()


def test_rate_limiter_reset():
    limiter = RateLimiter(requests_per_minute=2, window_seconds=60, enabled=True)
    key = "ip:10.0.0.2"

    limiter.is_allowed(key)
    limiter.is_allowed(key)
    allowed, _, _, _ = limiter.is_allowed(key)
    assert allowed is False

    # Reset specifically this key
    limiter.reset(key)
    allowed, remaining, _, _ = limiter.is_allowed(key)
    assert allowed is True
    assert remaining == 1

    # Reset all
    limiter.reset()
    assert len(limiter._clients) == 0


def test_extract_client_identifier_priorities():
    limiter = RateLimiter()

    # 1. API Key Header
    req_api_key = create_mock_request(headers={"X-API-Key": "my-secret-key-123"})
    id_key = limiter.extract_client_identifier(req_api_key)
    assert id_key.startswith("key:")

    # 2. Bearer Token Header
    req_bearer = create_mock_request(headers={"Authorization": "Bearer jwt-token-abc"})
    id_bearer = limiter.extract_client_identifier(req_bearer)
    assert id_bearer.startswith("token:")

    # 3. X-Forwarded-For Header
    req_forwarded = create_mock_request(headers={"X-Forwarded-For": "203.0.113.195, 70.41.3.18"})
    id_forwarded = limiter.extract_client_identifier(req_forwarded)
    assert id_forwarded == "ip:203.0.113.195"

    # 4. X-Real-IP Header
    req_real_ip = create_mock_request(headers={"X-Real-IP": "198.51.100.42"})
    id_real_ip = limiter.extract_client_identifier(req_real_ip)
    assert id_real_ip == "ip:198.51.100.42"

    # 5. Direct client IP fallback
    req_direct = create_mock_request(client_host="192.168.1.55")
    id_direct = limiter.extract_client_identifier(req_direct)
    assert id_direct == "ip:192.168.1.55"


def test_middleware_enforces_limit_and_injects_headers(api_client: TestClient):
    original_enabled = rate_limiter.enabled
    original_rpm = rate_limiter.requests_per_minute

    try:
        rate_limiter.enabled = True
        rate_limiter.requests_per_minute = 3
        rate_limiter.reset()

        test_ip = "192.0.2.1"
        headers = {"X-Forwarded-For": test_ip}

        # 1st request -> Allowed
        r1 = api_client.get("/api/plugins", headers=headers)
        assert r1.status_code == 200
        assert r1.headers.get("X-RateLimit-Limit") == "3"
        assert r1.headers.get("X-RateLimit-Remaining") == "2"
        assert "X-RateLimit-Reset" in r1.headers

        # 2nd request -> Allowed
        r2 = api_client.get("/api/plugins", headers=headers)
        assert r2.status_code == 200
        assert r2.headers.get("X-RateLimit-Remaining") == "1"

        # 3rd request -> Allowed
        r3 = api_client.get("/api/plugins", headers=headers)
        assert r3.status_code == 200
        assert r3.headers.get("X-RateLimit-Remaining") == "0"

        # 4th request -> 429 Too Many Requests
        r4 = api_client.get("/api/plugins", headers=headers)
        assert r4.status_code == 429
        data = r4.json()
        assert "Rate limit exceeded" in data["detail"]
        assert data["retry_after"] >= 1
        assert r4.headers.get("Retry-After") is not None
        assert r4.headers.get("X-RateLimit-Limit") == "3"
        assert r4.headers.get("X-RateLimit-Remaining") == "0"
        assert "X-RateLimit-Reset" in r4.headers

        # A different IP should NOT be blocked
        other_headers = {"X-Forwarded-For": "192.0.2.2"}
        r_other = api_client.get("/api/plugins", headers=other_headers)
        assert r_other.status_code == 200
        assert r_other.headers.get("X-RateLimit-Remaining") == "2"

    finally:
        rate_limiter.enabled = original_enabled
        rate_limiter.requests_per_minute = original_rpm
        rate_limiter.reset()


def test_middleware_exempt_routes(api_client: TestClient):
    original_enabled = rate_limiter.enabled
    original_rpm = rate_limiter.requests_per_minute

    try:
        rate_limiter.enabled = True
        rate_limiter.requests_per_minute = 1
        rate_limiter.reset()

        test_ip = "192.0.2.99"
        headers = {"X-Forwarded-For": test_ip}

        # Health endpoint should NEVER be rate limited even if limit is 1
        for _ in range(5):
            res = api_client.get("/health", headers=headers)
            assert res.status_code == 200
            assert res.json()["status"] == "healthy"

    finally:
        rate_limiter.enabled = original_enabled
        rate_limiter.requests_per_minute = original_rpm
        rate_limiter.reset()


def test_middleware_options_cors_preflight_exempt(api_client: TestClient):
    original_enabled = rate_limiter.enabled
    original_rpm = rate_limiter.requests_per_minute

    try:
        rate_limiter.enabled = True
        rate_limiter.requests_per_minute = 1
        rate_limiter.reset()

        test_ip = "192.0.2.88"
        headers = {
            "X-Forwarded-For": test_ip,
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        }

        # Multiple preflight OPTIONS requests should pass without 429
        for _ in range(4):
            res = api_client.options("/api/tasks", headers=headers)
            assert res.status_code in (200, 204)

    finally:
        rate_limiter.enabled = original_enabled
        rate_limiter.requests_per_minute = original_rpm
        rate_limiter.reset()
