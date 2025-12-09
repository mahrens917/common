"""Data classes for error analysis."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""

    NETWORK = "network"
    AUTHENTICATION = "authentication"
    DATA = "data"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    WEBSOCKET = "websocket"
    API = "api"
    UNKNOWN = "unknown"


@dataclass
class ErrorAnalysis:
    """Comprehensive error analysis result"""

    service_name: str
    error_message: str
    error_type: str
    category: ErrorCategory
    severity: ErrorSeverity
    root_cause: str
    suggested_action: str
    timestamp: float
    stack_trace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    recovery_possible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result["category"] = self.category.value
        result["severity"] = self.severity.value
        result["timestamp_iso"] = datetime.fromtimestamp(
            self.timestamp, tz=timezone.utc
        ).isoformat()
        return result
