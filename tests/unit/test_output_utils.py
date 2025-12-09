import logging
from datetime import datetime
from pathlib import Path

import pytest

from src.common import output_utils


def _set_root_handlers(root_logger: logging.Logger, handlers: list[logging.Handler]) -> None:
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    for handler in handlers:
        root_logger.addHandler(handler)


def test_output_console_with_headers(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "src.common.time_utils.get_current_utc", lambda: datetime(2024, 1, 2, 3, 4, 5), raising=True
    )

    output_utils.output("test message", level="warning", headers=True, log=False)

    captured = capsys.readouterr()
    assert captured.out == "2024-01-02 03:04:05 - WARNING - test message\n"
    assert captured.err == ""


def test_output_log_only_uses_specified_logger(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR, logger="custom.logger"):
        output_utils.output(
            "log message", level="error", console=False, logger_name="custom.logger"
        )

    assert ("custom.logger", logging.ERROR, "log message") in caplog.record_tuples


def test_output_plain_log_writes_to_file_handler(tmp_path: Path) -> None:
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    _set_root_handlers(root_logger, [])

    log_path = tmp_path / "plain.log"
    file_handler = logging.FileHandler(log_path)
    root_logger.addHandler(file_handler)
    try:
        output_utils.output("plain message", console=False, plain_log=True)
    finally:
        root_logger.removeHandler(file_handler)
        file_handler.close()
        _set_root_handlers(root_logger, original_handlers)

    assert log_path.read_text() == "plain message\n"


def test_output_plain_log_with_none_message(tmp_path: Path) -> None:
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    _set_root_handlers(root_logger, [])

    log_path = tmp_path / "plain_none.log"
    file_handler = logging.FileHandler(log_path)
    root_logger.addHandler(file_handler)
    try:
        output_utils.output(None, console=False, plain_log=True)
    finally:
        root_logger.removeHandler(file_handler)
        file_handler.close()
        _set_root_handlers(root_logger, original_handlers)

    assert log_path.read_text() == "\n"


def test_output_plain_log_writes_without_file_handlers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    root_logger = logging.getLogger()
    file_handlers = [
        handler for handler in root_logger.handlers if isinstance(handler, logging.FileHandler)
    ]
    for handler in file_handlers:
        root_logger.removeHandler(handler)

    original_level = root_logger.level
    with caplog.at_level(logging.DEBUG):
        output_utils.output(
            "secondary message",
            level="debug",
            console=False,
            plain_log=True,
            logger_name="test.logger",
        )

    for handler in file_handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(original_level)

    assert ("test.logger", logging.DEBUG, "secondary message") in caplog.record_tuples


def test_output_plain_log_handles_write_failure(tmp_path: Path) -> None:
    class BrokenStream:
        def write(self, _):
            raise OSError("cannot write")

        def flush(self):
            pass

        def close(self):
            pass

    class ListHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records: list[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    _set_root_handlers(root_logger, [])

    handler = logging.FileHandler(tmp_path / "broken.log")
    original_stream = handler.stream  # Save the original stream to close later
    handler.stream = BrokenStream()  # type: ignore[assignment]
    root_logger.addHandler(handler)

    logger = logging.getLogger("plain.degraded")
    previous_propagate = logger.propagate
    logger.propagate = False
    capture_handler = ListHandler()
    logger.addHandler(capture_handler)
    logger.setLevel(logging.INFO)

    try:
        output_utils.output(
            "broken",
            level="info",
            console=False,
            plain_log=True,
            logger_name="plain.degraded",
        )
    finally:
        logger.removeHandler(capture_handler)
        logger.propagate = previous_propagate
        root_logger.removeHandler(handler)
        handler.close()
        original_stream.close()  # Close the original file stream we replaced
        _set_root_handlers(root_logger, original_handlers)

    assert any(record.getMessage() == "broken" for record in capture_handler.records)


def test_output_with_unknown_level_defaults_to_info(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger=__name__):
        output_utils.output(
            "unknown level", level="not-a-level", console=False, logger_name=__name__
        )

    assert (__name__, logging.INFO, "unknown level") in caplog.record_tuples
