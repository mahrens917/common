"""State management helpers for backoff tracking."""

import logging
import time
from typing import Any, Dict, Optional

from .state_cleaner import StateCleaner
from .types import BackoffConfig, BackoffType

logger = logging.getLogger(__name__)


def _service_bucket(backoff_state: Dict, service_name: str) -> Dict[BackoffType, Dict[str, Any]]:
    return backoff_state.setdefault(service_name, {})


def _init_state(bucket: Dict[BackoffType, Dict[str, Any]], backoff_type: BackoffType) -> Dict[str, Any]:
    return bucket.setdefault(
        backoff_type,
        {"attempt": 0, "last_failure_time": time.time(), "consecutive_failures": 0},
    )


def _ensure_state(backoff_state: Dict, service_name: str, backoff_type: BackoffType) -> Dict[str, Any]:
    bucket = _service_bucket(backoff_state, service_name)
    return _init_state(bucket, backoff_type)


def _reset_state(backoff_state: Dict, service_name: str, backoff_type: Optional[BackoffType]):
    bucket = backoff_state.get(service_name)
    if not bucket:
        return
    if backoff_type is None:
        bucket.clear()
        logger.debug("[BackoffManager] Reset all backoff state for %s", service_name)
        return
    if backoff_type in bucket:
        del bucket[backoff_type]
        logger.debug("[BackoffManager] Reset backoff state for %s/%s", service_name, backoff_type.value)


def _info_for_missing_state(config: BackoffConfig) -> Dict[str, Any]:
    return {
        "attempt": 0,
        "consecutive_failures": 0,
        "last_failure_time": None,
        "max_attempts": config.max_attempts,
        "can_retry": True,
    }


def _info_for_state(state: Dict[str, Any], config: BackoffConfig) -> Dict[str, Any]:
    return {
        "attempt": state["attempt"],
        "consecutive_failures": state["consecutive_failures"],
        "last_failure_time": state["last_failure_time"],
        "max_attempts": config.max_attempts,
        "can_retry": state["attempt"] < config.max_attempts,
    }


class BackoffStateManager:
    """Manages backoff state tracking."""

    def __init__(self):
        self.backoff_state: Dict[str, Dict[BackoffType, Dict[str, Any]]] = {}

    def get_or_initialize_state(self, service_name: str, backoff_type: BackoffType) -> Dict[str, Any]:
        return _ensure_state(self.backoff_state, service_name, backoff_type)

    def update_failure_state(self, service_name: str, backoff_type: BackoffType) -> int:
        state = _ensure_state(self.backoff_state, service_name, backoff_type)
        state["attempt"] += 1
        state["consecutive_failures"] += 1
        state["last_failure_time"] = time.time()
        return state["attempt"]

    def reset_backoff(self, service_name: str, backoff_type: Optional[BackoffType] = None):
        _reset_state(self.backoff_state, service_name, backoff_type)

    def cleanup_old_state(self, max_age_seconds: int = 3600):
        StateCleaner.cleanup_old_state(self.backoff_state, max_age_seconds)

    def get_backoff_info(self, service_name: str, backoff_type: BackoffType, config: BackoffConfig) -> Dict[str, Any]:
        bucket = self.backoff_state.get(service_name) or {}
        state = bucket.get(backoff_type)
        if not state:
            return _info_for_missing_state(config)
        return _info_for_state(state, config)
