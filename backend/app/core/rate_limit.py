import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp
from fastapi import Depends, HTTPException, Request


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        self.minute_buckets = defaultdict(list)
        self.hour_buckets = defaultdict(list)
        self.burst_buckets = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        # Check for forwarded headers (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"

    def _cleanup_old_entries(self, bucket: list, window_seconds: int) -> list:
        now = time.time()
        return [ts for ts in bucket if now - ts < window_seconds]

    def _is_rate_limited(self, ip: str) -> tuple[bool, dict]:
        now = time.time()

        # Clean up old entries
        self.minute_buckets[ip] = self._cleanup_old_entries(self.minute_buckets[ip], 60)
        self.hour_buckets[ip] = self._cleanup_old_entries(self.hour_buckets[ip], 3600)
        self.burst_buckets[ip] = self._cleanup_old_entries(self.burst_buckets[ip], 10)

        # Check burst limit (10 requests in 10 seconds)
        if len(self.burst_buckets[ip]) >= self.burst_limit:
            return True, {
                "limit": self.burst_limit,
                "window": "10s",
                "retry_after": 10 - int(now - self.burst_buckets[ip][0]) if self.burst_buckets[ip] else 10
            }

        # Check minute limit
        if len(self.minute_buckets[ip]) >= self.requests_per_minute:
            return True, {
                "limit": self.requests_per_minute,
                "window": "60s",
                "retry_after": 60 - int(now - self.minute_buckets[ip][0]) if self.minute_buckets[ip] else 60
            }

        # Check hour limit
        if len(self.hour_buckets[ip]) >= self.requests_per_hour:
            return True, {
                "limit": self.requests_per_hour,
                "window": "3600s",
                "retry_after": 3600 - int(now - self.hour_buckets[ip][0]) if self.hour_buckets[ip] else 3600
            }

        return False, {}

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        ip = self._get_client_ip(request)
        limited, info = self._is_rate_limited(ip)

        if limited:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded. Max {info['limit']} requests per {info['window']}.",
                    "retry_after": info["retry_after"]
                },
                headers={
                    "Retry-After": str(info["retry_after"]),
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + info["retry_after"])
                }
            )

        # Record this request
        now = time.time()
        self.burst_buckets[ip].append(now)
        self.minute_buckets[ip].append(now)
        self.hour_buckets[ip].append(now)

        response = await call_next(request)

        # Add rate limit headers to response
        remaining = max(0, self.requests_per_minute - len(self.minute_buckets[ip]))
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now) + 60)

        return response


def rate_limit_middleware(app: ASGIApp) -> ASGIApp:
    return RateLimitMiddleware(app)


# Stricter rate limit for auth endpoints (register, login, password reset)
# Development: much higher limits to avoid blocking during testing
# 100 requests per minute, 1000 per hour, burst of 20
_stricter_buckets_minute = defaultdict(list)
_stricter_buckets_hour = defaultdict(list)
_stricter_buckets_burst = defaultdict(list)


async def stricter_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        ip = real_ip

    now = time.time()

    # Clean up
    _stricter_buckets_minute[ip] = [ts for ts in _stricter_buckets_minute[ip] if now - ts < 60]
    _stricter_buckets_hour[ip] = [ts for ts in _stricter_buckets_hour[ip] if now - ts < 3600]
    _stricter_buckets_burst[ip] = [ts for ts in _stricter_buckets_burst[ip] if now - ts < 10]

    # Burst: 20 requests per 10 seconds (dev)
    if len(_stricter_buckets_burst[ip]) >= 20:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Aguarde alguns segundos.",
            headers={"Retry-After": "10"}
        )

    # Minute: 100 requests per minute (dev)
    if len(_stricter_buckets_minute[ip]) >= 100:
        raise HTTPException(
            status_code=429,
            detail="Limite de tentativas excedido. Tente novamente em 1 minuto.",
            headers={"Retry-After": "60"}
        )

    # Hour: 1000 requests per hour (dev)
    if len(_stricter_buckets_hour[ip]) >= 1000:
        raise HTTPException(
            status_code=429,
            detail="Limite horário excedido. Tente novamente mais tarde.",
            headers={"Retry-After": "3600"}
        )

    # Record
    _stricter_buckets_burst[ip].append(now)
    _stricter_buckets_minute[ip].append(now)
    _stricter_buckets_hour[ip].append(now)

    return True