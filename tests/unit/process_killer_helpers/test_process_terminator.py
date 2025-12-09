"""Tests for process terminator module."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.process_killer_helpers.process_terminator import (
    _create_psutil_process_safe,
    _validate_process_executable,
    terminate_matching_processes,
    validate_process_candidates,
)


class TestTerminateMatchingProcesses:
    """Tests for terminate_matching_processes function."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_processes(self) -> None:
        """Returns empty list when no processes to terminate."""
        result = await terminate_matching_processes(
            [],
            service_name="test",
            graceful_timeout=5.0,
            force_timeout=3.0,
            console_output_func=MagicMock(),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_terminates_single_process(self) -> None:
        """Terminates a single process successfully."""
        mock_proc = MagicMock()
        mock_proc.pid = 123
        mock_proc.terminate = MagicMock()
        mock_proc.wait = MagicMock()

        result = await terminate_matching_processes(
            [mock_proc],
            service_name="test",
            graceful_timeout=5.0,
            force_timeout=3.0,
            console_output_func=MagicMock(),
        )

        assert result == [123]
        mock_proc.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_no_such_process(self) -> None:
        """Handles NoSuchProcess exception gracefully."""
        import psutil

        mock_proc = MagicMock()
        mock_proc.pid = 123
        mock_proc.terminate = MagicMock(side_effect=psutil.NoSuchProcess(123))

        result = await terminate_matching_processes(
            [mock_proc],
            service_name="test",
            graceful_timeout=5.0,
            force_timeout=3.0,
            console_output_func=MagicMock(),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_raises_on_access_denied(self) -> None:
        """Raises RuntimeError on AccessDenied."""
        import psutil

        mock_proc = MagicMock()
        mock_proc.pid = 123
        mock_proc.terminate = MagicMock(side_effect=psutil.AccessDenied(123))

        with pytest.raises(RuntimeError, match="Access denied"):
            await terminate_matching_processes(
                [mock_proc],
                service_name="test",
                graceful_timeout=5.0,
                force_timeout=3.0,
                console_output_func=MagicMock(),
            )


class TestValidateProcessCandidates:
    """Tests for validate_process_candidates function."""

    def test_returns_empty_for_no_candidates(self) -> None:
        """Returns empty list when no candidates."""
        result = validate_process_candidates([], service_name="test")

        assert result == []

    def test_validates_python_process(self) -> None:
        """Validates a Python process successfully."""
        candidates = [SimpleNamespace(pid=123, name="python3", cmdline=["python", "-m", "test"])]
        mock_process = MagicMock()

        with patch(
            "src.common.process_killer_helpers.process_terminator._create_psutil_process_safe",
            return_value=mock_process,
        ):
            result = validate_process_candidates(candidates, service_name="test")

        assert len(result) == 1

    def test_skips_process_when_create_returns_none(self) -> None:
        """Skips process when _create_psutil_process_safe returns None."""
        candidates = [SimpleNamespace(pid=123, name="python", cmdline=["python"])]

        with patch(
            "src.common.process_killer_helpers.process_terminator._create_psutil_process_safe",
            return_value=None,
        ):
            result = validate_process_candidates(candidates, service_name="test")

        assert len(result) == 0


class TestCreatePsutilProcessSafe:
    """Tests for _create_psutil_process_safe function."""

    def test_returns_process_on_success(self) -> None:
        """Returns psutil Process on success."""
        mock_process = MagicMock()
        with patch("psutil.Process", return_value=mock_process):
            result = _create_psutil_process_safe(123, service_name="test", cmdline=["python"])

        assert result == mock_process

    def test_returns_none_on_no_such_process(self) -> None:
        """Returns None when process doesn't exist."""
        import psutil

        with patch("psutil.Process", side_effect=psutil.NoSuchProcess(123)):
            result = _create_psutil_process_safe(123, service_name="test", cmdline=["python"])

        assert result is None

    def test_raises_on_access_denied(self) -> None:
        """Raises RuntimeError on AccessDenied."""
        import psutil

        with patch("psutil.Process", side_effect=psutil.AccessDenied(123)):
            with pytest.raises(RuntimeError, match="Access denied"):
                _create_psutil_process_safe(123, service_name="test", cmdline=["python"])


class TestValidateProcessExecutable:
    """Tests for _validate_process_executable function."""

    def test_passes_for_python_process(self) -> None:
        """Passes for process with python in name."""
        process_info = SimpleNamespace(pid=123, name="python3")

        _validate_process_executable(process_info, "test")  # Should not raise

    def test_passes_for_none_name(self) -> None:
        """Passes for process with None name."""
        process_info = SimpleNamespace(pid=123, name=None)

        _validate_process_executable(process_info, "test")  # Should not raise

    def test_raises_for_non_python_executable(self) -> None:
        """Raises RuntimeError for non-python executable."""
        process_info = SimpleNamespace(pid=123, name="node")

        with pytest.raises(RuntimeError, match="Unexpected executable"):
            _validate_process_executable(process_info, "test")
