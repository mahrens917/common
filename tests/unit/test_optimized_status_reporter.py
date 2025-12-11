"""Tests for optimized_status_reporter module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.optimized_status_reporter import OptimizedStatusReporter


class TestOptimizedStatusReporter:
    """Tests for OptimizedStatusReporter class."""

    def test_init_with_dependencies(self) -> None:
        """Initializes with provided dependencies."""
        process_manager = MagicMock()
        health_checker = MagicMock()
        metadata_store = MagicMock()
        tracker_controller = MagicMock()
        mock_deps = MagicMock()
        mock_deps.aggregator = MagicMock()
        mock_deps.printer = MagicMock()

        reporter = OptimizedStatusReporter(
            process_manager,
            health_checker,
            metadata_store,
            tracker_controller,
            dependencies=mock_deps,
        )

        assert reporter.process_manager is process_manager
        assert reporter._aggregator is mock_deps.aggregator
        assert reporter._printer is mock_deps.printer

    def test_init_creates_dependencies_when_not_provided(self) -> None:
        """Creates dependencies when not provided."""
        process_manager = MagicMock()
        health_checker = MagicMock()
        metadata_store = MagicMock()
        tracker_controller = MagicMock()

        with patch("common.optimized_status_reporter.StatusReporterDependenciesFactory.create") as mock_factory:
            mock_deps = MagicMock()
            mock_factory.return_value = mock_deps

            reporter = OptimizedStatusReporter(
                process_manager,
                health_checker,
                metadata_store,
                tracker_controller,
            )

        mock_factory.assert_called_once()
        assert reporter._aggregator is mock_deps.aggregator
        assert reporter._printer is mock_deps.printer

    def test_init_sets_kalshi_client_to_none(self) -> None:
        """Initializes _kalshi_client to None."""
        process_manager = MagicMock()
        health_checker = MagicMock()
        metadata_store = MagicMock()
        tracker_controller = MagicMock()
        mock_deps = MagicMock()
        mock_deps.aggregator = MagicMock()
        mock_deps.printer = MagicMock()

        reporter = OptimizedStatusReporter(
            process_manager,
            health_checker,
            metadata_store,
            tracker_controller,
            dependencies=mock_deps,
        )

        assert reporter._kalshi_client is None


class TestOptimizedStatusReporterGetKalshiClient:
    """Tests for OptimizedStatusReporter._get_kalshi_client method."""

    @pytest.mark.asyncio
    async def test_creates_kalshi_client_on_first_call(self) -> None:
        """Creates KalshiClient on first call."""
        mock_deps = MagicMock()
        mock_deps.aggregator = MagicMock()
        mock_deps.printer = MagicMock()

        reporter = OptimizedStatusReporter(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dependencies=mock_deps,
        )

        with patch("common.optimized_status_reporter.KalshiClient") as mock_kalshi:
            mock_client = MagicMock()
            mock_kalshi.return_value = mock_client

            result = await reporter._get_kalshi_client()

        assert result is mock_client
        mock_kalshi.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_cached_client_on_subsequent_calls(self) -> None:
        """Returns cached client on subsequent calls."""
        mock_deps = MagicMock()
        mock_deps.aggregator = MagicMock()
        mock_deps.printer = MagicMock()

        reporter = OptimizedStatusReporter(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dependencies=mock_deps,
        )

        with patch("common.optimized_status_reporter.KalshiClient") as mock_kalshi:
            mock_client = MagicMock()
            mock_kalshi.return_value = mock_client

            result1 = await reporter._get_kalshi_client()
            result2 = await reporter._get_kalshi_client()

        assert result1 is result2
        mock_kalshi.assert_called_once()


class TestReporterStreamReport:
    """Tests for OptimizedStatusReporter.generate_and_stream_status_report method."""

    @pytest.mark.asyncio
    async def test_returns_status_data_on_success(self) -> None:
        """Returns status data on success."""
        mock_deps = MagicMock()
        mock_deps.aggregator = AsyncMock()
        mock_deps.printer = AsyncMock()
        expected_status = {"service": "running", "health": "ok"}
        mock_deps.aggregator.gather_status_data = AsyncMock(return_value=expected_status)
        mock_deps.printer.print_status_report = AsyncMock()

        reporter = OptimizedStatusReporter(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dependencies=mock_deps,
        )

        mock_redis = MagicMock()
        mock_monitor = MagicMock()
        mock_kalshi = MagicMock()

        with patch(
            "common.redis_protocol.connection_pool_core.get_redis_client",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            with patch(
                "common.process_monitor.get_global_process_monitor",
                new_callable=AsyncMock,
                return_value=mock_monitor,
            ):
                with patch.object(reporter, "_get_kalshi_client", new_callable=AsyncMock, return_value=mock_kalshi):
                    result = await reporter.generate_and_stream_status_report()

        assert result == expected_status
        mock_deps.printer.print_status_report.assert_called_once_with(expected_status)

    @pytest.mark.asyncio
    async def test_raises_runtime_error_on_exception(self) -> None:
        """Raises RuntimeError when exception occurs."""
        mock_deps = MagicMock()
        mock_deps.aggregator = AsyncMock()
        mock_deps.aggregator.gather_status_data = AsyncMock(side_effect=ValueError("Test error"))
        mock_deps.printer = AsyncMock()

        reporter = OptimizedStatusReporter(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dependencies=mock_deps,
        )

        with patch(
            "common.redis_protocol.connection_pool_core.get_redis_client",
            new_callable=AsyncMock,
        ):
            with patch(
                "common.process_monitor.get_global_process_monitor",
                new_callable=AsyncMock,
            ):
                with patch.object(reporter, "_get_kalshi_client", new_callable=AsyncMock):
                    with patch("common.optimized_status_reporter.logger"):
                        with pytest.raises(RuntimeError) as exc_info:
                            await reporter.generate_and_stream_status_report()

        assert "Status report generation failed" in str(exc_info.value)


class TestOptimizedStatusReporterGatherStatusData:
    """Tests for OptimizedStatusReporter.gather_status_data method."""

    @pytest.mark.asyncio
    async def test_uses_provided_redis_client(self) -> None:
        """Uses provided redis client."""
        mock_deps = MagicMock()
        mock_deps.aggregator = AsyncMock()
        expected_status = {"service": "running"}
        mock_deps.aggregator.gather_status_data = AsyncMock(return_value=expected_status)
        mock_deps.printer = MagicMock()

        reporter = OptimizedStatusReporter(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dependencies=mock_deps,
        )

        mock_redis = MagicMock()

        with patch(
            "common.process_monitor.get_global_process_monitor",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ):
            with patch.object(reporter, "_get_kalshi_client", new_callable=AsyncMock):
                result = await reporter.gather_status_data(redis_client=mock_redis)

        assert result == expected_status
        # Verify the provided client was used
        call_args = mock_deps.aggregator.gather_status_data.call_args
        assert call_args[0][0] is mock_redis

    @pytest.mark.asyncio
    async def test_creates_client_when_not_provided(self) -> None:
        """Creates and closes client when not provided."""
        mock_deps = MagicMock()
        mock_deps.aggregator = AsyncMock()
        expected_status = {"service": "running"}
        mock_deps.aggregator.gather_status_data = AsyncMock(return_value=expected_status)
        mock_deps.printer = MagicMock()

        reporter = OptimizedStatusReporter(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dependencies=mock_deps,
        )

        mock_redis = AsyncMock()

        with patch(
            "common.redis_protocol.connection_pool_core.get_redis_client",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            with patch(
                "common.process_monitor.get_global_process_monitor",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ):
                with patch.object(reporter, "_get_kalshi_client", new_callable=AsyncMock):
                    result = await reporter.gather_status_data()

        assert result == expected_status
        mock_redis.aclose.assert_called_once()


class TestReporterGatherData:
    """Tests for OptimizedStatusReporter._gather_status_data_optimized method."""

    @pytest.mark.asyncio
    async def test_delegates_to_gather_status_data(self) -> None:
        """Delegates to gather_status_data."""
        mock_deps = MagicMock()
        mock_deps.aggregator = MagicMock()
        mock_deps.printer = MagicMock()

        reporter = OptimizedStatusReporter(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dependencies=mock_deps,
        )

        expected_status = {"service": "running"}
        reporter.gather_status_data = AsyncMock(return_value=expected_status)
        mock_redis = MagicMock()

        result = await reporter._gather_status_data_optimized(redis_client=mock_redis)

        assert result == expected_status
        reporter.gather_status_data.assert_called_once_with(redis_client=mock_redis)


class TestOptimizedStatusReporterGenerateWeatherSection:
    """Tests for OptimizedStatusReporter._generate_weather_section method."""

    def test_returns_empty_list_when_no_weather_generator(self) -> None:
        """Returns empty list when printer has no weather generator."""
        mock_deps = MagicMock()
        mock_deps.aggregator = MagicMock()
        mock_deps.printer = MagicMock(spec=[])  # No _weather_generator attribute

        reporter = OptimizedStatusReporter(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dependencies=mock_deps,
        )

        status_data = {"weather_temperatures": {"KJFK": 72}}

        result = reporter._generate_weather_section(status_data)

        assert result == []

    def test_returns_weather_lines_when_generator_available(self) -> None:
        """Returns weather lines when generator is available."""
        mock_deps = MagicMock()
        mock_deps.aggregator = MagicMock()
        mock_weather_gen = MagicMock()
        mock_weather_gen.generate_weather_section = MagicMock(return_value=["KJFK: 72°F", "KLAX: 65°F"])
        mock_deps.printer._weather_generator = mock_weather_gen

        reporter = OptimizedStatusReporter(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dependencies=mock_deps,
        )

        status_data = {"weather_temperatures": {"KJFK": 72, "KLAX": 65}}

        result = reporter._generate_weather_section(status_data)

        assert result == ["KJFK: 72°F", "KLAX: 65°F"]
        mock_weather_gen.generate_weather_section.assert_called_once_with({"KJFK": 72, "KLAX": 65})

    def test_handles_missing_weather_temperatures_key(self) -> None:
        """Handles missing weather_temperatures key in status_data."""
        mock_deps = MagicMock()
        mock_deps.aggregator = MagicMock()
        mock_weather_gen = MagicMock()
        mock_weather_gen.generate_weather_section = MagicMock(return_value=[])
        mock_deps.printer._weather_generator = mock_weather_gen

        reporter = OptimizedStatusReporter(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dependencies=mock_deps,
        )

        status_data = {}

        result = reporter._generate_weather_section(status_data)

        mock_weather_gen.generate_weather_section.assert_called_once_with({})
        assert result == []
