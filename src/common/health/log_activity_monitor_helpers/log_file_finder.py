"""
Log file discovery with rotation support.

Handles finding the most recent log file among potentially rotated versions
(service.log, service.log.1, service.log.2, etc.).
"""

import glob
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)


def find_most_recent_log_file(logs_directory: str, pattern: str, quick_check_seconds: int = 3600) -> Optional[str]:
    """
    Find the most recent log file among rotated versions.

    Strategy:
    1. Check if current log file exists and was modified within quick_check_seconds
    2. If so, return immediately (fast path for active services)
    3. Otherwise, scan all rotated versions and return the most recent

    Args:
        logs_directory: Base directory for log files
        pattern: Log file pattern (e.g., "service.log")
        quick_check_seconds: If current log is newer than this, skip rotation check

    Returns:
        Path to most recent log file or None if not found
    """
    base_path = os.path.join(logs_directory, pattern)
    current_log = base_path
    rotated_pattern = f"{base_path}.*"

    # Fast path: Check if current log file exists and is recent
    if os.path.exists(current_log):
        try:
            stat = os.stat(current_log)
            current_age = time.time() - stat.st_mtime
            if current_age < quick_check_seconds:
                return current_log
        except OSError as exc:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
            # File may have been removed between exists() and stat() - fall through to slow path
            logger.debug("Failed to stat log file %s: %s", current_log, exc)

    # Slow path: Find most recent among all log files (including rotated)
    all_log_files = []
    if os.path.exists(current_log):
        all_log_files.append(current_log)
    all_log_files.extend(glob.glob(rotated_pattern))

    if not all_log_files:
        return None

    # Return file with most recent modification time
    most_recent_file = None
    most_recent_time = None

    for log_file in all_log_files:
        try:
            stat = os.stat(log_file)
            file_time = stat.st_mtime
            if most_recent_time is None or file_time > most_recent_time:
                most_recent_time = file_time
                most_recent_file = log_file
        except OSError:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
            logger.debug("Best-effort cleanup operation")
            continue

    return most_recent_file
