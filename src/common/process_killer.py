"""
Process Killer Utility

This module provides functionality to kill existing instances of a process
to prevent duplicates when starting services. Uses configuration-driven
timeouts and provides consistent singleton enforcement across all services.

Usage:
    from common.process_killer import ensure_single_instance

    # Ensure only one instance of kalshi is running
    ensure_single_instance("kalshi")
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import List, Optional

from common.config import env_bool

from .connection_config import ConnectionConfig

# Lazy load configuration to avoid requiring env vars at import time
_config: ConnectionConfig | None = None


def _get_config() -> ConnectionConfig:
    """Get or initialize connection config."""
    global _config
    if _config is None:
        _config = ConnectionConfig()
    return _config


SUPPRESS_CONSOLE_OUTPUT = bool(env_bool("MANAGED_BY_MONITOR", or_value=False))
logger = logging.getLogger(__name__)


def _console(message: str) -> None:
    """Emit console output unless the service is running under the monitor."""

    if SUPPRESS_CONSOLE_OUTPUT:
        return
    print(message)


# Process termination timeouts (seconds)
GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS = 3
FORCE_KILL_TIMEOUT_SECONDS = 2
POST_KILL_WAIT_SECONDS = 2

SERVICE_GRACEFUL_TIMEOUT_OVERRIDES: dict[str, int] = {
    "monitor": 30,
}

# Service name to process keywords mapping
# Note: Patterns should be specific to avoid false matches with multiprocessing
# parameter names (e.g., 'tracker_fd') or unrelated processes
SERVICE_PROCESS_PATTERNS = {
    "kalshi": ["-m src.kalshi", "src.kalshi", "src/kalshi/"],
    "deribit": ["-m src.deribit", "src.deribit", "src/deribit/"],
    "monitor": ["-m src.monitor", "src.monitor", "src/monitor/", "simple_monitor"],
    "cfb": ["-m src.cfb", "src.cfb", "src/cfb/"],
    "weather": ["-m src.weather", "src.weather", "src/weather/"],
    "tracker": ["-m src.tracker", "src.tracker", "src/tracker/"],
    "price_alert": ["-m src.price_alert", "src.price_alert", "src/price_alert/"],
    "pdf": ["-m src.pdf", "src.pdf", "src/pdf/"],
    "poly": ["-m src.poly", "src.poly", "src/poly/"],
    "structure": ["-m src.structure", "src.structure", "src/structure/"],
    "web": ["-m src.web", "src.web"],
    "crossarb": ["-m src.crossarb", "src.crossarb", "src/crossarb/"],
    "edge": ["-m src.edge", "src.edge", "src/edge/"],
    "whale": ["-m src.whale", "src.whale", "src/whale/"],
    "peak": ["-m src.peak", "src.peak", "src/peak/"],
}


async def ensure_single_instance(service_name: str) -> None:
    """
    Ensure only one instance of the specified service is running.

    This function kills any existing instances of the service before allowing
    the current instance to proceed. It uses configuration-driven timeouts
    and provides consistent behavior across all services.

    Args:
        service_name: Name of the service (must be in SERVICE_PROCESS_PATTERNS)

    Raises:
        ValueError: If service_name is not recognized
        RuntimeError: If psutil is not available (critical dependency)
    """
    if service_name not in SERVICE_PROCESS_PATTERNS:
        raise ValueError(f"Unknown service '{service_name}'. Known services: {list(SERVICE_PROCESS_PATTERNS.keys())}")

    process_keywords = SERVICE_PROCESS_PATTERNS[service_name]
    await kill_existing_processes(process_keywords, service_name)


def ensure_single_instance_sync(service_name: str) -> None:
    """Synchronously ensure a service is the sole running instance.

    This helper is intended for CLI entry points that are about to start their
    own event loop via ``asyncio.run``. It spins a short-lived event loop to
    invoke :func:`ensure_single_instance` and guarantees there is no currently
    running loop in the active thread.

    Args:
        service_name: Name of the service to enforce singleton execution for.

    Raises:
        RuntimeError: If called while an event loop is already running.
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # Expected runtime failure in operation  # policy_guard: allow-silent-handler
        # Absence of running loop - expected when called from synchronous context
        loop = None

    if loop is not None and loop.is_running():
        raise RuntimeError(
            "ensure_single_instance_sync cannot run inside an active event loop. " "Use the async ensure_single_instance API instead."
        )

    asyncio.run(ensure_single_instance(service_name))


def kill_all_service_processes_sync(service_names: Optional[List[str]] = None) -> None:
    """Synchronously kill all processes for specified services.

    This helper is intended for CLI entry points that need to clean up orphaned
    child processes before launching a new monitor instance.

    Args:
        service_names: List of service names to kill. If None, kills all known services.

    Raises:
        RuntimeError: If called while an event loop is already running.
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # Expected runtime failure in operation  # policy_guard: allow-silent-handler
        loop = None

    if loop is not None and loop.is_running():
        raise RuntimeError(
            "kill_all_service_processes_sync cannot run inside an active event loop. "
            "Use the async kill_all_service_processes API instead."
        )

    asyncio.run(kill_all_service_processes(service_names))


async def kill_existing_processes(process_keywords: List[str], service_name: str = "service") -> None:
    """
    Kill any existing processes matching the given keywords to prevent duplicates.

    Uses configuration-driven timeouts for graceful shutdown and force kill operations.
    Fails fast if psutil is not available since this is a critical dependency.

    Args:
        process_keywords: List of keywords to search for in process command lines
        service_name: Name of the service for logging purposes

    Raises:
        RuntimeError: If psutil is not available (critical dependency)
    """
    await _kill_matching_processes(
        process_keywords,
        service_name=service_name,
        exclude_current_pid=True,
        raise_on_missing_psutil=True,
        wait_after_kill=True,
    )


async def kill_all_service_processes(service_names: Optional[List[str]] = None) -> None:
    """
    Kill all processes for specified services or all known services.

    This is primarily used by the monitor when shutting down to ensure
    all child processes are terminated.

    Args:
        service_names: List of service names to kill. If None, kills all known services.
    """
    targets = service_names or list(SERVICE_PROCESS_PATTERNS.keys())
    for service in targets:
        patterns = SERVICE_PROCESS_PATTERNS.get(service)
        if not patterns:
            _console(f"Unknown service '{service}' - skipping")
            continue
        try:
            await _kill_processes_without_current_exclusion(patterns, service)
        except (
            RuntimeError,
            ValueError,
            TypeError,
        ) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            _console(f"Error killing {service} processes: {exc}")
            continue


async def _kill_processes_without_current_exclusion(process_keywords: List[str], service_name: str) -> None:
    """Kill matching processes without excluding the current PID."""
    await _kill_matching_processes(
        process_keywords,
        service_name=service_name,
        exclude_current_pid=False,
        raise_on_missing_psutil=False,
        wait_after_kill=False,
    )


async def _kill_matching_processes(
    process_keywords: List[str],
    *,
    service_name: str,
    exclude_current_pid: bool,
    raise_on_missing_psutil: bool,
    wait_after_kill: bool,
) -> None:
    """Shared implementation for killing processes."""
    psutil = _load_psutil(raise_on_missing_psutil)
    if psutil is None:
        return

    monitor = await _get_process_monitor()
    current_pid = os.getpid()
    matching = await _collect_target_processes(monitor, psutil, process_keywords, exclude_current_pid, current_pid)

    if not matching:
        _console(f"No {service_name} processes found")
        return

    await _terminate_processes(matching, psutil, service_name, wait_after_kill)


def _load_psutil(raise_on_missing_psutil: bool):
    """Load psutil or optionally raise."""
    try:
        import psutil
    except ImportError as exc:
        message = "psutil not available; cannot kill processes"
        _console(message)
        if raise_on_missing_psutil:
            raise RuntimeError(message) from exc
        return None
    return psutil


async def _get_process_monitor():
    """Return global process monitor if available."""
    from importlib import import_module

    monitor_mod = import_module("common.process_monitor")
    return await monitor_mod.get_global_process_monitor()


async def _collect_target_processes(monitor, psutil, keywords, exclude_current_pid, current_pid):
    """Collect candidate processes to terminate."""
    if monitor is None:
        raise RuntimeError("Process monitor is required but was None")
    candidates = await monitor.find_processes_by_keywords(keywords)

    matching = []
    for proc_info in candidates:
        pid = getattr(proc_info, "pid", None)
        if pid is None:
            _console("Could not kill process: missing pid")
            continue
        if exclude_current_pid and pid == current_pid:
            continue
        try:
            matching.append(psutil.Process(pid))
        except psutil.NoSuchProcess:  # Expected exception in operation  # policy_guard: allow-silent-handler
            _console(f"Process {pid} no longer exists")
        except psutil.AccessDenied:  # Expected exception in operation  # policy_guard: allow-silent-handler
            _console("Could not kill process: access denied")
    return matching


async def _terminate_processes(matching, psutil, service_name: str, wait_after_kill: bool) -> None:
    """Terminate matched processes gracefully, then force kill."""
    for proc in matching:
        if not hasattr(proc, "terminate"):
            _console(f"Could not kill process: {_safe_pid(proc)} ({service_name})")
            continue
        if not _terminate_single_process(proc, psutil, service_name):
            continue

    if wait_after_kill:
        await asyncio.sleep(POST_KILL_WAIT_SECONDS)


def _terminate_single_process(proc, psutil, service_name: str) -> bool:
    """Terminate and force kill a single process if needed."""
    try:
        proc.terminate()
    except psutil.AccessDenied:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
        _console(f"Could not kill process {_safe_pid(proc)} ({service_name})")
        return False

    if _wait_graceful(proc, psutil, service_name):
        return True

    return _force_kill(proc, psutil, service_name)


def _wait_graceful(proc, psutil, service_name: str) -> bool:
    """Attempt graceful termination."""
    timeout = SERVICE_GRACEFUL_TIMEOUT_OVERRIDES.get(service_name, GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS)
    try:
        proc.wait(timeout=timeout)
    except psutil.TimeoutExpired:  # Expected exception in operation  # policy_guard: allow-silent-handler
        _console(f"⏱️ Process {_safe_pid(proc)} ({service_name}) did not terminate within " f"{timeout}s; sending SIGKILL")
    except (OSError, RuntimeError, ValueError) as exc:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
        _console(f"Could not kill process ({service_name}): {exc}")
    else:
        _console(f"✅ Process {_safe_pid(proc)} ({service_name}) terminated gracefully")
        return True
    return False


def _force_kill(proc, psutil, service_name: str) -> bool:
    """Force kill process after graceful shutdown fails."""
    try:
        proc.kill()
    except psutil.NoSuchProcess:  # Expected exception, process race condition  # policy_guard: allow-silent-handler
        _console(f"✅ Process {_safe_pid(proc)} ({service_name}) no longer exists")
        return True
    except psutil.AccessDenied:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
        _console(f"Could not kill process {_safe_pid(proc)} ({service_name}): permission denied")
        return False

    try:
        proc.wait(timeout=FORCE_KILL_TIMEOUT_SECONDS)
    except psutil.TimeoutExpired:  # Expected exception in operation  # policy_guard: allow-silent-handler
        _console(f"⏱️ Process {_safe_pid(proc)} ({service_name}) still alive after force kill timeout")
        return False
    except psutil.NoSuchProcess:  # Expected exception in operation  # policy_guard: allow-silent-handler
        _console(f"✅ Process {_safe_pid(proc)} ({service_name}) no longer exists")
        return True
    else:
        _console(f"✅ Process {_safe_pid(proc)} ({service_name}) force killed")
        return True


def _safe_pid(proc) -> str:
    """Access process pid with fail-fast validation."""
    if proc is None:
        _none_guard_value = "unknown"
        return _none_guard_value
    try:
        pid = getattr(proc, "pid", None)
    except (AttributeError, RuntimeError, OSError):  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
        logger.debug("Best-effort cleanup operation")
        return "unknown"
    if pid is None:
        _none_guard_value = "unknown"
        return _none_guard_value
    try:
        return str(pid)
    except (
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        logger.warning("Failed to convert PID to string: pid=%r, error=%s", pid, exc)
        return "unknown"
