"""
Shared types and constants for service health checking.

Defines health states, info dataclasses, and common error types.
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from redis.exceptions import RedisError

from ..redis_utils import RedisOperationError

MISSING_STATUS_VALUE = ""

HEALTH_CHECK_ERRORS = (
    RedisError,
    RedisOperationError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
    OSError,
)


class ServiceHealth(Enum):
    """Service responsiveness states"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNRESPONSIVE = "unresponsive"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealthInfo:
    """Service health information"""

    health: ServiceHealth
    response_time_ms: Optional[float] = None
    last_status_update: Optional[float] = None
    error_message: Optional[str] = None
