"""Redis key scanning for instruments."""

import logging
from typing import Any, Dict, List, Set, Tuple

from ....redis_schema import parse_deribit_market_key
from ... import config
from ...error_types import REDIS_ERRORS

logger = logging.getLogger(__name__)


class RedisInstrumentScanner:
    """Scans Redis for instrument keys and retrieves data."""

    def __init__(self, redis_getter):
        self._get_redis = redis_getter

    async def scan_and_fetch_instruments(
        self, currency: str
    ) -> List[Tuple[str, Any, Dict[str, Any]]]:
        try:
            logger.info("KEY_SCAN_DEBUG: Loading instruments for currency %s", currency)
            redis_client = await self._get_redis()
            pattern = f"markets:deribit:*:{currency.lower()}*"
            keys = await self._scan_keys(redis_client, pattern)
            if not keys:
                logger.warning("KEY_SCAN_DEBUG: No keys found for currency %s", currency)
                return []
            descriptors = self._parse_descriptors(keys, currency)
            if not descriptors:
                logger.warning("KEY_SCAN_DEBUG: No descriptors generated for %s", currency)
                return []
            data_blocks = await self._fetch_data(redis_client, descriptors)
            results = []
            for (key, descriptor), data in zip(descriptors, data_blocks):
                if data:
                    results.append((key, descriptor, data))
                else:
                    logger.debug("KEY_SCAN_DEBUG: Key %s returned no data", key)
            else:
                return results
        except REDIS_ERRORS as exc:
            logger.error("Error scanning instruments for %s: %s", currency, exc, exc_info=True)
            return []

    async def _scan_keys(self, redis_client, pattern: str) -> Set[str]:
        keys: Set[str] = set()
        cursor = 0
        while True:
            cursor, batch = await redis_client.scan(
                cursor=cursor, match=pattern, count=config.PDF_SCAN_COUNT
            )
            keys.update(batch)
            if cursor == 0:
                break
        return keys

    def _parse_descriptors(self, keys: Set[str], currency: str) -> List[Tuple[str, Any]]:
        descriptors = []
        for key in keys:
            try:
                descriptor = parse_deribit_market_key(key)
            except ValueError as exc:
                logger.debug("KEY_PARSE_DEBUG: skipping key %s (%s)", key, exc)
                continue
            if descriptor.currency.lower() != currency.lower():
                continue
            descriptors.append((key, descriptor))
        return descriptors

    async def _fetch_data(
        self, redis_client, descriptors: List[Tuple[str, Any]]
    ) -> List[Dict[str, Any]]:
        async with redis_client.pipeline() as pipe:
            for key, _ in descriptors:
                pipe.hgetall(key)
            return await pipe.execute()
