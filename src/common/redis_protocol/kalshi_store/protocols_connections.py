from __future__ import annotations

from typing import Any, Dict, Protocol, Tuple

from redis.asyncio import Redis


class IConnectionDelegator(Protocol):
    """Protocol for connection delegation operations."""

    async def get_redis(self) -> Redis:
        """Get Redis connection."""
        ...

    def reset_connection_state(self) -> None:
        """Reset connection state."""
        ...

    async def close_redis_client(self, redis_client: Any) -> None:
        """Close Redis client."""
        ...

    def resolve_connection_settings(self) -> Dict[str, Any]:
        """Resolve connection settings."""
        ...

    async def acquire_pool(self, *, allow_reuse: bool) -> Redis:
        """Acquire connection pool."""
        ...

    async def create_redis_client(self) -> Redis:
        """Create Redis client."""
        ...

    async def verify_connection(self, redis: Any) -> Tuple[bool, bool]:
        """Verify connection health."""
        ...

    async def ping_connection(self, redis: Any, *, timeout: float = 5.0) -> Tuple[bool, bool]:
        """Ping connection with timeout."""
        ...

    async def connect_with_retry(
        self,
        *,
        allow_reuse: bool = True,
        context: str = "facade_connection",
        attempts: int = 3,
        retry_delay: float = 0.1,
    ) -> bool:
        """Connect with retry logic."""
        ...

    async def ensure_redis_connection(self) -> bool:
        """Ensure Redis connection is available."""
        ...

    async def attach_redis_client(
        self,
        redis_client: Redis,
        *,
        health_check_timeout: float = 5.0,
    ) -> None:
        """Attach external Redis client."""
        ...

    def ensure_ready(self) -> None:
        """Ensure store is ready for operations."""
        ...

    async def initialize(self) -> bool:
        """Initialize Redis connection."""
        ...

    async def close(self) -> None:
        """Close Redis connection."""
        ...
