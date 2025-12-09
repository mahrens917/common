"""
Log activity types and enums.

Shared types used by both the coordinator and helper modules.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class LogActivityStatus(Enum):
    """Log activity states"""

    RECENT = "recent"
    STALE = "stale"
    OLD = "old"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass
class LogActivity:
    """Log activity information"""

    status: LogActivityStatus
    last_timestamp: Optional[datetime] = None
    age_seconds: Optional[float] = None
    log_file_path: Optional[str] = None
    error_message: Optional[str] = None
