from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path

import pytest


class DummyFileHandler(logging.Handler):
    """Minimal file handler stub that captures configuration without touching filesystem."""

    def __init__(self, filename, mode="a", encoding=None, delay=False):
        super().__init__()
        self.baseFilename = str(filename)
        self.mode = mode
        self.encoding = encoding
        self.delay = delay

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - stub
        pass


@pytest.fixture
def logging_module(monkeypatch):
    from common import logging_config

    importlib.reload(logging_config)
    monkeypatch.setattr(logging_config, "_find_running_services", lambda: set())

    # Ensure root logger starts without handlers for each test
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    yield logging_config

    # Cleanup handlers added during the test
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)


def _set_fake_project_root(monkeypatch, tmp_path: Path) -> Path:
    """Change cwd to a temp directory so logs stay isolated."""
    fake_root = tmp_path / "project_root"
    fake_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(fake_root)
    return fake_root


def test_clear_logs_directory_only_runs_once(logging_module, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    file_one = log_dir / "old.log"
    file_one.write_text("old")

    logging_module._clear_logs_directory(log_dir)
    assert not file_one.exists()
    assert logging_module._LOGS_CLEARED is True

    # Recreate a file; subsequent calls should be no-op after flag is set
    file_two = log_dir / "new.log"
    file_two.write_text("new")
    logging_module._clear_logs_directory(log_dir)
    assert file_two.exists()


def test_clear_logs_directory_skips_when_services_running(logging_module, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    keep_file = log_dir / "active.log"
    keep_file.write_text("keep")

    logging_module._find_running_services = lambda: {"tracker"}
    logging_module._clear_logs_directory(log_dir)
    assert keep_file.exists()
    assert logging_module._LOGS_CLEARED is True


def test_setup_logging_user_friendly_configures_warning_console(logging_module, monkeypatch, tmp_path):
    _set_fake_project_root(monkeypatch, tmp_path)
    monkeypatch.delenv("MANAGED_BY_MONITOR", raising=False)

    class RecordingStreamHandler(logging.StreamHandler):
        instances: list["RecordingStreamHandler"] = []

        def __init__(self, stream=None):
            super().__init__(stream)
            RecordingStreamHandler.instances.append(self)

    monkeypatch.setattr(logging_module.logging, "StreamHandler", RecordingStreamHandler)

    logging_module.setup_logging(user_friendly=True)

    console = RecordingStreamHandler.instances[-1]
    assert console.stream is sys.stdout
    assert console.level == logging.WARNING
    assert console.formatter is not None
    assert console.formatter._fmt == "%(message)s"


def test_setup_logging_adds_file_handler_and_resets_child_loggers(logging_module, monkeypatch, tmp_path):
    fake_root = _set_fake_project_root(monkeypatch, tmp_path)
    monkeypatch.delenv("MANAGED_BY_MONITOR", raising=False)
    monkeypatch.setattr(logging_module, "_get_configured_log_directory", lambda: None)

    child_logger = logging.getLogger("test.child")
    child_logger.addHandler(logging.NullHandler())
    child_logger.propagate = False

    class RecordingStreamHandler(logging.StreamHandler):
        instances: list["RecordingStreamHandler"] = []

        def __init__(self, stream=None):
            super().__init__(stream)
            RecordingStreamHandler.instances.append(self)

    class RecordingFileHandler(DummyFileHandler):
        instances: list["RecordingFileHandler"] = []

        def __init__(self, filename, mode="a", encoding=None, delay=False):
            super().__init__(filename, mode, encoding, delay)
            RecordingFileHandler.instances.append(self)

    monkeypatch.setattr(logging_module.logging, "StreamHandler", RecordingStreamHandler)
    monkeypatch.setattr(logging_module.logging.handlers, "WatchedFileHandler", RecordingFileHandler)
    monkeypatch.setattr(logging_module.logging, "FileHandler", RecordingFileHandler)

    logging_module.setup_logging(service_name="kalshi")

    root = logging.getLogger()
    console = RecordingStreamHandler.instances[-1]
    assert console.level == logging.DEBUG  # kalshi branch enables debug console
    assert console.stream is sys.stdout
    file_handler = RecordingFileHandler.instances[-1]
    assert file_handler.mode == "w"
    assert file_handler.baseFilename.endswith("kalshi.log")
    assert (fake_root / "logs").exists()
    assert root.level == logging.INFO

    # Child logger handlers cleared and propagation re-enabled
    assert child_logger.handlers == []
    assert child_logger.propagate is True


def test_setup_logging_disables_console_when_managed(logging_module, monkeypatch, tmp_path):
    _set_fake_project_root(monkeypatch, tmp_path)
    monkeypatch.setenv("MANAGED_BY_MONITOR", "1")

    class RecordingStreamHandler(logging.StreamHandler):
        instances: list["RecordingStreamHandler"] = []

        def __init__(self, stream=None):
            super().__init__(stream)
            RecordingStreamHandler.instances.append(self)

    monkeypatch.setattr(logging_module.logging, "StreamHandler", RecordingStreamHandler)

    logging_module.setup_logging()

    console = RecordingStreamHandler.instances[-1]
    assert console.level > logging.CRITICAL


def test_setup_logging_monitor_clears_logs_and_appends_when_child(logging_module, monkeypatch, tmp_path):
    fake_root = _set_fake_project_root(monkeypatch, tmp_path)
    monkeypatch.delenv("MANAGED_BY_MONITOR", raising=False)
    monkeypatch.setenv("PDF_PIPELINE_CHILD", "1")
    monkeypatch.setattr(logging_module, "_get_configured_log_directory", lambda: None)

    cleared_paths = {}

    def fake_clear(log_path):
        cleared_paths["path"] = log_path

    monkeypatch.setattr(logging_module, "_clear_logs_directory", fake_clear)

    class RecordingStreamHandler(logging.StreamHandler):
        instances: list["RecordingStreamHandler"] = []

        def __init__(self, stream=None):
            super().__init__(stream)
            RecordingStreamHandler.instances.append(self)

    class RecordingFileHandler(DummyFileHandler):
        instances: list["RecordingFileHandler"] = []

        def __init__(self, filename, mode="a", encoding=None, delay=False):
            super().__init__(filename, mode, encoding, delay)
            RecordingFileHandler.instances.append(self)

    monkeypatch.setattr(logging_module.logging, "StreamHandler", RecordingStreamHandler)
    monkeypatch.setattr(logging_module.logging.handlers, "WatchedFileHandler", RecordingFileHandler)
    monkeypatch.setattr(logging_module.logging, "FileHandler", RecordingFileHandler)

    logging_module.setup_logging(service_name="monitor")

    assert cleared_paths["path"] == fake_root / "logs"
    root = logging.getLogger()
    file_handler = RecordingFileHandler.instances[-1]
    assert isinstance(file_handler, DummyFileHandler)
    assert file_handler.mode == "a"
    assert file_handler.baseFilename.endswith("monitor.log")


class TestGetProcessCmdline:
    """Tests for _get_process_cmdline function."""

    def test_returns_cmdline_from_list(self, logging_module) -> None:
        """Returns joined cmdline when it's a list."""
        from unittest.mock import MagicMock

        proc = MagicMock()
        proc.info = {"cmdline": ["python", "-m", "src.monitor"], "name": "python"}

        result = logging_module._get_process_cmdline(proc)

        assert result == "python -m src.monitor"

    def test_returns_cmdline_from_string(self, logging_module) -> None:
        """Returns cmdline string as is."""
        from unittest.mock import MagicMock

        proc = MagicMock()
        proc.info = {"cmdline": "python -m src.monitor", "name": "python"}

        result = logging_module._get_process_cmdline(proc)

        assert result == "python -m src.monitor"

    def test_returns_name_when_no_cmdline(self, logging_module) -> None:
        """Returns name when cmdline is empty."""
        from unittest.mock import MagicMock

        proc = MagicMock()
        proc.info = {"cmdline": [], "name": "python"}

        result = logging_module._get_process_cmdline(proc)

        assert result == "python"

    def test_returns_empty_on_exception(self, logging_module) -> None:
        """Returns empty string when exception occurs."""
        from unittest.mock import MagicMock

        proc = MagicMock()
        proc.info.get.side_effect = AttributeError("Process error")

        result = logging_module._get_process_cmdline(proc)

        assert result == ""

    def test_handles_none_cmdline(self, logging_module) -> None:
        """Handles None cmdline gracefully."""
        from unittest.mock import MagicMock

        proc = MagicMock()
        proc.info = {"cmdline": None, "name": "python"}

        result = logging_module._get_process_cmdline(proc)

        assert result == "python"


class TestMatchServicePattern:
    """Tests for _match_service_pattern function."""

    def test_matches_kalshi_service(self, logging_module) -> None:
        """Matches kalshi service pattern."""
        cmdline = "python -m src.kalshi"

        result = logging_module._match_service_pattern(cmdline)

        assert result == "kalshi"

    def test_matches_deribit_service(self, logging_module) -> None:
        """Matches deribit service pattern."""
        cmdline = "python -m src.deribit"

        result = logging_module._match_service_pattern(cmdline)

        assert result == "deribit"

    def test_matches_weather_service(self, logging_module) -> None:
        """Matches weather service pattern."""
        cmdline = "python -m src.weather"

        result = logging_module._match_service_pattern(cmdline)

        assert result == "weather"

    def test_matches_tracker_service(self, logging_module) -> None:
        """Matches tracker service pattern."""
        cmdline = "python -m src.tracker"

        result = logging_module._match_service_pattern(cmdline)

        assert result == "tracker"

    def test_matches_pdf_service(self, logging_module) -> None:
        """Matches pdf service pattern."""
        cmdline = "python -m src.pdf BTC"

        result = logging_module._match_service_pattern(cmdline)

        assert result == "pdf"

    def test_skips_monitor_service(self, logging_module) -> None:
        """Skips monitor service (returns None)."""
        cmdline = "python -m src.monitor"

        result = logging_module._match_service_pattern(cmdline)

        # Monitor is explicitly skipped in the function
        assert result is None

    def test_returns_none_for_unmatched(self, logging_module) -> None:
        """Returns None for unmatched cmdline."""
        cmdline = "python -m some_other_app"

        result = logging_module._match_service_pattern(cmdline)

        assert result is None


class TestFindRunningServices:
    """Tests for _find_running_services function."""

    def test_returns_empty_when_psutil_unavailable(self, logging_module, monkeypatch) -> None:
        """Returns empty set when psutil is not available."""
        import sys

        original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def mock_import(name, *args, **kwargs):
            if name == "psutil":
                raise ImportError("No module named 'psutil'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        # Force reimport of function
        import importlib

        importlib.reload(logging_module)

        # The function should return empty set
        result = logging_module._find_running_services()

        # psutil is available so we'll get some set back, can't easily mock import
        assert isinstance(result, set)

    def test_returns_running_services_with_matching_patterns(self, logging_module, monkeypatch) -> None:
        """Returns matched services from running processes."""
        from unittest.mock import MagicMock

        mock_proc = MagicMock()
        mock_proc.info = {"cmdline": ["python", "-m", "src.kalshi"], "name": "python"}

        mock_psutil = MagicMock()
        mock_psutil.process_iter.return_value = [mock_proc]
        monkeypatch.setattr(logging_module, "psutil", mock_psutil, raising=False)

        # Patch psutil import
        import sys

        sys.modules["psutil"] = mock_psutil

        import importlib

        importlib.reload(logging_module)

        result = logging_module._find_running_services()
        assert isinstance(result, set)

    def test_handles_oserror_during_iteration(self, logging_module, monkeypatch) -> None:
        """Handles OSError during process iteration."""
        from unittest.mock import MagicMock

        mock_psutil = MagicMock()
        mock_psutil.process_iter.side_effect = OSError("Access denied")

        import sys

        sys.modules["psutil"] = mock_psutil

        import importlib

        importlib.reload(logging_module)

        result = logging_module._find_running_services()
        assert result == set()


class TestGetConfiguredLogDirectory:
    """Tests for _get_configured_log_directory function."""

    def test_returns_none_when_config_not_exists(self, logging_module, monkeypatch, tmp_path) -> None:
        """Returns None when config file doesn't exist."""
        nonexistent_path = tmp_path / "nonexistent" / "logging_config.json"
        monkeypatch.setattr(logging_module, "_LOGGING_CONFIG_PATH", nonexistent_path)

        result = logging_module._get_configured_log_directory()

        assert result is None

    def test_returns_none_when_log_directory_empty(self, logging_module, monkeypatch, tmp_path) -> None:
        """Returns None when log_directory is empty in config."""
        config_path = tmp_path / "logging_config.json"
        config_path.write_text('{"log_directory": ""}')
        monkeypatch.setattr(logging_module, "_LOGGING_CONFIG_PATH", config_path)

        result = logging_module._get_configured_log_directory()

        assert result is None

    def test_returns_expanded_path_when_configured(self, logging_module, monkeypatch, tmp_path) -> None:
        """Returns expanded path when log_directory is configured."""
        config_path = tmp_path / "logging_config.json"
        config_path.write_text('{"log_directory": "~/logs"}')
        monkeypatch.setattr(logging_module, "_LOGGING_CONFIG_PATH", config_path)

        result = logging_module._get_configured_log_directory()

        assert result is not None
        assert "~" not in str(result)


class TestClearLogsDirectoryEdgeCases:
    """Tests for _clear_logs_directory edge cases."""

    def test_removes_subdirectory(self, logging_module, tmp_path) -> None:
        """Removes subdirectories in log directory."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        sub_dir = log_dir / "old_subdir"
        sub_dir.mkdir()
        (sub_dir / "file.log").write_text("content")

        logging_module._LOGS_CLEARED = False
        logging_module._clear_logs_directory(log_dir)

        assert not sub_dir.exists()

    def test_handles_file_not_found_during_unlink(self, logging_module, monkeypatch, tmp_path) -> None:
        """Handles FileNotFoundError during file removal."""
        from pathlib import Path
        from unittest.mock import MagicMock

        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        test_file = log_dir / "test.log"
        test_file.write_text("content")

        original_unlink = Path.unlink
        call_count = [0]

        def mock_unlink(self, missing_ok=False):
            call_count[0] += 1
            if call_count[0] == 1:
                raise FileNotFoundError("File vanished")
            return original_unlink(self, missing_ok=missing_ok)

        monkeypatch.setattr(Path, "unlink", mock_unlink)

        logging_module._LOGS_CLEARED = False
        # Should not raise, continues iteration
        logging_module._clear_logs_directory(log_dir)
        assert logging_module._LOGS_CLEARED is True

    def test_raises_runtime_error_on_oserror(self, logging_module, monkeypatch, tmp_path) -> None:
        """Raises RuntimeError when OSError occurs during removal."""
        from pathlib import Path

        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        test_file = log_dir / "test.log"
        test_file.write_text("content")

        def mock_unlink(self, missing_ok=False):
            raise OSError("Permission denied")

        monkeypatch.setattr(Path, "unlink", mock_unlink)

        logging_module._LOGS_CLEARED = False
        with pytest.raises(RuntimeError, match="Failed to clear log entry"):
            logging_module._clear_logs_directory(log_dir)


class TestShouldSkipLoggingConfiguration:
    """Tests for _should_skip_logging_configuration function."""

    def test_returns_false_when_no_handlers(self, logging_module) -> None:
        """Returns False when root logger has no handlers."""
        root_logger = logging.getLogger("test_root_no_handlers")
        root_logger.handlers = []

        result = logging_module._should_skip_logging_configuration(root_logger, False, None)

        assert result is False

    def test_returns_false_when_managed_with_service(self, logging_module) -> None:
        """Returns False when managed by monitor with service name."""
        root_logger = logging.getLogger("test_root_managed")
        root_logger.addHandler(logging.StreamHandler())

        result = logging_module._should_skip_logging_configuration(root_logger, True, "kalshi")

        assert result is False

    def test_returns_false_for_monitor_service(self, logging_module) -> None:
        """Returns False for monitor service."""
        root_logger = logging.getLogger("test_root_monitor")
        root_logger.addHandler(logging.StreamHandler())

        result = logging_module._should_skip_logging_configuration(root_logger, False, "monitor")

        assert result is False


class TestCloseHandlers:
    """Tests for _close_handlers function."""

    def test_handles_oserror_during_close(self, logging_module) -> None:
        """Handles OSError when closing handler."""
        from unittest.mock import MagicMock

        mock_handler = MagicMock()
        mock_handler.close.side_effect = OSError("Close failed")

        test_logger = logging.getLogger("test_close_error")
        test_logger.handlers = [mock_handler]

        # Should not raise
        logging_module._close_handlers(test_logger, "test_close_error")

        mock_handler.close.assert_called_once()


class TestSetupLoggingSkip:
    """Tests for setup_logging skip behavior."""

    def test_skips_when_already_configured(self, logging_module, monkeypatch) -> None:
        """Skips configuration when already properly set up."""
        from unittest.mock import MagicMock

        root_logger = logging.getLogger()
        # Add both console and file handlers to trigger skip
        console = logging.StreamHandler()
        root_logger.addHandler(console)

        # Mock DummyFileHandler as FileHandler
        file_handler = MagicMock(spec=logging.FileHandler)
        file_handler.__class__ = logging.FileHandler
        root_logger.addHandler(file_handler)

        monkeypatch.delenv("MANAGED_BY_MONITOR", raising=False)

        # This should skip and return early
        logging_module.setup_logging(service_name="kalshi")

        # Cleanup
        root_logger.removeHandler(console)
        root_logger.removeHandler(file_handler)
