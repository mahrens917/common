"""Tests for monitor query helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.process_killer_helpers.monitor_query import query_monitor_for_processes


class TestQueryMonitorForProcesses:
    """Tests for query_monitor_for_processes function."""

    @pytest.mark.asyncio
    async def test_queries_global_monitor(self) -> None:
        """Queries the global process monitor."""
        mock_monitor = AsyncMock()
        mock_monitor.find_processes_by_keywords = AsyncMock(return_value=[])

        with patch(
            "common.process_killer_helpers.monitor_query.process_monitor_module.get_global_process_monitor",
            return_value=mock_monitor,
        ):
            await query_monitor_for_processes(["python"], "test_service")

            mock_monitor.find_processes_by_keywords.assert_called_once_with(["python"])

    @pytest.mark.asyncio
    async def test_returns_list_of_processes(self) -> None:
        """Returns a list of found processes."""
        proc1 = MagicMock()
        proc2 = MagicMock()
        mock_monitor = AsyncMock()
        mock_monitor.find_processes_by_keywords = AsyncMock(return_value=[proc1, proc2])

        with patch(
            "common.process_killer_helpers.monitor_query.process_monitor_module.get_global_process_monitor",
            return_value=mock_monitor,
        ):
            result = await query_monitor_for_processes(["service"], "test_service")

            assert len(result) == 2
            assert proc1 in result
            assert proc2 in result

    @pytest.mark.asyncio
    async def test_converts_to_list(self) -> None:
        """Converts generator/iterator result to list."""
        proc1 = MagicMock()
        mock_monitor = AsyncMock()

        def process_gen():
            yield proc1

        mock_monitor.find_processes_by_keywords = AsyncMock(return_value=process_gen())

        with patch(
            "common.process_killer_helpers.monitor_query.process_monitor_module.get_global_process_monitor",
            return_value=mock_monitor,
        ):
            result = await query_monitor_for_processes(["keyword"], "service")

            assert isinstance(result, list)
            assert proc1 in result

    @pytest.mark.asyncio
    async def test_passes_keywords_to_monitor(self) -> None:
        """Passes all keywords to monitor find method."""
        mock_monitor = AsyncMock()
        mock_monitor.find_processes_by_keywords = AsyncMock(return_value=[])

        keywords = ["python", "service", "main"]

        with patch(
            "common.process_killer_helpers.monitor_query.process_monitor_module.get_global_process_monitor",
            return_value=mock_monitor,
        ):
            await query_monitor_for_processes(keywords, "my_service")

            mock_monitor.find_processes_by_keywords.assert_called_once_with(keywords)
