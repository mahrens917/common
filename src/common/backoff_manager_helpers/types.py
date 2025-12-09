"""Type definitions and configurations for backoff management."""

from dataclasses import dataclass
from enum import Enum

DEFAULT_BACKOFF_MAX_DELAY_SECONDS = 60.0
DEFAULT_BACKOFF_MAX_ATTEMPTS = 10


class BackoffType(Enum):
    """Types of backoff strategies for different error scenarios"""

    NETWORK_FAILURE = "network_failure"
    AUTHENTICATION_FAILURE = "authentication_failure"
    RATE_LIMIT_FAILURE = "rate_limit_failure"
    WEBSOCKET_CONNECTION = "websocket_connection"
    WEBSOCKET_MESSAGE = "websocket_message"
    GENERAL_FAILURE = "general_failure"


@dataclass
class BackoffConfig:
    """Configuration for exponential backoff behavior"""

    initial_delay: float = 1.0
    max_delay: float = DEFAULT_BACKOFF_MAX_DELAY_SECONDS
    multiplier: float = 2.0
    jitter_range: float = 0.1  # ±10% randomization
    network_degraded_multiplier: float = 2.0
    max_attempts: int = DEFAULT_BACKOFF_MAX_ATTEMPTS


# Default backoff configurations for different failure types
DEFAULT_BACKOFF_CONFIGS = {
    BackoffType.NETWORK_FAILURE: BackoffConfig(
        initial_delay=5.0,
        max_delay=300.0,
        multiplier=1.5,
        jitter_range=0.15,
        network_degraded_multiplier=2.0,
        max_attempts=15,
    ),
    BackoffType.AUTHENTICATION_FAILURE: BackoffConfig(
        initial_delay=5.0,
        max_delay=300.0,
        multiplier=2.5,
        jitter_range=0.2,
        network_degraded_multiplier=2.0,
        max_attempts=5,
    ),
    BackoffType.RATE_LIMIT_FAILURE: BackoffConfig(
        initial_delay=30.0,
        max_delay=900.0,
        multiplier=1.5,
        jitter_range=0.25,
        network_degraded_multiplier=1.5,
        max_attempts=3,
    ),
    BackoffType.WEBSOCKET_CONNECTION: BackoffConfig(
        initial_delay=1.0,
        max_delay=60.0,
        multiplier=2.0,
        jitter_range=0.1,
        network_degraded_multiplier=2.5,
        max_attempts=10,
    ),
    BackoffType.WEBSOCKET_MESSAGE: BackoffConfig(
        initial_delay=0.5,
        max_delay=30.0,
        multiplier=2.0,
        jitter_range=0.1,
        network_degraded_multiplier=2.0,
        max_attempts=5,
    ),
    BackoffType.GENERAL_FAILURE: BackoffConfig(
        initial_delay=1.0,
        max_delay=60.0,
        multiplier=2.0,
        jitter_range=0.1,
        network_degraded_multiplier=2.0,
        max_attempts=8,
    ),
}
