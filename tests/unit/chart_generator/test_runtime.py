"""Tests for chart_generator.runtime module."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from common.chart_generator.runtime import (
    ChartCreationMixin,
    ChartGenerator,
    ChartHelperMixin,
    ChartPropertyMixin,
)

TEST_SERVICE_NAME = "test_service"
TEST_METRIC_NAME = "test_metric"
TEST_HOURS = 24
TEST_SYMBOL = "BTC"
TEST_HORIZON_DAYS = 7
TEST_STATION_ICAO = "KJFK"
TEST_CHART_PATH = "/tmp/test_chart.png"
TEST_CHART_PATHS = ["/tmp/chart1.png", "/tmp/chart2.png"]
TEST_PROGRESS_MESSAGE = "Test progress message"
TEST_MARKET_KEY = "test_market"
TEST_TODAY_MARKET_DATE = "2025-01-15"


class TestChartPropertyMixin:
    """Tests for ChartPropertyMixin class."""

    def test_progress_callback_property(self) -> None:
        """Test progress_callback property getter."""
        mixin = ChartPropertyMixin()
        test_callback = MagicMock()
        mixin._progress_callback = test_callback

        assert mixin.progress_callback == test_callback

    def test_progress_notifier_property_getter(self) -> None:
        """Test progress_notifier property getter."""
        mixin = ChartPropertyMixin()
        test_notifier = MagicMock()
        mixin._progress_notifier = test_notifier

        assert mixin.progress_notifier == test_notifier

    def test_progress_notifier_property_setter(self) -> None:
        """Test progress_notifier property setter."""
        mixin = ChartPropertyMixin()
        test_notifier = MagicMock()

        mixin.progress_notifier = test_notifier

        assert mixin._progress_notifier == test_notifier

    def test_price_chart_creator_property_getter(self) -> None:
        """Test price_chart_creator property getter."""
        mixin = ChartPropertyMixin()
        test_creator = MagicMock()
        mixin._price_chart_creator = test_creator

        assert mixin.price_chart_creator == test_creator

    def test_price_chart_creator_property_setter(self) -> None:
        """Test price_chart_creator property setter."""
        mixin = ChartPropertyMixin()
        test_creator = MagicMock()

        mixin.price_chart_creator = test_creator

        assert mixin._price_chart_creator == test_creator

    def test_time_configurator_property(self) -> None:
        """Test time_configurator property getter."""
        mixin = ChartPropertyMixin()
        test_configurator = MagicMock()
        mixin._time_configurator = test_configurator

        assert mixin.time_configurator == test_configurator

    def test_chart_file_manager_property_returns_chart_file_manager(self) -> None:
        """Test chart_file_manager property returns _chart_file_manager if exists."""
        mixin = ChartPropertyMixin()
        test_manager = MagicMock()
        mixin._chart_file_manager = test_manager

        assert mixin.chart_file_manager == test_manager

    def test_chart_file_manager_property_returns_file_manager(self) -> None:
        """Test chart_file_manager property returns _file_manager if no _chart_file_manager."""
        mixin = ChartPropertyMixin()
        test_manager = MagicMock()
        mixin._file_manager = test_manager

        assert mixin.chart_file_manager == test_manager

    def test_chart_file_manager_property_setter(self) -> None:
        """Test chart_file_manager property setter sets both attributes."""
        mixin = ChartPropertyMixin()
        test_manager = MagicMock()

        mixin.chart_file_manager = test_manager

        assert mixin._chart_file_manager == test_manager
        assert mixin._file_manager == test_manager

    def test_load_charts_generator_property(self) -> None:
        """Test load_charts_generator property getter."""
        mixin = ChartPropertyMixin()
        test_generator = MagicMock()
        mixin._load_charts_generator = test_generator

        assert mixin.load_charts_generator == test_generator

    def test_strike_collector_property(self) -> None:
        """Test strike_collector property getter."""
        mixin = ChartPropertyMixin()
        test_collector = MagicMock()
        mixin._strike_collector = test_collector

        assert mixin.strike_collector == test_collector


class TestChartCreationMixin:
    """Tests for ChartCreationMixin class."""

    @pytest.mark.asyncio
    async def test_create_load_chart(self) -> None:
        """Test create_load_chart delegates to internal method."""
        mixin = ChartCreationMixin()
        mixin._create_load_chart = AsyncMock(return_value=TEST_CHART_PATH)

        result = await mixin.create_load_chart(TEST_SERVICE_NAME, TEST_HOURS)

        assert result == TEST_CHART_PATH
        mixin._create_load_chart.assert_called_once_with(TEST_SERVICE_NAME, TEST_HOURS)

    @pytest.mark.asyncio
    async def test_create_system_chart(self) -> None:
        """Test create_system_chart delegates to internal method."""
        mixin = ChartCreationMixin()
        mixin._create_system_chart = AsyncMock(return_value=TEST_CHART_PATH)

        result = await mixin.create_system_chart(TEST_METRIC_NAME, TEST_HOURS)

        assert result == TEST_CHART_PATH
        mixin._create_system_chart.assert_called_once_with(TEST_METRIC_NAME, TEST_HOURS)

    @pytest.mark.asyncio
    async def test_create_price_chart(self) -> None:
        """Test create_price_chart delegates to internal method."""
        mixin = ChartCreationMixin()
        mixin._create_price_chart = AsyncMock(return_value=TEST_CHART_PATH)

        result = await mixin.create_price_chart(TEST_SYMBOL, TEST_HORIZON_DAYS)

        assert result == TEST_CHART_PATH
        mixin._create_price_chart.assert_called_once_with(TEST_SYMBOL, TEST_HORIZON_DAYS)

    @pytest.mark.asyncio
    async def test_create_price_chart_without_horizon(self) -> None:
        """Test create_price_chart without prediction horizon."""
        mixin = ChartCreationMixin()
        mixin._create_price_chart = AsyncMock(return_value=TEST_CHART_PATH)

        result = await mixin.create_price_chart(TEST_SYMBOL)

        assert result == TEST_CHART_PATH
        mixin._create_price_chart.assert_called_once_with(TEST_SYMBOL, None)

    @pytest.mark.asyncio
    async def test_get_city_tokens_for_icao(self) -> None:
        """Test get_city_tokens_for_icao delegates to internal method."""
        mixin = ChartCreationMixin()
        test_tokens = (["NYC"], "NYC")
        mixin._get_city_tokens_for_icao = AsyncMock(return_value=test_tokens)

        result = await mixin.get_city_tokens_for_icao(TEST_STATION_ICAO)

        assert result == test_tokens
        mixin._get_city_tokens_for_icao.assert_called_once_with(TEST_STATION_ICAO)


class TestChartHelperMixin:
    """Tests for ChartHelperMixin class."""

    def test_market_expires_today_validator_not_configured(self) -> None:
        """Test _market_expires_today raises when validator not configured."""
        mixin = ChartHelperMixin()
        mixin._strike_collector = MagicMock()
        mixin._strike_collector.expiration_validator = None

        with pytest.raises(RuntimeError, match="Strike collector has no expiration validator configured"):
            mixin._market_expires_today({}, None, None, TEST_MARKET_KEY, TEST_TODAY_MARKET_DATE)

    def test_market_expires_today_missing_method(self) -> None:
        """Test _market_expires_today raises when method missing."""
        mixin = ChartHelperMixin()
        validator = MagicMock()
        mixin._strike_collector = MagicMock()
        mixin._strike_collector.expiration_validator = validator

        with patch.object(type(validator), "market_expires_today", None, create=True):
            with pytest.raises(RuntimeError, match="Expiration validator is missing market_expires_today"):
                mixin._market_expires_today({}, None, None, TEST_MARKET_KEY, TEST_TODAY_MARKET_DATE)

    def test_market_expires_today_success(self) -> None:
        """Test _market_expires_today successful execution."""
        mixin = ChartHelperMixin()
        validator = MagicMock()
        validator_class = type(validator)
        validator_class.market_expires_today = MagicMock(return_value=True)
        mixin._strike_collector = MagicMock()
        mixin._strike_collector.expiration_validator = validator

        result = mixin._market_expires_today({}, None, None, TEST_MARKET_KEY, TEST_TODAY_MARKET_DATE)

        assert result is True

    def test_market_expires_today_no_metadata_error(self) -> None:
        """Test _market_expires_today wraps no metadata error."""
        mixin = ChartHelperMixin()
        validator = MagicMock()
        validator_class = type(validator)

        def raise_no_metadata(*args, **kwargs):
            raise RuntimeError("No expiration metadata available")

        validator_class.market_expires_today = raise_no_metadata
        mixin._strike_collector = MagicMock()
        mixin._strike_collector.expiration_validator = validator

        with pytest.raises(RuntimeError, match="Unable to determine expiration date"):
            mixin._market_expires_today({}, None, None, TEST_MARKET_KEY, TEST_TODAY_MARKET_DATE)

    def test_market_expires_today_other_runtime_error(self) -> None:
        """Test _market_expires_today propagates other runtime errors."""
        mixin = ChartHelperMixin()
        validator = MagicMock()
        validator_class = type(validator)

        def raise_other_error(*args, **kwargs):
            raise RuntimeError("Some other error")

        validator_class.market_expires_today = raise_other_error
        mixin._strike_collector = MagicMock()
        mixin._strike_collector.expiration_validator = validator

        with pytest.raises(RuntimeError, match="Some other error"):
            mixin._market_expires_today({}, None, None, TEST_MARKET_KEY, TEST_TODAY_MARKET_DATE)

    @pytest.mark.asyncio
    async def test_generate_load_charts(self) -> None:
        """Test generate_load_charts delegates to implementation."""
        mixin = ChartHelperMixin()
        test_charts = {"service": TEST_CHART_PATH}

        with patch("common.chart_generator.runtime._generate_load_charts_impl", new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = test_charts

            result = await mixin.generate_load_charts(TEST_HOURS)

            assert result == test_charts
            mock_impl.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_price_chart_with_path(self) -> None:
        """Test generate_price_chart_with_path delegates to implementation."""
        mixin = ChartHelperMixin()

        with patch("common.chart_generator.runtime._generate_price_chart_with_path_impl", new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = TEST_CHART_PATH

            result = await mixin.generate_price_chart_with_path(TEST_SYMBOL, TEST_HORIZON_DAYS)

            assert result == TEST_CHART_PATH
            mock_impl.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_price_chart(self) -> None:
        """Test _create_price_chart delegates to implementation."""
        mixin = ChartHelperMixin()

        with patch("common.chart_generator.runtime._create_price_chart_impl", new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = TEST_CHART_PATH

            result = await mixin._create_price_chart(TEST_SYMBOL, TEST_HORIZON_DAYS)

            assert result == TEST_CHART_PATH
            mock_impl.assert_called_once()

    def test_configure_time_axis(self) -> None:
        """Test _configure_time_axis delegates to implementation."""
        mixin = ChartHelperMixin()
        mock_ax = MagicMock()
        test_timestamps = [MagicMock()]

        with patch("common.chart_generator.runtime._configure_time_axis_impl") as mock_impl:
            mixin._configure_time_axis(mock_ax, test_timestamps, "price", None)

            mock_impl.assert_called_once_with(mixin, mock_ax, test_timestamps, "price", None)

    def test_configure_time_axis_with_5_minute_alignment(self) -> None:
        """Test _configure_time_axis_with_5_minute_alignment delegates to implementation."""
        mixin = ChartHelperMixin()
        mock_ax = MagicMock()
        test_timestamps = [MagicMock()]

        with patch("common.chart_generator.runtime._configure_time_axis_with_5_minute_alignment_impl") as mock_impl:
            mixin._configure_time_axis_with_5_minute_alignment(mock_ax, test_timestamps, "weather", None)

            mock_impl.assert_called_once_with(mixin, mock_ax, test_timestamps, "weather", None)

    def test_configure_price_chart_axis(self) -> None:
        """Test _configure_price_chart_axis delegates to implementation."""
        mixin = ChartHelperMixin()
        mock_ax = MagicMock()
        test_timestamps = [MagicMock()]

        with patch("common.chart_generator.runtime._configure_price_chart_axis_impl") as mock_impl:
            mixin._configure_price_chart_axis(mock_ax, test_timestamps)

            mock_impl.assert_called_once_with(mixin, mock_ax, test_timestamps)

    def test_cleanup_chart_files(self) -> None:
        """Test cleanup_chart_files delegates to implementation."""
        mixin = ChartHelperMixin()

        with patch("common.chart_generator.runtime._cleanup_chart_files_impl") as mock_impl:
            mixin.cleanup_chart_files(TEST_CHART_PATHS)

            mock_impl.assert_called_once_with(mixin, TEST_CHART_PATHS)

    def test_cleanup_single_chart_file(self) -> None:
        """Test cleanup_single_chart_file delegates to implementation."""
        mixin = ChartHelperMixin()

        with patch("common.chart_generator.runtime._cleanup_single_chart_file_impl") as mock_impl:
            mixin.cleanup_single_chart_file(TEST_CHART_PATH)

            mock_impl.assert_called_once_with(mixin, TEST_CHART_PATH)

    @pytest.mark.asyncio
    async def test_create_load_chart(self) -> None:
        """Test _create_load_chart delegates to implementation."""
        mixin = ChartHelperMixin()

        with patch("common.chart_generator.runtime._create_load_chart_impl", new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = TEST_CHART_PATH

            result = await mixin._create_load_chart(TEST_SERVICE_NAME, TEST_HOURS)

            assert result == TEST_CHART_PATH
            mock_impl.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_system_chart(self) -> None:
        """Test _create_system_chart delegates to implementation."""
        mixin = ChartHelperMixin()

        with patch("common.chart_generator.runtime._create_system_chart_impl", new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = TEST_CHART_PATH

            result = await mixin._create_system_chart(TEST_METRIC_NAME, TEST_HOURS)

            assert result == TEST_CHART_PATH
            mock_impl.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_city_tokens_for_icao(self) -> None:
        """Test _get_city_tokens_for_icao delegates to implementation."""
        mixin = ChartHelperMixin()
        test_tokens = (["NYC"], "NYC")

        with patch("common.chart_generator.runtime._get_city_tokens_for_icao_impl", new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = test_tokens

            result = await mixin._get_city_tokens_for_icao(TEST_STATION_ICAO)

            assert result == test_tokens
            mock_impl.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_kalshi_strikes_for_station(self) -> None:
        """Test _get_kalshi_strikes_for_station delegates to implementation."""
        mixin = ChartHelperMixin()
        test_strikes = [30.0, 40.0, 50.0]

        with patch("common.chart_generator.runtime._get_kalshi_strikes_for_station_impl", new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = test_strikes

            result = await mixin._get_kalshi_strikes_for_station(TEST_STATION_ICAO)

            assert result == test_strikes
            mock_impl.assert_called_once()

    def test_notify_progress(self) -> None:
        """Test _notify_progress delegates to implementation."""
        mixin = ChartHelperMixin()

        with patch("common.chart_generator.runtime._notify_progress_impl") as mock_impl:
            mixin._notify_progress(TEST_PROGRESS_MESSAGE)

            mock_impl.assert_called_once_with(mixin, TEST_PROGRESS_MESSAGE)

    def test_safe_float_success(self) -> None:
        """Test _safe_float returns float value on success."""
        with patch("common.chart_generator.runtime._safe_float_value_impl", return_value=42.5):
            result = ChartHelperMixin._safe_float("42.5")

            assert result == 42.5

    def test_safe_float_value_error(self) -> None:
        """Test _safe_float returns None on ValueError."""
        with patch("common.chart_generator.runtime._safe_float_value_impl", side_effect=ValueError("Invalid")):
            result = ChartHelperMixin._safe_float("invalid")

            assert result is None


class TestChartGenerator:
    """Tests for ChartGenerator class."""

    @pytest.mark.asyncio
    async def test_init_sets_progress_callback(self) -> None:
        """Test __init__ sets progress callback."""
        test_callback = MagicMock()

        with patch("common.chart_generator.runtime.plt"):
            with patch("common.chart_generator.runtime.ChartGeneratorInitializer.initialize_components") as mock_init:
                mock_init.return_value = {
                    "styler": MagicMock(
                        chart_width_inches=10,
                        chart_height_inches=6,
                        dpi=100,
                        background_color="#fff",
                        grid_color="#ccc",
                        primary_color="#blue",
                        secondary_color="#green",
                        highlight_color="#yellow",
                        deribit_color="#purple",
                        kalshi_color="#orange",
                        cpu_color="#red",
                        memory_color="#pink",
                    ),
                    "schema": MagicMock(),
                    "weather_history_tracker": MagicMock(),
                    "price_path_calculator": MagicMock(),
                    "price_path_horizon_days": 30,
                    "file_manager": MagicMock(),
                    "progress_notifier": MagicMock(),
                    "time_configurator": MagicMock(),
                    "token_resolver": MagicMock(),
                    "strike_collector": MagicMock(),
                    "load_chart_creator": MagicMock(),
                    "system_chart_creator": MagicMock(),
                    "price_chart_creator": MagicMock(),
                }

                generator = ChartGenerator(progress_callback=test_callback)

                assert generator._progress_callback == test_callback

    @pytest.mark.asyncio
    async def test_init_sets_styler_attributes(self) -> None:
        """Test __init__ sets all styler attributes."""
        mock_styler = MagicMock()
        mock_styler.chart_width_inches = 12
        mock_styler.chart_height_inches = 8
        mock_styler.dpi = 150
        mock_styler.background_color = "#000"
        mock_styler.grid_color = "#333"
        mock_styler.primary_color = "#blue"
        mock_styler.secondary_color = "#green"
        mock_styler.highlight_color = "#yellow"
        mock_styler.deribit_color = "#purple"
        mock_styler.kalshi_color = "#orange"
        mock_styler.cpu_color = "#red"
        mock_styler.memory_color = "#pink"

        with patch("common.chart_generator.runtime.plt"):
            with patch("common.chart_generator.runtime.ChartGeneratorInitializer.initialize_components") as mock_init:
                mock_init.return_value = {
                    "styler": mock_styler,
                    "schema": MagicMock(),
                    "weather_history_tracker": MagicMock(),
                    "price_path_calculator": MagicMock(),
                    "price_path_horizon_days": 30,
                    "file_manager": MagicMock(),
                    "progress_notifier": MagicMock(),
                    "time_configurator": MagicMock(),
                    "token_resolver": MagicMock(),
                    "strike_collector": MagicMock(),
                    "load_chart_creator": MagicMock(),
                    "system_chart_creator": MagicMock(),
                    "price_chart_creator": MagicMock(),
                }

                generator = ChartGenerator()

                assert generator.chart_width_inches == 12
                assert generator.chart_height_inches == 8
                assert generator.dpi == 150
                assert generator.background_color == "#000"
                assert generator.grid_color == "#333"
                assert generator.primary_color == "#blue"
                assert generator.secondary_color == "#green"
                assert generator.highlight_color == "#yellow"
                assert generator.deribit_color == "#purple"
                assert generator.kalshi_color == "#orange"
                assert generator.cpu_color == "#red"
                assert generator.memory_color == "#pink"

    @pytest.mark.asyncio
    async def test_init_sets_component_attributes(self) -> None:
        """Test __init__ sets all component attributes."""
        mock_components = {
            "styler": MagicMock(
                chart_width_inches=10,
                chart_height_inches=6,
                dpi=100,
                background_color="#fff",
                grid_color="#ccc",
                primary_color="#blue",
                secondary_color="#green",
                highlight_color="#yellow",
                deribit_color="#purple",
                kalshi_color="#orange",
                cpu_color="#red",
                memory_color="#pink",
            ),
            "schema": MagicMock(),
            "weather_history_tracker": MagicMock(),
            "price_path_calculator": MagicMock(),
            "price_path_horizon_days": 30,
            "file_manager": MagicMock(),
            "progress_notifier": MagicMock(),
            "time_configurator": MagicMock(),
            "token_resolver": MagicMock(),
            "strike_collector": MagicMock(),
            "load_chart_creator": MagicMock(),
            "system_chart_creator": MagicMock(),
            "price_chart_creator": MagicMock(),
        }

        with patch("common.chart_generator.runtime.plt"):
            with patch("common.chart_generator.runtime.ChartGeneratorInitializer.initialize_components") as mock_init:
                mock_init.return_value = mock_components

                generator = ChartGenerator()

                assert generator.schema == mock_components["schema"]
                assert generator.weather_history_tracker == mock_components["weather_history_tracker"]
                assert generator.price_path_calculator == mock_components["price_path_calculator"]
                assert generator.price_path_horizon_days == 30
                assert generator._chart_file_manager == mock_components["file_manager"]
                assert generator._file_manager == mock_components["file_manager"]
                assert generator._progress_notifier == mock_components["progress_notifier"]
                assert generator._time_configurator == mock_components["time_configurator"]
                assert generator._token_resolver == mock_components["token_resolver"]
                assert generator._strike_collector == mock_components["strike_collector"]
                assert generator._load_chart_creator == mock_components["load_chart_creator"]
                assert generator._system_chart_creator == mock_components["system_chart_creator"]
                assert generator._price_chart_creator == mock_components["price_chart_creator"]

    @pytest.mark.asyncio
    async def test_init_creates_load_charts_generator(self) -> None:
        """Test __init__ creates LoadChartsGenerator instance."""
        mock_load_chart_creator = MagicMock()
        mock_system_chart_creator = MagicMock()

        with patch("common.chart_generator.runtime.plt"):
            with patch("common.chart_generator.runtime.ChartGeneratorInitializer.initialize_components") as mock_init:
                mock_init.return_value = {
                    "styler": MagicMock(
                        chart_width_inches=10,
                        chart_height_inches=6,
                        dpi=100,
                        background_color="#fff",
                        grid_color="#ccc",
                        primary_color="#blue",
                        secondary_color="#green",
                        highlight_color="#yellow",
                        deribit_color="#purple",
                        kalshi_color="#orange",
                        cpu_color="#red",
                        memory_color="#pink",
                    ),
                    "schema": MagicMock(),
                    "weather_history_tracker": MagicMock(),
                    "price_path_calculator": MagicMock(),
                    "price_path_horizon_days": 30,
                    "file_manager": MagicMock(),
                    "progress_notifier": MagicMock(),
                    "time_configurator": MagicMock(),
                    "token_resolver": MagicMock(),
                    "strike_collector": MagicMock(),
                    "load_chart_creator": mock_load_chart_creator,
                    "system_chart_creator": mock_system_chart_creator,
                    "price_chart_creator": MagicMock(),
                }

                with patch("common.chart_generator.runtime.LoadChartsGenerator") as mock_gen_class:
                    generator = ChartGenerator()

                    mock_gen_class.assert_called_once_with(
                        load_chart_creator=mock_load_chart_creator,
                        system_chart_creator=mock_system_chart_creator,
                    )

    @pytest.mark.asyncio
    async def test_init_sets_weather_config_os_from_module(self) -> None:
        """Test __init__ sets _weather_config_os from chart_generator module."""
        import sys

        mock_os = MagicMock()
        mock_chart_module = MagicMock()
        mock_chart_module.os = mock_os

        with patch("common.chart_generator.runtime.plt"):
            with patch("common.chart_generator.runtime.ChartGeneratorInitializer.initialize_components") as mock_init:
                mock_init.return_value = {
                    "styler": MagicMock(
                        chart_width_inches=10,
                        chart_height_inches=6,
                        dpi=100,
                        background_color="#fff",
                        grid_color="#ccc",
                        primary_color="#blue",
                        secondary_color="#green",
                        highlight_color="#yellow",
                        deribit_color="#purple",
                        kalshi_color="#orange",
                        cpu_color="#red",
                        memory_color="#pink",
                    ),
                    "schema": MagicMock(),
                    "weather_history_tracker": MagicMock(),
                    "price_path_calculator": MagicMock(),
                    "price_path_horizon_days": 30,
                    "file_manager": MagicMock(),
                    "progress_notifier": MagicMock(),
                    "time_configurator": MagicMock(),
                    "token_resolver": MagicMock(),
                    "strike_collector": MagicMock(),
                    "load_chart_creator": MagicMock(),
                    "system_chart_creator": MagicMock(),
                    "price_chart_creator": MagicMock(),
                }

                with patch.dict(sys.modules, {"src.monitor.chart_generator": mock_chart_module}):
                    generator = ChartGenerator()

                    assert generator._weather_config_os == mock_os

    @pytest.mark.asyncio
    async def test_init_sets_weather_config_os_to_dependencies_os(self) -> None:
        """Test __init__ sets _weather_config_os to dependencies_os when module not found."""
        import sys

        with patch("common.chart_generator.runtime.plt"):
            with patch("common.chart_generator.runtime.ChartGeneratorInitializer.initialize_components") as mock_init:
                mock_init.return_value = {
                    "styler": MagicMock(
                        chart_width_inches=10,
                        chart_height_inches=6,
                        dpi=100,
                        background_color="#fff",
                        grid_color="#ccc",
                        primary_color="#blue",
                        secondary_color="#green",
                        highlight_color="#yellow",
                        deribit_color="#purple",
                        kalshi_color="#orange",
                        cpu_color="#red",
                        memory_color="#pink",
                    ),
                    "schema": MagicMock(),
                    "weather_history_tracker": MagicMock(),
                    "price_path_calculator": MagicMock(),
                    "price_path_horizon_days": 30,
                    "file_manager": MagicMock(),
                    "progress_notifier": MagicMock(),
                    "time_configurator": MagicMock(),
                    "token_resolver": MagicMock(),
                    "strike_collector": MagicMock(),
                    "load_chart_creator": MagicMock(),
                    "system_chart_creator": MagicMock(),
                    "price_chart_creator": MagicMock(),
                }

                with patch("common.chart_generator.runtime.dependencies_os") as mock_dep_os:
                    with patch.dict(sys.modules, {"src.monitor.chart_generator": None}):
                        generator = ChartGenerator()

                        assert generator._weather_config_os == mock_dep_os

    @pytest.mark.asyncio
    async def test_init_sets_weather_config_open_from_module(self) -> None:
        """Test __init__ sets _weather_config_open from chart_generator module."""
        import sys

        mock_open_func = MagicMock()
        mock_chart_module = MagicMock()
        mock_chart_module.open = mock_open_func

        with patch("common.chart_generator.runtime.plt"):
            with patch("common.chart_generator.runtime.ChartGeneratorInitializer.initialize_components") as mock_init:
                mock_init.return_value = {
                    "styler": MagicMock(
                        chart_width_inches=10,
                        chart_height_inches=6,
                        dpi=100,
                        background_color="#fff",
                        grid_color="#ccc",
                        primary_color="#blue",
                        secondary_color="#green",
                        highlight_color="#yellow",
                        deribit_color="#purple",
                        kalshi_color="#orange",
                        cpu_color="#red",
                        memory_color="#pink",
                    ),
                    "schema": MagicMock(),
                    "weather_history_tracker": MagicMock(),
                    "price_path_calculator": MagicMock(),
                    "price_path_horizon_days": 30,
                    "file_manager": MagicMock(),
                    "progress_notifier": MagicMock(),
                    "time_configurator": MagicMock(),
                    "token_resolver": MagicMock(),
                    "strike_collector": MagicMock(),
                    "load_chart_creator": MagicMock(),
                    "system_chart_creator": MagicMock(),
                    "price_chart_creator": MagicMock(),
                }

                with patch.dict(sys.modules, {"src.monitor.chart_generator": mock_chart_module}):
                    generator = ChartGenerator()

                    assert generator._weather_config_open == mock_open_func

    @pytest.mark.asyncio
    async def test_init_sets_weather_config_open_to_builtin_open(self) -> None:
        """Test __init__ sets _weather_config_open to builtin open when module not found."""
        import sys

        with patch("common.chart_generator.runtime.plt"):
            with patch("common.chart_generator.runtime.ChartGeneratorInitializer.initialize_components") as mock_init:
                mock_init.return_value = {
                    "styler": MagicMock(
                        chart_width_inches=10,
                        chart_height_inches=6,
                        dpi=100,
                        background_color="#fff",
                        grid_color="#ccc",
                        primary_color="#blue",
                        secondary_color="#green",
                        highlight_color="#yellow",
                        deribit_color="#purple",
                        kalshi_color="#orange",
                        cpu_color="#red",
                        memory_color="#pink",
                    ),
                    "schema": MagicMock(),
                    "weather_history_tracker": MagicMock(),
                    "price_path_calculator": MagicMock(),
                    "price_path_horizon_days": 30,
                    "file_manager": MagicMock(),
                    "progress_notifier": MagicMock(),
                    "time_configurator": MagicMock(),
                    "token_resolver": MagicMock(),
                    "strike_collector": MagicMock(),
                    "load_chart_creator": MagicMock(),
                    "system_chart_creator": MagicMock(),
                    "price_chart_creator": MagicMock(),
                }

                with patch.dict(sys.modules, {"src.monitor.chart_generator": None}):
                    generator = ChartGenerator()

                    assert generator._weather_config_open == open

    def test_configure_time_axis_with_5_minute_alignment_method(self) -> None:
        """Test configure_time_axis_with_5_minute_alignment method."""
        mock_ax = MagicMock()
        test_timestamps = [MagicMock()]

        with patch("common.chart_generator.runtime.plt"):
            with patch("common.chart_generator.runtime.ChartGeneratorInitializer.initialize_components") as mock_init:
                mock_init.return_value = {
                    "styler": MagicMock(
                        chart_width_inches=10,
                        chart_height_inches=6,
                        dpi=100,
                        background_color="#fff",
                        grid_color="#ccc",
                        primary_color="#blue",
                        secondary_color="#green",
                        highlight_color="#yellow",
                        deribit_color="#purple",
                        kalshi_color="#orange",
                        cpu_color="#red",
                        memory_color="#pink",
                    ),
                    "schema": MagicMock(),
                    "weather_history_tracker": MagicMock(),
                    "price_path_calculator": MagicMock(),
                    "price_path_horizon_days": 30,
                    "file_manager": MagicMock(),
                    "progress_notifier": MagicMock(),
                    "time_configurator": MagicMock(),
                    "token_resolver": MagicMock(),
                    "strike_collector": MagicMock(),
                    "load_chart_creator": MagicMock(),
                    "system_chart_creator": MagicMock(),
                    "price_chart_creator": MagicMock(),
                }

                generator = ChartGenerator()

                with patch("common.chart_generator.runtime._configure_time_axis_with_5_minute_alignment_impl") as mock_impl:
                    generator.configure_time_axis_with_5_minute_alignment(mock_ax, test_timestamps, "weather", None)

                    mock_impl.assert_called_once_with(generator, mock_ax, test_timestamps, "weather", None)

    @pytest.mark.asyncio
    async def test_init_uses_default_style(self) -> None:
        """Test __init__ uses default matplotlib style."""
        with patch("common.chart_generator.runtime.plt") as mock_plt:
            with patch("common.chart_generator.runtime.ChartGeneratorInitializer.initialize_components") as mock_init:
                mock_init.return_value = {
                    "styler": MagicMock(
                        chart_width_inches=10,
                        chart_height_inches=6,
                        dpi=100,
                        background_color="#fff",
                        grid_color="#ccc",
                        primary_color="#blue",
                        secondary_color="#green",
                        highlight_color="#yellow",
                        deribit_color="#purple",
                        kalshi_color="#orange",
                        cpu_color="#red",
                        memory_color="#pink",
                    ),
                    "schema": MagicMock(),
                    "weather_history_tracker": MagicMock(),
                    "price_path_calculator": MagicMock(),
                    "price_path_horizon_days": 30,
                    "file_manager": MagicMock(),
                    "progress_notifier": MagicMock(),
                    "time_configurator": MagicMock(),
                    "token_resolver": MagicMock(),
                    "strike_collector": MagicMock(),
                    "load_chart_creator": MagicMock(),
                    "system_chart_creator": MagicMock(),
                    "price_chart_creator": MagicMock(),
                }

                generator = ChartGenerator()

                mock_plt.style.use.assert_called_once_with("default")

    @pytest.mark.asyncio
    async def test_init_passes_price_path_calculator(self) -> None:
        """Test __init__ passes price_path_calculator to initializer."""
        mock_calculator = MagicMock()

        with patch("common.chart_generator.runtime.plt"):
            with patch("common.chart_generator.runtime.ChartGeneratorInitializer.initialize_components") as mock_init:
                mock_init.return_value = {
                    "styler": MagicMock(
                        chart_width_inches=10,
                        chart_height_inches=6,
                        dpi=100,
                        background_color="#fff",
                        grid_color="#ccc",
                        primary_color="#blue",
                        secondary_color="#green",
                        highlight_color="#yellow",
                        deribit_color="#purple",
                        kalshi_color="#orange",
                        cpu_color="#red",
                        memory_color="#pink",
                    ),
                    "schema": MagicMock(),
                    "weather_history_tracker": MagicMock(),
                    "price_path_calculator": MagicMock(),
                    "price_path_horizon_days": 30,
                    "file_manager": MagicMock(),
                    "progress_notifier": MagicMock(),
                    "time_configurator": MagicMock(),
                    "token_resolver": MagicMock(),
                    "strike_collector": MagicMock(),
                    "load_chart_creator": MagicMock(),
                    "system_chart_creator": MagicMock(),
                    "price_chart_creator": MagicMock(),
                }

                generator = ChartGenerator(price_path_calculator=mock_calculator)

                call_args = mock_init.call_args
                assert call_args[1]["price_path_calculator"] == mock_calculator

    @pytest.mark.asyncio
    async def test_init_passes_prediction_horizon_days(self) -> None:
        """Test __init__ passes prediction_horizon_days to initializer."""
        with patch("common.chart_generator.runtime.plt"):
            with patch("common.chart_generator.runtime.ChartGeneratorInitializer.initialize_components") as mock_init:
                mock_init.return_value = {
                    "styler": MagicMock(
                        chart_width_inches=10,
                        chart_height_inches=6,
                        dpi=100,
                        background_color="#fff",
                        grid_color="#ccc",
                        primary_color="#blue",
                        secondary_color="#green",
                        highlight_color="#yellow",
                        deribit_color="#purple",
                        kalshi_color="#orange",
                        cpu_color="#red",
                        memory_color="#pink",
                    ),
                    "schema": MagicMock(),
                    "weather_history_tracker": MagicMock(),
                    "price_path_calculator": MagicMock(),
                    "price_path_horizon_days": 30,
                    "file_manager": MagicMock(),
                    "progress_notifier": MagicMock(),
                    "time_configurator": MagicMock(),
                    "token_resolver": MagicMock(),
                    "strike_collector": MagicMock(),
                    "load_chart_creator": MagicMock(),
                    "system_chart_creator": MagicMock(),
                    "price_chart_creator": MagicMock(),
                }

                generator = ChartGenerator(prediction_horizon_days=14)

                call_args = mock_init.call_args
                assert call_args[1]["prediction_horizon_days"] == 14
