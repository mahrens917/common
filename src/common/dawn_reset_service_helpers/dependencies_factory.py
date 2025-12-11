"""Dependency factory for DawnResetService."""

from dataclasses import dataclass
from typing import Optional, TypeVar

from .alert_manager import AlertManager
from .cache_manager import CacheManager
from .dawn_calculator import DawnCalculator
from .field_reset_manager import FieldResetManager
from .logger import DawnResetLogger
from .timestamp_resolver import TimestampResolver


@dataclass
class DawnResetServiceDependencies:
    """Dependencies for DawnResetService."""

    dawn_calculator: DawnCalculator
    cache_manager: CacheManager
    timestamp_resolver: TimestampResolver
    field_reset_manager: FieldResetManager
    alert_manager: AlertManager
    logger: DawnResetLogger


@dataclass
class CreateOrUseConfig:
    """Configuration for create_or_use factory method."""

    telegram_handler: Optional[object] = None
    dawn_calculator: Optional[DawnCalculator] = None
    cache_manager: Optional[CacheManager] = None
    timestamp_resolver: Optional[TimestampResolver] = None
    field_reset_manager: Optional[FieldResetManager] = None
    alert_manager: Optional[AlertManager] = None
    logger: Optional[DawnResetLogger] = None
    calculate_dawn_fn: Optional[object] = None


T = TypeVar("T")


class DawnResetServiceDependenciesFactory:
    """Factory for creating DawnResetService dependencies."""

    @staticmethod
    def create(telegram_handler=None, calculate_dawn_fn=None) -> DawnResetServiceDependencies:
        """
        Build a complete dependencies object.
        """
        dawn_calculator = DawnCalculator(calculate_dawn_fn)
        cache_manager = CacheManager()
        timestamp_resolver = TimestampResolver()
        field_reset_manager = FieldResetManager(dawn_calculator, timestamp_resolver)
        alert_manager = AlertManager(telegram_handler)
        logger = DawnResetLogger()

        return DawnResetServiceDependencies(
            dawn_calculator=dawn_calculator,
            cache_manager=cache_manager,
            timestamp_resolver=timestamp_resolver,
            field_reset_manager=field_reset_manager,
            alert_manager=alert_manager,
            logger=logger,
        )

    @staticmethod
    def create_or_use(config: CreateOrUseConfig) -> DawnResetServiceDependencies:
        """Create dependencies only if not all are provided."""
        provided = {
            "dawn_calculator": config.dawn_calculator,
            "cache_manager": config.cache_manager,
            "timestamp_resolver": config.timestamp_resolver,
            "field_reset_manager": config.field_reset_manager,
            "alert_manager": config.alert_manager,
            "logger": config.logger,
        }

        if all(value is not None for value in provided.values()):
            return DawnResetServiceDependencies(**provided)

        defaults = DawnResetServiceDependenciesFactory.create(config.telegram_handler, calculate_dawn_fn=config.calculate_dawn_fn)

        return DawnResetServiceDependencies(
            dawn_calculator=_use_default(config.dawn_calculator, defaults.dawn_calculator),
            cache_manager=_use_default(config.cache_manager, defaults.cache_manager),
            timestamp_resolver=_use_default(config.timestamp_resolver, defaults.timestamp_resolver),
            field_reset_manager=_use_default(config.field_reset_manager, defaults.field_reset_manager),
            alert_manager=_use_default(config.alert_manager, defaults.alert_manager),
            logger=_use_default(config.logger, defaults.logger),
        )


def _use_default(value: Optional[T], alternate: T) -> T:
    """Return `value` if provided, otherwise the supplied alternate."""
    return value if value is not None else alternate
