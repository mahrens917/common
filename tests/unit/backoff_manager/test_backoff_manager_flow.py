import time

import pytest

from common.backoff_manager import BackoffManager
from common.backoff_manager_helpers.delay_calculator import DelayCalculator
from common.backoff_manager_helpers.retry_checker import RetryChecker
from common.backoff_manager_helpers.state_manager import BackoffStateManager
from common.backoff_manager_helpers.types import BackoffConfig, BackoffType


class _UnhealthyNetwork:
    def __init__(self, degraded: bool = True, offline: bool = False):
        self._degraded = degraded
        self._offline = offline

    def is_network_healthy(self) -> bool:
        return False

    def is_network_degraded(self) -> bool:
        return self._degraded

    def is_network_offline(self) -> bool:
        return self._offline


def test_delay_calculator_uses_network_multiplier_and_jitter(monkeypatch):
    config = BackoffConfig(
        initial_delay=1.0,
        max_delay=10.0,
        multiplier=2.0,
        jitter_range=0.25,
        network_degraded_multiplier=2.0,
    )
    network_monitor = _UnhealthyNetwork()
    # Keep jitter deterministic
    monkeypatch.setattr("common.backoff_manager.random.uniform", lambda a, b: 0.0)

    delay = DelayCalculator.calculate_full_delay(config, 2, network_monitor, "svc")

    # Base delay: 2s -> degraded multiplier doubles it -> jitter keeps it unchanged
    assert delay == 4.0


def test_state_manager_tracks_and_cleans_state(monkeypatch):
    manager = BackoffStateManager()
    attempt = manager.update_failure_state("svc", BackoffType.GENERAL_FAILURE)
    assert attempt == 1

    info = manager.get_backoff_info("svc", BackoffType.GENERAL_FAILURE, BackoffConfig(max_attempts=2))
    assert info["attempt"] == 1
    assert info["can_retry"]

    # Make the entry old enough to be cleaned
    manager.backoff_state["svc"][BackoffType.GENERAL_FAILURE]["last_failure_time"] = time.time() - 10_000
    manager.cleanup_old_state(max_age_seconds=1)
    assert "svc" not in manager.backoff_state

    # Resetting with a missing bucket should be a no-op
    manager.reset_backoff("svc")


def test_retry_checker_blocks_after_max_attempts():
    state_manager = BackoffStateManager()
    config = BackoffConfig(max_attempts=1)
    state_manager.backoff_state = {
        "svc": {
            BackoffType.GENERAL_FAILURE: {
                "attempt": 1,
                "consecutive_failures": 1,
                "last_failure_time": time.time(),
            }
        }
    }

    assert not RetryChecker.should_retry(state_manager, "svc", BackoffType.GENERAL_FAILURE, config)


def test_backoff_manager_reports_status(monkeypatch):
    monkeypatch.setattr("common.backoff_manager.random.uniform", lambda a, b: 0.0)
    config = BackoffConfig(
        initial_delay=0.5,
        max_delay=2.0,
        multiplier=2.0,
        jitter_range=0.0,
        max_attempts=2,
    )
    manager = BackoffManager(custom_configs={BackoffType.WEBSOCKET_CONNECTION: config})

    delay = manager.calculate_delay("svc", BackoffType.WEBSOCKET_CONNECTION)
    assert 0.0 <= delay <= config.max_delay
    assert manager.should_retry("svc", BackoffType.WEBSOCKET_CONNECTION)

    info = manager.get_backoff_info("svc", BackoffType.WEBSOCKET_CONNECTION)
    assert info["next_delay"] > 0

    status = manager.get_all_backoff_status()
    assert "svc" in status
    assert BackoffType.WEBSOCKET_CONNECTION.value in status["svc"]

    manager.reset_backoff("svc", BackoffType.WEBSOCKET_CONNECTION)
    manager.cleanup_old_state(0)
