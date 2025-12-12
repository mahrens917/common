"""
Timestamp extraction from log files.

Uses file modification time as proxy for last log entry timestamp.
This is faster than parsing log content and sufficient for activity monitoring.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def extract_last_log_timestamp(log_file_path: str) -> Optional[datetime]:
    """
    Extract the timestamp of the last log entry from a file.

    Uses file modification time (st_mtime) as proxy for last log entry.
    This is more efficient than parsing log content and sufficient for
    determining whether a service is actively logging.

    Args:
        log_file_path: Path to the log file

    Returns:
        Datetime of last log entry (timezone-aware UTC) or None if not readable
    """
    try:
        stat = os.stat(log_file_path)
        return datetime.fromtimestamp(stat.st_mtime, timezone.utc)
    except OSError:  # policy_guard: allow-silent-handler
        logger.debug(f"Could not read log modification time from {log_file_path}")
        return None
