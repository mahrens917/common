from __future__ import annotations

"""Pipeline helpers for the probability store."""

import inspect
from typing import Any

from redis.asyncio import Redis


async def create_pipeline(redis: Redis):
    pipeline = redis.pipeline()
    if inspect.isawaitable(pipeline):
        pipeline = await pipeline
    return pipeline


async def execute_pipeline(pipeline: Any):
    results = pipeline.execute()
    if inspect.isawaitable(results):
        results = await results
    return results


__all__ = ["create_pipeline", "execute_pipeline"]
