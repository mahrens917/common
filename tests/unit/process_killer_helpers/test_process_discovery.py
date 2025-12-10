"""Tests for process discovery module."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from common.process_killer_helpers.process_discovery import (
    _console,
    build_matching_processes,
    create_psutil_process,
    import_psutil,
)


class TestConsole:
    """Tests for _console function."""

    def test_prints_when_not_suppressed(self, capsys) -> None:
        """Prints message when suppress_output is False."""
        _console("test message", suppress_output=False)

        captured = capsys.readouterr()
        assert "test message" in captured.out

    def test_does_not_print_when_suppressed(self, capsys) -> None:
        """Does not print when suppress_output is True."""
        _console("test message", suppress_output=True)

        captured = capsys.readouterr()
        assert captured.out == ""


class TestCreatePsutilProcess:
    """Tests for create_psutil_process function."""

    def test_returns_process_on_success(self) -> None:
        """Returns psutil Process on success."""
        mock_process = MagicMock()
        with patch("psutil.Process", return_value=mock_process):
            result = create_psutil_process(123, service_name="test", cmdline=["python"])

        assert result == mock_process

    def test_returns_none_on_no_such_process(self) -> None:
        """Returns None when process doesn't exist."""
        import psutil

        with patch("psutil.Process", side_effect=psutil.NoSuchProcess(123)):
            result = create_psutil_process(123, service_name="test", cmdline=["python"])

        assert result is None

    def test_returns_none_on_access_denied(self) -> None:
        """Returns None when access denied."""
        import psutil

        with patch("psutil.Process", side_effect=psutil.AccessDenied(123)):
            result = create_psutil_process(123, service_name="test", cmdline=["python"])

        assert result is None

    def test_returns_none_on_key_error(self) -> None:
        """Returns None when KeyError occurs."""
        with patch("psutil.Process", side_effect=KeyError("pid")):
            result = create_psutil_process(123, service_name="test", cmdline=["python"])

        assert result is None


class TestBuildMatchingProcesses:
    """Tests for build_matching_processes function."""

    def test_returns_empty_for_no_candidates(self) -> None:
        """Returns empty list when no candidates."""
        result = build_matching_processes(
            [], "test_service", exclude_pid=None, suppress_output=True
        )

        assert result == []

    def test_skips_excluded_pid(self) -> None:
        """Skips process matching excluded PID."""
        candidates = [SimpleNamespace(pid=123, name="python", cmdline=["python", "-m", "test"])]

        result = build_matching_processes(
            candidates, "test_service", exclude_pid=123, suppress_output=True
        )

        assert len(result) == 0

    def test_includes_matching_python_process(self) -> None:
        """Includes process with python in name."""
        candidates = [SimpleNamespace(pid=456, name="python3", cmdline=["python", "-m", "test"])]
        mock_process = MagicMock()
        mock_process.pid = 456

        with patch(
            "common.process_killer_helpers.process_discovery.create_psutil_process",
            return_value=mock_process,
        ):
            result = build_matching_processes(
                candidates, "test_service", exclude_pid=None, suppress_output=True
            )

        assert len(result) == 1
        assert result[0] == mock_process

    def test_skips_non_python_process_when_not_strict(self) -> None:
        """Skips non-python process when strict_python=False."""
        candidates = [SimpleNamespace(pid=456, name="node", cmdline=["node", "app.js"])]
        mock_process = MagicMock()
        mock_process.pid = 456

        with patch(
            "common.process_killer_helpers.process_discovery.create_psutil_process",
            return_value=mock_process,
        ):
            result = build_matching_processes(
                candidates,
                "test_service",
                exclude_pid=None,
                strict_python=False,
                suppress_output=True,
            )

        assert len(result) == 0

    def test_raises_for_non_python_when_strict(self) -> None:
        """Raises RuntimeError for non-python process when strict_python=True."""
        candidates = [SimpleNamespace(pid=456, name="node", cmdline=["node", "app.js"])]
        mock_process = MagicMock()
        mock_process.pid = 456

        with patch(
            "common.process_killer_helpers.process_discovery.create_psutil_process",
            return_value=mock_process,
        ):
            with pytest.raises(RuntimeError, match="Unexpected executable"):
                build_matching_processes(
                    candidates,
                    "test_service",
                    exclude_pid=None,
                    strict_python=True,
                    suppress_output=True,
                )

    def test_skips_process_when_psutil_returns_none(self) -> None:
        """Skips process when create_psutil_process returns None."""
        candidates = [SimpleNamespace(pid=456, name="python", cmdline=["python"])]

        with patch(
            "common.process_killer_helpers.process_discovery.create_psutil_process",
            return_value=None,
        ):
            result = build_matching_processes(
                candidates, "test_service", exclude_pid=None, suppress_output=True
            )

        assert len(result) == 0


class TestImportPsutil:
    """Tests for import_psutil function."""

    def test_returns_psutil_module(self) -> None:
        """Returns psutil module when available."""
        result = import_psutil("test_service")

        import psutil

        assert result is psutil

    def test_raises_runtime_error_when_psutil_unavailable(self) -> None:
        """Raises RuntimeError when psutil not available."""
        with patch.dict("sys.modules", {"psutil": None}):
            with patch("builtins.__import__", side_effect=ImportError("No psutil")):
                with pytest.raises(RuntimeError, match="psutil is required"):
                    import_psutil("test_service")
