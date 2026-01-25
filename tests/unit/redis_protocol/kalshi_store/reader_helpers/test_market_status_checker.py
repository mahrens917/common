"""Tests for market_status_checker module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.kalshi_store.reader_helpers.market_status_checker import MarketStatusChecker


class TestMarketStatusChecker:
    """Tests for MarketStatusChecker class."""

    def test_init_stores_dependencies(self):
        """MarketStatusChecker should store all dependencies."""
        conn_wrapper = MagicMock()
        ticker_parser = MagicMock()
        expiry_checker = MagicMock()
        get_key_fn = MagicMock()

        checker = MarketStatusChecker(conn_wrapper, ticker_parser, expiry_checker, get_key_fn)

        assert checker._conn is conn_wrapper
        assert checker._ticker_parser is ticker_parser
        assert checker._expiry_checker is expiry_checker
        assert checker._get_key is get_key_fn


class TestIsExpired:
    """Tests for is_expired method."""

    @pytest.mark.asyncio
    async def test_returns_false_when_connection_fails(self):
        """is_expired should return False when connection fails."""
        conn_wrapper = MagicMock()
        conn_wrapper.ensure_connection = AsyncMock(return_value=False)
        ticker_parser = MagicMock()
        expiry_checker = MagicMock()
        get_key_fn = MagicMock()

        checker = MarketStatusChecker(conn_wrapper, ticker_parser, expiry_checker, get_key_fn)
        result = await checker.is_expired("MARKET-TICKER")

        assert result is False
        conn_wrapper.ensure_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_normalizes_ticker_and_checks_expiry(self):
        """is_expired should normalize ticker and check expiry."""
        conn_wrapper = MagicMock()
        conn_wrapper.ensure_connection = AsyncMock(return_value=True)
        redis_mock = MagicMock()
        conn_wrapper.get_redis = AsyncMock(return_value=redis_mock)

        ticker_parser = MagicMock()
        ticker_parser.normalize_ticker = MagicMock(return_value="NORMALIZED-TICKER")

        expiry_checker = MagicMock()
        expiry_checker.is_market_expired = AsyncMock(return_value=True)

        get_key_fn = MagicMock(return_value="redis:key:NORMALIZED-TICKER")

        checker = MarketStatusChecker(conn_wrapper, ticker_parser, expiry_checker, get_key_fn)
        result = await checker.is_expired("MARKET-TICKER")

        assert result is True
        ticker_parser.normalize_ticker.assert_called_once_with("MARKET-TICKER")
        get_key_fn.assert_called_once_with("NORMALIZED-TICKER")
        expiry_checker.is_market_expired.assert_called_once_with(redis_mock, "redis:key:NORMALIZED-TICKER", "NORMALIZED-TICKER")

    @pytest.mark.asyncio
    async def test_accepts_metadata_parameter(self):
        """is_expired should accept optional metadata parameter."""
        conn_wrapper = MagicMock()
        conn_wrapper.ensure_connection = AsyncMock(return_value=True)
        redis_mock = MagicMock()
        conn_wrapper.get_redis = AsyncMock(return_value=redis_mock)

        ticker_parser = MagicMock()
        ticker_parser.normalize_ticker = MagicMock(return_value="TICKER")

        expiry_checker = MagicMock()
        expiry_checker.is_market_expired = AsyncMock(return_value=False)

        get_key_fn = MagicMock(return_value="key")

        checker = MarketStatusChecker(conn_wrapper, ticker_parser, expiry_checker, get_key_fn)
        result = await checker.is_expired("TICKER", metadata={"some": "data"})

        assert result is False


class TestIsSettled:
    """Tests for is_settled method."""

    @pytest.mark.asyncio
    async def test_returns_false_when_connection_fails(self):
        """is_settled should return False when connection fails."""
        conn_wrapper = MagicMock()
        conn_wrapper.ensure_connection = AsyncMock(return_value=False)
        ticker_parser = MagicMock()
        expiry_checker = MagicMock()
        get_key_fn = MagicMock()

        checker = MarketStatusChecker(conn_wrapper, ticker_parser, expiry_checker, get_key_fn)
        result = await checker.is_settled("MARKET-TICKER")

        assert result is False
        conn_wrapper.ensure_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_normalizes_ticker_and_checks_settlement(self):
        """is_settled should normalize ticker and check settlement."""
        conn_wrapper = MagicMock()
        conn_wrapper.ensure_connection = AsyncMock(return_value=True)
        redis_mock = MagicMock()
        conn_wrapper.get_redis = AsyncMock(return_value=redis_mock)

        ticker_parser = MagicMock()
        ticker_parser.normalize_ticker = MagicMock(return_value="NORMALIZED-TICKER")

        expiry_checker = MagicMock()
        expiry_checker.is_market_settled = AsyncMock(return_value=True)

        get_key_fn = MagicMock(return_value="redis:key:NORMALIZED-TICKER")

        checker = MarketStatusChecker(conn_wrapper, ticker_parser, expiry_checker, get_key_fn)
        result = await checker.is_settled("MARKET-TICKER")

        assert result is True
        ticker_parser.normalize_ticker.assert_called_once_with("MARKET-TICKER")
        get_key_fn.assert_called_once_with("NORMALIZED-TICKER")
        expiry_checker.is_market_settled.assert_called_once_with(redis_mock, "redis:key:NORMALIZED-TICKER", "NORMALIZED-TICKER")

    @pytest.mark.asyncio
    async def test_returns_false_when_not_settled(self):
        """is_settled should return False when market is not settled."""
        conn_wrapper = MagicMock()
        conn_wrapper.ensure_connection = AsyncMock(return_value=True)
        redis_mock = MagicMock()
        conn_wrapper.get_redis = AsyncMock(return_value=redis_mock)

        ticker_parser = MagicMock()
        ticker_parser.normalize_ticker = MagicMock(return_value="TICKER")

        expiry_checker = MagicMock()
        expiry_checker.is_market_settled = AsyncMock(return_value=False)

        get_key_fn = MagicMock(return_value="key")

        checker = MarketStatusChecker(conn_wrapper, ticker_parser, expiry_checker, get_key_fn)
        result = await checker.is_settled("TICKER")

        assert result is False
