import asyncio
import time

import pytest

from common.reactive_rate_limiter import ReactiveRateLimiter

_TEST_COUNT_2 = 2


def test_handle_429_response_exponential_backoff(monkeypatch):
    current_time = 100.0

    def fake_time():
        return current_time

    monkeypatch.setattr(time, "time", fake_time)

    limiter = ReactiveRateLimiter(base_delay=1.0)
    delay1 = limiter.handle_429_response()
    assert delay1 == pytest.approx(1.0)
    assert limiter.consecutive_429s == 1

    delay2 = limiter.handle_429_response()
    assert delay2 == pytest.approx(_TEST_COUNT_2)
    assert limiter.consecutive_429s == _TEST_COUNT_2
    assert limiter.backoff_until == pytest.approx(current_time + 2.0)


@pytest.mark.asyncio
async def test_wait_if_needed_and_reset(monkeypatch):
    current_time = 200.0

    async def fake_sleep(duration):
        nonlocal current_time
        current_time += duration

    def fake_time():
        return current_time

    monkeypatch.setattr(time, "time", fake_time)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    limiter = ReactiveRateLimiter(base_delay=1.0)
    limiter.handle_429_response()  # sets backoff_until

    await limiter.wait_if_needed()
    assert limiter.consecutive_429s == 1

    await limiter.reset_backoff()
    assert limiter.consecutive_429s == 0


@pytest.mark.asyncio
async def test_reset_backoff_notifies_analyzer(monkeypatch):
    class DummyAnalyzer:
        def __init__(self):
            self.reported = []

        async def report_recovery(self, message, context):
            self.reported.append((message, context))

    analyzer = DummyAnalyzer()
    limiter = ReactiveRateLimiter(base_delay=0.5, error_analyzer=analyzer)

    for _ in range(3):
        limiter.handle_429_response()

    await limiter.reset_backoff()
    assert analyzer.reported
    assert analyzer.reported[0][0] == "Rate limit recovery"


def test_get_metrics_reflects_state(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 300.0)
    limiter = ReactiveRateLimiter(base_delay=1.0)
    limiter.handle_429_response()
    metrics = limiter.get_metrics()
    assert metrics["consecutive_429s"] == 1
    assert metrics["is_in_backoff"] is True
