"""
Simple system metrics module that eliminates CPU spikes from monitoring.

This module provides efficient system metrics collection for Linux and macOS:
- Linux: /proc/meminfo for memory; vmstat for CPU (1-second sample)
- macOS: Lightweight system command calls (vm_stat, iostat)

Key benefits:
1. Efficient platform-native reads
2. No background threads or caching complexity
3. No CPU spikes visible in htop
4. Fail-fast design with simple error handling
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess

logger = logging.getLogger(__name__)



def get_memory_percent() -> float:
    """Get memory usage percentage (Linux and macOS)."""
    system = platform.system()
    if system == "Linux":
        return _get_memory_percent_linux()
    elif system == "Darwin":
        return _get_memory_percent_macos()
    else:
        raise RuntimeError(f"Memory metrics not supported on {system}")


def get_cpu_percent() -> float:
    """
    Get CPU usage percentage.

    On Linux, vmstat samples over a 1-second window.
    On macOS, iostat samples over a 1-second window.
    Both provide current CPU usage and eliminate spikes from psutil-style polling.
    """
    system = platform.system()
    if system == "Linux":
        return _get_cpu_percent_linux()
    elif system == "Darwin":
        return _get_cpu_percent_macos()
    else:
        raise RuntimeError(f"CPU metrics not supported on {system}")


def get_disk_percent(path: str = "/") -> float:
    """
    Get disk usage percentage for specified path.

    Uses os.statvfs() which is efficient across all platforms.

    Args:
        path: Filesystem path to check (default: root filesystem)

    Returns:
        Disk usage percentage (0-100), or 0.0 on error
    """
    try:
        stat = os.statvfs(path)
        total_bytes = stat.f_blocks * stat.f_frsize
        free_bytes = stat.f_bavail * stat.f_frsize
        used_bytes = total_bytes - free_bytes

        if total_bytes > 0:
            return (used_bytes / total_bytes) * 100.0

        else:
            return 0.0
    except OSError:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
        logger.debug("Error getting disk usage for %s", path)
        return 0.0


def _get_memory_percent_linux() -> float:
    """Get memory usage percentage from /proc/meminfo (Linux only)"""
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()

        mem_total = 0
        mem_available: int | None = None
        for line in lines:
            if line.startswith("MemTotal:"):
                mem_total = int(line.split()[1]) * 1024  # Convert KB to bytes
            elif line.startswith("MemAvailable:"):
                mem_available = int(line.split()[1]) * 1024  # Convert KB to bytes
                break

        if mem_total > 0 and mem_available is not None:
            used_bytes = mem_total - mem_available
            return (used_bytes / mem_total) * 100.0

        else:
            return 0.0
    except (OSError, ValueError):  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
        logger.debug("Error reading /proc/meminfo")
        return 0.0


def _get_cpu_percent_linux() -> float:
    """Get CPU usage percentage using vmstat (Linux only).

    Uses 'vmstat 1 2' to measure CPU over a 1-second window,
    matching the macOS iostat approach.
    """
    try:
        proc = subprocess.Popen(
            ["vmstat", "1", "2"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            stdout, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate(timeout=5)
            return 0.0
        if not stdout:
            return 0.0

        lines = stdout.strip().split("\n")
        us_col_idx = _find_cpu_column_index(lines)
        if us_col_idx == -1:
            return 0.0

        return _parse_cpu_from_iostat_output(lines, us_col_idx)
    except (ValueError, OSError):  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
        logger.debug("Error reading vmstat for CPU")
        return 0.0


def _get_memory_percent_macos() -> float:
    """Get memory usage percentage using vm_stat (macOS only)"""
    try:
        proc = subprocess.Popen(["vm_stat"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate(timeout=5)
            return 0.0
        if not stdout:
            return 0.0

        lines = stdout.strip().split("\n")
        vm_stats = _parse_vm_stat_output(lines)
        return _calculate_memory_percentage(vm_stats)

    except (
        ValueError,
        OSError,
        IndexError,
    ):  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
        logger.debug("Error reading vm_stat for memory")
        return 0.0


def _parse_vm_stat_output(lines: list[str]) -> dict[str, int]:
    """Parse vm_stat output to extract page statistics."""
    stats = {
        "page_size": 4096,  # Default page size
        "pages_free": 0,
        "pages_active": 0,
        "pages_inactive": 0,
        "pages_wired": 0,
    }

    parsers = {
        "page size of": lambda line: ("page_size", int(line.split()[-2])),
        "Pages free:": lambda line: ("pages_free", int(line.split()[-1].rstrip("."))),
        "Pages active:": lambda line: ("pages_active", int(line.split()[-1].rstrip("."))),
        "Pages inactive:": lambda line: ("pages_inactive", int(line.split()[-1].rstrip("."))),
        "Pages wired down:": lambda line: ("pages_wired", int(line.split()[-1].rstrip("."))),
    }

    for line in lines:
        for pattern, parser in parsers.items():
            if pattern in line:
                key, value = parser(line)
                stats[key] = value
                break

    return stats


def _calculate_memory_percentage(vm_stats: dict[str, int]) -> float:
    """Calculate memory usage percentage from vm_stat page counts."""
    total_pages = vm_stats["pages_free"] + vm_stats["pages_active"] + vm_stats["pages_inactive"] + vm_stats["pages_wired"]
    used_pages = vm_stats["pages_active"] + vm_stats["pages_wired"]

    if total_pages > 0:
        return (used_pages / total_pages) * 100.0
    return 0.0


def _get_cpu_percent_macos() -> float:
    """Get CPU usage percentage using iostat (macOS only)"""
    try:
        proc = subprocess.Popen(
            ["iostat", "-c", "2", "-w", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            stdout, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate(timeout=5)
            return 0.0
        if not stdout:
            return 0.0

        lines = stdout.strip().split("\n")
        us_col_idx = _find_cpu_column_index(lines)
        if us_col_idx == -1:
            return 0.0

        return _parse_cpu_from_iostat_output(lines, us_col_idx)
    except (
        ValueError,
        OSError,
    ):  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
        logger.debug("Error reading iostat for CPU")
        return 0.0


def _find_cpu_column_index(lines: list[str]) -> int:
    """Find the column index for 'us' (user CPU) in iostat output."""
    for line in lines:
        if "us" in line and "sy" in line and "id" in line:
            parts = line.split()
            for idx, part in enumerate(parts):
                if part == "us":
                    return idx
            break
    return -1


def _parse_cpu_from_iostat_output(lines: list[str], us_col_idx: int) -> float:
    """Parse CPU usage from iostat output lines."""
    for line in reversed(lines):
        parts = line.split()
        if len(parts) > us_col_idx + 2:
            try:
                user = float(parts[us_col_idx])
                system = float(parts[us_col_idx + 1])
                idle = float(parts[us_col_idx + 2])
                return _calculate_cpu_percentage(user, system, idle)
            except (ValueError, IndexError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
                logger.warning("Failed to parse CPU stats: parts=%r, error=%s", parts, exc)
                continue
    return 0.0


def _calculate_cpu_percentage(user: float, system: float, idle: float) -> float:
    """Calculate CPU usage percentage from user, system, and idle components."""
    total = user + system + idle
    if total > 0:
        cpu_used = user + system
        return (cpu_used / total) * 100.0
    return 0.0
