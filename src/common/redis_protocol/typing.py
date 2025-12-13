from __future__ import annotations

"""
Typing helpers for redis.asyncio usage.

redis-py exposes unified sync/async command signatures that confuse static type
checkers like Pyright. These helpers provide narrow aliases that reflect the
async behavior we rely on in the codebase.
"""


from typing import TYPE_CHECKING, Awaitable, TypeVar, cast

from redis import asyncio as redis_asyncio

if TYPE_CHECKING:
    from redis.asyncio import Redis as RedisClient
else:  # pragma: no cover - runtime alias for typing-only import
    RedisClient = redis_asyncio.Redis

T = TypeVar("T")


def ensure_awaitable(result: "Awaitable[T] | T") -> Awaitable[T]:
    """
    Coerce redis command results into awaitables for typing purposes.

    The redis.asyncio client always returns awaitables at runtime, but redis-py's
    type hints use a sync/async union to support both variants. Casting the result
    keeps our code compliant with Pyright without changing runtime behavior.
    """

    return cast(Awaitable[T], result)


__all__ = ["RedisClient", "ensure_awaitable"]
