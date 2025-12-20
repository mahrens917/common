from __future__ import annotations

"""Shared data structures for monitor alerting."""

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class AlerterError(RuntimeError):
    """Base exception for alerting failures."""


class TelegramAPIError(AlerterError):
    """Raised when the Telegram API responds with an unexpected payload."""


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


@dataclass
class QueuedCommand:
    """Represents a queued Telegram command."""

    command: str
    handler: Callable
    message: Dict[str, Any]
    timestamp: float


@dataclass
class PendingTelegramMessage:
    """Represents a queued Telegram text alert."""

    alert: Alert
    recipients: List[str]
    enqueued_at: float = field(default_factory=time.time)


@dataclass
class PendingTelegramMedia:
    """Represents a queued Telegram media payload (photo/video/document)."""

    original_path: Path
    spooled_path: Path
    caption: str
    recipients: List[str]
    is_photo: bool
    telegram_method: str
    enqueued_at: float = field(default_factory=time.time)


@dataclass
class TelegramDeliveryResult:
    """Represents the outcome of attempting to deliver a Telegram payload."""

    success: bool
    failed_recipients: List[str]
    queued_recipients: List[str]
