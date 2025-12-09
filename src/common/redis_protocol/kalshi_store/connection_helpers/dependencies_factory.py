"""Dependency factory for RedisConnectionManager."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .connection_verifier import ConnectionVerifier
from .lifecycle_coordinator import LifecycleCoordinator
from .method_adapter import MethodAdapter
from .pool_manager import PoolManager
from .property_accessor import PropertyAccessor
from .property_manager import PropertyManager
from .retry_handler import RetryHandler

if TYPE_CHECKING:  # pragma: no cover
    import logging

    from ..connection import RedisConnectionManager


@dataclass
class RedisConnectionDependencies:
    """Container for RedisConnectionManager dependencies."""

    property_manager: PropertyManager
    property_accessor: PropertyAccessor
    pool_manager: PoolManager
    connection_verifier: ConnectionVerifier
    retry_handler: RetryHandler
    lifecycle: LifecycleCoordinator
    method_adapter: MethodAdapter


class RedisConnectionDependenciesFactory:
    """Factory for creating RedisConnectionManager dependencies."""

    @staticmethod
    def create(
        manager: "RedisConnectionManager", logger: "logging.Logger"
    ) -> RedisConnectionDependencies:
        """Create dependencies for RedisConnectionManager."""
        property_manager = PropertyManager(manager)
        property_accessor = PropertyAccessor(manager)
        pool_manager = PoolManager()
        connection_verifier = ConnectionVerifier()
        retry_handler = RetryHandler(logger)
        lifecycle = LifecycleCoordinator(manager)
        method_adapter = MethodAdapter(manager)

        return RedisConnectionDependencies(
            property_manager=property_manager,
            property_accessor=property_accessor,
            pool_manager=pool_manager,
            connection_verifier=connection_verifier,
            retry_handler=retry_handler,
            lifecycle=lifecycle,
            method_adapter=method_adapter,
        )
