"""Tests for strike enricher module."""

from common.redis_protocol.market_normalization_helpers.metadata_enricher_helpers.strike_enricher import (
    StrikeEnricher,
)


class TestStrikeEnricherEnrichGreaterType:
    """Tests for StrikeEnricher.enrich_greater_type."""

    def test_sets_floor_strike(self) -> None:
        """Sets floor_strike from floor value."""
        enriched = {}

        StrikeEnricher.enrich_greater_type(enriched, 50000.0)

        assert enriched["floor_strike"] == "50000.0"

    def test_sets_cap_to_inf(self) -> None:
        """Sets cap_strike to 'inf'."""
        enriched = {}

        StrikeEnricher.enrich_greater_type(enriched, 50000.0)

        assert enriched["cap_strike"] == "inf"

    def test_preserves_existing_floor(self) -> None:
        """Preserves existing floor_strike."""
        enriched = {"floor_strike": "45000.0"}

        StrikeEnricher.enrich_greater_type(enriched, 50000.0)

        assert enriched["floor_strike"] == "45000.0"

    def test_preserves_existing_cap(self) -> None:
        """Preserves existing cap_strike."""
        enriched = {"cap_strike": "60000.0"}

        StrikeEnricher.enrich_greater_type(enriched, 50000.0)

        assert enriched["cap_strike"] == "60000.0"

    def test_none_floor_does_nothing(self) -> None:
        """Does nothing when floor is None."""
        enriched = {}

        StrikeEnricher.enrich_greater_type(enriched, None)

        assert "floor_strike" not in enriched


class TestStrikeEnricherEnrichLessType:
    """Tests for StrikeEnricher.enrich_less_type."""

    def test_sets_cap_strike(self) -> None:
        """Sets cap_strike from cap value."""
        enriched = {}

        StrikeEnricher.enrich_less_type(enriched, 50000.0)

        assert enriched["cap_strike"] == "50000.0"

    def test_sets_floor_to_zero(self) -> None:
        """Sets floor_strike to '0'."""
        enriched = {}

        StrikeEnricher.enrich_less_type(enriched, 50000.0)

        assert enriched["floor_strike"] == "0"

    def test_preserves_existing_cap(self) -> None:
        """Preserves existing cap_strike."""
        enriched = {"cap_strike": "45000.0"}

        StrikeEnricher.enrich_less_type(enriched, 50000.0)

        assert enriched["cap_strike"] == "45000.0"

    def test_preserves_existing_floor(self) -> None:
        """Preserves existing floor_strike."""
        enriched = {"floor_strike": "40000.0"}

        StrikeEnricher.enrich_less_type(enriched, 50000.0)

        assert enriched["floor_strike"] == "40000.0"

    def test_none_cap_does_nothing(self) -> None:
        """Does nothing when cap is None."""
        enriched = {}

        StrikeEnricher.enrich_less_type(enriched, None)

        assert "cap_strike" not in enriched


class TestStrikeEnricherEnrichBetweenType:
    """Tests for StrikeEnricher.enrich_between_type."""

    def test_sets_empty_floor(self) -> None:
        """Sets floor_strike to empty if missing."""
        enriched = {}

        StrikeEnricher.enrich_between_type(enriched)

        assert enriched["floor_strike"] == ""

    def test_sets_empty_cap(self) -> None:
        """Sets cap_strike to empty if missing."""
        enriched = {}

        StrikeEnricher.enrich_between_type(enriched)

        assert enriched["cap_strike"] == ""

    def test_preserves_existing_floor(self) -> None:
        """Preserves existing floor_strike."""
        enriched = {"floor_strike": "50000.0"}

        StrikeEnricher.enrich_between_type(enriched)

        assert enriched["floor_strike"] == "50000.0"

    def test_preserves_existing_cap(self) -> None:
        """Preserves existing cap_strike."""
        enriched = {"cap_strike": "60000.0"}

        StrikeEnricher.enrich_between_type(enriched)

        assert enriched["cap_strike"] == "60000.0"
