from __future__ import annotations

"""Utilities for running long-lived async services with consistent shutdown handling."""

import asyncio
import logging
import os
import signal
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from .logging_config import setup_logging
from .process_killer import ensure_single_instance_sync

try:
    import fcntl
except ImportError:  # pragma: no cover - fcntl unavailable on non-POSIX platforms  # policy_guard: allow-silent-handler
    fcntl = None


class SingleInstanceError(RuntimeError):
    """Raised when another instance of the same service is already running."""


class ServiceInstanceLock:
    """File-lock based guard to enforce single service instance per host."""

    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        project_root = Path(__file__).resolve().parents[2]
        env_override = os.getenv("SERVICE_RUNTIME_DIR")
        self.runtime_dir = Path(env_override) if env_override else project_root / "runtime"
        self.runtime_dir.mkdir(exist_ok=True)
        self.lock_path = self.runtime_dir / f"{service_name}.lock"
        self._fd: Optional[int] = None
        self._released = False

    def acquire(self) -> None:
        """Attempt to acquire the lock; raises if already held."""

        if fcntl is None:  # pragma: no cover - non-POSIX platforms
            raise SingleInstanceError("Single instance enforcement requires fcntl on this platform.")

        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o664)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            existing_pid = None
            try:
                with os.fdopen(fd, "r") as fh:
                    data = fh.read().strip()
                    if data:
                        existing_pid = data
            except (OSError, ValueError):  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
                # Best-effort PID inspection - errors are not fatal
                existing_pid = None
            try:
                os.close(fd)
            except OSError:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
                # Best-effort descriptor cleanup - errors are not fatal
                pass

            if existing_pid:
                suffix = f" (PID {existing_pid})."
            else:
                suffix = "."
            raise SingleInstanceError(f"Service '{self.service_name}' appears to be running already" + suffix) from exc

        os.ftruncate(fd, 0)
        os.write(fd, str(os.getpid()).encode("utf-8"))
        os.fsync(fd)
        self._fd = fd

    def release(self) -> None:
        """Release the lock and clean up the lock file."""

        if self._released:
            return

        if self._fd is not None:
            try:
                if fcntl is not None:
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
            finally:
                try:
                    os.close(self._fd)
                except OSError:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
                    # Best-effort descriptor cleanup - errors are not fatal
                    pass
                self._fd = None

        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
        except OSError:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
            # Lock file might have been cleaned up by another process or permissions issue.
            pass

        self._released = True

    def __del__(self) -> None:  # pragma: no cover - best-effort safety net
        self.release()


@contextmanager
def single_instance_guard(service_name: str):
    """Context manager enforcing one running instance per service name."""

    lock = ServiceInstanceLock(service_name)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()


ServiceFactory = Callable[[], Coroutine[Any, Any, None]]


def run_async_service(
    factory: ServiceFactory,
    *,
    service_name: str,
    logger_name: Optional[str] = None,
    configure_logging: bool = True,
    shutdown_message: Optional[str] = None,
    ignore_sighup: bool = False,
) -> None:
    """Run an async service with consistent Ctrl+C handling.

    Args:
        factory: Callable returning the coroutine to execute.
        service_name: Identifier used for logging configuration.
        logger_name: Optional logger name override.
        configure_logging: Whether to configure logging via ``setup_logging``.
        shutdown_message: Optional custom message when interrupted.
        ignore_sighup: When ``True`` the service ignores ``SIGHUP`` so it keeps
            running after the launching terminal closes. Unsupported platforms
            (e.g. Windows) simply skip the signal tweak.
    """

    try:
        ensure_single_instance_sync(service_name)
        with single_instance_guard(service_name):
            if configure_logging:
                setup_logging(service_name)

            logger = logging.getLogger(logger_name or f"src.{service_name}")

            if ignore_sighup:
                try:
                    signal.signal(signal.SIGHUP, signal.SIG_IGN)
                    logger.debug("Ignoring SIGHUP for %s", service_name)
                except AttributeError:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
                    # SIGHUP is not defined on all platforms (e.g., Windows).
                    logger.debug("SIGHUP not available; cannot ignore for %s", service_name)
                except ValueError:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
                    # Raised when signals are configured outside the main thread.
                    logger.warning("Failed to ignore SIGHUP for %s", service_name)

            try:
                logger.debug("DEBUG: run_async_service - about to call asyncio.run(factory())")
                asyncio.run(factory())
                logger.warning("DEBUG: run_async_service - asyncio.run(factory()) returned normally! service=%s", service_name)
            except KeyboardInterrupt:  # Expected exception in operation  # policy_guard: allow-silent-handler
                # CTRL+C translates into a friendly shutdown log
                logger.warning("DEBUG: run_async_service - KeyboardInterrupt received for %s", service_name)
                if shutdown_message:
                    logger.info(shutdown_message)
                else:
                    logger.info("%s service interrupted by user", service_name)
    except SingleInstanceError as exc:
        message = str(exc)
        sys.stderr.write(message + "\n")
        raise SystemExit(1) from exc
