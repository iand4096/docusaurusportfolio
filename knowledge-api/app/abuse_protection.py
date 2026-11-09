"""Low-cost, per-process protections for public portfolio API endpoints.

Memory quotas reset on restart/scale-to-zero and do not coordinate across workers.
Only enable trusted X-Forwarded-For processing behind Azure Container Apps ingress.
"""
from __future__ import annotations

import ipaddress
import math
import os
import threading
import time
from collections import deque
from typing import Callable

from fastapi import Request
from starlette.responses import JSONResponse


LIMITS = {('POST', '/search'): 20, ('GET', '/taxonomy'): 60, ('POST', '/chat'): 3}
WINDOW_SECONDS = 60
MAX_IDENTITIES = 10000  # Bound memory use under many distinct source addresses.


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, 'true' if default else 'false').strip().lower() == 'true'


def client_identifier(request: Request, trust_azure_xff: bool = False) -> str:
    if trust_azure_xff:
        # ACA appends the connecting client address at the right of XFF.
        # This is only safe when requests cannot bypass the trusted ingress.
        value = request.headers.get('x-forwarded-for', '')
        if value:
            candidate = value.rsplit(',', 1)[-1].strip()
            try:
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                pass
    return request.client.host if request.client else 'unknown'


class SlidingWindowLimiter:
    """Thread-safe exact sliding window. Intended for one worker/replica only."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self._lock = threading.Lock()
        self._hits: dict[tuple[str, str], deque[float]] = {}

    def check(self, client: str, route: str, limit: int) -> tuple[bool, int]:
        now = self.clock()
        key = (client, route)
        with self._lock:
            if len(self._hits) >= MAX_IDENTITIES and key not in self._hits:
                # Purge expired identities; if exhausted, refuse rather than grow endlessly.
                for old_key, values in list(self._hits.items()):
                    if not values or values[-1] <= now - WINDOW_SECONDS:
                        del self._hits[old_key]
                if len(self._hits) >= MAX_IDENTITIES:
                    return False, WINDOW_SECONDS
            timestamps = self._hits.setdefault(key, deque())
            while timestamps and timestamps[0] <= now - WINDOW_SECONDS:
                timestamps.popleft()
            if len(timestamps) >= limit:
                return False, max(1, math.ceil(WINDOW_SECONDS - (now - timestamps[0])))
            timestamps.append(now)
            return True, 0


class RateLimitMiddleware:
    """ASGI middleware; register before CORSMiddleware so 429 gets CORS headers."""

    def __init__(self, app, *, enabled: bool = True, trust_azure_xff: bool = False):
        self.app = app
        self.enabled = enabled
        self.trust_azure_xff = trust_azure_xff
        self.limiter = SlidingWindowLimiter()

    async def __call__(self, scope, receive, send):
        if not self.enabled or scope['type'] != 'http':
            return await self.app(scope, receive, send)
        route = (scope['method'].upper(), scope['path'])
        limit = LIMITS.get(route)
        if limit is None:
            return await self.app(scope, receive, send)
        request = Request(scope)
        client = client_identifier(request, self.trust_azure_xff)
        allowed, retry_after = self.limiter.check(client, route[1], limit)
        if not allowed:
            response = JSONResponse(
                {'detail': f'Too many requests to {route[1]}. Please try again shortly.'},
                status_code=429,
                headers={'Retry-After': str(retry_after)},
            )
            return await response(scope, receive, send)
        return await self.app(scope, receive, send)
