"""Terminate processes with proper handling and timeouts."""

import logging
from types import SimpleNamespace
from typing import Any, List

logger = logging.getLogger(__name__)


async def terminate_matching_processes(
    matching_processes: List[Any],
    *,
    service_name: str,
    graceful_timeout: float,
    force_timeout: float,
    console_output_func: Any,
) -> List[int]:
    """
    Terminate all matching processes with graceful shutdown then force kill if needed.

    Args:
        matching_processes: List of psutil.Process objects to terminate
        service_name: Name of the service for logging
        graceful_timeout: Timeout for graceful shutdown in seconds
        force_timeout: Timeout for force kill in seconds
        console_output_func: Function to print console messages

    Returns:
        List of PIDs that were successfully killed

    Raises:
        RuntimeError: If access is denied or process persists after force kill
    """
    try:
        import psutil
    except ImportError as import_exc:  # policy_guard: allow-silent-handler
        raise RuntimeError("psutil is required for process termination") from import_exc

    killed_processes = []
    for proc in matching_processes:
        try:
            await _terminate_single_process(
                proc,
                psutil_module=psutil,
                service_name=service_name,
                graceful_timeout=graceful_timeout,
                force_timeout=force_timeout,
                console_output_func=console_output_func,
            )
            killed_processes.append(proc.pid)
        except psutil.NoSuchProcess:  # policy_guard: allow-silent-handler
            logger.debug("%s process %s exited before termination completed", service_name, proc.pid)
        except psutil.AccessDenied as access_exc:  # policy_guard: allow-silent-handler
            raise RuntimeError(f"Access denied while terminating {service_name} process {proc.pid}") from access_exc

    return killed_processes


async def _terminate_single_process(
    proc,
    *,
    psutil_module,
    service_name: str,
    graceful_timeout: float,
    force_timeout: float,
    console_output_func: Any,
) -> None:
    """Terminate a single process with graceful shutdown then force kill if needed."""
    pid = proc.pid
    console_output_func(f"🔪 Killing existing {service_name} process (PID {pid})")
    proc.terminate()

    try:
        proc.wait(timeout=graceful_timeout)
    except psutil_module.TimeoutExpired:  # policy_guard: allow-silent-handler
        console_output_func(f"⏱️ Process {pid} did not terminate within {graceful_timeout}s; sending SIGKILL")
    else:
        console_output_func(f"✅ Process {pid} terminated gracefully")
        return

    proc.kill()
    try:
        proc.wait(timeout=force_timeout)
    except psutil_module.TimeoutExpired as kill_exc:  # policy_guard: allow-silent-handler
        raise RuntimeError(
            f"{service_name} process {pid} persisted after SIGKILL for " f"{force_timeout}s; manual intervention required."
        ) from kill_exc
    console_output_func(f"✅ Process {pid} force killed")


def validate_process_candidates(candidates: List[SimpleNamespace], *, service_name: str) -> List[Any]:
    """
    Convert process candidates to psutil Process objects and validate them.

    Args:
        candidates: List of normalized process info objects
        service_name: Name of the service for validation

    Returns:
        List of valid psutil.Process objects

    Raises:
        RuntimeError: If process has unexpected executable or access is denied
    """
    matching_processes = []
    for process_info in candidates:
        process = _create_psutil_process_safe(
            process_info.pid,
            service_name=service_name,
            cmdline=process_info.cmdline,
        )
        if process is None:
            continue

        _validate_process_executable(process_info, service_name)
        matching_processes.append(process)

    return matching_processes


def _create_psutil_process_safe(pid: int, *, service_name: str, cmdline: list) -> Any:
    """Create psutil Process object with error handling."""
    try:
        import psutil
    except ImportError as import_exc:  # policy_guard: allow-silent-handler
        raise RuntimeError(f"psutil is required to manage {service_name} processes but is not installed.") from import_exc

    try:
        return psutil.Process(pid)
    except psutil.NoSuchProcess:  # policy_guard: allow-silent-handler
        logger.debug("Process %s vanished before psutil inspection", pid)
        return None
    except psutil.AccessDenied as access_exc:  # policy_guard: allow-silent-handler
        raise RuntimeError(f"Access denied while inspecting {service_name} process {pid} ({' '.join(cmdline)})") from access_exc


def _validate_process_executable(process_info: SimpleNamespace, service_name: str) -> None:
    """Validate that process has expected executable name."""
    if process_info.name and "python" not in process_info.name.lower():
        raise RuntimeError(f"Unexpected executable for {service_name} process {process_info.pid}: " f"{process_info.name}")
