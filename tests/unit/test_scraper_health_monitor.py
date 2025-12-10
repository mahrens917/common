import asyncio

import pytest

from common.scraper_connection_manager_helpers.health_monitor import ScraperHealthMonitor


class DummyResponse:
    def __init__(self, status: int, text: str = ""):
        self.status = status
        self._text = text

    async def text(self):
        return self._text


class DummyRequestContext:
    def __init__(self, response):
        self._response = response

    def __await__(self):
        async def _inner():
            if isinstance(self._response, Exception):
                raise self._response
            return self._response

        return _inner().__await__()

    async def __aenter__(self):
        if isinstance(self._response, Exception):
            raise self._response
        return self._response

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False


class DummySession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.closed = False

    def get(self, *_args, **_kwargs):
        return DummyRequestContext(self._responses.pop(0))


class DummySessionProvider:
    def __init__(self, session):
        self._session = session

    def get_session(self):
        return self._session


class DummyContentValidator:
    def __init__(self, *, valid: bool = True, enabled: bool = True):
        self._valid = valid
        self._enabled = enabled
        self.calls = 0

    def has_validators(self) -> bool:
        return self._enabled

    async def validate_content(self, content: str, url: str) -> bool:
        self.calls += 1
        return self._valid

    def get_validation_metrics(self):
        return {}


@pytest.mark.asyncio
async def test_scraper_monitor_success_tracks_urls():
    session = DummySession([DummyResponse(200, "ok"), DummyResponse(201, "ok")])
    monitor = ScraperHealthMonitor(
        "svc",
        ["https://a", "https://b"],
        DummySessionProvider(session),
        DummyContentValidator(enabled=False),
    )

    result = await monitor.check_health()

    assert result.healthy is True
    assert monitor.consecutive_failures == 0
    assert monitor.url_health_status == {
        "https://a": True,
        "https://b": True,
    }
    assert monitor.last_success_time > 0


@pytest.mark.asyncio
async def test_scraper_monitor_content_validation_failure_marks_unhealthy():
    session = DummySession([DummyResponse(200, "bad")])
    validator = DummyContentValidator(valid=False, enabled=True)
    monitor = ScraperHealthMonitor(
        "svc",
        ["https://only"],
        DummySessionProvider(session),
        validator,
    )

    result = await monitor.check_health()

    assert result.healthy is False
    assert result.details["url_health_status"]["https://only"] is False
    assert validator.calls == 1
    assert monitor.consecutive_failures == 1


@pytest.mark.asyncio
async def test_scraper_monitor_majority_failure_increments_counter():
    session = DummySession(
        [
            DummyResponse(200, "ok"),
            DummyResponse(500, "bad-1"),
            DummyResponse(500, "bad-2"),
            DummyResponse(404, "bad-3"),
        ]
    )
    monitor = ScraperHealthMonitor(
        "svc",
        ["https://a", "https://b", "https://c", "https://d"],
        DummySessionProvider(session),
        DummyContentValidator(enabled=False),
    )

    result = await monitor.check_health()

    assert result.healthy is False
    assert monitor.consecutive_failures == 1
    assert list(result.details["url_health_status"].values()).count(True) == 1
