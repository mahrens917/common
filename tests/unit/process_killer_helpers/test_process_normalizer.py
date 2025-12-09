"""Tests for process normalizer."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.common.process_killer_helpers.process_normalizer import normalize_process
from src.common.process_monitor import ProcessInfo


class TestNormalizeProcess:
    """Tests for normalize_process function."""

    def test_normalizes_process_info(self) -> None:
        """Normalizes ProcessInfo object correctly."""
        import time

        info = ProcessInfo(
            pid=123, name="test", cmdline=["python", "-m", "test"], last_seen=time.time()
        )

        result = normalize_process(info, "test_service")

        assert result.pid == 123
        assert result.name == "test"
        assert result.cmdline == ["python", "-m", "test"]

    def test_normalizes_simple_namespace(self) -> None:
        """Normalizes SimpleNamespace object correctly."""
        ns = SimpleNamespace(pid=456, name="service", cmdline=["./run.sh"])

        result = normalize_process(ns, "test_service")

        assert result.pid == 456
        assert result.name == "service"
        assert result.cmdline == ["./run.sh"]

    def test_normalizes_simple_namespace_with_missing_attrs(self) -> None:
        """Handles SimpleNamespace with missing attributes."""
        ns = SimpleNamespace()

        result = normalize_process(ns, "test_service")

        assert result.pid is None
        assert result.name is None
        assert result.cmdline == []

    def test_normalizes_dict(self) -> None:
        """Normalizes dict payload correctly."""
        raw = {"pid": "789", "name": "worker", "cmdline": ["node", "app.js"]}

        result = normalize_process(raw, "test_service")

        assert result.pid == 789
        assert result.name == "worker"
        assert result.cmdline == ["node", "app.js"]

    def test_normalizes_dict_with_none_cmdline(self) -> None:
        """Handles dict with None cmdline."""
        raw = {"pid": "100", "name": "proc", "cmdline": None}

        result = normalize_process(raw, "test_service")

        assert result.cmdline == []

    def test_raises_for_unsupported_type(self) -> None:
        """Raises TypeError for unsupported payload type."""
        with pytest.raises(TypeError, match="Unsupported process payload"):
            normalize_process("invalid", "test_service")

    def test_raises_for_list_type(self) -> None:
        """Raises TypeError for list payload."""
        with pytest.raises(TypeError, match="Unsupported process payload"):
            normalize_process([1, 2, 3], "test_service")
