"""Pagination helper for market fetching."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PaginationHelper:
    """Handles pagination cursor logic."""

    @staticmethod
    def should_continue(cursor: Optional[str], seen_cursors: set[str | None], label: str) -> bool:
        """Check if pagination should continue."""
        if cursor in seen_cursors:
            logger.warning("Received repeated cursor '%s' for %s; stopping pagination", cursor, label)
            return False
        return True

    @staticmethod
    def extract_cursor(payload: dict) -> Optional[str]:
        """Extract next cursor from payload."""
        cursor_val = payload.get("cursor")
        if cursor_val is None or not isinstance(cursor_val, str) or not cursor_val.strip():
            return None
        return cursor_val
