"""Tests for memory monitor metrics reader."""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import psutil
import pytest

from src.common.memory_monitor_helpers.metrics_reader import MetricsReader


class TestInit:
    """Tests for MetricsReader initialization."""

    def test_init_stores_process(self):
        """Test that initialization stores the process."""
        process = MagicMock()
        reader = MetricsReader(process)
        assert reader.process is process

    def test_init_accepts_psutil_process(self):
        """Test that initialization accepts psutil.Process."""
        with patch("psutil.Process") as mock_process_class:
            mock_process = MagicMock()
            mock_process_class.return_value = mock_process
            process = mock_process_class()
            reader = MetricsReader(process)
            assert reader.process is process


class TestGetCurrentMemoryUsage:
    """Tests for get_current_memory_usage method."""

    def test_returns_memory_in_mb(self):
        """Test that memory is returned in MB."""
        process = MagicMock()
        process.memory_info.return_value = SimpleNamespace(rss=2 * 1024 * 1024)
        reader = MetricsReader(process)

        assert reader.get_current_memory_usage() == pytest.approx(2.0)
        process.memory_info.assert_called_once()

    def test_converts_bytes_to_mb_correctly(self):
        """Test byte to MB conversion is accurate."""
        process = MagicMock()
        process.memory_info.return_value = SimpleNamespace(rss=1048576)
        reader = MetricsReader(process)

        assert reader.get_current_memory_usage() == pytest.approx(1.0)

    def test_handles_zero_memory(self):
        """Test handling of zero memory usage."""
        process = MagicMock()
        process.memory_info.return_value = SimpleNamespace(rss=0)
        reader = MetricsReader(process)

        assert reader.get_current_memory_usage() == pytest.approx(0.0)

    def test_handles_large_memory_values(self):
        """Test handling of large memory values."""
        process = MagicMock()
        process.memory_info.return_value = SimpleNamespace(rss=10 * 1024 * 1024 * 1024)
        reader = MetricsReader(process)

        assert reader.get_current_memory_usage() == pytest.approx(10240.0)

    def test_handles_fractional_mb(self):
        """Test handling of fractional MB values."""
        process = MagicMock()
        process.memory_info.return_value = SimpleNamespace(rss=int(1.5 * 1024 * 1024))
        reader = MetricsReader(process)

        assert reader.get_current_memory_usage() == pytest.approx(1.5)

    def test_handles_psutil_error(self):
        """Test that psutil.Error is caught and returns 0.0."""
        process = MagicMock()
        process.memory_info.side_effect = psutil.Error("fail")
        reader = MetricsReader(process)

        assert reader.get_current_memory_usage() == 0.0

    def test_handles_psutil_noaccessdenied(self):
        """Test that psutil.AccessDenied is caught and returns 0.0."""
        process = MagicMock()
        process.memory_info.side_effect = psutil.AccessDenied("denied")
        reader = MetricsReader(process)

        assert reader.get_current_memory_usage() == 0.0

    def test_handles_psutil_nosuchprocess(self):
        """Test that psutil.NoSuchProcess is caught and returns 0.0."""
        process = MagicMock()
        process.memory_info.side_effect = psutil.NoSuchProcess(pid=123, name="test")
        reader = MetricsReader(process)

        assert reader.get_current_memory_usage() == 0.0

    def test_handles_os_error(self):
        """Test that OSError is caught and returns 0.0."""
        process = MagicMock()
        process.memory_info.side_effect = OSError("os error")
        reader = MetricsReader(process)

        assert reader.get_current_memory_usage() == 0.0

    def test_handles_permission_error(self):
        """Test that PermissionError is caught and returns 0.0."""
        process = MagicMock()
        process.memory_info.side_effect = PermissionError("permission denied")
        reader = MetricsReader(process)

        assert reader.get_current_memory_usage() == 0.0

    def test_logs_warning_on_psutil_error(self, caplog):
        """Test that a warning is logged on psutil error."""
        process = MagicMock()
        process.memory_info.side_effect = psutil.Error("fail")
        reader = MetricsReader(process)

        with caplog.at_level("WARNING"):
            reader.get_current_memory_usage()

        assert "Failed to get memory usage" in caplog.text

    def test_logs_warning_on_os_error(self, caplog):
        """Test that a warning is logged on OS error."""
        process = MagicMock()
        process.memory_info.side_effect = OSError("os error")
        reader = MetricsReader(process)

        with caplog.at_level("WARNING"):
            reader.get_current_memory_usage()

        assert "Failed to get memory usage" in caplog.text


class TestGetSystemMemoryPercent:
    """Tests for get_system_memory_percent method."""

    def test_returns_system_memory_percentage(self, monkeypatch):
        """Test that system memory percentage is returned."""
        monkeypatch.setattr(psutil, "virtual_memory", lambda: SimpleNamespace(percent=42.0))
        reader = MetricsReader(MagicMock())

        assert reader.get_system_memory_percent() == 42.0

    def test_returns_exact_percentage(self, monkeypatch):
        """Test that exact percentage value is returned."""
        monkeypatch.setattr(psutil, "virtual_memory", lambda: SimpleNamespace(percent=73.5))
        reader = MetricsReader(MagicMock())

        assert reader.get_system_memory_percent() == pytest.approx(73.5)

    def test_handles_zero_percent(self, monkeypatch):
        """Test handling of zero percent memory usage."""
        monkeypatch.setattr(psutil, "virtual_memory", lambda: SimpleNamespace(percent=0.0))
        reader = MetricsReader(MagicMock())

        assert reader.get_system_memory_percent() == pytest.approx(0.0)

    def test_handles_hundred_percent(self, monkeypatch):
        """Test handling of 100% memory usage."""
        monkeypatch.setattr(psutil, "virtual_memory", lambda: SimpleNamespace(percent=100.0))
        reader = MetricsReader(MagicMock())

        assert reader.get_system_memory_percent() == pytest.approx(100.0)

    def test_handles_psutil_error(self, monkeypatch):
        """Test that psutil.Error is caught and returns 0.0."""

        def _virtual_memory():
            raise psutil.Error("boom")

        monkeypatch.setattr(psutil, "virtual_memory", _virtual_memory)
        reader = MetricsReader(MagicMock())

        assert reader.get_system_memory_percent() == 0.0

    def test_handles_os_error(self, monkeypatch):
        """Test that OSError is caught and returns 0.0."""

        def _virtual_memory():
            raise OSError("os error")

        monkeypatch.setattr(psutil, "virtual_memory", _virtual_memory)
        reader = MetricsReader(MagicMock())

        assert reader.get_system_memory_percent() == 0.0

    def test_handles_permission_error(self, monkeypatch):
        """Test that PermissionError is caught and returns 0.0."""

        def _virtual_memory():
            raise PermissionError("permission denied")

        monkeypatch.setattr(psutil, "virtual_memory", _virtual_memory)
        reader = MetricsReader(MagicMock())

        assert reader.get_system_memory_percent() == 0.0

    def test_logs_warning_on_psutil_error(self, monkeypatch, caplog):
        """Test that a warning is logged on psutil error."""

        def _virtual_memory():
            raise psutil.Error("boom")

        monkeypatch.setattr(psutil, "virtual_memory", _virtual_memory)
        reader = MetricsReader(MagicMock())

        with caplog.at_level("WARNING"):
            reader.get_system_memory_percent()

        assert "Failed to get system memory" in caplog.text

    def test_logs_warning_on_os_error(self, monkeypatch, caplog):
        """Test that a warning is logged on OS error."""

        def _virtual_memory():
            raise OSError("os error")

        monkeypatch.setattr(psutil, "virtual_memory", _virtual_memory)
        reader = MetricsReader(MagicMock())

        with caplog.at_level("WARNING"):
            reader.get_system_memory_percent()

        assert "Failed to get system memory" in caplog.text


class TestGetCurrentTaskCount:
    """Tests for get_current_task_count method."""

    def test_counts_only_running_tasks(self, monkeypatch):
        """Test that only non-done tasks are counted."""

        class DummyTask:
            def __init__(self, done):
                self._done = done

            def done(self):
                return self._done

        dummy_loop = MagicMock()
        monkeypatch.setattr(asyncio, "get_running_loop", lambda: dummy_loop)
        monkeypatch.setattr(
            asyncio,
            "all_tasks",
            lambda loop: {DummyTask(False), DummyTask(True)},
        )
        reader = MetricsReader(MagicMock())

        assert reader.get_current_task_count() == 1

    def test_returns_zero_when_all_tasks_done(self, monkeypatch):
        """Test that zero is returned when all tasks are done."""

        class DummyTask:
            def __init__(self, done):
                self._done = done

            def done(self):
                return self._done

        dummy_loop = MagicMock()
        monkeypatch.setattr(asyncio, "get_running_loop", lambda: dummy_loop)
        monkeypatch.setattr(
            asyncio,
            "all_tasks",
            lambda loop: {DummyTask(True), DummyTask(True)},
        )
        reader = MetricsReader(MagicMock())

        assert reader.get_current_task_count() == 0

    def test_returns_zero_when_no_tasks(self, monkeypatch):
        """Test that zero is returned when there are no tasks."""
        dummy_loop = MagicMock()
        monkeypatch.setattr(asyncio, "get_running_loop", lambda: dummy_loop)
        monkeypatch.setattr(asyncio, "all_tasks", lambda loop: set())
        reader = MetricsReader(MagicMock())

        assert reader.get_current_task_count() == 0

    def test_counts_all_running_tasks(self, monkeypatch):
        """Test that all running tasks are counted."""

        class DummyTask:
            def __init__(self, done):
                self._done = done

            def done(self):
                return self._done

        dummy_loop = MagicMock()
        monkeypatch.setattr(asyncio, "get_running_loop", lambda: dummy_loop)
        monkeypatch.setattr(
            asyncio,
            "all_tasks",
            lambda loop: {
                DummyTask(False),
                DummyTask(False),
                DummyTask(False),
                DummyTask(True),
            },
        )
        reader = MetricsReader(MagicMock())

        assert reader.get_current_task_count() == 3

    def test_handles_runtime_error(self, monkeypatch):
        """Test that RuntimeError is caught and returns 0."""

        def _raise_loop():
            raise RuntimeError("fail")

        monkeypatch.setattr(asyncio, "get_running_loop", _raise_loop)
        reader = MetricsReader(MagicMock())

        assert reader.get_current_task_count() == 0

    def test_handles_value_error(self, monkeypatch):
        """Test that ValueError is caught and returns 0."""

        def _raise_loop():
            raise ValueError("fail")

        monkeypatch.setattr(asyncio, "get_running_loop", _raise_loop)
        reader = MetricsReader(MagicMock())

        assert reader.get_current_task_count() == 0

    def test_handles_runtime_error_from_all_tasks(self, monkeypatch):
        """Test that RuntimeError from all_tasks is caught and returns 0."""
        dummy_loop = MagicMock()
        monkeypatch.setattr(asyncio, "get_running_loop", lambda: dummy_loop)

        def _raise_error(loop):
            raise RuntimeError("all_tasks error")

        monkeypatch.setattr(asyncio, "all_tasks", _raise_error)
        reader = MetricsReader(MagicMock())

        assert reader.get_current_task_count() == 0

    def test_handles_value_error_from_all_tasks(self, monkeypatch):
        """Test that ValueError from all_tasks is caught and returns 0."""
        dummy_loop = MagicMock()
        monkeypatch.setattr(asyncio, "get_running_loop", lambda: dummy_loop)

        def _raise_error(loop):
            raise ValueError("all_tasks error")

        monkeypatch.setattr(asyncio, "all_tasks", _raise_error)
        reader = MetricsReader(MagicMock())

        assert reader.get_current_task_count() == 0

    def test_logs_warning_on_runtime_error(self, monkeypatch, caplog):
        """Test that a warning is logged on RuntimeError."""

        def _raise_loop():
            raise RuntimeError("fail")

        monkeypatch.setattr(asyncio, "get_running_loop", _raise_loop)
        reader = MetricsReader(MagicMock())

        with caplog.at_level("WARNING"):
            reader.get_current_task_count()

        assert "Failed to get task count" in caplog.text

    def test_logs_warning_on_value_error(self, monkeypatch, caplog):
        """Test that a warning is logged on ValueError."""

        def _raise_loop():
            raise ValueError("fail")

        monkeypatch.setattr(asyncio, "get_running_loop", _raise_loop)
        reader = MetricsReader(MagicMock())

        with caplog.at_level("WARNING"):
            reader.get_current_task_count()

        assert "Failed to get task count" in caplog.text

    def test_passes_loop_to_all_tasks(self, monkeypatch):
        """Test that the loop is passed to all_tasks."""
        dummy_loop = MagicMock()
        all_tasks_calls = []

        def _capture_all_tasks(loop):
            all_tasks_calls.append(loop)
            return set()

        monkeypatch.setattr(asyncio, "get_running_loop", lambda: dummy_loop)
        monkeypatch.setattr(asyncio, "all_tasks", _capture_all_tasks)
        reader = MetricsReader(MagicMock())

        reader.get_current_task_count()

        assert len(all_tasks_calls) == 1
        assert all_tasks_calls[0] is dummy_loop


class TestErrorConstants:
    """Tests for error constant definitions."""

    def test_psutil_errors_includes_psutil_error(self):
        """Test that PSUTIL_ERRORS includes psutil.Error."""
        from src.common.memory_monitor_helpers.metrics_reader import (
            PSUTIL_ERRORS,
        )

        assert psutil.Error in PSUTIL_ERRORS

    def test_psutil_errors_includes_os_error(self):
        """Test that PSUTIL_ERRORS includes OSError."""
        from src.common.memory_monitor_helpers.metrics_reader import (
            PSUTIL_ERRORS,
        )

        assert OSError in PSUTIL_ERRORS

    def test_task_query_errors_includes_runtime_error(self):
        """Test that TASK_QUERY_ERRORS includes RuntimeError."""
        from src.common.memory_monitor_helpers.metrics_reader import (
            TASK_QUERY_ERRORS,
        )

        assert RuntimeError in TASK_QUERY_ERRORS

    def test_task_query_errors_includes_value_error(self):
        """Test that TASK_QUERY_ERRORS includes ValueError."""
        from src.common.memory_monitor_helpers.metrics_reader import (
            TASK_QUERY_ERRORS,
        )

        assert ValueError in TASK_QUERY_ERRORS


class TestIntegration:
    """Integration tests for MetricsReader."""

    def test_all_methods_return_non_negative_values_on_error(self, monkeypatch):
        """Test that all methods return non-negative values on error."""
        process = MagicMock()
        process.memory_info.side_effect = psutil.Error("fail")

        def _virtual_memory():
            raise psutil.Error("fail")

        def _raise_loop():
            raise RuntimeError("fail")

        monkeypatch.setattr(psutil, "virtual_memory", _virtual_memory)
        monkeypatch.setattr(asyncio, "get_running_loop", _raise_loop)

        reader = MetricsReader(process)

        assert reader.get_current_memory_usage() >= 0.0
        assert reader.get_system_memory_percent() >= 0.0
        assert reader.get_current_task_count() >= 0

    def test_multiple_method_calls_with_same_reader(self):
        """Test that multiple calls work correctly."""
        process = MagicMock()
        process.memory_info.return_value = SimpleNamespace(rss=1024 * 1024)
        reader = MetricsReader(process)

        result1 = reader.get_current_memory_usage()
        result2 = reader.get_current_memory_usage()

        assert result1 == pytest.approx(1.0)
        assert result2 == pytest.approx(1.0)
        assert process.memory_info.call_count == 2
