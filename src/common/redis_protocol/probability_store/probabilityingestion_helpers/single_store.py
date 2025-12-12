"""Single probability storage logic."""

import logging
import math
from typing import Any, Dict

from ...error_types import REDIS_ERRORS
from ...probability_payloads import build_probability_record
from ...typing import ensure_awaitable
from ..exceptions import ProbabilityStoreError
from ..probability_data_config import ProbabilityData
from ..redis_provider_mixin import RedisProviderMixin

logger = logging.getLogger(__name__)


class SingleStore(RedisProviderMixin):
    """Handles storage of single probability entries."""

    async def store_probability(self, data: ProbabilityData) -> None:
        """
        Store a single probability entry.

        Args:
            data: ProbabilityData configuration object

        Raises:
            ProbabilityStoreError: If storage fails
        """
        currency_upper = data.currency.upper()
        payload: Dict[str, Any] = {
            "strike_type": data.strike_type,
            "probability": data.probability,
            "error": data.error,
            "confidence": data.confidence,
        }
        if data.probability_range is not None:
            range_low, range_high = data.probability_range
            payload["range_low"] = range_low
            payload["range_high"] = range_high

        try:
            record = build_probability_record(
                currency_upper,
                data.expiry,
                data.strike,
                payload,
                default_missing_event_ticker=False,
            )
        except (ValueError, TypeError) as exc:  # policy_guard: allow-silent-handler
            raise ProbabilityStoreError(
                f"Failed to build probability record for {currency_upper}:{data.expiry}:{data.strike_type}:{data.strike}"
            ) from exc

        if not record.fields:
            raise ProbabilityStoreError(f"No data to store for key: {record.key}")

        if isinstance(data.error, float) and math.isnan(data.error):
            record.fields["error"] = "NaN"
        if isinstance(data.confidence, float) and math.isnan(data.confidence):
            record.fields["confidence"] = "NaN"

        try:
            redis = await self._redis_provider()
            await ensure_awaitable(redis.hset(record.key, mapping=record.fields))
            logger.debug("Stored single probability entry for key: %s", record.key)
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            raise ProbabilityStoreError(f"Failed to store single probability for {record.key}") from exc
