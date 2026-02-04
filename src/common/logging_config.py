"""Centralized logging configuration for all services.

Console output to stdout, file output to logs/{service_name}.log.
Every restart rewrites the log file fresh (mode "w").
"""

import logging
import sys
import threading
from pathlib import Path
from typing import Optional

from common.config import env_bool

_config_lock = threading.Lock()
_UNKNOWN_LOGGER_NAME = "<unknown>"


def _close_handlers(logger: logging.Logger, logger_name: Optional[str] = None) -> None:
    """Close all handlers for a logger."""
    for handler in list(logger.handlers):
        try:
            handler.close()
        except OSError as e:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
            safe_name = logger_name if logger_name else _UNKNOWN_LOGGER_NAME
            logging.getLogger(__name__).debug("Handler close failed for logger '%s': %s", safe_name, e)


def _reset_all_handlers(root_logger: logging.Logger) -> None:
    """Close existing handlers and reset all loggers."""
    _close_handlers(root_logger)
    root_logger.handlers = []
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        try:
            child = logging.getLogger(logger_name)
            _close_handlers(child, logger_name)
            child.handlers = []
            child.propagate = True
        except (AttributeError, RuntimeError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            logging.getLogger(__name__).debug("Failed to reset handlers for logger '%s': %s", logger_name, exc)


def _suppress_noisy_third_parties() -> None:
    """Suppress verbose third-party loggers to WARNING."""
    for name in ("urllib3", "asyncio", "websockets", "aiohttp", "redis", "redis.connection", "redis.asyncio", "matplotlib", "PIL"):
        logging.getLogger(name).setLevel(logging.WARNING)


def setup_logging(service_name: Optional[str] = None) -> None:
    """Configure logging for the application."""
    with _config_lock:
        root_logger = logging.getLogger()
        managed_by_monitor = bool(env_bool("MANAGED_BY_MONITOR", or_value=False))

        _reset_all_handlers(root_logger)

        formatter = logging.Formatter(
            "%(asctime)s%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO if managed_by_monitor else logging.DEBUG)
        root_logger.addHandler(console_handler)

        if service_name and not managed_by_monitor:
            logs_dir = Path.cwd() / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(logs_dir / f"{service_name}.log", mode="w")
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.INFO)
            root_logger.addHandler(file_handler)

        root_logger.setLevel(logging.INFO)
        _suppress_noisy_third_parties()
