"""Tests for the PrivateMethods wrapper."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.kalshi_trading_client.client_helpers.private_methods import PrivateMethods


def _build_private_methods():
    orders = MagicMock()
    trade_store_manager = MagicMock()
    kalshi_client = MagicMock()
    return PrivateMethods(orders, trade_store_manager, kalshi_client)


def test_order_operations_wrappers(monkeypatch):
    instance = _build_private_methods()
    orders = instance._orders

    order_ops = MagicMock()
    order_ops.build_order_poller.return_value = "poller"
    order_ops.build_trade_finalizer.return_value = "finalizer"
    order_ops.parse_order_response.return_value = "parsed"
    order_ops.has_sufficient_balance_for_trade_with_fees.return_value = True

    monkeypatch.setattr(
        "src.common.kalshi_trading_client.client_helpers.order_operations.OrderOperations",
        order_ops,
    )

    assert instance.build_order_poller() == "poller"
    assert instance.build_trade_finalizer() == "finalizer"

    instance.apply_polling_outcome("response", "outcome")
    order_ops.apply_polling_outcome.assert_called_once_with(orders, "response", "outcome")

    instance.validate_order_request("req")
    order_ops.validate_order_request.assert_called_once_with(orders, "req")

    assert instance.parse_order_response({}, "op", "rule", "reason") == "parsed"
    order_ops.parse_order_response.assert_called_once()

    assert instance.has_sufficient_balance_for_trade_with_fees(1, 2, 3) is True
    order_ops.has_sufficient_balance_for_trade_with_fees.assert_called_once_with(orders, 1, 2, 3)


def test_trade_context_resolver_wrappers(monkeypatch):
    instance = _build_private_methods()
    resolver = MagicMock()
    resolver.create_icao_to_city_mapping.return_value = {"ABC": "City"}
    resolver.extract_weather_station_from_ticker.return_value = "station"
    resolver.resolve_trade_context.return_value = ("type", None)

    monkeypatch.setattr(
        "src.common.kalshi_trading_client.client_helpers.trade_context.TradeContextResolver",
        resolver,
    )

    assert instance.create_icao_to_city_mapping() == {"ABC": "City"}
    resolver.create_icao_to_city_mapping.assert_called_once_with(instance._orders)

    assert instance.extract_weather_station_from_ticker("ticker") == "station"
    resolver.extract_weather_station_from_ticker.assert_called_once_with(instance._orders, "ticker")

    assert instance.resolve_trade_context("ticker") == ("type", None)
    resolver.resolve_trade_context.assert_called_once_with(instance._orders, "ticker")


@pytest.mark.asyncio
async def test_async_operations(monkeypatch):
    instance = _build_private_methods()
    calculation = AsyncMock(return_value=10)
    monkeypatch.setattr(
        "src.common.kalshi_trading_client.services.order_helpers.fee_calculator.calculate_order_fees",
        calculation,
    )

    order_ops = MagicMock()
    order_ops.get_trade_metadata_from_order = AsyncMock(return_value=("rule", "reason"))

    monkeypatch.setattr(
        "src.common.kalshi_trading_client.client_helpers.order_operations.OrderOperations",
        order_ops,
    )

    fees = await instance.calculate_order_fees("ticker", 2, 3)
    assert fees == 10
    calculation.assert_awaited_once_with("ticker", 2, 3)

    metadata = await instance.get_trade_metadata_from_order("order42")
    assert metadata == ("rule", "reason")
    order_ops.get_trade_metadata_from_order.assert_awaited_once_with(instance._orders, "order42")


def test_factory_methods_wrappers(monkeypatch):
    orders = MagicMock()
    orders.get_fills = MagicMock()
    orders.resolve_trade_context = MagicMock()
    trade_store_manager = MagicMock()
    kalshi_client = MagicMock()
    instance = PrivateMethods(orders, trade_store_manager, kalshi_client)

    factory = MagicMock()
    factory.create_order_poller.return_value = "poller"
    factory.create_trade_finalizer.return_value = "finalizer"

    monkeypatch.setattr(
        "src.common.kalshi_trading_client.client_helpers.factory_methods.FactoryMethods",
        factory,
    )

    assert instance.create_order_poller() == "poller"
    factory.create_order_poller.assert_called_once_with(orders.get_fills)

    assert instance.create_trade_finalizer() == "finalizer"
    factory.create_trade_finalizer.assert_called_once_with(
        trade_store_manager, orders.resolve_trade_context, kalshi_client
    )
