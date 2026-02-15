"""Tests for weather_services.market_repository module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.weather_services.market_repository import (
    MarketSnapshot,
    RedisWeatherMarketRepository,
)


class TestMarketSnapshot:
    """Tests for MarketSnapshot dataclass."""

    def test_stores_all_fields(self) -> None:
        """Test stores all fields."""
        snapshot = MarketSnapshot(
            key="kalshi:weather:KMIA",
            ticker="KXHIGHMIA-25DEC26-T72",
            strike_type="greater",
            data={"open": 0.5, "close": 0.6},
        )

        assert snapshot.key == "kalshi:weather:KMIA"
        assert snapshot.ticker == "KXHIGHMIA-25DEC26-T72"
        assert snapshot.strike_type == "greater"
        assert snapshot.data == {"open": 0.5, "close": 0.6}

    def test_is_frozen(self) -> None:
        """Test dataclass is frozen."""
        snapshot = MarketSnapshot(
            key="test",
            ticker="TEST-123",
            strike_type="between",
            data={},
        )

        with pytest.raises(AttributeError):
            snapshot.key = "new_key"


class TestRedisWeatherMarketRepositoryInit:
    """Tests for RedisWeatherMarketRepository initialization."""

    def test_stores_dependencies(self) -> None:
        """Test stores dependencies."""
        mock_redis = MagicMock()
        mock_store = MagicMock()

        repo = RedisWeatherMarketRepository(mock_redis, mock_store)

        assert repo._redis is mock_redis
        assert repo._kalshi_store is mock_store


class TestRedisWeatherMarketRepositoryGetWeatherData:
    """Tests for get_weather_data method."""

    @pytest.mark.asyncio
    async def test_returns_decoded_hash(self) -> None:
        """Test returns decoded Redis hash."""
        mock_redis = MagicMock()
        mock_redis.hgetall = MagicMock(return_value={b"temp": b"72.5"})
        mock_store = MagicMock()

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            with patch("common.weather_services.market_repository.decode_redis_hash", return_value={"temp": 72.5}):
                repo = RedisWeatherMarketRepository(mock_redis, mock_store)
                result = await repo.get_weather_data("KMIA")

                assert result == {"temp": 72.5}


class TestRedisWeatherMarketRepositorySetMarketFields:
    """Tests for set_market_fields method."""

    @pytest.mark.asyncio
    async def test_calls_redis_hset(self) -> None:
        """Test calls Redis hset with mapping."""
        mock_redis = MagicMock()
        mock_redis.hset = MagicMock()
        mock_store = MagicMock()

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            repo = RedisWeatherMarketRepository(mock_redis, mock_store)
            await repo.set_market_fields("market:key", {"field1": "value1"})

            mock_redis.hset.assert_called_once_with("market:key", mapping={"field1": "value1"})


class TestRedisWeatherMarketRepositoryResolveStrikeType:
    """Tests for _resolve_strike_type static method."""

    def test_uses_snapshot_strike_type(self) -> None:
        """Test uses strike_type from snapshot when available."""
        result = RedisWeatherMarketRepository._resolve_strike_type(
            {"strike_type": "Greater"},
        )

        assert result == "greater"

    def test_returns_between(self) -> None:
        """Test returns between strike type."""
        result = RedisWeatherMarketRepository._resolve_strike_type(
            {"strike_type": "between"},
        )

        assert result == "between"

    def test_returns_less(self) -> None:
        """Test returns less strike type."""
        result = RedisWeatherMarketRepository._resolve_strike_type(
            {"strike_type": "Less"},
        )

        assert result == "less"

    def test_returns_none_when_missing(self) -> None:
        """Test returns None when strike_type is absent."""
        result = RedisWeatherMarketRepository._resolve_strike_type({})

        assert result is None

    def test_returns_none_for_empty_strike_type(self) -> None:
        """Test returns None for empty/whitespace strike_type string."""
        result = RedisWeatherMarketRepository._resolve_strike_type(
            {"strike_type": "  "},
        )

        assert result is None

    def test_returns_none_for_none_strike_type(self) -> None:
        """Test returns None when strike_type is None."""
        result = RedisWeatherMarketRepository._resolve_strike_type(
            {"strike_type": None},
        )

        assert result is None


class TestRedisWeatherMarketRepositoryScan:
    """Tests for _scan method."""

    @pytest.mark.asyncio
    async def test_iterates_over_keys(self) -> None:
        """Test iterates over all matching keys."""
        mock_redis = MagicMock()
        # Simulate two batches, then cursor returns to 0
        mock_redis.scan = MagicMock(
            side_effect=[
                (1, [b"key1", b"key2"]),
                (0, [b"key3"]),
            ]
        )
        mock_store = MagicMock()

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            repo = RedisWeatherMarketRepository(mock_redis, mock_store)
            keys = []
            async for key in repo._scan("pattern:*"):
                keys.append(key)

            assert len(keys) == 3

    @pytest.mark.asyncio
    async def test_stops_when_cursor_zero(self) -> None:
        """Test stops iteration when cursor returns to 0."""
        mock_redis = MagicMock()
        mock_redis.scan = MagicMock(return_value=(0, [b"key1"]))
        mock_store = MagicMock()

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            repo = RedisWeatherMarketRepository(mock_redis, mock_store)
            keys = []
            async for key in repo._scan("pattern:*"):
                keys.append(key)

            assert len(keys) == 1
            mock_redis.scan.assert_called_once()


TEST_CITY_CODE = "MIA"
TEST_DAY_CODE = "25DEC26"
TEST_TICKER_WITH_DAY = "KXHIGHMIA-25DEC26-T72"
TEST_TICKER_WITHOUT_DAY = "KXHIGHMIA-26DEC26-T75"
TEST_MARKET_KEY = "markets:kalshi:weather:KXHIGHMIA-25DEC26-T72"
TEST_MARKET_KEY_ALT = "markets:kalshi:weather:KXHIGHMIA-26DEC26-T75"
TEST_TRADING_SIGNAL_KEY = "markets:kalshi:weather:KXHIGHMIA-25DEC26-T72:trading_signal"
TEST_POSITION_STATE_KEY = "markets:kalshi:weather:position_state:KXHIGHMIA-25DEC26-T72"


class TestRedisWeatherMarketRepositoryIterCityMarkets:
    """Tests for iter_city_markets method."""

    @pytest.mark.asyncio
    async def test_yields_valid_market_snapshots(self) -> None:
        """Test yields valid market snapshots."""
        mock_redis = MagicMock()
        mock_redis.scan = MagicMock(return_value=(0, [TEST_MARKET_KEY.encode()]))

        mock_descriptor = MagicMock()
        mock_descriptor.ticker = TEST_TICKER_WITH_DAY

        mock_snapshot = {"open": 0.5, "close": 0.6}
        mock_enriched = {"open": 0.5, "close": 0.6, "strike_type": "greater"}

        mock_store = MagicMock()
        mock_store.get_market_snapshot_by_key = AsyncMock(return_value=mock_snapshot)

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            with patch("common.weather_services.market_repository.parse_kalshi_market_key", return_value=mock_descriptor):
                with patch("common.weather_services.market_repository.ensure_market_metadata_fields", return_value=mock_enriched):
                    repo = RedisWeatherMarketRepository(mock_redis, mock_store)
                    snapshots = []
                    async for snapshot in repo.iter_city_markets(TEST_CITY_CODE):
                        snapshots.append(snapshot)

                    assert len(snapshots) == 1
                    assert snapshots[0].key == TEST_MARKET_KEY
                    assert snapshots[0].ticker == TEST_TICKER_WITH_DAY
                    assert snapshots[0].strike_type == "greater"
                    assert snapshots[0].data == mock_enriched

    @pytest.mark.asyncio
    async def test_filters_by_day_code(self) -> None:
        """Test filters markets by day_code."""
        mock_redis = MagicMock()
        mock_redis.scan = MagicMock(return_value=(0, [TEST_MARKET_KEY.encode(), TEST_MARKET_KEY_ALT.encode()]))

        mock_descriptor1 = MagicMock()
        mock_descriptor1.ticker = TEST_TICKER_WITH_DAY

        mock_descriptor2 = MagicMock()
        mock_descriptor2.ticker = TEST_TICKER_WITHOUT_DAY

        mock_snapshot = {"open": 0.5}
        mock_enriched = {"open": 0.5, "strike_type": "greater"}

        mock_store = MagicMock()
        mock_store.get_market_snapshot_by_key = AsyncMock(return_value=mock_snapshot)

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            with patch(
                "common.weather_services.market_repository.parse_kalshi_market_key", side_effect=[mock_descriptor1, mock_descriptor2]
            ):
                with patch("common.weather_services.market_repository.ensure_market_metadata_fields", return_value=mock_enriched):
                    repo = RedisWeatherMarketRepository(mock_redis, mock_store)
                    snapshots = []
                    async for snapshot in repo.iter_city_markets(TEST_CITY_CODE, day_code=TEST_DAY_CODE):
                        snapshots.append(snapshot)

                    assert len(snapshots) == 1
                    assert snapshots[0].ticker == TEST_TICKER_WITH_DAY

    @pytest.mark.asyncio
    async def test_skips_trading_signal_keys(self) -> None:
        """Test skips keys ending with :trading_signal."""
        mock_redis = MagicMock()
        mock_redis.scan = MagicMock(return_value=(0, [TEST_TRADING_SIGNAL_KEY.encode()]))

        mock_store = MagicMock()

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            repo = RedisWeatherMarketRepository(mock_redis, mock_store)
            snapshots = []
            async for snapshot in repo.iter_city_markets(TEST_CITY_CODE):
                snapshots.append(snapshot)

            assert len(snapshots) == 0

    @pytest.mark.asyncio
    async def test_skips_position_state_keys(self) -> None:
        """Test skips keys containing :position_state."""
        mock_redis = MagicMock()
        mock_redis.scan = MagicMock(return_value=(0, [TEST_POSITION_STATE_KEY.encode()]))

        mock_store = MagicMock()

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            repo = RedisWeatherMarketRepository(mock_redis, mock_store)
            snapshots = []
            async for snapshot in repo.iter_city_markets(TEST_CITY_CODE):
                snapshots.append(snapshot)

            assert len(snapshots) == 0

    @pytest.mark.asyncio
    async def test_handles_string_keys(self) -> None:
        """Test handles string keys instead of bytes."""
        mock_redis = MagicMock()
        mock_redis.scan = MagicMock(return_value=(0, [TEST_MARKET_KEY]))

        mock_descriptor = MagicMock()
        mock_descriptor.ticker = TEST_TICKER_WITH_DAY

        mock_snapshot = {"open": 0.5}
        mock_enriched = {"open": 0.5, "strike_type": "greater"}

        mock_store = MagicMock()
        mock_store.get_market_snapshot_by_key = AsyncMock(return_value=mock_snapshot)

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            with patch("common.weather_services.market_repository.parse_kalshi_market_key", return_value=mock_descriptor):
                with patch("common.weather_services.market_repository.ensure_market_metadata_fields", return_value=mock_enriched):
                    repo = RedisWeatherMarketRepository(mock_redis, mock_store)
                    snapshots = []
                    async for snapshot in repo.iter_city_markets(TEST_CITY_CODE):
                        snapshots.append(snapshot)

                    assert len(snapshots) == 1
                    assert snapshots[0].key == TEST_MARKET_KEY

    @pytest.mark.asyncio
    async def test_skips_parse_value_errors(self) -> None:
        """Test skips keys that raise ValueError during parsing."""
        mock_redis = MagicMock()
        mock_redis.scan = MagicMock(return_value=(0, [b"invalid:key:format"]))

        mock_store = MagicMock()

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            with patch("common.weather_services.market_repository.parse_kalshi_market_key", side_effect=ValueError("Invalid format")):
                repo = RedisWeatherMarketRepository(mock_redis, mock_store)
                snapshots = []
                async for snapshot in repo.iter_city_markets(TEST_CITY_CODE):
                    snapshots.append(snapshot)

                assert len(snapshots) == 0

    @pytest.mark.asyncio
    async def test_skips_parse_type_errors(self) -> None:
        """Test skips keys that raise TypeError during parsing."""
        mock_redis = MagicMock()
        mock_redis.scan = MagicMock(return_value=(0, [b"malformed:key"]))

        mock_store = MagicMock()

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            with patch("common.weather_services.market_repository.parse_kalshi_market_key", side_effect=TypeError("Invalid type")):
                repo = RedisWeatherMarketRepository(mock_redis, mock_store)
                snapshots = []
                async for snapshot in repo.iter_city_markets(TEST_CITY_CODE):
                    snapshots.append(snapshot)

                assert len(snapshots) == 0

    @pytest.mark.asyncio
    async def test_skips_empty_snapshots(self) -> None:
        """Test skips when get_market_snapshot_by_key returns None."""
        mock_redis = MagicMock()
        mock_redis.scan = MagicMock(return_value=(0, [TEST_MARKET_KEY.encode()]))

        mock_descriptor = MagicMock()
        mock_descriptor.ticker = TEST_TICKER_WITH_DAY

        mock_store = MagicMock()
        mock_store.get_market_snapshot_by_key = AsyncMock(return_value=None)

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            with patch("common.weather_services.market_repository.parse_kalshi_market_key", return_value=mock_descriptor):
                repo = RedisWeatherMarketRepository(mock_redis, mock_store)
                snapshots = []
                async for snapshot in repo.iter_city_markets(TEST_CITY_CODE):
                    snapshots.append(snapshot)

                assert len(snapshots) == 0

    @pytest.mark.asyncio
    async def test_skips_falsy_snapshots(self) -> None:
        """Test skips when get_market_snapshot_by_key returns empty dict."""
        mock_redis = MagicMock()
        mock_redis.scan = MagicMock(return_value=(0, [TEST_MARKET_KEY.encode()]))

        mock_descriptor = MagicMock()
        mock_descriptor.ticker = TEST_TICKER_WITH_DAY

        mock_store = MagicMock()
        mock_store.get_market_snapshot_by_key = AsyncMock(return_value={})

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            with patch("common.weather_services.market_repository.parse_kalshi_market_key", return_value=mock_descriptor):
                repo = RedisWeatherMarketRepository(mock_redis, mock_store)
                snapshots = []
                async for snapshot in repo.iter_city_markets(TEST_CITY_CODE):
                    snapshots.append(snapshot)

                assert len(snapshots) == 0

    @pytest.mark.asyncio
    async def test_resolves_strike_type_from_snapshot(self) -> None:
        """Test resolves strike_type using _resolve_strike_type."""
        mock_redis = MagicMock()
        mock_redis.scan = MagicMock(return_value=(0, [TEST_MARKET_KEY.encode()]))

        mock_descriptor = MagicMock()
        mock_descriptor.ticker = TEST_TICKER_WITH_DAY

        mock_snapshot = {"open": 0.5}
        mock_enriched = {"open": 0.5, "strike_type": "BETWEEN"}

        mock_store = MagicMock()
        mock_store.get_market_snapshot_by_key = AsyncMock(return_value=mock_snapshot)

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            with patch("common.weather_services.market_repository.parse_kalshi_market_key", return_value=mock_descriptor):
                with patch("common.weather_services.market_repository.ensure_market_metadata_fields", return_value=mock_enriched):
                    repo = RedisWeatherMarketRepository(mock_redis, mock_store)
                    snapshots = []
                    async for snapshot in repo.iter_city_markets(TEST_CITY_CODE):
                        snapshots.append(snapshot)

                    assert len(snapshots) == 1
                    assert snapshots[0].strike_type == "between"

    @pytest.mark.asyncio
    async def test_uses_lowercase_city_code_in_pattern(self) -> None:
        """Test uses lowercase city code in scan pattern."""
        mock_redis = MagicMock()
        mock_redis.scan = MagicMock(return_value=(0, []))

        mock_store = MagicMock()

        with patch("common.weather_services.market_repository.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            with patch("common.weather_services.market_repository.SCHEMA") as mock_schema:
                mock_schema.kalshi_weather_prefix = "markets:kalshi:weather"
                repo = RedisWeatherMarketRepository(mock_redis, mock_store)
                snapshots = []
                async for snapshot in repo.iter_city_markets("MIA"):
                    snapshots.append(snapshot)

                mock_redis.scan.assert_called_once()
                call_args = mock_redis.scan.call_args
                assert "mia" in call_args[1]["match"].lower()
