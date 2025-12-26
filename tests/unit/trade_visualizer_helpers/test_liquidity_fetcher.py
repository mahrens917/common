"""Tests for trade_visualizer_helpers.liquidity_fetcher module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.trade_visualizer_helpers.liquidity_fetcher import (
    LiquidityFetcher,
    MarketState,
)


class TestMarketState:
    """Tests for MarketState dataclass."""

    def test_init(self) -> None:
        """Test MarketState initialization."""
        timestamp = datetime.now(timezone.utc)
        state = MarketState(
            timestamp=timestamp,
            market_ticker="KXBTC-25JAN01-100000",
            yes_bid=0.45,
            yes_ask=0.55,
            traded=True,
            min_strike_price_cents=100.0,
            max_strike_price_cents=200.0,
        )

        assert state.timestamp == timestamp
        assert state.market_ticker == "KXBTC-25JAN01-100000"
        assert state.yes_bid == 0.45
        assert state.yes_ask == 0.55
        assert state.traded is True
        assert state.min_strike_price_cents == 100.0
        assert state.max_strike_price_cents == 200.0

    def test_init_optional_values(self) -> None:
        """Test MarketState with None values."""
        timestamp = datetime.now(timezone.utc)
        state = MarketState(
            timestamp=timestamp,
            market_ticker="KXBTC-25JAN01-100000",
            yes_bid=None,
            yes_ask=None,
            traded=False,
            min_strike_price_cents=None,
            max_strike_price_cents=None,
        )

        assert state.yes_bid is None
        assert state.yes_ask is None
        assert state.traded is False


class TestLiquidityFetcherSafeFloat:
    """Tests for LiquidityFetcher.safe_float method."""

    def test_valid_float(self) -> None:
        """Test parsing valid float string."""
        result = LiquidityFetcher.safe_float("1.5")
        assert result == 1.5

    def test_valid_integer(self) -> None:
        """Test parsing integer string."""
        result = LiquidityFetcher.safe_float("42")
        assert result == 42.0

    def test_none_value(self) -> None:
        """Test None returns None."""
        result = LiquidityFetcher.safe_float(None)
        assert result is None

    def test_empty_string(self) -> None:
        """Test empty string returns None."""
        result = LiquidityFetcher.safe_float("")
        assert result is None

    def test_invalid_string(self) -> None:
        """Test invalid string returns None."""
        result = LiquidityFetcher.safe_float("not_a_number")
        assert result is None


class TestLiquidityFetcherShouldScanStation:
    """Tests for _should_scan_station method."""

    def test_kmia_returns_true(self) -> None:
        """Test KMIA station returns True."""
        fetcher = LiquidityFetcher()
        assert fetcher._should_scan_station("KMIA") is True

    def test_other_station_returns_false(self) -> None:
        """Test other stations return False."""
        fetcher = LiquidityFetcher()
        assert fetcher._should_scan_station("KJFK") is False


class TestLiquidityFetcherShouldSkipMarket:
    """Tests for _should_skip_market method."""

    def test_trading_signal_skipped(self) -> None:
        """Test trading signal keys are skipped."""
        fetcher = LiquidityFetcher()
        assert fetcher._should_skip_market("market:trading_signal:test") is True

    def test_position_state_skipped(self) -> None:
        """Test position state keys are skipped."""
        fetcher = LiquidityFetcher()
        assert fetcher._should_skip_market("market:position_state:test") is True

    def test_regular_market_not_skipped(self) -> None:
        """Test regular market keys are not skipped."""
        fetcher = LiquidityFetcher()
        assert fetcher._should_skip_market("kalshi_weather:KXMIA-25JAN01") is False


class TestLiquidityFetcherBuildMarketState:
    """Tests for _build_market_state method."""

    def test_builds_state_with_all_fields(self) -> None:
        """Test building state with all fields."""
        fetcher = LiquidityFetcher()
        decoded = {
            "yes_bid": "0.45",
            "yes_ask": "0.55",
            "traded": "true",
            "floor_strike": "100.0",
            "cap_strike": "200.0",
        }

        state = fetcher._build_market_state(decoded, "KXMIA-25JAN01-100")

        assert state.market_ticker == "KXMIA-25JAN01-100"
        assert state.yes_bid == 0.45
        assert state.yes_ask == 0.55
        assert state.traded is True
        assert state.min_strike_price_cents == 100.0
        assert state.max_strike_price_cents == 200.0

    def test_builds_state_with_false_traded(self) -> None:
        """Test building state with traded=false."""
        fetcher = LiquidityFetcher()
        decoded = {
            "yes_bid": "0.30",
            "yes_ask": "0.40",
            "traded": "false",
            "floor_strike": "50.0",
            "cap_strike": "75.0",
        }

        state = fetcher._build_market_state(decoded, "KXMIA-25JAN01-50")

        assert state.traded is False

    def test_builds_state_missing_traded(self) -> None:
        """Test building state with missing traded field."""
        fetcher = LiquidityFetcher()
        decoded = {
            "yes_bid": "0.30",
            "yes_ask": "0.40",
        }

        state = fetcher._build_market_state(decoded, "KXMIA-25JAN01-50")

        assert state.traded is False


class TestLiquidityFetcherGetMarketLiquidityStates:
    """Tests for get_market_liquidity_states method."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_non_kmia_station(self) -> None:
        """Test returns empty for non-KMIA station."""
        fetcher = LiquidityFetcher()
        start = datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)

        result = await fetcher.get_market_liquidity_states("KJFK", start, end)

        assert result == []

    @pytest.mark.asyncio
    async def test_handles_redis_connection_error(self) -> None:
        """Test handles Redis connection error gracefully."""
        fetcher = LiquidityFetcher()
        start = datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)

        with patch(
            "common.trade_visualizer_helpers.liquidity_fetcher.get_redis_connection",
            side_effect=ConnectionError("Redis unavailable"),
        ):
            result = await fetcher.get_market_liquidity_states("KMIA", start, end)

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_states_for_valid_markets(self) -> None:
        """Test returns states for valid markets."""
        fetcher = LiquidityFetcher()
        start = datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)

        mock_redis = MagicMock()
        mock_redis.keys = AsyncMock(return_value=[b"kalshi_weather:KXMIA-25JAN01-100"])
        mock_redis.hgetall = AsyncMock(
            return_value={
                b"yes_bid": b"0.45",
                b"yes_ask": b"0.55",
                b"traded": b"true",
                b"floor_strike": b"100.0",
                b"cap_strike": b"200.0",
            }
        )
        mock_redis.aclose = AsyncMock()

        with (
            patch(
                "common.trade_visualizer_helpers.liquidity_fetcher.get_redis_connection",
                return_value=mock_redis,
            ),
            patch("common.trade_visualizer_helpers.liquidity_fetcher.parse_kalshi_market_key") as mock_parse,
        ):
            mock_parsed = MagicMock()
            mock_parsed.ticker = "KXMIA-25JAN01-100"
            mock_parse.return_value = mock_parsed

            result = await fetcher.get_market_liquidity_states("KMIA", start, end)

        assert len(result) == 1
        assert result[0].market_ticker == "KXMIA-25JAN01-100"

    @pytest.mark.asyncio
    async def test_skips_trading_signal_keys(self) -> None:
        """Test skips trading signal keys."""
        fetcher = LiquidityFetcher()
        start = datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)

        mock_redis = MagicMock()
        mock_redis.keys = AsyncMock(return_value=[b"kalshi_weather:trading_signal:test"])
        mock_redis.aclose = AsyncMock()

        with patch(
            "common.trade_visualizer_helpers.liquidity_fetcher.get_redis_connection",
            return_value=mock_redis,
        ):
            result = await fetcher.get_market_liquidity_states("KMIA", start, end)

        assert result == []


class TestLiquidityFetcherLoadMarketHash:
    """Tests for _load_market_hash method."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_data(self) -> None:
        """Test returns empty dict when no market data."""
        fetcher = LiquidityFetcher()
        mock_redis = MagicMock()
        mock_redis.hgetall = AsyncMock(return_value={})

        result = await fetcher._load_market_hash(mock_redis, "test_key")

        assert result == {}

    @pytest.mark.asyncio
    async def test_decodes_bytes_keys_and_values(self) -> None:
        """Test decodes bytes to strings."""
        fetcher = LiquidityFetcher()
        mock_redis = MagicMock()
        mock_redis.hgetall = AsyncMock(return_value={b"key1": b"value1", b"key2": b"value2"})

        result = await fetcher._load_market_hash(mock_redis, "test_key")

        assert result == {"key1": "value1", "key2": "value2"}


class TestLiquidityFetcherParseMarketTicker:
    """Tests for _parse_market_ticker method."""

    def test_returns_ticker_on_success(self) -> None:
        """Test returns ticker when parsing succeeds."""
        fetcher = LiquidityFetcher()

        with patch("common.trade_visualizer_helpers.liquidity_fetcher.parse_kalshi_market_key") as mock_parse:
            mock_result = MagicMock()
            mock_result.ticker = "KXMIA-25JAN01-100"
            mock_parse.return_value = mock_result

            result = fetcher._parse_market_ticker("kalshi_weather:KXMIA-25JAN01-100")

        assert result == "KXMIA-25JAN01-100"

    def test_returns_none_on_parse_error(self) -> None:
        """Test returns None when parsing fails."""
        fetcher = LiquidityFetcher()

        with patch(
            "common.trade_visualizer_helpers.liquidity_fetcher.parse_kalshi_market_key",
            side_effect=ValueError("Invalid key"),
        ):
            result = fetcher._parse_market_ticker("invalid_key")

        assert result is None
