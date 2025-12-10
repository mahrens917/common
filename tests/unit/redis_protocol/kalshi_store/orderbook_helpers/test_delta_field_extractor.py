"""Tests for delta field extractor module."""

from __future__ import annotations

from common.redis_protocol.kalshi_store.orderbook_helpers.delta_field_extractor import (
    DeltaFieldExtractor,
)


class TestDeltaFieldExtractor:
    """Tests for DeltaFieldExtractor class."""

    def test_extract_fields_valid_data(self) -> None:
        """Extracts fields from valid data."""
        msg_data = {"side": "YES", "price": 50.0, "delta": 100.0}

        side, price, delta = DeltaFieldExtractor.extract_fields(msg_data)

        assert side == "yes"
        assert price == 50.0
        assert delta == 100.0

    def test_extract_fields_missing_side(self) -> None:
        """Returns empty string for side when missing (converted to lowercase)."""
        msg_data = {"price": 50.0, "delta": 100.0}

        side, price, delta = DeltaFieldExtractor.extract_fields(msg_data)

        assert side == ""
        assert price == 50.0
        assert delta == 100.0

    def test_extract_fields_missing_price(self) -> None:
        """Returns None tuple for missing price."""
        msg_data = {"side": "yes", "delta": 100.0}

        result = DeltaFieldExtractor.extract_fields(msg_data)

        assert result == (None, None, None)

    def test_extract_fields_invalid_price_type(self) -> None:
        """Returns None tuple for invalid price type."""
        msg_data = {"side": "yes", "price": "invalid", "delta": 100.0}

        result = DeltaFieldExtractor.extract_fields(msg_data)

        assert result == (None, None, None)

    def test_extract_fields_invalid_delta_type(self) -> None:
        """Returns None tuple for invalid delta type."""
        msg_data = {"side": "yes", "price": 50.0, "delta": "invalid"}

        result = DeltaFieldExtractor.extract_fields(msg_data)

        assert result == (None, None, None)

    def test_convert_side_and_price_yes(self) -> None:
        """Converts yes side to yes_bids field."""
        field, price = DeltaFieldExtractor.convert_side_and_price("yes", 50.0)

        assert field == "yes_bids"
        assert price == "50.0"

    def test_convert_side_and_price_no(self) -> None:
        """Converts no side to yes_asks field with price conversion."""
        field, price = DeltaFieldExtractor.convert_side_and_price("no", 40.0)

        assert field == "yes_asks"
        assert price == "60.0"

    def test_convert_side_and_price_unknown(self) -> None:
        """Returns None tuple for unknown side."""
        result = DeltaFieldExtractor.convert_side_and_price("unknown", 50.0)

        assert result == (None, None)
