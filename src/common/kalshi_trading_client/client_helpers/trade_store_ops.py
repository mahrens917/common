from __future__ import annotations

"""Trade store operations and lifecycle management."""


from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from common.redis_protocol.trade_store import TradeStore
    from common.trading import TradeStoreManager


class TradeStoreOperations:
    """Manages trade store operations."""

    @staticmethod
    async def ensure_trade_store(
        manager: TradeStoreManager, *, create: bool
    ) -> Optional[TradeStore]:
        """Ensure trade store exists, optionally creating it."""
        return await manager.ensure(create=create)

    @staticmethod
    async def get_trade_store(manager: TradeStoreManager) -> TradeStore:
        """Get or create trade store."""
        return await manager.get_or_create()

    @staticmethod
    async def require_trade_store(manager: TradeStoreManager) -> TradeStore:
        """Require and return trade store, updating reference."""
        return await manager.get_or_create()

    @staticmethod
    async def maybe_get_trade_store(manager: TradeStoreManager) -> Optional[TradeStore]:
        """Maybe get trade store without creating."""
        return await manager.maybe_get()
