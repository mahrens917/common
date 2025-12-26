"""Tests for pagination_helper module."""

from common.kalshi_catalog_helpers.market_fetcher_helpers.pagination_helper import (
    PaginationHelper,
)


class TestPaginationHelper:
    """Tests for PaginationHelper class."""

    def test_should_continue_with_new_cursor(self) -> None:
        """Test should_continue returns True for new cursor."""
        seen_cursors: set[str | None] = {"cursor1", "cursor2"}
        result = PaginationHelper.should_continue("cursor3", seen_cursors, "test_label")
        assert result is True

    def test_should_continue_with_repeated_cursor(self) -> None:
        """Test should_continue returns False for repeated cursor."""
        seen_cursors: set[str | None] = {"cursor1", "cursor2"}
        result = PaginationHelper.should_continue("cursor1", seen_cursors, "test_label")
        assert result is False

    def test_should_continue_with_none_cursor_not_seen(self) -> None:
        """Test should_continue returns True for None cursor not seen."""
        seen_cursors: set[str | None] = {"cursor1"}
        result = PaginationHelper.should_continue(None, seen_cursors, "test_label")
        assert result is True

    def test_should_continue_with_none_cursor_already_seen(self) -> None:
        """Test should_continue returns False for None cursor already seen."""
        seen_cursors: set[str | None] = {None, "cursor1"}
        result = PaginationHelper.should_continue(None, seen_cursors, "test_label")
        assert result is False

    def test_extract_cursor_with_valid_string(self) -> None:
        """Test extract_cursor returns cursor string."""
        payload = {"cursor": "next_page_cursor", "data": []}
        result = PaginationHelper.extract_cursor(payload)
        assert result == "next_page_cursor"

    def test_extract_cursor_with_none(self) -> None:
        """Test extract_cursor returns None when cursor is None."""
        payload = {"cursor": None, "data": []}
        result = PaginationHelper.extract_cursor(payload)
        assert result is None

    def test_extract_cursor_with_missing_key(self) -> None:
        """Test extract_cursor returns None when cursor key is missing."""
        payload = {"data": []}
        result = PaginationHelper.extract_cursor(payload)
        assert result is None

    def test_extract_cursor_with_empty_string(self) -> None:
        """Test extract_cursor returns None for empty string."""
        payload = {"cursor": "", "data": []}
        result = PaginationHelper.extract_cursor(payload)
        assert result is None

    def test_extract_cursor_with_whitespace_string(self) -> None:
        """Test extract_cursor returns None for whitespace-only string."""
        payload = {"cursor": "   ", "data": []}
        result = PaginationHelper.extract_cursor(payload)
        assert result is None

    def test_extract_cursor_with_non_string(self) -> None:
        """Test extract_cursor returns None for non-string cursor."""
        payload = {"cursor": 12345, "data": []}
        result = PaginationHelper.extract_cursor(payload)
        assert result is None
