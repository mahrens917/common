"""Backoff delay calculation for connection retry logic."""

from typing import Any


def calculate_backoff_delay(manager: Any) -> float:
    """
    Calculate exponential backoff delay with jitter.

    Uses the same algorithm as DelayCalculator in
    common.backoff_manager_helpers.delay_calculator, but implemented
    inline to avoid circular imports with the backoff_manager module hierarchy.
    """
    import random

    metrics = manager.metrics_tracker.get_metrics()
    if metrics.consecutive_failures <= 0:
        return 0.0

    # Same formula as DelayCalculator.calculate_base_delay
    base_delay = manager.config.reconnection_initial_delay_seconds * (
        manager.config.reconnection_backoff_multiplier ** (metrics.consecutive_failures - 1)
    )
    delay = min(base_delay, manager.config.reconnection_max_delay_seconds)

    # Same jitter formula as DelayCalculator.apply_jitter with 20% range,
    # but keep it deterministic for tests that monkeypatch random.random.
    jitter_range = 0.2
    jitter_amount = delay * jitter_range
    jitter = (random.random() * 2 - 1) * jitter_amount
    delay = max(0.1, delay + jitter)

    manager.metrics_tracker.set_backoff_delay(delay)
    return delay
