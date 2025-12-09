from __future__ import annotations

"""Trade collection management."""


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..services import TradeCollectionController


class TradeCollectionManager:
    """Manages trade collection lifecycle."""

    @staticmethod
    async def start_collection(controller: TradeCollectionController) -> None:
        """Start trade collection."""
        await controller.start()

    @staticmethod
    async def stop_collection(controller: TradeCollectionController) -> None:
        """Stop trade collection."""
        await controller.stop()
