"""Tests for trade_visualizer_helpers.redis_fetcher module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.trade_visualizer_helpers.redis_fetcher import RedisFetcher

TEST_STATION_ICAO = "KMIA"
TEST_MARKET_KEY = "kalshi:weather:KMIA:KXHIGHMIA-T72"
TEST_MARKET_KEY_BYTES = b"kalshi:weather:KMIA:KXHIGHMIA-T72"
TEST_TRADING_SIGNAL_KEY = "kalshi:weather:KMIA:trading_signal"
TEST_POSITION_STATE_KEY = "kalshi:weather:KMIA:position_state"
TEST_TICKER = "KXHIGHMIA-T72"
TEST_YES_BID = "45"
TEST_YES_ASK = "55"
TEST_TRADED_TRUE = "true"
TEST_TRADED_FALSE = "false"
TEST_FLOOR_STRIKE = "70"
TEST_CAP_STRIKE = "75"


class TestRedisFetcherInit:
    """Tests for RedisFetcher initialization."""

    def test_stores_trade_store(self) -> None:
        """Test stores trade store."""
        mock_store = MagicMock()
        fetcher = RedisFetcher(mock_store)

        assert fetcher._trade_store is mock_store


class TestRedisFetcherGetExecutedTradesForStation:
    """Tests for get_executed_trades_for_station method."""

    @pytest.mark.asyncio
    async def test_fetches_order_ids_from_redis(self) -> None:
        """Test fetches order ids from Redis."""
        mock_store = MagicMock()
        mock_redis = MagicMock()
        mock_redis.smembers = AsyncMock(return_value=set())

        fetcher = RedisFetcher(mock_store)
        await fetcher.get_executed_trades_for_station(
            mock_redis,
            TEST_STATION_ICAO,
            datetime.now(tz=timezone.utc),
            datetime.now(tz=timezone.utc),
        )

        mock_redis.smembers.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_trades(self) -> None:
        """Test returns empty list when no trades."""
        mock_store = MagicMock()
        mock_redis = MagicMock()
        mock_redis.smembers = AsyncMock(return_value=set())

        fetcher = RedisFetcher(mock_store)
        result = await fetcher.get_executed_trades_for_station(
            mock_redis,
            TEST_STATION_ICAO,
            datetime.now(tz=timezone.utc),
            datetime.now(tz=timezone.utc),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_filters_trades_by_time_range(self) -> None:
        """Test filters trades by time range."""
        from datetime import timedelta

        now = datetime.now(tz=timezone.utc)
        start_time = now - timedelta(hours=1)
        end_time = now

        mock_trade = MagicMock()
        mock_trade.trade_timestamp = now - timedelta(minutes=30)

        mock_store = MagicMock()
        mock_store.get_trade_by_order_id = AsyncMock(return_value=mock_trade)

        mock_redis = MagicMock()
        mock_redis.smembers = AsyncMock(return_value={b"order-123"})

        fetcher = RedisFetcher(mock_store)
        result = await fetcher.get_executed_trades_for_station(mock_redis, TEST_STATION_ICAO, start_time, end_time)

        assert len(result) == 1
        assert result[0] is mock_trade

    @pytest.mark.asyncio
    async def test_skips_trades_outside_time_range(self) -> None:
        """Test skips trades outside time range."""
        from datetime import timedelta

        now = datetime.now(tz=timezone.utc)
        start_time = now - timedelta(hours=1)
        end_time = now

        mock_trade = MagicMock()
        mock_trade.trade_timestamp = now - timedelta(hours=2)

        mock_store = MagicMock()
        mock_store.get_trade_by_order_id = AsyncMock(return_value=mock_trade)

        mock_redis = MagicMock()
        mock_redis.smembers = AsyncMock(return_value={b"order-123"})

        fetcher = RedisFetcher(mock_store)
        result = await fetcher.get_executed_trades_for_station(mock_redis, TEST_STATION_ICAO, start_time, end_time)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_handles_none_trade(self) -> None:
        """Test handles None trade from store."""
        mock_store = MagicMock()
        mock_store.get_trade_by_order_id = AsyncMock(return_value=None)

        mock_redis = MagicMock()
        mock_redis.smembers = AsyncMock(return_value={b"order-123"})

        fetcher = RedisFetcher(mock_store)
        result = await fetcher.get_executed_trades_for_station(
            mock_redis,
            TEST_STATION_ICAO,
            datetime.now(tz=timezone.utc),
            datetime.now(tz=timezone.utc),
        )

        assert result == []


class TestRedisFetcherGetMarketLiquidityStates:
    """Tests for get_market_liquidity_states method."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_non_kmia_station(self) -> None:
        """Test returns empty list for non-KMIA station."""
        mock_store = MagicMock()
        mock_redis = MagicMock()

        fetcher = RedisFetcher(mock_store)
        result = await fetcher.get_market_liquidity_states(
            mock_redis,
            "KJFK",
            datetime.now(tz=timezone.utc),
            datetime.now(tz=timezone.utc),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_fetches_market_keys_for_kmia(self) -> None:
        """Test fetches market keys for KMIA station."""
        mock_store = MagicMock()
        mock_redis = MagicMock()
        mock_redis.keys = AsyncMock(return_value=[])

        with patch("common.trade_visualizer.get_schema_config") as mock_get_schema:
            mock_schema = MagicMock()
            mock_schema.kalshi_weather_prefix = "kalshi:weather"
            mock_get_schema.return_value = mock_schema

            fetcher = RedisFetcher(mock_store)
            await fetcher.get_market_liquidity_states(
                mock_redis,
                TEST_STATION_ICAO,
                datetime.now(tz=timezone.utc),
                datetime.now(tz=timezone.utc),
            )

            mock_redis.keys.assert_called_once()


class TestRedisFetcherIsAuxiliaryKey:
    """Tests for _is_auxiliary_key method."""

    def test_returns_true_for_trading_signal_key(self) -> None:
        """Test returns True for trading signal key."""
        fetcher = RedisFetcher(MagicMock())

        result = fetcher._is_auxiliary_key(TEST_TRADING_SIGNAL_KEY)

        assert result is True

    def test_returns_true_for_position_state_key(self) -> None:
        """Test returns True for position state key."""
        fetcher = RedisFetcher(MagicMock())

        result = fetcher._is_auxiliary_key(TEST_POSITION_STATE_KEY)

        assert result is True

    def test_returns_false_for_market_key(self) -> None:
        """Test returns False for regular market key."""
        fetcher = RedisFetcher(MagicMock())

        result = fetcher._is_auxiliary_key(TEST_MARKET_KEY)

        assert result is False


class TestRedisFetcherDecodeMarketData:
    """Tests for _decode_market_data method."""

    def test_decodes_bytes_keys_and_values(self) -> None:
        """Test decodes bytes keys and values."""
        fetcher = RedisFetcher(MagicMock())
        market_data = {b"yes_bid": TEST_YES_BID.encode(), b"yes_ask": TEST_YES_ASK.encode()}

        result = fetcher._decode_market_data(market_data)

        assert result == {"yes_bid": TEST_YES_BID, "yes_ask": TEST_YES_ASK}

    def test_handles_string_keys_and_values(self) -> None:
        """Test handles string keys and values."""
        fetcher = RedisFetcher(MagicMock())
        market_data = {"yes_bid": TEST_YES_BID, "yes_ask": TEST_YES_ASK}

        result = fetcher._decode_market_data(market_data)

        assert result == {"yes_bid": TEST_YES_BID, "yes_ask": TEST_YES_ASK}

    def test_handles_mixed_types(self) -> None:
        """Test handles mixed bytes and string types."""
        fetcher = RedisFetcher(MagicMock())
        market_data = {b"yes_bid": TEST_YES_BID, "yes_ask": TEST_YES_ASK.encode()}

        result = fetcher._decode_market_data(market_data)

        assert result == {"yes_bid": TEST_YES_BID, "yes_ask": TEST_YES_ASK}


class TestRedisFetcherSafeFloat:
    """Tests for _safe_float method."""

    def test_converts_valid_float_string(self) -> None:
        """Test converts valid float string."""
        fetcher = RedisFetcher(MagicMock())

        result = fetcher._safe_float("45.5")

        assert result == 45.5

    def test_converts_int_string(self) -> None:
        """Test converts integer string."""
        fetcher = RedisFetcher(MagicMock())

        result = fetcher._safe_float("100")

        assert result == 100.0

    def test_returns_none_for_none_value(self) -> None:
        """Test returns None for None value."""
        fetcher = RedisFetcher(MagicMock())

        result = fetcher._safe_float(None)

        assert result is None

    def test_returns_none_for_invalid_string(self) -> None:
        """Test returns None for invalid string."""
        fetcher = RedisFetcher(MagicMock())

        result = fetcher._safe_float("invalid")

        assert result is None

    def test_converts_numeric_value(self) -> None:
        """Test converts numeric value directly."""
        fetcher = RedisFetcher(MagicMock())

        result = fetcher._safe_float(50.5)

        assert result == 50.5


class TestRedisFetcherBuildMarketState:
    """Tests for _build_market_state method."""

    def test_raises_for_missing_traded_field(self) -> None:
        """Test raises ValueError when traded field is missing."""
        fetcher = RedisFetcher(MagicMock())

        with pytest.raises(ValueError) as exc_info:
            fetcher._build_market_state("TICKER-123", {})

        assert "missing 'traded' field" in str(exc_info.value)

    def test_builds_market_state_with_all_fields(self) -> None:
        """Test builds MarketState with all fields."""
        fetcher = RedisFetcher(MagicMock())
        decoded = {
            "traded": TEST_TRADED_TRUE,
            "yes_bid": TEST_YES_BID,
            "yes_ask": TEST_YES_ASK,
            "floor_strike": TEST_FLOOR_STRIKE,
            "cap_strike": TEST_CAP_STRIKE,
        }

        result = fetcher._build_market_state(TEST_TICKER, decoded)

        assert result.market_ticker == TEST_TICKER
        assert result.yes_bid == 45.0
        assert result.yes_ask == 55.0
        assert result.traded is True

    def test_handles_false_traded(self) -> None:
        """Test handles false traded value."""
        fetcher = RedisFetcher(MagicMock())
        decoded = {"traded": TEST_TRADED_FALSE}

        result = fetcher._build_market_state(TEST_TICKER, decoded)

        assert result.traded is False


class TestRedisFetcherProcessMarketKeys:
    """Tests for _process_market_keys method."""

    @pytest.mark.asyncio
    async def test_processes_bytes_keys(self) -> None:
        """Test processes bytes keys correctly."""
        mock_redis = MagicMock()
        mock_redis.hgetall = AsyncMock(return_value={b"traded": b"true", b"yes_bid": b"45"})

        with patch("common.trade_visualizer.parse_kalshi_market_key") as mock_parse:
            mock_result = MagicMock()
            mock_result.ticker = TEST_TICKER
            mock_parse.return_value = mock_result

            fetcher = RedisFetcher(MagicMock())
            result = await fetcher._process_market_keys(mock_redis, [TEST_MARKET_KEY_BYTES])

            assert len(result) == 1
            assert result[0].market_ticker == TEST_TICKER

    @pytest.mark.asyncio
    async def test_skips_auxiliary_keys(self) -> None:
        """Test skips auxiliary keys during processing."""
        mock_redis = MagicMock()

        fetcher = RedisFetcher(MagicMock())
        result = await fetcher._process_market_keys(mock_redis, [TEST_TRADING_SIGNAL_KEY, TEST_POSITION_STATE_KEY])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_skips_none_states(self) -> None:
        """Test skips None states from extraction."""
        mock_redis = MagicMock()
        mock_redis.hgetall = AsyncMock(return_value={})

        fetcher = RedisFetcher(MagicMock())
        result = await fetcher._process_market_keys(mock_redis, [TEST_MARKET_KEY])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_appends_valid_states(self) -> None:
        """Test appends valid states to results."""
        mock_redis = MagicMock()
        mock_redis.hgetall = AsyncMock(return_value={b"traded": b"true"})

        with patch("common.trade_visualizer.parse_kalshi_market_key") as mock_parse:
            mock_result = MagicMock()
            mock_result.ticker = TEST_TICKER
            mock_parse.return_value = mock_result

            fetcher = RedisFetcher(MagicMock())
            result = await fetcher._process_market_keys(mock_redis, [TEST_MARKET_KEY])

            assert len(result) == 1


class TestRedisFetcherExtractMarketState:
    """Tests for _extract_market_state method."""

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_market_data(self) -> None:
        """Test returns None when market data is empty."""
        mock_redis = MagicMock()
        mock_redis.hgetall = AsyncMock(return_value={})

        fetcher = RedisFetcher(MagicMock())
        result = await fetcher._extract_market_state(mock_redis, TEST_MARKET_KEY)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_ticker_is_none(self) -> None:
        """Test returns None when ticker extraction fails."""
        mock_redis = MagicMock()
        mock_redis.hgetall = AsyncMock(return_value={b"traded": b"true"})

        with patch("common.trade_visualizer.parse_kalshi_market_key") as mock_parse:
            mock_parse.side_effect = ValueError("Invalid key")

            fetcher = RedisFetcher(MagicMock())
            result = await fetcher._extract_market_state(mock_redis, TEST_MARKET_KEY)

            assert result is None

    @pytest.mark.asyncio
    async def test_builds_market_state_on_success(self) -> None:
        """Test builds market state when all data is valid."""
        mock_redis = MagicMock()
        mock_redis.hgetall = AsyncMock(
            return_value={b"traded": b"true", b"yes_bid": b"45", b"yes_ask": b"55", b"floor_strike": b"70", b"cap_strike": b"75"}
        )

        with patch("common.trade_visualizer.parse_kalshi_market_key") as mock_parse:
            mock_result = MagicMock()
            mock_result.ticker = TEST_TICKER
            mock_parse.return_value = mock_result

            fetcher = RedisFetcher(MagicMock())
            result = await fetcher._extract_market_state(mock_redis, TEST_MARKET_KEY)

            assert result is not None
            assert result.market_ticker == TEST_TICKER
            assert result.traded is True


class TestRedisFetcherExtractTicker:
    """Tests for _extract_ticker method."""

    def test_extracts_ticker_successfully(self) -> None:
        """Test extracts ticker from valid market key."""
        with patch("common.trade_visualizer.parse_kalshi_market_key") as mock_parse:
            mock_result = MagicMock()
            mock_result.ticker = TEST_TICKER
            mock_parse.return_value = mock_result

            fetcher = RedisFetcher(MagicMock())
            result = fetcher._extract_ticker(TEST_MARKET_KEY)

            assert result == TEST_TICKER

    def test_returns_none_on_value_error(self) -> None:
        """Test returns None when parsing raises ValueError."""
        with patch("common.trade_visualizer.parse_kalshi_market_key") as mock_parse:
            mock_parse.side_effect = ValueError("Invalid key format")

            fetcher = RedisFetcher(MagicMock())
            result = fetcher._extract_ticker("invalid:key")

            assert result is None
