"""Tests for expiry operations."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.common.redis_protocol.kalshi_store.reader_helpers.expiry_operations import (
    check_expiry_status,
    check_settlement_status,
)


class TestCheckExpiryStatus:
    """Tests for check_expiry_status function."""

    @pytest.mark.asyncio
    async def test_returns_true_when_expired(self) -> None:
        """Returns True when market is expired."""
        redis = AsyncMock()
        expiry_checker = AsyncMock()
        expiry_checker.is_market_expired = AsyncMock(return_value=True)

        result = await check_expiry_status(
            redis, "markets:kalshi:test:TICKER", "TICKER", expiry_checker
        )

        assert result is True
        expiry_checker.is_market_expired.assert_called_once_with(
            redis, "markets:kalshi:test:TICKER", "TICKER"
        )

    @pytest.mark.asyncio
    async def test_returns_false_when_not_expired(self) -> None:
        """Returns False when market is not expired."""
        redis = AsyncMock()
        expiry_checker = AsyncMock()
        expiry_checker.is_market_expired = AsyncMock(return_value=False)

        result = await check_expiry_status(
            redis, "markets:kalshi:test:TICKER", "TICKER", expiry_checker
        )

        assert result is False


class TestCheckSettlementStatus:
    """Tests for check_settlement_status function."""

    @pytest.mark.asyncio
    async def test_returns_true_when_settled(self) -> None:
        """Returns True when market is settled."""
        redis = AsyncMock()
        expiry_checker = AsyncMock()
        expiry_checker.is_market_settled = AsyncMock(return_value=True)

        result = await check_settlement_status(
            redis, "markets:kalshi:test:TICKER", "TICKER", expiry_checker
        )

        assert result is True
        expiry_checker.is_market_settled.assert_called_once_with(
            redis, "markets:kalshi:test:TICKER", "TICKER"
        )

    @pytest.mark.asyncio
    async def test_returns_false_when_not_settled(self) -> None:
        """Returns False when market is not settled."""
        redis = AsyncMock()
        expiry_checker = AsyncMock()
        expiry_checker.is_market_settled = AsyncMock(return_value=False)

        result = await check_settlement_status(
            redis, "markets:kalshi:test:TICKER", "TICKER", expiry_checker
        )

        assert result is False
