"""Tests for chart_generator.runtime_helpers module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator.exceptions import (
    InsufficientDataError,
    ProgressNotificationError,
)
from common.chart_generator.runtime_helpers import (
    _coerce_into_float,
    cleanup_chart_files,
    cleanup_single_chart_file,
    configure_price_chart_axis,
    configure_time_axis,
    configure_time_axis_with_5_minute_alignment,
    create_load_chart,
    create_price_chart_impl,
    create_system_chart,
    generate_load_charts,
    generate_price_chart_with_path,
    get_chart_file_manager,
    get_city_tokens_for_icao,
    get_kalshi_strikes_for_station,
    notify_progress,
    safe_float_value,
)


class TestCoerceIntoFloat:
    """Tests for _coerce_into_float function."""

    def test_valid_float_string(self) -> None:
        """Test coercing valid float string."""
        result = _coerce_into_float("123.45")
        assert result == 123.45

    def test_valid_integer_string(self) -> None:
        """Test coercing valid integer string."""
        result = _coerce_into_float("100")
        assert result == 100.0

    def test_integer_value(self) -> None:
        """Test coercing integer value."""
        result = _coerce_into_float(42)
        assert result == 42.0

    def test_float_value(self) -> None:
        """Test coercing float value."""
        result = _coerce_into_float(3.14)
        assert result == 3.14

    def test_invalid_string(self) -> None:
        """Test coercing invalid string returns None."""
        result = _coerce_into_float("invalid")
        assert result is None

    def test_none_value(self) -> None:
        """Test coercing None returns None."""
        result = _coerce_into_float(None)
        assert result is None


class TestSafeFloatValue:
    """Tests for safe_float_value function."""

    def test_float_input(self) -> None:
        """Test float input returns float."""
        result = safe_float_value(3.14)
        assert result == 3.14

    def test_integer_input(self) -> None:
        """Test integer input returns float."""
        result = safe_float_value(42)
        assert result == 42.0

    def test_valid_string_input(self) -> None:
        """Test valid string input returns float."""
        with patch("common.chart_generator.runtime_helpers.safe_float", return_value=123.45):
            result = safe_float_value("123.45")
        assert result == 123.45

    def test_none_input(self) -> None:
        """Test None input delegates to safe_float."""
        with patch("common.chart_generator.runtime_helpers.safe_float", return_value=None):
            result = safe_float_value(None)
        assert result is None


class TestNotifyProgress:
    """Tests for notify_progress function."""

    def test_with_callback(self) -> None:
        """Test notify_progress with callback."""
        mock_generator = MagicMock()
        callback = MagicMock()
        mock_generator.progress_callback = callback
        mock_generator.progress_notifier = None

        notify_progress(mock_generator, "Test message")

        callback.assert_called_once_with("Test message")

    def test_with_notifier(self) -> None:
        """Test notify_progress with notifier."""
        mock_generator = MagicMock()
        mock_generator.progress_callback = None
        mock_notifier = MagicMock()
        mock_generator.progress_notifier = mock_notifier

        notify_progress(mock_generator, "Test message")

        mock_notifier.notify_progress.assert_called_once_with("Test message")

    def test_no_callback_or_notifier(self) -> None:
        """Test notify_progress with neither callback nor notifier."""
        mock_generator = MagicMock()
        mock_generator.progress_callback = None
        mock_generator.progress_notifier = None

        notify_progress(mock_generator, "Test message")


class TestGetChartFileManager:
    """Tests for get_chart_file_manager function."""

    def test_creates_new_manager(self) -> None:
        """Test creates new manager if none exists."""
        from common.chart_generator_helpers.chart_file_manager import ChartFileManager

        mock_generator = MagicMock(spec=["_chart_file_manager", "chart_file_manager"])
        mock_generator._chart_file_manager = None

        result = get_chart_file_manager(mock_generator)

        assert isinstance(result, ChartFileManager)

    def test_returns_existing_manager(self) -> None:
        """Test returns existing manager."""
        from common.chart_generator_helpers.chart_file_manager import ChartFileManager

        mock_generator = MagicMock(spec=["_chart_file_manager", "chart_file_manager"])
        mock_manager = MagicMock(spec=ChartFileManager)

        with patch("common.chart_generator.runtime_helpers.ChartFileManager", type(mock_manager)):
            mock_generator._chart_file_manager = mock_manager
            result = get_chart_file_manager(mock_generator)

        assert result == mock_manager


class TestCleanupChartFiles:
    """Tests for cleanup_chart_files function."""

    def test_cleanup_chart_files(self) -> None:
        """Test cleanup_chart_files delegates to manager."""
        mock_generator = MagicMock()
        mock_manager = MagicMock()

        with patch(
            "common.chart_generator.runtime_helpers.get_chart_file_manager",
            return_value=mock_manager,
        ):
            cleanup_chart_files(mock_generator, ["/tmp/chart1.png", "/tmp/chart2.png"])

        mock_manager.cleanup_chart_files.assert_called_once_with(["/tmp/chart1.png", "/tmp/chart2.png"])


class TestCleanupSingleChartFile:
    """Tests for cleanup_single_chart_file function."""

    def test_cleanup_single_chart_file(self) -> None:
        """Test cleanup_single_chart_file delegates to manager."""
        mock_generator = MagicMock()
        mock_manager = MagicMock()

        with patch(
            "common.chart_generator.runtime_helpers.get_chart_file_manager",
            return_value=mock_manager,
        ):
            cleanup_single_chart_file(mock_generator, "/tmp/chart.png")

        mock_manager.cleanup_single_chart_file.assert_called_once_with("/tmp/chart.png")


class TestConfigureTimeAxis:
    """Tests for configure_time_axis function."""

    def test_price_chart_type(self) -> None:
        """Test configure_time_axis for price chart type."""
        mock_generator = MagicMock()
        mock_ax = MagicMock()
        timestamps = [datetime.now(timezone.utc)]

        configure_time_axis(mock_generator, mock_ax, timestamps, chart_type="price")

        mock_generator.time_configurator.configure_price_chart_axis.assert_called_once()

    def test_default_chart_type(self) -> None:
        """Test configure_time_axis for default chart type."""
        mock_generator = MagicMock()
        mock_ax = MagicMock()
        timestamps = [datetime.now(timezone.utc)]

        configure_time_axis(mock_generator, mock_ax, timestamps, chart_type="default")

        mock_generator.time_configurator.configure_time_axis_with_5_minute_alignment.assert_called_once()


class TestConfigureTimeAxisWith5MinuteAlignment:
    """Tests for configure_time_axis_with_5_minute_alignment function."""

    def test_delegates_to_configurator(self) -> None:
        """Test delegates to time_configurator."""
        mock_generator = MagicMock()
        mock_ax = MagicMock()
        timestamps = [datetime.now(timezone.utc)]
        coordinates = (40.7128, -74.0060)

        configure_time_axis_with_5_minute_alignment(mock_generator, mock_ax, timestamps, "weather", coordinates)

        mock_generator.time_configurator.configure_time_axis_with_5_minute_alignment.assert_called_once()


class TestConfigurePriceChartAxis:
    """Tests for configure_price_chart_axis function."""

    def test_delegates_to_configurator(self) -> None:
        """Test delegates to time_configurator."""
        mock_generator = MagicMock()
        mock_ax = MagicMock()
        timestamps = [datetime.now(timezone.utc)]

        configure_price_chart_axis(mock_generator, mock_ax, timestamps)

        mock_generator.time_configurator.configure_price_chart_axis.assert_called_once()


class TestCreateLoadChart:
    """Tests for create_load_chart function."""

    @pytest.mark.asyncio
    async def test_no_history_data(self) -> None:
        """Test raises error when no history data."""
        mock_generator = MagicMock()
        mock_metadata_store = MagicMock()
        mock_metadata_store.initialize = AsyncMock()
        mock_metadata_store.cleanup = AsyncMock()
        mock_metadata_store.get_service_history = AsyncMock(return_value=[])

        with patch(
            "common.metadata_store.MetadataStore",
            return_value=mock_metadata_store,
        ):
            with pytest.raises(InsufficientDataError, match="No history data"):
                await create_load_chart(mock_generator, "deribit", 24)

    @pytest.mark.asyncio
    async def test_insufficient_data_points(self) -> None:
        """Test raises error when insufficient data points."""
        mock_generator = MagicMock()
        mock_metadata_store = MagicMock()
        mock_metadata_store.initialize = AsyncMock()
        mock_metadata_store.cleanup = AsyncMock()
        mock_metadata_store.get_service_history = AsyncMock(return_value=[{"messages_per_minute": 100, "timestamp": datetime.now()}])

        with patch(
            "common.metadata_store.MetadataStore",
            return_value=mock_metadata_store,
        ):
            with pytest.raises(InsufficientDataError, match="Insufficient data points"):
                await create_load_chart(mock_generator, "deribit", 24)

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        """Test successful chart creation."""
        mock_generator = MagicMock()
        mock_generator.generate_unified_chart = AsyncMock(return_value="/tmp/chart.png")
        mock_generator.primary_color = "#627EEA"
        now = datetime.now(timezone.utc)
        mock_metadata_store = MagicMock()
        mock_metadata_store.initialize = AsyncMock()
        mock_metadata_store.cleanup = AsyncMock()
        mock_metadata_store.get_service_history = AsyncMock(
            return_value=[
                {"messages_per_minute": 100, "timestamp": now},
                {"messages_per_minute": 200, "timestamp": now},
            ]
        )

        with patch(
            "common.metadata_store.MetadataStore",
            return_value=mock_metadata_store,
        ):
            result = await create_load_chart(mock_generator, "deribit", 24)

        assert result == "/tmp/chart.png"


class TestCreateSystemChart:
    """Tests for create_system_chart function."""

    @pytest.mark.asyncio
    async def test_no_data(self) -> None:
        """Test raises error when no data."""
        mock_generator = MagicMock()
        mock_redis = MagicMock()
        mock_redis.hgetall = MagicMock(return_value={})
        mock_redis.aclose = AsyncMock()

        with (
            patch(
                "common.redis_utils.get_redis_connection",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch(
                "common.chart_generator.runtime_helpers.ensure_awaitable",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            with pytest.raises(InsufficientDataError, match="No history data"):
                await create_system_chart(mock_generator, "cpu", 24)

    @pytest.mark.asyncio
    async def test_insufficient_data_points(self) -> None:
        """Test raises error with insufficient data points."""
        mock_generator = MagicMock()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with (
            patch(
                "common.redis_utils.get_redis_connection",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch(
                "common.chart_generator.runtime_helpers.ensure_awaitable",
                new_callable=AsyncMock,
                return_value=[("1735689600|50.0", 1735689600.0)],
            ),
        ):
            with pytest.raises(InsufficientDataError, match="Insufficient data points"):
                await create_system_chart(mock_generator, "cpu", 24)


class TestGetCityTokensForIcao:
    """Tests for get_city_tokens_for_icao function."""

    @pytest.mark.asyncio
    async def test_delegates_to_resolver(self) -> None:
        """Test delegates to CityTokenResolver."""
        mock_generator = MagicMock()
        mock_resolver = MagicMock()
        mock_resolver.get_city_tokens_for_icao = AsyncMock(return_value=(["NYC"], "NYC"))

        with patch(
            "common.chart_generator_helpers.city_token_resolver.CityTokenResolver",
            return_value=mock_resolver,
        ):
            result = await get_city_tokens_for_icao(mock_generator, "KJFK")

        assert result == (["NYC"], "NYC")


class TestGetKalshiStrikesForStation:
    """Tests for get_kalshi_strikes_for_station function."""

    @pytest.mark.asyncio
    async def test_no_tokens_available(self) -> None:
        """Test raises error when no tokens available."""
        mock_generator = MagicMock()
        mock_generator.get_city_tokens_for_icao = AsyncMock(return_value=([], None))
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with patch(
            "common.redis_utils.get_redis_connection",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            with pytest.raises(RuntimeError, match="No Kalshi tokens"):
                await get_kalshi_strikes_for_station(mock_generator, "KJFK")

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        """Test successful strike retrieval."""
        mock_generator = MagicMock()
        mock_generator.get_city_tokens_for_icao = AsyncMock(return_value=(["NYC"], "NYC"))
        mock_generator.strike_collector.get_kalshi_strikes_for_station = AsyncMock(return_value=[30.0, 40.0, 50.0])
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with patch(
            "common.redis_utils.get_redis_connection",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            result = await get_kalshi_strikes_for_station(mock_generator, "KJFK")

        assert result == [30.0, 40.0, 50.0]


class TestGeneratePriceChartWithPath:
    """Tests for generate_price_chart_with_path function."""

    @pytest.mark.asyncio
    async def test_with_creator(self) -> None:
        """Test with price chart creator."""
        mock_generator = MagicMock()
        mock_creator = MagicMock()
        mock_creator.create_price_chart = AsyncMock(return_value="/tmp/price.png")
        mock_generator.price_chart_creator = mock_creator

        result = await generate_price_chart_with_path(mock_generator, "BTC", 7)

        assert result == "/tmp/price.png"

    @pytest.mark.asyncio
    async def test_without_creator(self) -> None:
        """Test without price chart creator."""
        mock_generator = MagicMock()
        mock_generator.price_chart_creator = None
        mock_generator.create_price_chart = AsyncMock(return_value="/tmp/price.png")

        result = await generate_price_chart_with_path(mock_generator, "BTC", 7)

        assert result == "/tmp/price.png"


class TestCreatePriceChartImpl:
    """Tests for create_price_chart_impl function."""

    @pytest.mark.asyncio
    async def test_creates_creator_if_none(self) -> None:
        """Test creates price chart creator if none exists."""
        mock_generator = MagicMock()
        mock_generator.price_chart_creator = None
        mock_generator.progress_notifier = None
        mock_generator.progress_callback = None
        mock_generator.primary_color = "#627EEA"
        mock_generator.price_path_calculator = MagicMock()
        mock_generator.price_path_horizon_days = 7

        mock_creator = MagicMock()
        mock_creator.create_price_chart = AsyncMock(return_value="/tmp/price.png")

        with (
            patch(
                "common.chart_generator.runtime_helpers.PriceChartCreator",
                return_value=mock_creator,
            ),
            patch("common.chart_generator.runtime_helpers.ProgressNotifier"),
        ):
            result = await create_price_chart_impl(mock_generator, "BTC", 7)

        assert result == "/tmp/price.png"


class TestGenerateLoadCharts:
    """Tests for generate_load_charts function."""

    @pytest.mark.asyncio
    async def test_with_load_charts_generator(self) -> None:
        """Test with load charts generator."""
        mock_generator = MagicMock()
        mock_load_gen = MagicMock()
        mock_load_gen.generate_load_charts = AsyncMock(return_value={"deribit": "/tmp/deribit.png"})
        mock_generator.load_charts_generator = mock_load_gen

        result = await generate_load_charts(mock_generator, 24)

        assert result == {"deribit": "/tmp/deribit.png"}

    @pytest.mark.asyncio
    async def test_without_load_charts_generator(self) -> None:
        """Test without load charts generator."""
        mock_generator = MagicMock()
        mock_generator.load_charts_generator = None
        mock_generator.create_load_chart = AsyncMock(return_value="/tmp/chart.png")
        mock_generator.create_system_chart = AsyncMock(return_value="/tmp/system.png")

        result = await generate_load_charts(mock_generator, 24)

        assert "deribit" in result
        assert "kalshi" in result
        assert "cpu" in result
        assert "memory" in result
