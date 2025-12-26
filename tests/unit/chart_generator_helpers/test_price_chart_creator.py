"""Tests for chart_generator_helpers.price_chart_creator module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator_helpers.price_chart_creator import PriceChartCreator
from common.price_path_calculator import PricePathComputationError

# Test constants (data_guard requirement)
TEST_SYMBOL_BTC = "BTC"
TEST_SYMBOL_ETH = "ETH"
TEST_PRIMARY_COLOR = "blue"
TEST_PRICE_PATH_HORIZON_DAYS = 30
TEST_PREDICTION_HORIZON_DAYS = 7
TEST_CURRENT_PRICE = 50000.0
TEST_CHART_PATH = "/tmp/price_chart.png"
TEST_TIMESTAMP_1 = 1700000000
TEST_TIMESTAMP_2 = 1700000001
TEST_PRICE_1 = 49000.0
TEST_PRICE_2 = 51000.0
TEST_UNCERTAINTY = 1000.0


class TestPriceChartCreatorInit:
    """Tests for PriceChartCreator initialization."""

    def test_stores_primary_color(self) -> None:
        """Test stores primary color."""
        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=MagicMock(),
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=MagicMock(),
        )

        assert creator.primary_color == TEST_PRIMARY_COLOR

    def test_stores_price_path_calculator(self) -> None:
        """Test stores price path calculator."""
        mock_calculator = MagicMock()

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=mock_calculator,
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=MagicMock(),
        )

        assert creator.price_path_calculator is mock_calculator

    def test_stores_price_path_horizon_days(self) -> None:
        """Test stores price path horizon days."""
        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=MagicMock(),
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=MagicMock(),
        )

        assert creator.price_path_horizon_days == TEST_PRICE_PATH_HORIZON_DAYS

    def test_stores_progress_notifier(self) -> None:
        """Test stores progress notifier."""
        mock_notifier = MagicMock()

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=MagicMock(),
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=mock_notifier,
            generate_unified_chart_func=MagicMock(),
        )

        assert creator.progress_notifier is mock_notifier

    def test_stores_generate_unified_chart_func(self) -> None:
        """Test stores generate unified chart function."""
        mock_func = MagicMock()

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=MagicMock(),
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=mock_func,
        )

        assert creator.generate_unified_chart_func is mock_func

    def test_creates_price_collector(self) -> None:
        """Test creates PriceDataCollector."""
        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=MagicMock(),
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=MagicMock(),
        )

        from common.chart_generator_helpers.price_data_collector import PriceDataCollector

        assert isinstance(creator.price_collector, PriceDataCollector)

    def test_creates_title_formatter(self) -> None:
        """Test creates ChartTitleFormatter."""
        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=MagicMock(),
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=MagicMock(),
        )

        from common.chart_generator_helpers.chart_title_formatter import ChartTitleFormatter

        assert isinstance(creator.title_formatter, ChartTitleFormatter)


class TestPriceChartCreatorCreatePriceChart:
    """Tests for create_price_chart method."""

    @pytest.mark.asyncio
    async def test_notifies_progress_fetching_price_history(self) -> None:
        """Test notifies progress when fetching price history."""
        now = datetime.now(tz=timezone.utc)
        mock_notifier = MagicMock()
        mock_calculator = MagicMock()
        mock_calculator.generate_price_path.return_value = [(TEST_TIMESTAMP_1, TEST_PRICE_1, TEST_UNCERTAINTY)]
        mock_generate = AsyncMock(return_value=TEST_CHART_PATH)

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=mock_calculator,
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=mock_notifier,
            generate_unified_chart_func=mock_generate,
        )

        creator.price_collector.collect_price_history = AsyncMock(return_value=([now], [TEST_CURRENT_PRICE]))
        creator.title_formatter.format_price_chart_title = MagicMock(return_value="Chart Title")

        await creator.create_price_chart(TEST_SYMBOL_BTC)

        mock_notifier.notify_progress.assert_any_call(f"{TEST_SYMBOL_BTC}: fetching price history")

    @pytest.mark.asyncio
    async def test_collects_price_history(self) -> None:
        """Test collects price history for symbol."""
        now = datetime.now(tz=timezone.utc)
        mock_calculator = MagicMock()
        mock_calculator.generate_price_path.return_value = [(TEST_TIMESTAMP_1, TEST_PRICE_1, TEST_UNCERTAINTY)]
        mock_generate = AsyncMock(return_value=TEST_CHART_PATH)

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=mock_calculator,
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=mock_generate,
        )

        creator.price_collector.collect_price_history = AsyncMock(return_value=([now], [TEST_CURRENT_PRICE]))
        creator.title_formatter.format_price_chart_title = MagicMock(return_value="Chart Title")

        await creator.create_price_chart(TEST_SYMBOL_ETH)

        creator.price_collector.collect_price_history.assert_called_once_with(TEST_SYMBOL_ETH)

    @pytest.mark.asyncio
    async def test_uses_default_horizon_when_none_provided(self) -> None:
        """Test uses default price path horizon days when prediction horizon is None."""
        now = datetime.now(tz=timezone.utc)
        mock_calculator = MagicMock()
        mock_calculator.generate_price_path.return_value = [(TEST_TIMESTAMP_1, TEST_PRICE_1, TEST_UNCERTAINTY)]
        mock_notifier = MagicMock()
        mock_generate = AsyncMock(return_value=TEST_CHART_PATH)

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=mock_calculator,
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=mock_notifier,
            generate_unified_chart_func=mock_generate,
        )

        creator.price_collector.collect_price_history = AsyncMock(return_value=([now], [TEST_CURRENT_PRICE]))
        creator.title_formatter.format_price_chart_title = MagicMock(return_value="Chart Title")

        await creator.create_price_chart(TEST_SYMBOL_BTC, prediction_horizon_days=None)

        mock_notifier.notify_progress.assert_any_call(f"{TEST_SYMBOL_BTC}: computing price path ({TEST_PRICE_PATH_HORIZON_DAYS}d)")
        mock_calculator.generate_price_path.assert_called_once_with(TEST_SYMBOL_BTC, prediction_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS)

    @pytest.mark.asyncio
    async def test_uses_custom_horizon_when_provided(self) -> None:
        """Test uses custom prediction horizon days when provided."""
        now = datetime.now(tz=timezone.utc)
        mock_calculator = MagicMock()
        mock_calculator.generate_price_path.return_value = [(TEST_TIMESTAMP_1, TEST_PRICE_1, TEST_UNCERTAINTY)]
        mock_notifier = MagicMock()
        mock_generate = AsyncMock(return_value=TEST_CHART_PATH)

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=mock_calculator,
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=mock_notifier,
            generate_unified_chart_func=mock_generate,
        )

        creator.price_collector.collect_price_history = AsyncMock(return_value=([now], [TEST_CURRENT_PRICE]))
        creator.title_formatter.format_price_chart_title = MagicMock(return_value="Chart Title")

        await creator.create_price_chart(TEST_SYMBOL_BTC, prediction_horizon_days=TEST_PREDICTION_HORIZON_DAYS)

        mock_notifier.notify_progress.assert_any_call(f"{TEST_SYMBOL_BTC}: computing price path ({TEST_PREDICTION_HORIZON_DAYS}d)")
        mock_calculator.generate_price_path.assert_called_once_with(TEST_SYMBOL_BTC, prediction_horizon_days=TEST_PREDICTION_HORIZON_DAYS)

    @pytest.mark.asyncio
    async def test_raises_error_when_no_predicted_path(self) -> None:
        """Test raises PricePathComputationError when calculator returns no points."""
        now = datetime.now(tz=timezone.utc)
        mock_calculator = MagicMock()
        mock_calculator.generate_price_path.return_value = []

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=mock_calculator,
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=AsyncMock(),
        )

        creator.price_collector.collect_price_history = AsyncMock(return_value=([now], [TEST_CURRENT_PRICE]))

        with pytest.raises(PricePathComputationError) as exc_info:
            await creator.create_price_chart(TEST_SYMBOL_BTC)

        assert f"Price path calculator returned no points for {TEST_SYMBOL_BTC}" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_error_when_predicted_path_is_none(self) -> None:
        """Test raises PricePathComputationError when calculator returns None."""
        now = datetime.now(tz=timezone.utc)
        mock_calculator = MagicMock()
        mock_calculator.generate_price_path.return_value = None

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=mock_calculator,
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=AsyncMock(),
        )

        creator.price_collector.collect_price_history = AsyncMock(return_value=([now], [TEST_CURRENT_PRICE]))

        with pytest.raises(PricePathComputationError) as exc_info:
            await creator.create_price_chart(TEST_SYMBOL_ETH)

        assert f"Price path calculator returned no points for {TEST_SYMBOL_ETH}" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extracts_predicted_data_from_path(self) -> None:
        """Test extracts timestamps, prices, and uncertainties from predicted path."""
        now = datetime.now(tz=timezone.utc)
        mock_calculator = MagicMock()
        predicted_path = [
            (TEST_TIMESTAMP_1, TEST_PRICE_1, TEST_UNCERTAINTY),
            (TEST_TIMESTAMP_2, TEST_PRICE_2, TEST_UNCERTAINTY),
        ]
        mock_calculator.generate_price_path.return_value = predicted_path
        mock_generate = AsyncMock(return_value=TEST_CHART_PATH)

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=mock_calculator,
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=mock_generate,
        )

        creator.price_collector.collect_price_history = AsyncMock(return_value=([now], [TEST_CURRENT_PRICE]))
        creator.title_formatter.format_price_chart_title = MagicMock(return_value="Chart Title")

        await creator.create_price_chart(TEST_SYMBOL_BTC)

        call_kwargs = mock_generate.call_args[1]
        assert len(call_kwargs["prediction_timestamps"]) == 2
        assert call_kwargs["prediction_timestamps"][0].timestamp() == TEST_TIMESTAMP_1
        assert call_kwargs["prediction_timestamps"][1].timestamp() == TEST_TIMESTAMP_2
        assert call_kwargs["prediction_values"] == [TEST_PRICE_1, TEST_PRICE_2]
        assert call_kwargs["prediction_uncertainties"] == [TEST_UNCERTAINTY, TEST_UNCERTAINTY]

    @pytest.mark.asyncio
    async def test_formats_chart_title(self) -> None:
        """Test formats chart title with symbol and current price."""
        now = datetime.now(tz=timezone.utc)
        mock_calculator = MagicMock()
        mock_calculator.generate_price_path.return_value = [(TEST_TIMESTAMP_1, TEST_PRICE_1, TEST_UNCERTAINTY)]
        mock_generate = AsyncMock(return_value=TEST_CHART_PATH)

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=mock_calculator,
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=mock_generate,
        )

        creator.price_collector.collect_price_history = AsyncMock(return_value=([now], [TEST_CURRENT_PRICE]))
        creator.title_formatter.format_price_chart_title = MagicMock(return_value="BTC Price Chart")

        await creator.create_price_chart(TEST_SYMBOL_BTC)

        creator.title_formatter.format_price_chart_title.assert_called_once_with(TEST_SYMBOL_BTC, TEST_CURRENT_PRICE)

    @pytest.mark.asyncio
    async def test_notifies_progress_rendering_chart(self) -> None:
        """Test notifies progress when rendering chart."""
        now = datetime.now(tz=timezone.utc)
        mock_notifier = MagicMock()
        mock_calculator = MagicMock()
        mock_calculator.generate_price_path.return_value = [(TEST_TIMESTAMP_1, TEST_PRICE_1, TEST_UNCERTAINTY)]
        mock_generate = AsyncMock(return_value=TEST_CHART_PATH)

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=mock_calculator,
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=mock_notifier,
            generate_unified_chart_func=mock_generate,
        )

        creator.price_collector.collect_price_history = AsyncMock(return_value=([now], [TEST_CURRENT_PRICE]))
        creator.title_formatter.format_price_chart_title = MagicMock(return_value="Chart Title")

        await creator.create_price_chart(TEST_SYMBOL_ETH)

        mock_notifier.notify_progress.assert_any_call(f"{TEST_SYMBOL_ETH}: rendering chart")

    @pytest.mark.asyncio
    async def test_calls_generate_func_with_params(self) -> None:
        """Test calls generate function with correct parameters."""
        now = datetime.now(tz=timezone.utc)
        timestamps = [now]
        prices = [TEST_CURRENT_PRICE]
        mock_calculator = MagicMock()
        mock_calculator.generate_price_path.return_value = [(TEST_TIMESTAMP_1, TEST_PRICE_1, TEST_UNCERTAINTY)]
        mock_generate = AsyncMock(return_value=TEST_CHART_PATH)

        with patch("common.chart_generator_helpers.price_chart_creator.datetime") as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.fromtimestamp = datetime.fromtimestamp

            creator = PriceChartCreator(
                primary_color="green",
                price_path_calculator=mock_calculator,
                price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
                progress_notifier=MagicMock(),
                generate_unified_chart_func=mock_generate,
            )

            creator.price_collector.collect_price_history = AsyncMock(return_value=(timestamps, prices))
            creator.title_formatter.format_price_chart_title = MagicMock(return_value="Price Chart")

            await creator.create_price_chart(TEST_SYMBOL_BTC)

            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args[1]
            assert call_kwargs["timestamps"] == timestamps
            assert call_kwargs["values"] == prices
            assert call_kwargs["chart_title"] == "Price Chart"
            assert call_kwargs["y_label"] == ""
            assert call_kwargs["is_price_chart"] is True
            assert call_kwargs["line_color"] == "green"
            assert len(call_kwargs["vertical_lines"]) == 1
            assert call_kwargs["vertical_lines"][0] == (mock_now, "black", "Current Time")

    @pytest.mark.asyncio
    async def test_returns_chart_path(self) -> None:
        """Test returns chart file path."""
        now = datetime.now(tz=timezone.utc)
        mock_calculator = MagicMock()
        mock_calculator.generate_price_path.return_value = [(TEST_TIMESTAMP_1, TEST_PRICE_1, TEST_UNCERTAINTY)]
        mock_generate = AsyncMock(return_value=TEST_CHART_PATH)

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=mock_calculator,
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=mock_generate,
        )

        creator.price_collector.collect_price_history = AsyncMock(return_value=([now], [TEST_CURRENT_PRICE]))
        creator.title_formatter.format_price_chart_title = MagicMock(return_value="Chart Title")

        result = await creator.create_price_chart(TEST_SYMBOL_BTC)

        assert result == TEST_CHART_PATH

    @pytest.mark.asyncio
    async def test_price_formatter_formats_integer_prices(self) -> None:
        """Test price formatter formats integer prices without decimals."""
        now = datetime.now(tz=timezone.utc)
        mock_calculator = MagicMock()
        mock_calculator.generate_price_path.return_value = [(TEST_TIMESTAMP_1, TEST_PRICE_1, TEST_UNCERTAINTY)]
        mock_generate = AsyncMock(return_value=TEST_CHART_PATH)

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=mock_calculator,
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=mock_generate,
        )

        creator.price_collector.collect_price_history = AsyncMock(return_value=([now], [TEST_CURRENT_PRICE]))
        creator.title_formatter.format_price_chart_title = MagicMock(return_value="Chart Title")

        await creator.create_price_chart(TEST_SYMBOL_BTC)

        call_kwargs = mock_generate.call_args[1]
        formatter = call_kwargs["value_formatter_func"]
        assert formatter(100.0) == "$100"
        assert formatter(1000.0) == "$1,000"
        assert formatter(50000.0) == "$50,000"

    @pytest.mark.asyncio
    async def test_price_formatter_formats_float_prices(self) -> None:
        """Test price formatter formats float prices with two decimals."""
        now = datetime.now(tz=timezone.utc)
        mock_calculator = MagicMock()
        mock_calculator.generate_price_path.return_value = [(TEST_TIMESTAMP_1, TEST_PRICE_1, TEST_UNCERTAINTY)]
        mock_generate = AsyncMock(return_value=TEST_CHART_PATH)

        creator = PriceChartCreator(
            primary_color=TEST_PRIMARY_COLOR,
            price_path_calculator=mock_calculator,
            price_path_horizon_days=TEST_PRICE_PATH_HORIZON_DAYS,
            progress_notifier=MagicMock(),
            generate_unified_chart_func=mock_generate,
        )

        creator.price_collector.collect_price_history = AsyncMock(return_value=([now], [TEST_CURRENT_PRICE]))
        creator.title_formatter.format_price_chart_title = MagicMock(return_value="Chart Title")

        await creator.create_price_chart(TEST_SYMBOL_BTC)

        call_kwargs = mock_generate.call_args[1]
        formatter = call_kwargs["value_formatter_func"]
        assert formatter(100.50) == "$100.50"
        assert formatter(1000.99) == "$1,000.99"
        assert formatter(50000.12) == "$50,000.12"
