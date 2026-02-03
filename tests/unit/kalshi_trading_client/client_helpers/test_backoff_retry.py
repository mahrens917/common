"""Tests for backoff retry logic."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.backoff_manager import BackoffManager
from common.backoff_manager_helpers import BackoffType
from common.kalshi_trading_client.client_helpers.backoff_retry import (
    with_backoff_retry,
)

_SERVICE = "test_service"
_BACKOFF_TYPE = BackoffType.NETWORK_FAILURE


def _make_backoff_manager(*, max_retries: int = 3) -> MagicMock:
    manager = MagicMock(spec=BackoffManager)
    call_count = 0

    def should_retry(service_name, backoff_type):
        nonlocal call_count
        call_count += 1
        return call_count <= max_retries

    manager.should_retry = MagicMock(side_effect=should_retry)
    manager.calculate_delay = MagicMock(return_value=0.0)
    manager.reset_backoff = MagicMock()
    return manager


@pytest.mark.asyncio
async def test_success_resets_backoff(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    manager = _make_backoff_manager()
    operation = AsyncMock(return_value="result")

    result = await with_backoff_retry(
        operation,
        backoff_manager=manager,
        service_name=_SERVICE,
        backoff_type=_BACKOFF_TYPE,
        context="test_op",
    )

    assert result == "result"
    manager.reset_backoff.assert_called_once_with(_SERVICE, _BACKOFF_TYPE)


@pytest.mark.asyncio
async def test_retries_on_connection_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    manager = _make_backoff_manager(max_retries=3)
    attempts: list[int] = []

    async def flaky():
        attempts.append(len(attempts) + 1)
        if len(attempts) == 1:
            raise ConnectionError("conn failed")
        return "ok"

    result = await with_backoff_retry(
        flaky,
        backoff_manager=manager,
        service_name=_SERVICE,
        backoff_type=_BACKOFF_TYPE,
        context="test_op",
    )

    assert result == "ok"
    assert manager.calculate_delay.call_count == 1


@pytest.mark.asyncio
async def test_exhausted_retries_raises_last_exception(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    manager = _make_backoff_manager(max_retries=1)
    operation = AsyncMock(side_effect=ConnectionError("persistent failure"))

    with pytest.raises(ConnectionError, match="persistent failure"):
        await with_backoff_retry(
            operation,
            backoff_manager=manager,
            service_name=_SERVICE,
            backoff_type=_BACKOFF_TYPE,
            context="test_op",
        )


@pytest.mark.asyncio
async def test_non_retryable_error_propagates(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    manager = _make_backoff_manager()
    operation = AsyncMock(side_effect=ValueError("not retryable"))

    with pytest.raises(ValueError, match="not retryable"):
        await with_backoff_retry(
            operation,
            backoff_manager=manager,
            service_name=_SERVICE,
            backoff_type=_BACKOFF_TYPE,
            context="test_op",
        )


@pytest.mark.asyncio
async def test_timeout_error_retries(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    manager = _make_backoff_manager(max_retries=3)
    attempts: list[int] = []

    async def flaky():
        attempts.append(len(attempts) + 1)
        if len(attempts) == 1:
            raise TimeoutError("timed out")
        return "recovered"

    result = await with_backoff_retry(
        flaky,
        backoff_manager=manager,
        service_name=_SERVICE,
        backoff_type=_BACKOFF_TYPE,
        context="test_op",
    )

    assert result == "recovered"
