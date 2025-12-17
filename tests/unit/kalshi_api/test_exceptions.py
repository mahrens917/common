"""Tests for kalshi_api exception classes."""

import pytest

from common.kalshi_api import exceptions


def test_private_key_not_rsa_error():
    err = exceptions.PrivateKeyNotRSAError()
    assert "not RSA" in str(err)


def test_trade_store_not_provided_error():
    err = exceptions.TradeStoreNotProvidedError()
    assert "must not be None" in str(err)


def test_trade_store_not_configured_error():
    err = exceptions.TradeStoreNotConfiguredError()
    assert "not configured" in str(err)


def test_trade_store_initialization_error():
    cause = ValueError("underlying error")
    err = exceptions.TradeStoreInitializationError(cause=cause)
    assert "Failed to initialize" in str(err)
    assert err.__cause__ is cause


def test_trade_metadata_fetch_error():
    err = exceptions.TradeMetadataFetchError("order-123", cause=ValueError("test"))
    assert "order-123" in str(err)
    assert err.order_id == "order-123"


def test_trade_metadata_missing_error():
    err = exceptions.TradeMetadataMissingError("order-456")
    assert "order-456" in str(err)
    assert err.order_id == "order-456"


def test_order_creation_missing_id_error():
    err = exceptions.OrderCreationMissingIdError()
    assert "missing 'order_id'" in str(err)


def test_order_id_required_error_without_operation():
    err = exceptions.OrderIdRequiredError()
    assert "Order ID must be provided" in str(err)
    assert err.operation == ""


def test_order_id_required_error_with_operation():
    err = exceptions.OrderIdRequiredError("cancel")
    assert "cancel" in str(err)
    assert err.operation == "cancel"


def test_fills_response_not_object_error():
    err = exceptions.FillsResponseNotObjectError()
    assert "not a JSON object" in str(err)


def test_fills_response_not_list_error():
    err = exceptions.FillsResponseNotListError()
    assert "not a list" in str(err)


def test_fill_entry_not_object_error():
    err = exceptions.FillEntryNotObjectError()
    assert "must be a JSON object" in str(err)


def test_portfolio_balance_empty_error():
    err = exceptions.PortfolioBalanceEmptyError()
    assert "Empty response" in str(err)


def test_portfolio_balance_invalid_type_error():
    err = exceptions.PortfolioBalanceInvalidTypeError("string")
    assert "integer cents" in str(err)
    assert err.received == "string"


def test_portfolio_balance_missing_timestamp_error():
    err = exceptions.PortfolioBalanceMissingTimestampError()
    assert "updated_ts" in str(err)


def test_portfolio_balance_timestamp_not_numeric_error():
    err = exceptions.PortfolioBalanceTimestampNotNumericError()
    assert "numeric" in str(err)


def test_portfolio_balance_timestamp_invalid_error():
    err = exceptions.PortfolioBalanceTimestampInvalidError()
    assert "milliseconds" in str(err)


def test_portfolio_positions_empty_error():
    err = exceptions.PortfolioPositionsEmptyError()
    assert "Empty response" in str(err)


def test_portfolio_positions_missing_field_error():
    err = exceptions.PortfolioPositionsMissingFieldError({"foo": "bar"})
    assert "positions" in str(err)
    assert err.payload == {"foo": "bar"}


def test_portfolio_positions_not_list_error():
    err = exceptions.PortfolioPositionsNotListError()
    assert "must be a list" in str(err)


def test_position_entry_not_object_error():
    err = exceptions.PositionEntryNotObjectError()
    assert "must be a JSON object" in str(err)


def test_invalid_position_payload_error():
    err = exceptions.InvalidPositionPayloadError({"bad": "data"}, cause=TypeError("test"))
    assert "Invalid position" in str(err)
    assert err.item == {"bad": "data"}


def test_position_missing_average_price_error():
    err = exceptions.PositionMissingAveragePriceError()
    assert "average_price" in str(err)


def test_invalid_average_price_error():
    err = exceptions.InvalidAveragePriceError("not_a_number")
    assert "not_a_number" in str(err)
    assert err.average_price == "not_a_number"


def test_invalid_position_side_error():
    err = exceptions.InvalidPositionSideError("bad_side")
    assert "bad_side" in str(err)
    assert err.side == "bad_side"
