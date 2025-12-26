"""Tests for chart_generator_helpers.load_charts_generator module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator_helpers.load_charts_generator import LoadChartsGenerator

TEST_HOURS = 24
TEST_DERIBIT_PATH = "/tmp/deribit_chart.png"
TEST_KALSHI_PATH = "/tmp/kalshi_chart.png"
TEST_CPU_PATH = "/tmp/cpu_chart.png"
TEST_MEMORY_PATH = "/tmp/memory_chart.png"


class TestLoadChartsGeneratorInit:
    """Tests for LoadChartsGenerator initialization."""

    def test_stores_load_chart_creator(self) -> None:
        """Test stores load chart creator."""
        mock_load_creator = MagicMock()
        mock_system_creator = MagicMock()

        generator = LoadChartsGenerator(
            load_chart_creator=mock_load_creator,
            system_chart_creator=mock_system_creator,
        )

        assert generator.load_chart_creator is mock_load_creator

    def test_stores_system_chart_creator(self) -> None:
        """Test stores system chart creator."""
        mock_load_creator = MagicMock()
        mock_system_creator = MagicMock()

        generator = LoadChartsGenerator(
            load_chart_creator=mock_load_creator,
            system_chart_creator=mock_system_creator,
        )

        assert generator.system_chart_creator is mock_system_creator


class TestLoadChartsGeneratorGenerateLoadCharts:
    """Tests for generate_load_charts method."""

    @pytest.mark.asyncio
    async def test_creates_deribit_chart(self) -> None:
        """Test creates deribit load chart."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, TEST_KALSHI_PATH])
        mock_system_creator = MagicMock()
        mock_system_creator.create_system_chart = AsyncMock(side_effect=[TEST_CPU_PATH, TEST_MEMORY_PATH])
        mock_os = MagicMock()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with patch("common.redis_utils.get_redis_connection") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            generator = LoadChartsGenerator(
                load_chart_creator=mock_load_creator,
                system_chart_creator=mock_system_creator,
            )

            await generator.generate_load_charts(TEST_HOURS, mock_os)

            assert mock_load_creator.create_load_chart.call_args_list[0][0] == ("deribit", TEST_HOURS)

    @pytest.mark.asyncio
    async def test_creates_kalshi_chart(self) -> None:
        """Test creates kalshi load chart."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, TEST_KALSHI_PATH])
        mock_system_creator = MagicMock()
        mock_system_creator.create_system_chart = AsyncMock(side_effect=[TEST_CPU_PATH, TEST_MEMORY_PATH])
        mock_os = MagicMock()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with patch("common.redis_utils.get_redis_connection") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            generator = LoadChartsGenerator(
                load_chart_creator=mock_load_creator,
                system_chart_creator=mock_system_creator,
            )

            await generator.generate_load_charts(TEST_HOURS, mock_os)

            assert mock_load_creator.create_load_chart.call_args_list[1][0] == ("kalshi", TEST_HOURS)

    @pytest.mark.asyncio
    async def test_gets_redis_connection(self) -> None:
        """Test gets redis connection for system charts."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, TEST_KALSHI_PATH])
        mock_system_creator = MagicMock()
        mock_system_creator.create_system_chart = AsyncMock(side_effect=[TEST_CPU_PATH, TEST_MEMORY_PATH])
        mock_os = MagicMock()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with patch("common.redis_utils.get_redis_connection") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            generator = LoadChartsGenerator(
                load_chart_creator=mock_load_creator,
                system_chart_creator=mock_system_creator,
            )

            await generator.generate_load_charts(TEST_HOURS, mock_os)

            mock_get_redis.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_cpu_chart(self) -> None:
        """Test creates cpu system chart."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, TEST_KALSHI_PATH])
        mock_system_creator = MagicMock()
        mock_system_creator.create_system_chart = AsyncMock(side_effect=[TEST_CPU_PATH, TEST_MEMORY_PATH])
        mock_os = MagicMock()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with patch("common.redis_utils.get_redis_connection") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            generator = LoadChartsGenerator(
                load_chart_creator=mock_load_creator,
                system_chart_creator=mock_system_creator,
            )

            await generator.generate_load_charts(TEST_HOURS, mock_os)

            assert mock_system_creator.create_system_chart.call_args_list[0][0] == ("cpu", TEST_HOURS, mock_redis)

    @pytest.mark.asyncio
    async def test_creates_memory_chart(self) -> None:
        """Test creates memory system chart."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, TEST_KALSHI_PATH])
        mock_system_creator = MagicMock()
        mock_system_creator.create_system_chart = AsyncMock(side_effect=[TEST_CPU_PATH, TEST_MEMORY_PATH])
        mock_os = MagicMock()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with patch("common.redis_utils.get_redis_connection") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            generator = LoadChartsGenerator(
                load_chart_creator=mock_load_creator,
                system_chart_creator=mock_system_creator,
            )

            await generator.generate_load_charts(TEST_HOURS, mock_os)

            assert mock_system_creator.create_system_chart.call_args_list[1][0] == ("memory", TEST_HOURS, mock_redis)

    @pytest.mark.asyncio
    async def test_closes_redis_connection(self) -> None:
        """Test closes redis connection after use."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, TEST_KALSHI_PATH])
        mock_system_creator = MagicMock()
        mock_system_creator.create_system_chart = AsyncMock(side_effect=[TEST_CPU_PATH, TEST_MEMORY_PATH])
        mock_os = MagicMock()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with patch("common.redis_utils.get_redis_connection") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            generator = LoadChartsGenerator(
                load_chart_creator=mock_load_creator,
                system_chart_creator=mock_system_creator,
            )

            await generator.generate_load_charts(TEST_HOURS, mock_os)

            mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_closes_redis_even_on_system_chart_error(self) -> None:
        """Test closes redis connection even when system chart creation fails."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, TEST_KALSHI_PATH])
        mock_system_creator = MagicMock()
        mock_system_creator.create_system_chart = AsyncMock(side_effect=RuntimeError("Chart error"))
        mock_os = MagicMock()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with patch("common.redis_utils.get_redis_connection") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            generator = LoadChartsGenerator(
                load_chart_creator=mock_load_creator,
                system_chart_creator=mock_system_creator,
            )

            with pytest.raises(RuntimeError):
                await generator.generate_load_charts(TEST_HOURS, mock_os)

            mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_chart_paths_dict(self) -> None:
        """Test returns dictionary with all chart paths."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, TEST_KALSHI_PATH])
        mock_system_creator = MagicMock()
        mock_system_creator.create_system_chart = AsyncMock(side_effect=[TEST_CPU_PATH, TEST_MEMORY_PATH])
        mock_os = MagicMock()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with patch("common.redis_utils.get_redis_connection") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            generator = LoadChartsGenerator(
                load_chart_creator=mock_load_creator,
                system_chart_creator=mock_system_creator,
            )

            result = await generator.generate_load_charts(TEST_HOURS, mock_os)

            assert result == {
                "deribit": TEST_DERIBIT_PATH,
                "kalshi": TEST_KALSHI_PATH,
                "cpu": TEST_CPU_PATH,
                "memory": TEST_MEMORY_PATH,
            }

    @pytest.mark.asyncio
    async def test_cleanup_on_load_chart_failure(self) -> None:
        """Test cleans up chart files when load chart creation fails."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, RuntimeError("Load error")])
        mock_system_creator = MagicMock()
        mock_os = MagicMock()

        generator = LoadChartsGenerator(
            load_chart_creator=mock_load_creator,
            system_chart_creator=mock_system_creator,
        )

        with pytest.raises(RuntimeError):
            await generator.generate_load_charts(TEST_HOURS, mock_os)

        mock_os.unlink.assert_called_once_with(TEST_DERIBIT_PATH)

    @pytest.mark.asyncio
    async def test_cleanup_on_system_chart_failure(self) -> None:
        """Test cleans up chart files when system chart creation fails."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, TEST_KALSHI_PATH])
        mock_system_creator = MagicMock()
        mock_system_creator.create_system_chart = AsyncMock(side_effect=[TEST_CPU_PATH, RuntimeError("System error")])
        mock_os = MagicMock()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with patch("common.redis_utils.get_redis_connection") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            generator = LoadChartsGenerator(
                load_chart_creator=mock_load_creator,
                system_chart_creator=mock_system_creator,
            )

            with pytest.raises(RuntimeError):
                await generator.generate_load_charts(TEST_HOURS, mock_os)

            assert mock_os.unlink.call_count == 3
            unlink_calls = [call[0][0] for call in mock_os.unlink.call_args_list]
            assert TEST_DERIBIT_PATH in unlink_calls
            assert TEST_KALSHI_PATH in unlink_calls
            assert TEST_CPU_PATH in unlink_calls

    @pytest.mark.asyncio
    async def test_cleanup_handles_os_error(self) -> None:
        """Test cleanup handles OSError when unlinking fails."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, RuntimeError("Load error")])
        mock_system_creator = MagicMock()
        mock_os = MagicMock()
        mock_os.unlink.side_effect = OSError("File not found")

        with patch("common.chart_generator_helpers.load_charts_generator.logger") as mock_logger:
            generator = LoadChartsGenerator(
                load_chart_creator=mock_load_creator,
                system_chart_creator=mock_system_creator,
            )

            with pytest.raises(RuntimeError):
                await generator.generate_load_charts(TEST_HOURS, mock_os)

            mock_logger.warning.assert_called_once_with("Unable to clean up chart file %s", TEST_DERIBIT_PATH)

    @pytest.mark.asyncio
    async def test_no_cleanup_on_success(self) -> None:
        """Test does not attempt cleanup when all charts succeed."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, TEST_KALSHI_PATH])
        mock_system_creator = MagicMock()
        mock_system_creator.create_system_chart = AsyncMock(side_effect=[TEST_CPU_PATH, TEST_MEMORY_PATH])
        mock_os = MagicMock()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with patch("common.redis_utils.get_redis_connection") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            generator = LoadChartsGenerator(
                load_chart_creator=mock_load_creator,
                system_chart_creator=mock_system_creator,
            )

            await generator.generate_load_charts(TEST_HOURS, mock_os)

            mock_os.unlink.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_on_redis_connection_failure(self) -> None:
        """Test cleans up load charts when redis connection fails."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, TEST_KALSHI_PATH])
        mock_system_creator = MagicMock()
        mock_os = MagicMock()

        with patch("common.redis_utils.get_redis_connection") as mock_get_redis:
            mock_get_redis.side_effect = RuntimeError("Redis connection failed")

            generator = LoadChartsGenerator(
                load_chart_creator=mock_load_creator,
                system_chart_creator=mock_system_creator,
            )

            with pytest.raises(RuntimeError):
                await generator.generate_load_charts(TEST_HOURS, mock_os)

            assert mock_os.unlink.call_count == 2
            unlink_calls = [call[0][0] for call in mock_os.unlink.call_args_list]
            assert TEST_DERIBIT_PATH in unlink_calls
            assert TEST_KALSHI_PATH in unlink_calls

    @pytest.mark.asyncio
    async def test_cleanup_multiple_files_with_mixed_errors(self) -> None:
        """Test cleanup continues even when some unlink operations fail."""
        mock_load_creator = MagicMock()
        mock_load_creator.create_load_chart = AsyncMock(side_effect=[TEST_DERIBIT_PATH, TEST_KALSHI_PATH])
        mock_system_creator = MagicMock()
        mock_system_creator.create_system_chart = AsyncMock(side_effect=RuntimeError("System error"))
        mock_os = MagicMock()
        mock_os.unlink.side_effect = [OSError("First fail"), None]
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        with patch("common.redis_utils.get_redis_connection") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            with patch("common.chart_generator_helpers.load_charts_generator.logger") as mock_logger:
                generator = LoadChartsGenerator(
                    load_chart_creator=mock_load_creator,
                    system_chart_creator=mock_system_creator,
                )

                with pytest.raises(RuntimeError):
                    await generator.generate_load_charts(TEST_HOURS, mock_os)

                assert mock_os.unlink.call_count == 2
                mock_logger.warning.assert_called_once()
