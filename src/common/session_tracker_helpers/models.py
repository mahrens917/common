"""Data models for session tracking."""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SessionInfo:
    """Information about a tracked HTTP session."""

    session_id: str
    service_name: str
    created_at: float
    created_stack: str
    closed_at: Optional[float] = None
    closed_stack: Optional[str] = None
    is_closed: bool = False
    last_activity: float = field(default_factory=time.time)
    request_count: int = 0
