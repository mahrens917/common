"""
Centralized logging configuration for all services.

This module provides a single setup_logging function that configures
logging consistently across all services with:
- Console output (configurable level based on service)
- File output to logs/{service_name}.log
- Fresh log file on each service start (no append, no rotation)
- User-friendly mode for tracker output
"""

import json
import logging
import logging.handlers
import os
import shutil
import sys
import threading
from pathlib import Path
from typing import Any, Optional, Set

from common.config import env_bool
from common.process_killer import SERVICE_PROCESS_PATTERNS
from common.truthy import pick_truthy

# Thread-safe lock for logging configuration
_config_lock = threading.Lock()
_LOGS_CLEARED = False
_MODULE_LOGGER = logging.getLogger(__name__)
_UNKNOWN_LOGGER_NAME = "<unknown>"
_LOGGING_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "logging_config.json"


def _get_configured_log_directory() -> Optional[Path]:
    """Load log directory from logging_config.json if available."""
    if not _LOGGING_CONFIG_PATH.exists():
        return None
    with _LOGGING_CONFIG_PATH.open() as f:
        config = json.load(f)
    log_dir = config.get("log_directory")
    if not log_dir:
        return None
    return Path(log_dir).expanduser()


def _get_process_cmdline(proc: Any) -> str:
    """Extract command line string from process."""
    try:
        cmdline = pick_truthy(proc.info.get("cmdline"), [])
        name = pick_truthy(proc.info.get("name"), "")
    except (AttributeError, OSError, KeyError, TypeError):  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
        _MODULE_LOGGER.debug("Best-effort cleanup operation")
        return ""

    cmdline_str = " ".join(cmdline) if isinstance(cmdline, list) else str(cmdline)
    if not cmdline_str and name:
        cmdline_str = str(name)
    return cmdline_str


def _match_service_pattern(cmdline_str: str) -> Optional[str]:
    """Match command line against service patterns, return matched service name."""
    for service_name, patterns in SERVICE_PROCESS_PATTERNS.items():
        if service_name == "monitor":
            continue
        if any(pattern in cmdline_str for pattern in patterns):
            return service_name
    return None


def _find_running_services() -> Set[str]:
    """Return a set of running services that are already active on the host."""

    try:
        import psutil
    except ImportError:  # Optional module not available  # policy_guard: allow-silent-handler
        _MODULE_LOGGER.debug("psutil unavailable; skipping running service detection")
        return set()

    running_services: Set[str] = set()
    try:
        for proc in psutil.process_iter(["cmdline", "name"]):
            cmdline_str = _get_process_cmdline(proc)
            if not cmdline_str:
                continue

            matched_service = _match_service_pattern(cmdline_str)
            if matched_service:
                running_services.add(matched_service)
    except OSError as exc:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
        _MODULE_LOGGER.debug("Failed to detect running services during log cleanup: %s", exc)

    return running_services


def _remove_log_entry(entry: Path) -> None:
    """Remove a single log entry (file or directory)."""
    try:
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    except FileNotFoundError as exc:  # Expected exception in loop, continuing iteration  # policy_guard: allow-silent-handler
        # File was removed between listdir and unlink - expected race condition
        _MODULE_LOGGER.debug("Log entry disappeared during cleanup: %s", exc)
    except OSError as exc:
        raise RuntimeError(f"Failed to clear log entry {entry}") from exc


def _clear_log_entries(log_dir: Path) -> None:
    """Clear all log entries except monitor.log."""
    monitor_log = log_dir / "monitor.log"
    for entry in log_dir.iterdir():
        if entry == monitor_log:
            # Skip monitor.log; the file handler truncates it in-place,
            # preserving the inode so tail -f keeps working.
            continue
        _remove_log_entry(entry)


def _clear_logs_directory(log_dir: Path) -> None:
    """Remove all existing log files to ensure a clean monitor startup."""
    global _LOGS_CLEARED

    if _LOGS_CLEARED:
        return

    active_services = _find_running_services()
    if active_services:
        _MODULE_LOGGER.warning("Skipping log cleanup; services still running: %s", ", ".join(sorted(active_services)))
        _LOGS_CLEARED = True
        return

    if log_dir.exists():
        _clear_log_entries(log_dir)

    _LOGS_CLEARED = True


def _should_skip_logging_configuration(root_logger: logging.Logger, managed_by_monitor: bool, service_name: Optional[str]) -> bool:
    if not root_logger.handlers:
        return False
    if managed_by_monitor and service_name:
        return False
    if service_name == "monitor":
        return False

    has_console = any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler) for handler in root_logger.handlers
    )
    if not service_name:
        has_file = True
    else:
        has_file = any(isinstance(handler, logging.FileHandler) for handler in root_logger.handlers)
    return has_console and has_file


def _close_handlers(logger: logging.Logger, logger_name: Optional[str] = None) -> None:
    """Close all handlers for a logger, logging any errors."""
    for handler in list(logger.handlers):
        try:
            handler.close()
        except OSError as e:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
            safe_name = logger_name if logger_name else _UNKNOWN_LOGGER_NAME
            _MODULE_LOGGER.debug("Handler close failed for logger '%s': %s", safe_name, e)


def _reset_handlers(root_logger: logging.Logger) -> None:
    """Reset handlers for all loggers in the system."""
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        try:
            target_logger = logging.getLogger(logger_name)
            _close_handlers(target_logger, logger_name)
            target_logger.handlers = []
            target_logger.propagate = True
        except (AttributeError, RuntimeError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            safe_name = logger_name if logger_name else _UNKNOWN_LOGGER_NAME
            _MODULE_LOGGER.debug("Failed to reset handlers for logger '%s': %s", safe_name, exc)


def _reset_all_handlers(root_logger: logging.Logger) -> None:
    """Close existing handlers and reset all loggers."""
    _close_handlers(root_logger)
    root_logger.handlers = []
    _reset_handlers(root_logger)


def _build_console_handler(service_name: Optional[str], user_friendly: bool, managed_by_monitor: bool) -> logging.Handler:
    if user_friendly:
        formatter = logging.Formatter("%(message)s")
    else:
        formatter = logging.Formatter(
            "%(asctime)s%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    if user_friendly:
        console_handler.setLevel(logging.WARNING)
    elif managed_by_monitor:
        console_handler.setLevel(logging.CRITICAL + 1)
    else:
        console_handler.setLevel(logging.DEBUG)

    return console_handler


def _configure_file_handler(service_name: Optional[str], project_root: Path) -> Optional[logging.Handler]:
    if not service_name:
        return None

    configured_dir = _get_configured_log_directory()
    logs_dir = configured_dir if configured_dir else project_root / "logs"
    if service_name == "monitor":
        _clear_logs_directory(logs_dir)

    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{service_name}.log"
    if os.getenv("PDF_PIPELINE_CHILD") == "1":
        file_mode = "a"
    elif os.getenv("LOG_APPEND") == "1":
        file_mode = "a"
    else:
        file_mode = "w"

    handler_cls = getattr(logging.handlers, "WatchedFileHandler", logging.FileHandler)
    file_handler = handler_cls(log_path, mode=file_mode)
    technical_formatter = logging.Formatter(
        "%(asctime)s%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(technical_formatter)
    file_handler.setLevel(logging.INFO)
    return file_handler


def _suppress_noisy_third_parties() -> None:
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("redis.connection").setLevel(logging.WARNING)
    logging.getLogger("redis.asyncio").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)


def setup_logging(service_name: Optional[str] = None, user_friendly: bool = False):
    """Configure logging for the application"""

    # Use thread-safe lock to ensure single configuration
    with _config_lock:
        # Check if root logger already has handlers configured
        root_logger = logging.getLogger()

        # Check if this process is managed by monitor
        managed_by_monitor = bool(env_bool("MANAGED_BY_MONITOR", or_value=False))

        if _should_skip_logging_configuration(root_logger, managed_by_monitor, service_name):
            return

        _reset_all_handlers(root_logger)

        console_handler = _build_console_handler(service_name, user_friendly, managed_by_monitor)
        root_logger.addHandler(console_handler)

        project_root = Path(__file__).resolve().parents[2]
        file_handler = _configure_file_handler(service_name, project_root)
        if file_handler:
            root_logger.addHandler(file_handler)

        root_logger.setLevel(logging.INFO)
        _suppress_noisy_third_parties()
