"""Process discovery and validation logic."""

import logging
from types import SimpleNamespace
from typing import Any, List, Optional, Sequence

from .process_normalizer import NormalizedProcess

logger = logging.getLogger(__name__)


def _console(message: str, *, suppress_output: bool) -> None:
    """Emit console output unless suppressed."""
    if not suppress_output:
        print(message)


async def collect_process_candidates(
    process_keywords: Sequence[str],
    *,
    service_name: str,
    exclude_pid: Optional[int],
) -> List[NormalizedProcess]:
    """
    Ask the shared process monitor for matching processes and normalize the results.

    Raises:
        RuntimeError: When the monitor cannot provide keyword search results or returns
                      unexpected payloads.
    """
    from .monitor_query import query_monitor_for_processes
    from .process_filter import filter_processes_by_pid
    from .process_normalizer import normalize_process

    # Query monitor for matching processes
    monitor_matches = await query_monitor_for_processes(process_keywords, service_name)

    # Normalize all process objects
    normalized = [normalize_process(raw, service_name) for raw in monitor_matches]

    # Filter by PID if needed
    filtered = filter_processes_by_pid(normalized, exclude_pid)
    if filtered:
        return filtered

    # Direct OS scan when monitor has no matches
    try:
        import psutil
    except ImportError:
        return []
    if not hasattr(psutil, "process_iter"):
        return []

    def _matches(cmdline: Sequence[str]) -> bool:
        cmdline_str = " ".join(cmdline)
        return any(pattern in cmdline_str for pattern in process_keywords)

    os_scan_matches: List[NormalizedProcess] = []
    for proc in psutil.process_iter(["pid", "cmdline", "name"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if not _matches(cmdline):
                continue
            os_scan_matches.append(
                normalize_process(
                    SimpleNamespace(
                        pid=proc.info.get("pid"),
                        name=proc.info.get("name"),
                        cmdline=cmdline,
                    ),
                    service_name,
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return filter_processes_by_pid(os_scan_matches, exclude_pid)


def create_psutil_process(pid: int, *, service_name: str, cmdline: Sequence[str]) -> Optional[Any]:
    """Create a psutil.Process instance for the given PID."""
    try:
        import psutil
    except ImportError as import_exc:
        raise RuntimeError(f"psutil is required to manage {service_name} processes but is not installed.") from import_exc

    try:
        return psutil.Process(pid)
    except KeyError:
        logger.debug("Process %s disappeared before psutil inspection", pid)
        return None
    except psutil.NoSuchProcess:
        # Process already exited; treat as non-candidate.
        logger.debug("Process %s vanished before psutil inspection", pid)
        return None
    except psutil.AccessDenied:
        logger.debug(
            "Access denied inspecting %s process %s (cmdline=%s)",
            service_name,
            pid,
            " ".join(cmdline),
        )
        return None


def build_matching_processes(
    candidates: List[NormalizedProcess],
    service_name: str,
    *,
    exclude_pid: Optional[int],
    strict_python: bool = False,
    suppress_output: bool = False,
) -> list:
    """Create psutil process instances and validate executables."""
    matching_processes = []
    for process_info in candidates:
        if _skip_candidate(process_info, exclude_pid, service_name):
            continue

        process = _create_valid_process(process_info, service_name, suppress_output)
        if process is None:
            continue

        pid = _get_process_pid(process, service_name, suppress_output)
        if pid is None:
            continue

        if not _validate_process_name(process_info, service_name, strict_python):
            continue

        display_cmdline = " ".join(process_info.cmdline)
        _console(
            f"🔍 Found {service_name} process: PID {pid} - {display_cmdline[:100]}...",
            suppress_output=suppress_output,
        )
        logger.debug("Found %s process with PID %s via process monitor", service_name, pid)
        matching_processes.append(process)

    _console(
        f"🔍 Used centralized process monitor (found {len(matching_processes)} processes)",
        suppress_output=suppress_output,
    )
    logger.debug("Process killer identified %d matching %s processes", len(matching_processes), service_name)
    return matching_processes


def _skip_candidate(process_info: NormalizedProcess, exclude_pid: Optional[int], service_name: str) -> bool:
    if exclude_pid is not None and process_info.pid == exclude_pid:
        logger.debug(
            "Skipping %s process %s because it matches current PID",
            service_name,
            process_info.pid,
        )
        return True
    return False


def _create_valid_process(process_info: NormalizedProcess, service_name: str, suppress_output: bool) -> Optional[Any]:
    if process_info.pid is None:
        return None
    return create_psutil_process(
        process_info.pid,
        service_name=service_name,
        cmdline=process_info.cmdline,
    )


def _get_process_pid(process: Any, service_name: str, suppress_output: bool) -> Optional[int]:
    try:
        return process.pid
    except (AttributeError, RuntimeError, OSError) as exc:
        _console(f"⚠️ Could not kill process: {exc}", suppress_output=suppress_output)
        logger.debug("Unable to read PID for %s process: %s", service_name, exc)
        return None


def _validate_process_name(process_info: NormalizedProcess, service_name: str, strict_python: bool) -> bool:
    if not process_info.name or "python" in process_info.name.lower():
        return True
    if strict_python:
        raise RuntimeError(f"Unexpected executable for {service_name} process {process_info.pid}: " f"{process_info.name}")
    logger.debug(
        "Skipping %s process %s with executable %s",
        service_name,
        process_info.pid,
        process_info.name,
    )
    return False


def import_psutil(service_name: str) -> Any:
    """Import psutil or raise a helpful error."""
    try:
        import psutil

    except ImportError as import_exc:
        raise RuntimeError(
            f"psutil is required for process management but not available. Cannot ensure single instance of {service_name}"
        ) from import_exc
    else:
        return psutil
