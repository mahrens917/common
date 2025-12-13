from __future__ import annotations

"""
Trade store lifecycle helpers for the Kalshi trading client.
"""


import asyncio
import inspect
import logging
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:  # pragma: no cover - import for type checking only
    from ..redis_protocol.trade_store import TradeStore

from ..redis_protocol.error_types import REDIS_ERRORS
from ..redis_protocol.trade_store import TradeStoreError

CLOSE_ERRORS = REDIS_ERRORS + (RuntimeError,)

logger = logging.getLogger(__name__)


class TradeStoreManager:
    """
    Coordinates access to the trade store used by the trading client.
    """

    def __init__(
        self,
        *,
        kalshi_client,
        store_supplier: Callable[[], Optional["TradeStore"]],
    ) -> None:
        self._kalshi_client = kalshi_client
        self._store_supplier = store_supplier
        self._managed_store: Optional["TradeStore"] = None
        self._lock = asyncio.Lock()

    async def get_or_create(self) -> "TradeStore":
        store = await self.ensure(create=True)
        if store is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Trade store could not be created")
        return store

    async def maybe_get(self) -> Optional["TradeStore"]:
        return await self.ensure(create=False)

    async def ensure(self, *, create: bool) -> Optional["TradeStore"]:
        """
        Ensure a trade store is available. Returns None when no store exists and
        create is False.
        """
        external_store = self._store_supplier()
        if external_store is not None:
            await self._initialize_store(external_store)
            self._attach_store(external_store)
            return external_store

        if not create:
            return None

        async with self._lock:
            if self._managed_store is None:
                from ..redis_protocol.trade_store import TradeStore

                managed_store = TradeStore()
                await self._initialize_store(managed_store)
                self._managed_store = managed_store
            else:
                await self._initialize_store(self._managed_store)

            self._attach_store(self._managed_store)
            return self._managed_store

    async def close_managed(self) -> None:
        """Close the internally managed store, if one exists."""
        if self._managed_store is None:
            return
        try:
            await self._managed_store.close()
        except CLOSE_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.warning("Error while closing managed trade store: %s", exc, exc_info=True)
        finally:
            self._managed_store = None

    async def _initialize_store(self, store: "TradeStore") -> None:
        initializer = getattr(store, "initialize", None)
        if callable(initializer):
            result = initializer()
            if inspect.isawaitable(result):
                outcome = await result
                if isinstance(outcome, bool) and not outcome:
                    raise TradeStoreError("Trade store initialization returned False")

    def _attach_store(self, store: Optional["TradeStore"]) -> None:
        if store is None:
            return
        attach = getattr(self._kalshi_client, "attach_trade_store", None)
        if callable(attach):
            try:
                attach(store)
            except (  # policy_guard: allow-silent-handler
                RuntimeError,
                ValueError,
                TypeError,
            ) as exc:  # pragma: no cover - attach errors should not break workflow
                logger.debug("Kalshi client attach_trade_store raised: %s", exc, exc_info=True)

    def override_store_supplier(self, supplier: Callable[[], Optional["TradeStore"]]) -> None:
        """Replace the trade store supplier used when the client overrides the store."""
        self._store_supplier = supplier
