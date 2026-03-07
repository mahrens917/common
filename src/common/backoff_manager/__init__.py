"""Configurable exponential backoff manager with jitter and state tracking."""

from __future__ import annotations

import logging
import random as _random
from typing import Any, Dict, Final, Optional

from common.backoff_manager_helpers import (
    DEFAULT_BACKOFF_CONFIGS,
    BackoffConfig,
    BackoffType,
)
from common.backoff_manager_helpers.state_manager import BackoffStateManager

__all__ = ["BackoffManager", "BackoffConfig", "BackoffType"]

logger = logging.getLogger(__name__)

_MIN_DELAY = 0.1
_SECURE_RANDOM: Final = _random.SystemRandom()


def _calculate_base_delay(config: BackoffConfig, attempt: int) -> float:
    return min(config.initial_delay * (config.multiplier ** (attempt - 1)), config.max_delay)


def _apply_network_multiplier(
    base_delay: float,
    config: BackoffConfig,
    network_health_monitor,
    service_name: str,
) -> float:
    if network_health_monitor and not network_health_monitor.is_network_healthy():
        if network_health_monitor.is_network_degraded() or network_health_monitor.is_network_offline():
            adjusted_delay = base_delay * config.network_degraded_multiplier
            logger.debug(f"[BackoffManager] Applied network degraded multiplier ({config.network_degraded_multiplier}x) for {service_name}")
            return adjusted_delay
    return base_delay


def _apply_jitter(base_delay: float, jitter_range: float) -> float:
    jitter_amount = base_delay * jitter_range
    jitter = _SECURE_RANDOM.uniform(-jitter_amount, jitter_amount)
    return max(_MIN_DELAY, base_delay + jitter)


def _calculate_full_delay(
    config: BackoffConfig,
    attempt: int,
    network_health_monitor,
    service_name: str,
) -> float:
    base_delay = _calculate_base_delay(config, attempt)
    network_adjusted = _apply_network_multiplier(base_delay, config, network_health_monitor, service_name)
    final_delay = _apply_jitter(network_adjusted, config.jitter_range)

    logger.debug(
        f"[BackoffManager] Calculated backoff for {service_name}: "
        f"attempt={attempt}, base_delay={base_delay:.2f}s, final_delay={final_delay:.2f}s"
    )

    return final_delay


def _should_retry(
    state_manager: BackoffStateManager,
    service_name: str,
    backoff_type: BackoffType,
    config: BackoffConfig,
) -> bool:
    info = state_manager.get_backoff_info(service_name, backoff_type, config)

    result = info["can_retry"]
    if not result:
        logger.warning(f"[BackoffManager] Max attempts ({config.max_attempts}) reached for {service_name}/{backoff_type.value}")

    return result


def _get_backoff_info(
    state_manager: BackoffStateManager,
    service_name: str,
    backoff_type: BackoffType,
    config: BackoffConfig,
    next_delay: float,
) -> Dict[str, Any]:
    info = state_manager.get_backoff_info(service_name, backoff_type, config)
    info["next_delay"] = next_delay
    return info


def _get_all_backoff_status(
    state_manager: BackoffStateManager,
    configs: Dict[BackoffType, BackoffConfig],
    delay_calculator,
) -> Dict[str, Dict[str, Any]]:
    status = {}

    for service_name, service_state in state_manager.backoff_state.items():
        status[service_name] = {}
        for backoff_type, state in service_state.items():
            config = configs.get(backoff_type, configs[BackoffType.GENERAL_FAILURE])
            info = state_manager.get_backoff_info(service_name, backoff_type, config)

            next_delay = delay_calculator(service_name, backoff_type, state["attempt"] + 1)
            info["next_delay"] = next_delay

            status[service_name][backoff_type.value] = info

    return status


class BackoffManager:
    """Configurable exponential backoff with jitter, network awareness, and state tracking."""

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

    def calculate_delay(
        self,
        service_name: str,
        backoff_type: BackoffType,
        attempt: Optional[int] = None,
    ) -> float:
        config = self.get_config(backoff_type)
        current_attempt = attempt if attempt is not None else self.state_manager.update_failure_state(service_name, backoff_type)
        return _calculate_full_delay(config, current_attempt, self.network_health_monitor, service_name)

    def should_retry(self, service_name: str, backoff_type: BackoffType) -> bool:
        config = self.get_config(backoff_type)
        return _should_retry(self.state_manager, service_name, backoff_type, config)

    def reset_backoff(self, service_name: str, backoff_type: Optional[BackoffType] = None):
        self.state_manager.reset_backoff(service_name, backoff_type)

    def get_backoff_info(self, service_name: str, backoff_type: BackoffType) -> Dict[str, Any]:
        config = self.get_config(backoff_type)
        state = self.state_manager.get_or_initialize_state(service_name, backoff_type)
        next_delay = self.calculate_delay(service_name, backoff_type, state["attempt"] + 1)
        return _get_backoff_info(self.state_manager, service_name, backoff_type, config, next_delay)

    def get_all_backoff_status(self) -> Dict[str, Dict[str, Any]]:
        return _get_all_backoff_status(self.state_manager, self.configs, self.calculate_delay)

    def cleanup_old_state(self, max_age_seconds: int = 3600) -> None:
        self.state_manager.cleanup_old_state(max_age_seconds)
