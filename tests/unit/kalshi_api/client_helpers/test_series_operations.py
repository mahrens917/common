"""Tests for kalshi_api series_operations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.kalshi_api.client_helpers.errors import KalshiClientError
from common.kalshi_api.client_helpers.series_operations import SeriesOperations


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.api_request = AsyncMock(return_value={"series": []})
    return client


@pytest.fixture
def series_ops(mock_client):
    return SeriesOperations(mock_client)


@pytest.mark.asyncio
async def test_get_series_no_category(series_ops, mock_client):
    with patch("common.kalshi_api.client_helpers.series_operations.validate_series_response") as mock_validate:
        mock_validate.return_value = [{"series": "data"}]

        result = await series_ops.get_series()

        mock_client.api_request.assert_called_once()
        call_kwargs = mock_client.api_request.call_args[1]
        assert call_kwargs["params"] == {}
        assert call_kwargs["operation_name"] == "get_series_all"
        assert result == [{"series": "data"}]


@pytest.mark.asyncio
async def test_get_series_with_category(series_ops, mock_client):
    with patch("common.kalshi_api.client_helpers.series_operations.validate_series_response") as mock_validate:
        mock_validate.return_value = [{"series": "weather"}]

        result = await series_ops.get_series(category="WEATHER")

        call_kwargs = mock_client.api_request.call_args[1]
        assert call_kwargs["params"] == {"category": "WEATHER"}
        assert call_kwargs["operation_name"] == "get_series_weather"


@pytest.mark.asyncio
async def test_get_series_validation_error(series_ops, mock_client):
    with patch("common.kalshi_api.client_helpers.series_operations.validate_series_response") as mock_validate:
        mock_validate.side_effect = ValueError("invalid response")

        with pytest.raises(KalshiClientError) as exc_info:
            await series_ops.get_series()

        assert "invalid" in str(exc_info.value)


def test_build_params_empty():
    params = SeriesOperations._build_params(None)
    assert params == {}


def test_build_params_with_category():
    params = SeriesOperations._build_params("SPORTS")
    assert params == {"category": "SPORTS"}


def test_build_params_empty_string():
    params = SeriesOperations._build_params("")
    assert params == {}
