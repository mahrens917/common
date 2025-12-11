from __future__ import annotations

"""Verification helpers for the probability store."""


import inspect
from typing import Iterable, Optional

from redis.asyncio import Redis

from .exceptions import ProbabilityStoreVerificationError


async def verify_probability_storage(redis: Redis, sample_keys: Iterable[str], currency: str) -> None:
    keys = list(sample_keys)
    if not keys:
        return

    pipeline = redis.pipeline()
    if inspect.isawaitable(pipeline):
        pipeline = await pipeline

    for key in keys:
        pipeline.exists(key)

    results = await pipeline.execute()
    keys_verified = sum(1 for result in results if result)

    if keys_verified != len(keys):
        await run_direct_connectivity_test(redis, currency)
        missing = sorted(key for key, exists in zip(keys, results) if not exists)
        raise ProbabilityStoreVerificationError(f"Probability storage verification failed for {currency}: missing keys={missing}")


async def run_direct_connectivity_test(redis: Optional[Redis], currency: str) -> None:
    if redis is None:
        raise ProbabilityStoreVerificationError(f"Cannot run connectivity test for {currency}: Redis connection is None")

    test_key = f"probabilities:{currency}:connectivity_probe"
    await redis.set(test_key, "probability-store-connectivity")
    await redis.get(test_key)
    await redis.delete(test_key)


__all__ = ["verify_probability_storage", "run_direct_connectivity_test"]
