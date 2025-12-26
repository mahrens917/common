"""Tests for kalshi_market_catalog module."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from common.kalshi_market_catalog import (
    KalshiMarketCatalog,
    KalshiMarketCatalogError,
    _load_kalshi_settings_func,
)
from common.redis_protocol.messages import InstrumentMetadata

# Module-level test constants (data_guard requirement)
TEST_TICKER_BTC = "BTC-31JAN25-60000-P"
TEST_TICKER_ETH = "ETH-31JAN25-3000-C"
TEST_TICKER_WEATHER = "KXHIGH-NYC-25DEC25"
TEST_CURRENCY = "USD"
TEST_CLOSE_TIME = "2025-01-31T16:00:00Z"
TEST_REFRESH_INTERVAL = 900
TEST_MARKET_STATUS = "open"
TEST_CATEGORY_CRYPTO = "Crypto"
TEST_CATEGORY_WEATHER = "Climate and Weather"
TEST_STATION_TOKEN_NYC = "NYC"
TEST_STATION_TOKEN_LAX = "LAX"
TEST_CONFIG_DIR = "/test/config"


class TestLoadKalshiSettingsFunc:
    """Tests for _load_kalshi_settings_func."""

    def test_loads_kalshi_settings_from_src_kalshi(self) -> None:
        """Test loading settings from src.kalshi.settings module."""
        mock_module = Mock()
        mock_get_settings = Mock()
        mock_module.get_kalshi_settings = mock_get_settings

        with patch("importlib.import_module", return_value=mock_module) as mock_import:
            get_settings_func = _load_kalshi_settings_func()

            assert get_settings_func is mock_get_settings
            mock_import.assert_called_once_with("src.kalshi.settings")

    def test_loads_kalshi_settings_from_kalshi(self) -> None:
        """Test loading settings from kalshi.settings module when src.kalshi fails."""

        def side_effect(module_path: str):
            if module_path == "src.kalshi.settings":
                raise ImportError("Module not found")
            mock_module = Mock()
            mock_get_settings = Mock()
            mock_module.get_kalshi_settings = mock_get_settings
            return mock_module

        with patch("importlib.import_module", side_effect=side_effect) as mock_import:
            get_settings_func = _load_kalshi_settings_func()

            assert get_settings_func is not None
            assert callable(get_settings_func)
            assert mock_import.call_count == 2

    def test_returns_fallback_when_modules_not_found(self) -> None:
        """Test fallback when kalshi modules are not installed."""
        with patch("importlib.import_module", side_effect=ImportError("Module not found")):
            get_settings_func = _load_kalshi_settings_func()
            settings = get_settings_func()

            assert settings.market_catalog.refresh_interval_seconds == TEST_REFRESH_INTERVAL
            assert settings.market_catalog.categories == (TEST_CATEGORY_CRYPTO, TEST_CATEGORY_WEATHER)
            assert settings.market_catalog.status == TEST_MARKET_STATUS

    def test_fallback_on_module_not_found_error(self) -> None:
        """Test fallback when ModuleNotFoundError is raised."""
        with patch("importlib.import_module", side_effect=ModuleNotFoundError("No module")):
            get_settings_func = _load_kalshi_settings_func()
            settings = get_settings_func()

            assert settings.market_catalog is not None

    def test_fallback_on_attribute_error(self) -> None:
        """Test fallback when AttributeError is raised."""
        with patch("importlib.import_module", side_effect=AttributeError("No attribute")):
            get_settings_func = _load_kalshi_settings_func()
            settings = get_settings_func()

            assert settings.market_catalog is not None


class TestKalshiMarketCatalogInit:
    """Tests for KalshiMarketCatalog initialization."""

    def test_init_with_settings_from_external_module(self) -> None:
        """Test initialization with settings from external kalshi module."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=600, categories=(TEST_CATEGORY_CRYPTO,), status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = {TEST_STATION_TOKEN_NYC, TEST_STATION_TOKEN_LAX}
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)

            assert catalog._refresh_interval_seconds == 600
            assert catalog._market_categories == (TEST_CATEGORY_CRYPTO,)
            assert catalog._market_status == TEST_MARKET_STATUS

    def test_init_with_minimum_refresh_interval(self) -> None:
        """Test initialization enforces minimum refresh interval of 1 second."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=0, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)

            assert catalog._refresh_interval_seconds == 1

    def test_init_with_none_categories(self) -> None:
        """Test initialization with None categories."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)

            assert catalog._market_categories is None

    def test_init_with_empty_status_uses_default(self) -> None:
        """Test initialization with empty status uses default."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status="")
        )
        mock_get_settings = Mock(return_value=mock_settings)

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)

            assert catalog._market_status == TEST_MARKET_STATUS

    def test_init_with_none_status_uses_default(self) -> None:
        """Test initialization with None status uses default."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=None)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)

            assert catalog._market_status == TEST_MARKET_STATUS

    def test_init_loads_weather_station_tokens(self) -> None:
        """Test initialization loads weather station tokens."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        expected_tokens = {TEST_STATION_TOKEN_NYC, TEST_STATION_TOKEN_LAX, "CHI"}

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
            patch("common.kalshi_market_catalog.Path") as mock_path,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = expected_tokens
            mock_loader_cls.return_value = mock_loader

            mock_path_instance = Mock()
            mock_path_instance.resolve.return_value.parents = [Mock(), Mock(), Mock()]
            mock_path_instance.resolve.return_value.parents[2] = Mock()
            mock_path_instance.resolve.return_value.parents[2].__truediv__ = Mock(return_value="config_root")
            mock_path.__file__ = "/src/common/kalshi_market_catalog.py"

            catalog = KalshiMarketCatalog(mock_client)

            mock_loader.load_station_tokens.assert_called_once()
            assert catalog._market_filter is not None


class TestKalshiMarketCatalogRefreshIntervalProperty:
    """Tests for refresh_interval_seconds property."""

    def test_refresh_interval_seconds_property(self) -> None:
        """Test refresh_interval_seconds property returns configured value."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=1200, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)

            assert catalog.refresh_interval_seconds == 1200


class TestKalshiMarketCatalogFetchMarkets:
    """Tests for fetch_markets method."""

    @pytest.mark.asyncio
    async def test_fetch_markets_success_with_categories(self) -> None:
        """Test successful market fetch with categories."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(
                refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=(TEST_CATEGORY_CRYPTO,), status=TEST_MARKET_STATUS
            )
        )
        mock_get_settings = Mock(return_value=mock_settings)

        test_markets = [{"ticker": TEST_TICKER_BTC, "currency": TEST_CURRENCY}]

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)
            catalog._market_fetcher = Mock()
            catalog._market_fetcher.fetch_all_markets = AsyncMock(return_value=(test_markets, 1))
            catalog._market_filter = Mock()
            catalog._market_filter.filter_markets.return_value = (
                test_markets,
                {"crypto_kept": 1, "crypto_total": 1, "weather_kept": 0, "weather_total": 0, "other_total": 0},
            )

            markets = await catalog.fetch_markets()

            assert markets == test_markets
            catalog._market_fetcher.fetch_all_markets.assert_called_once_with((TEST_CATEGORY_CRYPTO,))

    @pytest.mark.asyncio
    async def test_fetch_markets_success_with_all_categories(self) -> None:
        """Test successful market fetch with all categories (None)."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        test_markets = [{"ticker": TEST_TICKER_BTC, "currency": TEST_CURRENCY}]

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)
            catalog._market_fetcher = Mock()
            catalog._market_fetcher.fetch_all_markets = AsyncMock(return_value=(test_markets, 2))
            catalog._market_filter = Mock()
            catalog._market_filter.filter_markets.return_value = (
                test_markets,
                {"crypto_kept": 1, "crypto_total": 1, "weather_kept": 0, "weather_total": 0, "other_total": 0},
            )

            markets = await catalog.fetch_markets()

            assert markets == test_markets
            catalog._market_fetcher.fetch_all_markets.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_fetch_markets_raises_error_when_no_filtered_markets(self) -> None:
        """Test fetch_markets raises error when no markets pass filtering."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)
            catalog._market_fetcher = Mock()
            catalog._market_fetcher.fetch_all_markets = AsyncMock(return_value=([{"ticker": TEST_TICKER_BTC}], 1))
            catalog._market_filter = Mock()
            catalog._market_filter.filter_markets.return_value = (
                [],
                {"crypto_kept": 0, "crypto_total": 1, "weather_kept": 0, "weather_total": 0, "other_total": 0},
            )

            with pytest.raises(KalshiMarketCatalogError, match="No eligible Kalshi markets returned after filtering"):
                await catalog.fetch_markets()


class TestKalshiMarketCatalogFetchMetadata:
    """Tests for fetch_metadata method."""

    @pytest.mark.asyncio
    async def test_fetch_metadata_success(self) -> None:
        """Test successful metadata fetch."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        test_markets = [{"ticker": TEST_TICKER_BTC, "currency": TEST_CURRENCY, "close_time": TEST_CLOSE_TIME}]

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)
            catalog._market_fetcher = Mock()
            catalog._market_fetcher.fetch_all_markets = AsyncMock(return_value=(test_markets, 1))
            catalog._market_filter = Mock()
            catalog._market_filter.filter_markets.return_value = (
                test_markets,
                {"crypto_kept": 1, "crypto_total": 1, "weather_kept": 0, "weather_total": 0, "other_total": 0},
            )

            metadata = await catalog.fetch_metadata()

            assert TEST_TICKER_BTC in metadata
            assert isinstance(metadata[TEST_TICKER_BTC], InstrumentMetadata)
            assert metadata[TEST_TICKER_BTC].type == "market"
            assert metadata[TEST_TICKER_BTC].channel == f"market.{TEST_TICKER_BTC}"
            assert metadata[TEST_TICKER_BTC].currency == TEST_CURRENCY
            assert metadata[TEST_TICKER_BTC].expiry == TEST_CLOSE_TIME


class TestKalshiMarketCatalogBuildMetadata:
    """Tests for build_metadata method."""

    def test_build_metadata_success(self) -> None:
        """Test successful metadata building from markets."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        test_markets = [
            {"ticker": TEST_TICKER_BTC, "currency": TEST_CURRENCY, "close_time": TEST_CLOSE_TIME},
            {"ticker": TEST_TICKER_ETH, "currency": TEST_CURRENCY, "close_time": TEST_CLOSE_TIME},
        ]

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)
            metadata = catalog.build_metadata(test_markets)

            assert len(metadata) == 2
            assert TEST_TICKER_BTC in metadata
            assert TEST_TICKER_ETH in metadata

    def test_build_metadata_raises_error_on_empty_list(self) -> None:
        """Test build_metadata raises error when market list is empty."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)

            with pytest.raises(KalshiMarketCatalogError, match="Cannot build metadata from empty market list"):
                catalog.build_metadata([])


class TestKalshiMarketCatalogMetadataFromMarkets:
    """Tests for _metadata_from_markets method."""

    def test_metadata_from_markets_with_ticker(self) -> None:
        """Test metadata creation from markets with ticker."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        test_markets = [{"ticker": TEST_TICKER_BTC, "currency": TEST_CURRENCY, "close_time": TEST_CLOSE_TIME}]

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)
            metadata = catalog._metadata_from_markets(test_markets)

            assert TEST_TICKER_BTC in metadata
            assert metadata[TEST_TICKER_BTC].channel == f"market.{TEST_TICKER_BTC}"

    def test_metadata_from_markets_missing_ticker(self) -> None:
        """Test metadata creation raises error when ticker is missing."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        test_markets = [{"currency": TEST_CURRENCY}]

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)

            with pytest.raises(KalshiMarketCatalogError, match="Kalshi market missing ticker"):
                catalog._metadata_from_markets(test_markets)

    def test_metadata_from_markets_non_string_ticker(self) -> None:
        """Test metadata creation raises error when ticker is not a string."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        test_markets = [{"ticker": 12345, "currency": TEST_CURRENCY}]

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)

            with pytest.raises(KalshiMarketCatalogError, match="Kalshi market missing ticker"):
                catalog._metadata_from_markets(test_markets)

    def test_metadata_from_markets_with_none_currency(self) -> None:
        """Test metadata creation with None currency uses 'unknown'."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        test_markets = [{"ticker": TEST_TICKER_BTC, "currency": None, "close_time": TEST_CLOSE_TIME}]

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)
            metadata = catalog._metadata_from_markets(test_markets)

            assert metadata[TEST_TICKER_BTC].currency == "unknown"

    def test_metadata_from_markets_without_currency_field(self) -> None:
        """Test metadata creation without currency field uses 'unknown'."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        test_markets = [{"ticker": TEST_TICKER_BTC, "close_time": TEST_CLOSE_TIME}]

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)
            metadata = catalog._metadata_from_markets(test_markets)

            assert metadata[TEST_TICKER_BTC].currency == "unknown"

    def test_metadata_from_markets_with_none_close_time(self) -> None:
        """Test metadata creation with None close_time uses empty string."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        test_markets = [{"ticker": TEST_TICKER_BTC, "currency": TEST_CURRENCY, "close_time": None}]

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)
            metadata = catalog._metadata_from_markets(test_markets)

            assert metadata[TEST_TICKER_BTC].expiry == ""

    def test_metadata_from_markets_without_close_time_field(self) -> None:
        """Test metadata creation without close_time field uses empty string."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        test_markets = [{"ticker": TEST_TICKER_BTC, "currency": TEST_CURRENCY}]

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)
            metadata = catalog._metadata_from_markets(test_markets)

            assert metadata[TEST_TICKER_BTC].expiry == ""

    def test_metadata_from_markets_converts_currency_to_string(self) -> None:
        """Test metadata creation converts currency to string."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        test_markets = [{"ticker": TEST_TICKER_BTC, "currency": 100, "close_time": TEST_CLOSE_TIME}]

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)
            metadata = catalog._metadata_from_markets(test_markets)

            assert metadata[TEST_TICKER_BTC].currency == "100"

    def test_metadata_from_markets_converts_close_time_to_string(self) -> None:
        """Test metadata creation converts close_time to string."""
        mock_client = Mock()
        mock_settings = SimpleNamespace(
            market_catalog=SimpleNamespace(refresh_interval_seconds=TEST_REFRESH_INTERVAL, categories=None, status=TEST_MARKET_STATUS)
        )
        mock_get_settings = Mock(return_value=mock_settings)

        test_markets = [{"ticker": TEST_TICKER_BTC, "currency": TEST_CURRENCY, "close_time": 1234567890}]

        with (
            patch("common.kalshi_market_catalog._load_kalshi_settings_func", return_value=mock_get_settings),
            patch("common.kalshi_market_catalog.WeatherStationLoader") as mock_loader_cls,
        ):
            mock_loader = Mock()
            mock_loader.load_station_tokens.return_value = set()
            mock_loader_cls.return_value = mock_loader

            catalog = KalshiMarketCatalog(mock_client)
            metadata = catalog._metadata_from_markets(test_markets)

            assert metadata[TEST_TICKER_BTC].expiry == "1234567890"


class TestKalshiMarketCatalogError:
    """Tests for KalshiMarketCatalogError exception."""

    def test_exception_can_be_raised(self) -> None:
        """Test KalshiMarketCatalogError can be raised and caught."""
        with pytest.raises(KalshiMarketCatalogError):
            raise KalshiMarketCatalogError("Test error message")

    def test_exception_is_runtime_error(self) -> None:
        """Test KalshiMarketCatalogError is a RuntimeError."""
        assert issubclass(KalshiMarketCatalogError, RuntimeError)
