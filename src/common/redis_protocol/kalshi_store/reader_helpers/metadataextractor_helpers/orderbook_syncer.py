"""
Orderbook Syncer - Synchronize top-of-book fields

Aligns scalar YES side fields with JSON orderbook payload.
"""

from typing import Any, Dict

from ...utils_coercion import sync_top_of_book_fields as canonical_sync_top_of_book


class OrderbookSyncer:
    """Synchronize orderbook top-of-book fields"""

    @staticmethod
    def sync_top_of_book_fields(snapshot: Dict[str, Any]) -> None:
        """Delegate to canonical top-of-book sync to keep logic consistent."""
        _sync_top_of_book_fields(snapshot)


def _sync_top_of_book_fields(snapshot: Dict[str, Any]) -> None:
    """Module-level helper retained for backward-compatible patching in tests."""
    canonical_sync_top_of_book(snapshot)
