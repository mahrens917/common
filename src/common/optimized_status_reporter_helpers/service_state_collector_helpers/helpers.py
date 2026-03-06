"""Service state collection: PID validation, process rediscovery, info updates."""

from __future__ import annotations

from typing import Any, Optional

import psutil

# --- PID validation ---


def is_running(pid: int) -> bool:
    """Check if PID is running and not a zombie."""
    try:
        ps_process = psutil.Process(pid)
        return ps_process.is_running() and ps_process.status() != psutil.STATUS_ZOMBIE
    except (  # policy_guard: allow-silent-handler
        psutil.NoSuchProcess,
        psutil.AccessDenied,
        psutil.ZombieProcess,
    ):
        return False


# --- Process rediscovery ---


def rediscover_and_validate(
    service_name: str,
    process_manager: Any,
    pid_validator: Any,
) -> tuple[bool, Optional[Any]]:
    """Rediscover process and validate its state.

    Returns (is_running, process_info).
    """
    process_manager._rediscover_process(service_name)  # pyright: ignore[reportPrivateUsage]
    info = process_manager.process_info.get(service_name)

    if not info or not info.pid:
        return False, info

    is_running_now = pid_validator.is_running(info.pid)
    return is_running_now, info


# --- Service info updates (intentional no-ops) ---
# ProcessInfo should only be modified by the ProcessManager via psutil probing,
# not by status reporters. Status reporters are read-only collectors.


def update_from_handle(info: Any, process_handle: Any) -> None:
    """No-op. ProcessInfo should only be modified by ProcessManager."""


def clear_stopped_process(info: Any) -> None:
    """No-op. ProcessInfo should only be modified by ProcessManager."""


def mark_as_running(info: Optional[Any]) -> None:
    """No-op. ProcessInfo should only be modified by ProcessManager."""
