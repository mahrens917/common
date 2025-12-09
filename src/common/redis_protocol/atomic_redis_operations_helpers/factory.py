"""
Factory for creating atomic Redis operations components.

Handles dependency wiring for all helper components.
"""

from redis.asyncio import Redis

from .. import config
from .data_converter import DataConverter
from .data_fetcher import DataFetcher
from .deletion_validator import DeletionValidator
from .field_validator import FieldValidator
from .spread_validator import SpreadValidator
from .transaction_writer import TransactionWriter

# Retry configuration - drawn from real production requirements
MAX_READ_RETRIES = config.REDIS_MAX_RETRIES


class AtomicOperationsFactory:
    """Factory for creating atomic operations components."""

    @staticmethod
    def create_components(redis_client: Redis) -> dict:
        """
        Create all helper components with proper dependency wiring.

        Args:
            redis_client: Redis connection with decode_responses=True

        Returns:
            Dictionary containing all helper components
        """
        return {
            "transaction_writer": TransactionWriter(redis_client),
            "data_fetcher": DataFetcher(redis_client),
            "field_validator": FieldValidator(MAX_READ_RETRIES),
            "data_converter": DataConverter(MAX_READ_RETRIES),
            "spread_validator": SpreadValidator(MAX_READ_RETRIES),
            "deletion_validator": DeletionValidator(redis_client),
        }
