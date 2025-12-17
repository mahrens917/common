"""Tests for kalshi_api portfolio_operations."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.kalshi_api import exceptions
from common.kalshi_api.portfolio_operations import (
    PortfolioOperations,
    _parse_position_entry,
    _validate_positions_payload,
)


class TestPortfolioOperations:
    @pytest.fixture
    def mock_request_builder(self):
        builder = MagicMock()
        builder.build_request_context = MagicMock(return_value=("GET", "http://url", {}, "op"))
        builder.execute_request = AsyncMock(return_value={})
        return builder

    @pytest.fixture
    def portfolio_ops(self, mock_request_builder):
        return PortfolioOperations(mock_request_builder)

    @pytest.mark.asyncio
    async def test_get_balance_success(self, portfolio_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(return_value={"balance": 10000, "updated_ts": 1700000000000})

        balance = await portfolio_ops.get_balance()

        assert balance.balance_cents == 10000
        assert balance.currency == "USD"

    @pytest.mark.asyncio
    async def test_get_balance_empty_response(self, portfolio_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(return_value={})

        with pytest.raises(exceptions.PortfolioBalanceEmptyError):
            await portfolio_ops.get_balance()

    @pytest.mark.asyncio
    async def test_get_balance_invalid_type(self, portfolio_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(return_value={"balance": "not_an_int", "updated_ts": 1700000000000})

        with pytest.raises(exceptions.PortfolioBalanceInvalidTypeError):
            await portfolio_ops.get_balance()

    @pytest.mark.asyncio
    async def test_get_balance_missing_timestamp(self, portfolio_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(return_value={"balance": 10000})

        with pytest.raises(exceptions.PortfolioBalanceMissingTimestampError):
            await portfolio_ops.get_balance()

    @pytest.mark.asyncio
    async def test_get_balance_timestamp_not_numeric(self, portfolio_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(return_value={"balance": 10000, "updated_ts": "not_numeric"})

        with pytest.raises(exceptions.PortfolioBalanceTimestampNotNumericError):
            await portfolio_ops.get_balance()

    @pytest.mark.asyncio
    async def test_get_balance_timestamp_seconds(self, portfolio_ops, mock_request_builder):
        # Timestamp in seconds (less than 10^12)
        mock_request_builder.execute_request = AsyncMock(return_value={"balance": 10000, "updated_ts": 1700000000})

        balance = await portfolio_ops.get_balance()

        assert balance.balance_cents == 10000

    @pytest.mark.asyncio
    async def test_get_positions_success(self, portfolio_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(
            return_value={
                "positions": [
                    {
                        "ticker": "ABC",
                        "position": 10,
                        "side": "yes",
                        "market_value": 500,
                        "unrealized_pnl": 50,
                        "average_price": 45,
                    }
                ]
            }
        )

        positions = await portfolio_ops.get_positions()

        assert len(positions) == 1
        assert positions[0].ticker == "ABC"
        assert positions[0].position_count == 10


class TestValidatePositionsPayload:
    def test_success(self):
        result = _validate_positions_payload({"positions": [{"ticker": "ABC"}]})
        assert result == [{"ticker": "ABC"}]

    def test_none_payload(self):
        with pytest.raises(exceptions.PortfolioPositionsEmptyError):
            _validate_positions_payload(None)

    def test_missing_positions_key(self):
        with pytest.raises(exceptions.PortfolioPositionsMissingFieldError):
            _validate_positions_payload({"other": "data"})

    def test_positions_not_list(self):
        with pytest.raises(exceptions.PortfolioPositionsNotListError):
            _validate_positions_payload({"positions": "not a list"})


class TestParsePositionEntry:
    def test_success(self):
        item = {
            "ticker": "ABC",
            "position": 10,
            "side": "yes",
            "market_value": 500,
            "unrealized_pnl": 50,
            "average_price": 45,
        }

        position = _parse_position_entry(item)

        assert position.ticker == "ABC"
        assert position.position_count == 10
        assert position.average_price_cents == 45

    def test_not_dict(self):
        with pytest.raises(exceptions.PositionEntryNotObjectError):
            _parse_position_entry("not a dict")

    def test_missing_fields(self):
        with pytest.raises(exceptions.InvalidPositionPayloadError):
            _parse_position_entry({"ticker": "ABC"})

    def test_missing_average_price(self):
        item = {
            "ticker": "ABC",
            "position": 10,
            "side": "yes",
        }
        with pytest.raises(exceptions.PositionMissingAveragePriceError):
            _parse_position_entry(item)

    def test_invalid_average_price(self):
        item = {
            "ticker": "ABC",
            "position": 10,
            "side": "yes",
            "average_price": "not_a_number",
        }
        with pytest.raises(exceptions.InvalidAveragePriceError):
            _parse_position_entry(item)

    def test_invalid_side(self):
        item = {
            "ticker": "ABC",
            "position": 10,
            "side": "invalid",
            "average_price": 45,
        }
        with pytest.raises(exceptions.InvalidPositionSideError):
            _parse_position_entry(item)

    def test_none_market_value(self):
        item = {
            "ticker": "ABC",
            "position": 10,
            "side": "yes",
            "average_price": 45,
            "market_value": None,
            "unrealized_pnl": None,
        }

        position = _parse_position_entry(item)

        assert position.market_value_cents == 0
        assert position.unrealized_pnl_cents == 0
