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


def _close_and_remove_handlers(logger: logging.Logger) -> None:
    """Close and remove all handlers from a logger."""
    for handler in list(logger.handlers):
        try:
            handler.close()
        except OSError:
            pass
        logger.removeHandler(handler)


@pytest.fixture
def logging_module(monkeypatch):
    from common import logging_config

    importlib.reload(logging_config)

    root = logging.getLogger()
    _close_and_remove_handlers(root)

    yield logging_config

    root = logging.getLogger()
    _close_and_remove_handlers(root)


def _set_fake_project_root(monkeypatch, tmp_path: Path) -> Path:
    """Change cwd to a temp directory so logs stay isolated."""
    fake_root = tmp_path / "project_root"
    fake_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(fake_root)
    return fake_root


class TestConsoleHandler:
    """Tests for console handler configuration."""

    def test_console_debug_when_standalone(self, logging_module, monkeypatch, tmp_path):
        _set_fake_project_root(monkeypatch, tmp_path)
        monkeypatch.delenv("MANAGED_BY_MONITOR", raising=False)

        monkeypatch.setattr(logging_module.logging, "FileHandler", DummyFileHandler)

        logging_module.setup_logging("kalshi")

        root = logging.getLogger()
        console_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, DummyFileHandler)]
        assert len(console_handlers) == 1
        console = console_handlers[0]
        assert console.stream is sys.stdout
        assert console.level == logging.DEBUG

    def test_console_info_when_managed(self, logging_module, monkeypatch, tmp_path):
        _set_fake_project_root(monkeypatch, tmp_path)
        monkeypatch.setenv("MANAGED_BY_MONITOR", "1")

        class RecordingStreamHandler(logging.StreamHandler):
            instances: list[RecordingStreamHandler] = []

            def __init__(self, stream=None):
                super().__init__(stream)
                RecordingStreamHandler.instances.append(self)

        monkeypatch.setattr(logging_module.logging, "StreamHandler", RecordingStreamHandler)

        logging_module.setup_logging()

        console = RecordingStreamHandler.instances[-1]
        assert console.level == logging.INFO


class TestFileHandler:
    """Tests for file handler configuration."""

    def test_file_handler_created_with_write_mode(self, logging_module, monkeypatch, tmp_path):
        fake_root = _set_fake_project_root(monkeypatch, tmp_path)
        monkeypatch.delenv("MANAGED_BY_MONITOR", raising=False)

        class RecordingFileHandler(DummyFileHandler):
            instances: list[RecordingFileHandler] = []

            def __init__(self, filename, mode="a", encoding=None, delay=False):
                super().__init__(filename, mode, encoding, delay)
                RecordingFileHandler.instances.append(self)

        monkeypatch.setattr(logging_module.logging, "FileHandler", RecordingFileHandler)

        logging_module.setup_logging(service_name="kalshi")

        file_handler = RecordingFileHandler.instances[-1]
        assert file_handler.mode == "w"
        assert file_handler.baseFilename.endswith("kalshi.log")
        assert (fake_root / "logs").exists()

    def test_file_handler_skipped_when_managed(self, logging_module, monkeypatch, tmp_path):
        _set_fake_project_root(monkeypatch, tmp_path)
        monkeypatch.setenv("MANAGED_BY_MONITOR", "1")

        logging_module.setup_logging(service_name="kalshi")

        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert file_handlers == []

    def test_file_handler_skipped_when_no_service_name(self, logging_module, monkeypatch, tmp_path):
        _set_fake_project_root(monkeypatch, tmp_path)
        monkeypatch.delenv("MANAGED_BY_MONITOR", raising=False)

        logging_module.setup_logging()

        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert file_handlers == []


class TestThirdPartySuppression:
    """Tests for noisy third-party logger suppression."""

    def test_third_party_loggers_set_to_warning(self, logging_module, monkeypatch, tmp_path):
        _set_fake_project_root(monkeypatch, tmp_path)
        monkeypatch.delenv("MANAGED_BY_MONITOR", raising=False)

        logging_module.setup_logging()

        for name in ("urllib3", "asyncio", "websockets", "aiohttp", "redis", "matplotlib", "PIL"):
            assert logging.getLogger(name).level == logging.WARNING


class TestHandlerReset:
    """Tests for handler reset on reconfiguration."""

    def test_child_logger_handlers_reset(self, logging_module, monkeypatch, tmp_path):
        _set_fake_project_root(monkeypatch, tmp_path)
        monkeypatch.delenv("MANAGED_BY_MONITOR", raising=False)

        child_logger = logging.getLogger("test.child.reset")
        child_logger.addHandler(logging.NullHandler())
        child_logger.propagate = False

        logging_module.setup_logging(service_name="kalshi")

        assert child_logger.handlers == []
        assert child_logger.propagate is True


class TestCloseHandlers:
    """Tests for _close_handlers error handling."""

    def test_handles_oserror_during_close(self, logging_module):
        from unittest.mock import MagicMock

        mock_handler = MagicMock()
        mock_handler.close.side_effect = OSError("Close failed")

        test_logger = logging.getLogger("test_close_error_v2")
        test_logger.handlers = [mock_handler]

        logging_module._close_handlers(test_logger, "test_close_error_v2")

        mock_handler.close.assert_called_once()
