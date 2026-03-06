"""Unified console and log output utilities."""

from __future__ import annotations

import contextlib
import logging

import common.time_utils as _time_utils

_LEVEL_MAP: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def _resolve_level(level: str) -> int:
    """Return the logging constant for the given level name string, INFO for unrecognised."""
    resolved = _LEVEL_MAP.get(level.lower())
    if resolved is not None:
        return resolved
    return logging.INFO


def _write_to_handlers(message: str | None) -> bool:
    """Write message to FileHandler instances on the root logger.

    Returns True if at least one file handler was written to successfully.
    Silently skips handlers whose stream raises OSError.
    """
    content = str(message) if message is not None else ""
    any_written = False
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.FileHandler):
            with contextlib.suppress(OSError):
                handler.stream.write(content + "\n")
                handler.stream.flush()
                any_written = True
    return any_written


def _log_message(message: str | None, level: str, logger_name: str | None) -> None:
    """Log message to the named logger (or module logger) at the resolved level."""
    log_level = _resolve_level(level)
    target = logger_name if logger_name is not None else __name__
    logging.getLogger(target).log(log_level, message)


def output(
    message: str | None,
    *,
    level: str = "info",
    headers: bool = False,
    log: bool = True,
    console: bool = True,
    logger_name: str | None = None,
    plain_log: bool = False,
) -> None:
    """Output a message to the console and/or log at the specified level."""
    if plain_log:
        written = _write_to_handlers(message)
        if not written:
            _log_message(message, level, logger_name)
        return

    if console:
        if headers:
            ts = _time_utils.get_current_utc().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{ts} - {level.upper()} - {message}")
        else:
            print(message)

    if log:
        _log_message(message, level, logger_name)


__all__ = ["output"]
