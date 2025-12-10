"""Tests for order service operation helpers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.kalshi_trading_client.services.order_helpers import order_validator
from common.kalshi_trading_client.services.order_helpers.order_service_operations import (
    FillsOperations,
    MetadataOperations,
    ValidationOperations,
)


def test_validation_operations_delegate(monkeypatch):
    validator = MagicMock()
    parser = MagicMock()
    parser.parse_order_response.return_value = {"parsed": True}
    operations = ValidationOperations(validator, parser)

    operations.validate_order_request("request")
    validator.validate_order_request.assert_called_once_with("request")

    parsed = operations.parse_order_response("data", "op", "rule", "reason")
    assert parsed == {"parsed": True}

    monkeypatch.setattr(
        order_validator.OrderValidator,
        "has_sufficient_balance_for_trade_with_fees",
        MagicMock(return_value=True),
    )

    assert ValidationOperations.has_sufficient_balance_for_trade_with_fees(10, 5, 2) is True
    order_validator.OrderValidator.has_sufficient_balance_for_trade_with_fees.assert_called_once_with(
        10, 5, 2
    )


@pytest.mark.asyncio
async def test_fills_operations_proxies_to_dependencies():
    canceller = MagicMock()
    canceller.cancel_order = AsyncMock(return_value=True)
    fills_fetcher = MagicMock()
    fills_fetcher.get_fills = AsyncMock(return_value=[{"fill": 1}])
    fills_fetcher.get_all_fills = AsyncMock(return_value={"cursor": "next"})

    operations = FillsOperations(canceller, fills_fetcher)

    assert await operations.cancel_order("order-1") is True
    assert await operations.get_fills("order-2") == [{"fill": 1}]
    assert await operations.get_all_fills(0, 10, "ticker", "cursor") == {"cursor": "next"}
    canceller.cancel_order.assert_awaited_once_with("order-1")
    fills_fetcher.get_fills.assert_awaited_once_with("order-2")
    fills_fetcher.get_all_fills.assert_awaited_once_with(0, 10, "ticker", "cursor")


@pytest.mark.asyncio
async def test_metadata_operations_delegates(monkeypatch):
    metadata_resolver = MagicMock()
    metadata_resolver.create_icao_to_city_mapping.return_value = {"ICAO": "City"}
    metadata_resolver.extract_weather_station_from_ticker.return_value = "ICAO"
    metadata_resolver.resolve_trade_context.return_value = {"context": "value"}

    fee_calculator = MagicMock()
    fee_calculator.calculate_order_fees = AsyncMock(return_value=123)

    metadata_fetcher = MagicMock()
    metadata_fetcher.get_trade_metadata_from_order = AsyncMock(return_value={"meta": True})

    operations = MetadataOperations(metadata_resolver, fee_calculator, metadata_fetcher)

    assert operations.create_icao_to_city_mapping() == {"ICAO": "City"}
    assert operations.extract_weather_station_from_ticker("TICKER") == "ICAO"
    assert operations.resolve_trade_context("TICKER") == {"context": "value"}
    assert await operations.calculate_order_fees("TICKER", 5, 10) == 123
    assert await operations.get_trade_metadata_from_order("order-1") == {"meta": True}

    handler = MagicMock()
    operations.update_telegram_handler(handler)
    assert metadata_fetcher._telegram_handler is handler
