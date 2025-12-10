"""Tests for metadata enricher module."""

from common.redis_protocol.market_normalization_helpers.metadata_enricher import (
    enrich_close_time,
    enrich_orderbook_defaults,
    enrich_status_field,
    enrich_strike_fields,
)


class TestEnrichStrikeFields:
    """Tests for enrich_strike_fields function."""

    def test_sets_strike_type(self) -> None:
        """Sets strike_type when missing."""
        enriched: dict = {}

        enrich_strike_fields(enriched, "greater", None, None, None)

        assert enriched["strike_type"] == "greater"

    def test_preserves_existing_strike_type(self) -> None:
        """Preserves existing strike_type."""
        enriched = {"strike_type": "less"}

        enrich_strike_fields(enriched, "greater", None, None, None)

        assert enriched["strike_type"] == "less"

    def test_sets_strike_value(self) -> None:
        """Sets strike from strike_value."""
        enriched: dict = {}

        enrich_strike_fields(enriched, "greater", None, None, 50000.0)

        assert enriched["strike"] == "50000.0"

    def test_preserves_existing_strike(self) -> None:
        """Preserves existing strike."""
        enriched = {"strike": "45000.0"}

        enrich_strike_fields(enriched, "greater", None, None, 50000.0)

        assert enriched["strike"] == "45000.0"

    def test_greater_sets_floor_strike(self) -> None:
        """Greater type sets floor_strike."""
        enriched: dict = {}

        enrich_strike_fields(enriched, "greater", 50000.0, None, None)

        assert enriched["floor_strike"] == "50000.0"

    def test_greater_sets_cap_to_inf(self) -> None:
        """Greater type sets cap_strike to inf."""
        enriched: dict = {}

        enrich_strike_fields(enriched, "greater", 50000.0, None, None)

        assert enriched["cap_strike"] == "inf"

    def test_greater_preserves_existing_cap(self) -> None:
        """Greater type preserves existing cap_strike."""
        enriched = {"cap_strike": "60000.0"}

        enrich_strike_fields(enriched, "greater", 50000.0, None, None)

        assert enriched["cap_strike"] == "60000.0"

    def test_less_sets_cap_strike(self) -> None:
        """Less type sets cap_strike."""
        enriched: dict = {}

        enrich_strike_fields(enriched, "less", None, 50000.0, None)

        assert enriched["cap_strike"] == "50000.0"

    def test_less_sets_floor_to_zero(self) -> None:
        """Less type sets floor_strike to zero."""
        enriched: dict = {}

        enrich_strike_fields(enriched, "less", None, 50000.0, None)

        assert enriched["floor_strike"] == "0"

    def test_less_preserves_existing_floor(self) -> None:
        """Less type preserves existing floor_strike."""
        enriched = {"floor_strike": "40000.0"}

        enrich_strike_fields(enriched, "less", None, 50000.0, None)

        assert enriched["floor_strike"] == "40000.0"

    def test_between_sets_empty_floor(self) -> None:
        """Between type sets floor_strike to empty string."""
        enriched: dict = {}

        enrich_strike_fields(enriched, "between", None, None, None)

        assert enriched["floor_strike"] == ""

    def test_between_sets_empty_cap(self) -> None:
        """Between type sets cap_strike to empty string."""
        enriched: dict = {}

        enrich_strike_fields(enriched, "between", None, None, None)

        assert enriched["cap_strike"] == ""

    def test_between_preserves_existing_floor(self) -> None:
        """Between type preserves existing floor_strike."""
        enriched = {"floor_strike": "50000.0"}

        enrich_strike_fields(enriched, "between", None, None, None)

        assert enriched["floor_strike"] == "50000.0"


class TestEnrichCloseTime:
    """Tests for enrich_close_time function."""

    def test_normalizes_existing_close_time(self) -> None:
        """Normalizes existing valid close_time."""
        enriched = {"close_time": "2025-01-15T12:00:00Z"}

        enrich_close_time(enriched, {})

        assert enriched["close_time"] == "2025-01-15T12:00:00+00:00"

    def test_uses_close_time_ms_as_fallback(self) -> None:
        """Uses close_time_ms when close_time is empty."""
        enriched = {"close_time": "", "close_time_ms": "1705320000000"}

        enrich_close_time(enriched, {})

        assert "close_time" in enriched

    def test_converts_string_ms_to_int(self) -> None:
        """Converts string close_time_ms to int."""
        enriched = {"close_time": None, "close_time_ms": "1705320000000"}

        enrich_close_time(enriched, {})

        assert "close_time" in enriched

    def test_handles_empty_close_time(self) -> None:
        """Handles empty close_time gracefully."""
        enriched = {"close_time": ""}

        enrich_close_time(enriched, {})

        assert "close_time" in enriched


class TestEnrichOrderbookDefaults:
    """Tests for enrich_orderbook_defaults function."""

    def test_adds_yes_bids(self) -> None:
        """Adds yes_bids default."""
        enriched: dict = {}

        enrich_orderbook_defaults(enriched)

        assert enriched["yes_bids"] == "{}"

    def test_adds_yes_asks(self) -> None:
        """Adds yes_asks default."""
        enriched: dict = {}

        enrich_orderbook_defaults(enriched)

        assert enriched["yes_asks"] == "{}"

    def test_adds_no_bids(self) -> None:
        """Adds no_bids default."""
        enriched: dict = {}

        enrich_orderbook_defaults(enriched)

        assert enriched["no_bids"] == "{}"

    def test_adds_no_asks(self) -> None:
        """Adds no_asks default."""
        enriched: dict = {}

        enrich_orderbook_defaults(enriched)

        assert enriched["no_asks"] == "{}"

    def test_preserves_existing_yes_bids(self) -> None:
        """Preserves existing yes_bids."""
        enriched = {"yes_bids": '{"50": 100}'}

        enrich_orderbook_defaults(enriched)

        assert enriched["yes_bids"] == '{"50": 100}'

    def test_preserves_existing_no_asks(self) -> None:
        """Preserves existing no_asks."""
        enriched = {"no_asks": '{"55": 200}'}

        enrich_orderbook_defaults(enriched)

        assert enriched["no_asks"] == '{"55": 200}'


class TestEnrichStatusField:
    """Tests for enrich_status_field function."""

    def test_adds_open_as_default(self) -> None:
        """Adds 'open' as default status."""
        enriched: dict = {}

        enrich_status_field(enriched, {})

        assert enriched["status"] == "open"

    def test_uses_metadata_status(self) -> None:
        """Uses status from metadata."""
        enriched: dict = {}
        metadata = {"status": "closed"}

        enrich_status_field(enriched, metadata)

        assert enriched["status"] == "closed"

    def test_preserves_existing_status(self) -> None:
        """Preserves existing status."""
        enriched = {"status": "active"}
        metadata = {"status": "closed"}

        enrich_status_field(enriched, metadata)

        assert enriched["status"] == "active"

    def test_metadata_takes_precedence_over_default(self) -> None:
        """Metadata status takes precedence over default."""
        enriched: dict = {}
        metadata = {"status": "settled"}

        enrich_status_field(enriched, metadata)

        assert enriched["status"] == "settled"
