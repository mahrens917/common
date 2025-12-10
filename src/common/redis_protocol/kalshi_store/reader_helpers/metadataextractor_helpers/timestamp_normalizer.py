"""
Timestamp Normalizer - Normalize timestamp values

Delegates to KalshiMetadataAdapter for timestamp normalization.
"""

from typing import Any, Optional


class TimestampNormalizer:
    """Normalize timestamp values to strings"""

    @staticmethod
    def normalize_timestamp(timestamp: Any) -> Optional[str]:
        """Normalize timestamp to string format."""
        # Late import to avoid circular dependency
        from common.redis_protocol.kalshi_store.metadata_helpers.timestamp_normalization import (
            normalize_timestamp as _normalize_timestamp,
        )

        return _normalize_timestamp(timestamp)
