"""Retry policy factory for ConnectionRetryHelper."""

from .....retry import RedisRetryPolicy


def create_retry_policy(attempts: int, retry_delay: float) -> RedisRetryPolicy:
    """Create retry policy with validated parameters."""
    return RedisRetryPolicy(
        max_attempts=max(1, attempts),
        initial_delay=max(0.01, retry_delay),
        max_delay=max(retry_delay * 4, retry_delay),
    )
