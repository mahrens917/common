from __future__ import annotations

"""Shared data structures for monitor alerting."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class AlerterError(RuntimeError):
    """Base exception for alerting failures."""


class AlertSeverity(Enum):
    """Simple alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Simple alert data structure."""

    message: str
    severity: AlertSeverity
    timestamp: float
    alert_type: str
    details: Optional[Dict[str, Any]] = None
