"""Tests for process filter helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from common.process_killer_helpers.process_filter import filter_processes_by_pid


class TestFilterProcessesByPid:
    """Tests for filter_processes_by_pid function."""

    def test_returns_all_processes_when_exclude_pid_is_none(self) -> None:
        """Returns all processes when no exclusion PID provided."""
        proc1 = MagicMock(pid=100)
        proc2 = MagicMock(pid=200)
        processes = [proc1, proc2]

        result = filter_processes_by_pid(processes, None)

        assert len(result) == 2
        assert proc1 in result
        assert proc2 in result

    def test_excludes_matching_pid(self) -> None:
        """Excludes process with matching PID."""
        proc1 = MagicMock(pid=100)
        proc2 = MagicMock(pid=200)
        proc3 = MagicMock(pid=300)
        processes = [proc1, proc2, proc3]

        result = filter_processes_by_pid(processes, 200)

        assert len(result) == 2
        assert proc1 in result
        assert proc2 not in result
        assert proc3 in result

    def test_returns_all_when_no_match(self) -> None:
        """Returns all processes when exclude PID doesn't match any."""
        proc1 = MagicMock(pid=100)
        proc2 = MagicMock(pid=200)
        processes = [proc1, proc2]

        result = filter_processes_by_pid(processes, 999)

        assert len(result) == 2

    def test_handles_empty_list(self) -> None:
        """Handles empty process list."""
        result = filter_processes_by_pid([], 100)

        assert result == []

    def test_handles_generator_input(self) -> None:
        """Handles generator as input."""
        proc1 = MagicMock(pid=100)
        proc2 = MagicMock(pid=200)

        def process_generator():
            yield proc1
            yield proc2

        result = filter_processes_by_pid(process_generator(), 100)

        assert len(result) == 1
        assert proc2 in result
