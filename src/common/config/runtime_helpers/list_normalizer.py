"""List normalization utilities for environment variables."""

from __future__ import annotations

from typing import Iterable, Sequence


class ListNormalizer:
    """Normalizes delimited list values from environment variables."""

    @staticmethod
    def split_and_normalize(
        raw_value: str,
        separator: str,
        strip_items: bool,
    ) -> list[str]:
        """
        Split raw value by separator and normalize items.

        Args:
            raw_value: Raw string value
            separator: Delimiter (empty string means no splitting)
            strip_items: Whether to strip whitespace from items

        Returns:
            List of normalized string items
        """
        parts = ListNormalizer._split_value(raw_value, separator)
        return ListNormalizer._normalize_items(parts, strip_items)

    @staticmethod
    def deduplicate_preserving_order(items: Sequence[str]) -> tuple[str, ...]:
        """
        Remove duplicates while preserving order.

        Args:
            items: Sequence of items

        Returns:
            Tuple with duplicates removed
        """
        seen: set[str] = set()
        deduped: list[str] = []

        for item in items:
            if item not in seen:
                deduped.append(item)
                seen.add(item)

        return tuple(deduped)

    @staticmethod
    def _split_value(raw_value: str, separator: str) -> Iterable[str]:
        """Split value by separator."""
        if separator:
            return raw_value.split(separator)
        return [raw_value]

    @staticmethod
    def _normalize_items(parts: Iterable[str], strip_items: bool) -> list[str]:
        """Normalize individual items."""
        normalized_items: list[str] = []

        for item in parts:
            candidate = item.strip() if strip_items else item
            if strip_items and candidate == "":
                continue
            normalized_items.append(candidate)

        return normalized_items
