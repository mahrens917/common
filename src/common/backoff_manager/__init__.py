"""Configurable exponential backoff manager with jitter and state tracking."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Protocol, cast

from src.common.backoff_manager_helpers import (
    DEFAULT_BACKOFF_CONFIGS,
    BackoffConfig,
    BackoffType,
)
from src.common.backoff_manager_helpers.delay_calculator import DelayCalculator
from src.common.backoff_manager_helpers.retry_checker import RetryChecker
from src.common.backoff_manager_helpers.state_manager import BackoffStateManager
from src.common.backoff_manager_helpers.status_reporter import BackoffStatusReporter

__all__ = ["BackoffManager", "BackoffConfig", "BackoffType"]

logger = logging.getLogger(__name__)


class _BackoffBaseProtocol(Protocol):
    configs: Dict[BackoffType, BackoffConfig]
    network_health_monitor: Optional[Any]
    state_manager: BackoffStateManager

    def get_config(self, backoff_type: BackoffType) -> BackoffConfig: ...


class _BackoffStatusProtocol(_BackoffBaseProtocol, Protocol):
    def calculate_delay(
        self,
        service_name: str,
        backoff_type: BackoffType,
        attempt: Optional[int] = None,
    ) -> float: ...


class _BackoffBase:
    def __init__(
        self,
        network_health_monitor=None,
        custom_configs: Optional[Dict[BackoffType, BackoffConfig]] = None,
    ):
        self.network_health_monitor = network_health_monitor
        self.configs = DEFAULT_BACKOFF_CONFIGS.copy()
        if custom_configs:
            self.configs.update(custom_configs)
        self.state_manager = BackoffStateManager()
        logger.info("[BackoffManager] Initialized with %s configurations", len(self.configs))

    def get_config(self, backoff_type: BackoffType) -> BackoffConfig:
        return self.configs.get(backoff_type, self.configs[BackoffType.GENERAL_FAILURE])

    @property
    def backoff_state(self) -> Dict[str, Dict[BackoffType, Dict[str, Any]]]:
        return self.state_manager.backoff_state


class _BackoffDelayMixin:
    def calculate_delay(
        self,
        service_name: str,
        backoff_type: BackoffType,
        attempt: Optional[int] = None,
    ) -> float:
        context = cast(_BackoffBaseProtocol, self)
        config = context.get_config(backoff_type)
        current_attempt = (
            attempt
            if attempt is not None
            else context.state_manager.update_failure_state(service_name, backoff_type)
        )
        return DelayCalculator.calculate_full_delay(
            config, current_attempt, context.network_health_monitor, service_name
        )


class _BackoffRetryMixin:
    def should_retry(self, service_name: str, backoff_type: BackoffType) -> bool:
        context = cast(_BackoffBaseProtocol, self)
        config = context.get_config(backoff_type)
        return RetryChecker.should_retry(context.state_manager, service_name, backoff_type, config)

    def reset_backoff(self, service_name: str, backoff_type: Optional[BackoffType] = None):
        context = cast(_BackoffBaseProtocol, self)
        context.state_manager.reset_backoff(service_name, backoff_type)


class _BackoffStatusMixin:
    def get_backoff_info(
        self: _BackoffStatusProtocol, service_name: str, backoff_type: BackoffType
    ) -> Dict[str, Any]:
        config = self.get_config(backoff_type)
        state = self.state_manager.get_or_initialize_state(service_name, backoff_type)
        next_delay = self.calculate_delay(service_name, backoff_type, state["attempt"] + 1)
        return BackoffStatusReporter.get_backoff_info(
            self.state_manager, service_name, backoff_type, config, next_delay
        )

    def get_all_backoff_status(
        self: _BackoffStatusProtocol,
    ) -> Dict[str, Dict[str, Any]]:
        return BackoffStatusReporter.get_all_backoff_status(
            self.state_manager, self.configs, self.calculate_delay
        )

    def cleanup_old_state(self: _BackoffBaseProtocol, max_age_seconds: int = 3600) -> None:
        self.state_manager.cleanup_old_state(max_age_seconds)


class BackoffManager(
    _BackoffBase,
    _BackoffDelayMixin,
    _BackoffRetryMixin,
    _BackoffStatusMixin,
):
    """Public entry point combining initialization, delay, retry, and reporting."""

    pass
