"""Tests for kalshi_api request_builder."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.kalshi_api.client_helpers.errors import KalshiClientError
from common.kalshi_api.request_builder import RequestBuilder


@pytest.fixture
def mock_session_manager():
    return MagicMock()


@pytest.fixture
def mock_auth_helper():
    return MagicMock()


@pytest.fixture
def builder(mock_session_manager, mock_auth_helper):
    return RequestBuilder(
        base_url="https://api.kalshi.com",
        session_manager=mock_session_manager,
        auth_helper=mock_auth_helper,
        max_retries=3,
        backoff_base=1.0,
        backoff_max=10.0,
    )


def test_build_request_context_basic(builder):
    method, url, kwargs, op = builder.build_request_context(
        method="GET",
        path="/api/v1/markets",
        params=None,
        json_payload=None,
        operation_name=None,
    )

    assert method == "GET"
    assert url == "https://api.kalshi.com/api/v1/markets"
    assert kwargs == {}
    assert op == "/api/v1/markets"


def test_build_request_context_with_params(builder):
    method, url, kwargs, op = builder.build_request_context(
        method="GET",
        path="/api/v1/markets",
        params={"limit": 10, "cursor": "abc"},
        json_payload=None,
        operation_name="list_markets",
    )

    assert method == "GET"
    assert kwargs == {"params": {"limit": 10, "cursor": "abc"}}
    assert op == "list_markets"


def test_build_request_context_with_json(builder):
    method, url, kwargs, op = builder.build_request_context(
        method="POST",
        path="/api/v1/orders",
        params=None,
        json_payload={"ticker": "ABC", "count": 10},
        operation_name="create_order",
    )

    assert method == "POST"
    assert kwargs == {"json": {"ticker": "ABC", "count": 10}}


def test_build_request_context_path_must_start_with_slash(builder):
    with pytest.raises(KalshiClientError) as exc_info:
        builder.build_request_context(
            method="GET",
            path="api/v1/markets",  # Missing leading slash
            params=None,
            json_payload=None,
            operation_name=None,
        )

    assert "must begin with '/'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_request_delegates_to_executor(builder):
    builder._executor.execute_request = AsyncMock(return_value={"data": "result"})

    result = await builder.execute_request(
        method_upper="GET",
        url="https://api.kalshi.com/test",
        request_kwargs={},
        path="/test",
        operation_name="test_op",
    )

    assert result == {"data": "result"}
    builder._executor.execute_request.assert_called_once()
