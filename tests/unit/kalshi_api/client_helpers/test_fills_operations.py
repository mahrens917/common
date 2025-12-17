"""Tests for kalshi_api fills_operations."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.kalshi_api.client_helpers.fills_operations import FillsOperations


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.api_request = AsyncMock(return_value={"fills": []})
    return client


@pytest.fixture
def fills_ops(mock_client):
    return FillsOperations(mock_client)


@pytest.mark.asyncio
async def test_get_all_fills_no_params(fills_ops, mock_client):
    result = await fills_ops.get_all_fills()

    mock_client.api_request.assert_called_once_with(
        method="GET",
        path="/trade-api/v2/portfolio/fills",
        params={},
        operation_name="get_all_fills",
    )
    assert result == {"fills": []}


@pytest.mark.asyncio
async def test_get_all_fills_with_params(fills_ops, mock_client):
    await fills_ops.get_all_fills(
        min_ts=1000,
        max_ts=2000,
        ticker="ABC",
        cursor="cursor123",
    )

    mock_client.api_request.assert_called_once()
    call_kwargs = mock_client.api_request.call_args[1]
    assert call_kwargs["params"] == {
        "min_ts": 1000,
        "max_ts": 2000,
        "ticker": "ABC",
        "cursor": "cursor123",
    }


def test_build_params_empty():
    params = FillsOperations._build_params(None, None, None, None)
    assert params == {}


def test_build_params_all_values():
    params = FillsOperations._build_params(
        min_ts=100,
        max_ts=200,
        ticker="XYZ",
        cursor="abc",
    )

    assert params == {
        "min_ts": 100,
        "max_ts": 200,
        "ticker": "XYZ",
        "cursor": "abc",
    }


def test_build_params_partial():
    params = FillsOperations._build_params(
        min_ts=100,
        max_ts=None,
        ticker="",
        cursor=None,
    )

    assert params == {"min_ts": 100}
