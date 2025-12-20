"""Dependencies for Telegram polling coordinator."""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class PollingDependencies:
    """Dependencies required for Telegram polling operations."""

    telegram_client: object
    telegram_timeout_seconds: int
    telegram_long_poll_timeout_seconds: int
    rate_limit_handler: object
    request_executor: object
    backoff_manager: object
    update_processor: object
    queue_processor_starter: Callable[[], None]
