"""Fast, model-free tests for the in-memory limiter."""
from types import SimpleNamespace

from starlette.datastructures import Headers

from app.abuse_protection import SlidingWindowLimiter, client_identifier


def test_sliding_window_limit_and_expiry():
    now = [100.0]
    limiter = SlidingWindowLimiter(clock=lambda: now[0])
    assert limiter.check('client-a', '/search', 2) == (True, 0)
    assert limiter.check('client-a', '/search', 2) == (True, 0)
    assert limiter.check('client-a', '/search', 2) == (False, 60)
    assert limiter.check('client-b', '/search', 2) == (True, 0)
    now[0] += 61
    assert limiter.check('client-a', '/search', 2) == (True, 0)


def test_endpoint_budgets_are_independent():
    limiter = SlidingWindowLimiter(clock=lambda: 10.0)
    assert limiter.check('client-a', '/search', 1)[0]
    assert not limiter.check('client-a', '/search', 1)[0]
    assert limiter.check('client-a', '/taxonomy', 1)[0]


def test_forwarded_header_is_ignored_unless_trusted():
    request = SimpleNamespace(
        headers=Headers({'x-forwarded-for': '198.51.100.1, 203.0.113.20'}),
        client=SimpleNamespace(host='10.0.0.5'),
    )
    assert client_identifier(request, trust_azure_xff=False) == '10.0.0.5'
    assert client_identifier(request, trust_azure_xff=True) == '203.0.113.20'
