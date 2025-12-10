"""Tests for strike type enrichers module."""

from common.redis_protocol.market_normalization_helpers.metadata_enricher_helpers.strike_type_enrichers import (
    enrich_between_strike,
    enrich_greater_strike,
    enrich_less_strike,
    enrich_strike_type_field,
    enrich_strike_value_field,
)


class TestEnrichGreaterStrike:
    """Tests for enrich_greater_strike function."""

    def test_sets_floor_strike(self) -> None:
        """Sets floor_strike from floor value."""
        enriched = {}

        enrich_greater_strike(enriched, 50000.0)

        assert enriched["floor_strike"] == "50000.0"

    def test_sets_cap_to_inf(self) -> None:
        """Sets cap_strike to 'inf'."""
        enriched = {}

        enrich_greater_strike(enriched, 50000.0)

        assert enriched["cap_strike"] == "inf"

    def test_none_floor_does_nothing(self) -> None:
        """Does nothing when floor is None."""
        enriched = {}

        enrich_greater_strike(enriched, None)

        assert "floor_strike" not in enriched


class TestEnrichLessStrike:
    """Tests for enrich_less_strike function."""

    def test_sets_cap_strike(self) -> None:
        """Sets cap_strike from cap value."""
        enriched = {}

        enrich_less_strike(enriched, 50000.0)

        assert enriched["cap_strike"] == "50000.0"

    def test_sets_floor_to_zero(self) -> None:
        """Sets floor_strike to '0'."""
        enriched = {}

        enrich_less_strike(enriched, 50000.0)

        assert enriched["floor_strike"] == "0"

    def test_none_cap_does_nothing(self) -> None:
        """Does nothing when cap is None."""
        enriched = {}

        enrich_less_strike(enriched, None)

        assert "cap_strike" not in enriched


class TestEnrichBetweenStrike:
    """Tests for enrich_between_strike function."""

    def test_sets_empty_floor(self) -> None:
        """Sets floor_strike to empty if missing."""
        enriched = {}

        enrich_between_strike(enriched)

        assert enriched["floor_strike"] == ""

    def test_sets_empty_cap(self) -> None:
        """Sets cap_strike to empty if missing."""
        enriched = {}

        enrich_between_strike(enriched)

        assert enriched["cap_strike"] == ""

    def test_preserves_existing_floor(self) -> None:
        """Preserves existing floor_strike."""
        enriched = {"floor_strike": "50000.0"}

        enrich_between_strike(enriched)

        assert enriched["floor_strike"] == "50000.0"


class TestEnrichStrikeTypeField:
    """Tests for enrich_strike_type_field function."""

    def test_sets_strike_type(self) -> None:
        """Sets strike_type field."""
        enriched = {}

        enrich_strike_type_field(enriched, "greater")

        assert enriched["strike_type"] == "greater"

    def test_preserves_existing_strike_type(self) -> None:
        """Preserves existing strike_type."""
        enriched = {"strike_type": "less"}

        enrich_strike_type_field(enriched, "greater")

        assert enriched["strike_type"] == "less"


class TestEnrichStrikeValueField:
    """Tests for enrich_strike_value_field function."""

    def test_sets_strike_value(self) -> None:
        """Sets strike field."""
        enriched = {}

        enrich_strike_value_field(enriched, 50000.0)

        assert enriched["strike"] == "50000.0"

    def test_preserves_existing_strike(self) -> None:
        """Preserves existing strike."""
        enriched = {"strike": "45000.0"}

        enrich_strike_value_field(enriched, 50000.0)

        assert enriched["strike"] == "45000.0"

    def test_none_value_does_nothing(self) -> None:
        """Does nothing when value is None."""
        enriched = {}

        enrich_strike_value_field(enriched, None)

        assert "strike" not in enriched
