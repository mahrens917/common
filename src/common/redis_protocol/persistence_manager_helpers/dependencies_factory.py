"""Dependency factory for RedisPersistenceManager."""

from dataclasses import dataclass
from typing import Any, Optional

from . import (
    ConfigOrchestrator,
    ConnectionManager,
    DataSerializer,
    KeyScanner,
    PersistenceCoordinator,
    SnapshotManager,
    ValidationManager,
)


@dataclass
class RedisPersistenceManagerDependencies:
    """Dependencies for RedisPersistenceManager."""  # gitleaks:allow

    connection: ConnectionManager
    configorchestrator: ConfigOrchestrator
    snapshot: SnapshotManager
    keyscanner: KeyScanner
    dataserializer: DataSerializer
    validation: ValidationManager


class RedisPersistenceManagerDependenciesFactory:  # gitleaks:allow
    """Factory for creating RedisPersistenceManager dependencies."""

    @staticmethod
    def create(
        redis: Optional[Any] = None,
    ) -> RedisPersistenceManagerDependencies:  # gitleaks:allow
        """
        Create all dependencies for RedisPersistenceManager.

        Args:
            redis: Optional Redis connection

        Returns:
            RedisPersistenceManager dependency bundle.
        """
        connection = ConnectionManager()
        if redis:
            connection.set_redis(redis)

        coordinator = PersistenceCoordinator()
        snapshot = SnapshotManager()

        configorchestrator = ConfigOrchestrator(coordinator, snapshot)
        keyscanner = KeyScanner()
        dataserializer = DataSerializer()
        validation = ValidationManager()

        return RedisPersistenceManagerDependencies(  # gitleaks:allow
            connection=connection,
            configorchestrator=configorchestrator,
            snapshot=snapshot,
            keyscanner=keyscanner,
            dataserializer=dataserializer,
            validation=validation,
        )
