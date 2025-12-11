from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from common.scraper_connection_manager_helpers.scraping_operations import ScrapingOperations


class DummySessionProvider:
    def __init__(self, session):
        self._session = session

    def get_session(self):
        return self._session

    def is_session_valid(self):
        return self._session is not None and not getattr(self._session, "closed", False)


class DummyValidator:
    def __init__(self, valid=True):
        self._valid = valid

    def has_validators(self):
        return True

    async def validate_content(self, content, url):
        return self._valid


class DummyResponse:
    def __init__(self, status=200, text_value="content"):
        self.status = status
        self._text = text_value

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False

    async def text(self):
        return self._text


@pytest.mark.asyncio
async def test_scrape_url_success_with_validation():
    session = MagicMock()
    session.closed = False
    session.get = MagicMock(return_value=DummyResponse())
    ops = ScrapingOperations("svc", ["http://a"], DummySessionProvider(session), DummyValidator(valid=True))

    result = await ops.scrape_url("http://a")

    assert result == "content"
    session.get.assert_called_once()


@pytest.mark.asyncio
async def test_scrape_url_validation_failure_logs_warning():
    session = MagicMock()
    session.closed = False
    session.get = MagicMock(return_value=DummyResponse())
    ops = ScrapingOperations("svc", ["http://a"], DummySessionProvider(session), DummyValidator(valid=False))

    result = await ops.scrape_url("http://a")

    assert result is None


@pytest.mark.asyncio
async def test_scrape_url_handles_http_error_status():
    session = MagicMock()
    session.closed = False
    session.get = MagicMock(return_value=DummyResponse(status=500))
    ops = ScrapingOperations("svc", ["http://a"], DummySessionProvider(session), DummyValidator(valid=True))

    result = await ops.scrape_url("http://a")

    assert result is None


@pytest.mark.asyncio
async def test_scrape_url_handles_client_error():
    session = MagicMock()
    session.closed = False
    session.get = MagicMock(side_effect=aiohttp.ClientError("boom"))
    ops = ScrapingOperations("svc", ["http://a"], DummySessionProvider(session), DummyValidator(valid=True))

    result = await ops.scrape_url("http://a")

    assert result is None


@pytest.mark.asyncio
async def test_scrape_all_urls_handles_exceptions_and_successes():
    async def failing_task():
        await asyncio.sleep(0)
        raise RuntimeError("fail")

    session = MagicMock()
    session.closed = False
    session.get = MagicMock(return_value=DummyResponse())
    ops = ScrapingOperations(
        "svc",
        ["http://ok", "http://fail"],
        DummySessionProvider(session),
        DummyValidator(valid=True),
    )
    # Override scrape_url to simulate mixed results
    ops.scrape_url = AsyncMock(side_effect=["good", RuntimeError("boom")])

    results = await ops.scrape_all_urls()

    assert results["http://ok"] == "good"
    assert results["http://fail"] is None
