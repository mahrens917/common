"""Tests for field reset applicator module."""

from unittest.mock import patch

from common.dawn_reset_service_helpers.field_reset_applicator import FieldResetApplicator


class TestFieldResetApplicatorApplyResetLogic:
    """Tests for FieldResetApplicator.apply_reset_logic."""

    def test_clears_field_on_reset_for_clear_fields(self) -> None:
        """Clears field when reset is needed for CLEAR_ON_RESET_FIELDS."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator.apply_reset_logic(
                "t_yes_bid", 50.0, {"t_yes_bid": 45.0}, was_reset=True
            )

        assert result is None

    def test_returns_current_on_reset_for_non_clear_fields(self) -> None:
        """Returns current value when reset is needed for non-clear fields."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator.apply_reset_logic(
                "other_field", 50.0, {"other_field": 45.0}, was_reset=True
            )

        assert result == 50.0

    def test_preserves_previous_when_current_is_none(self) -> None:
        """Preserves previous value when no reset and current is None."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator.apply_reset_logic(
                "other_field", None, {"other_field": 45.0}, was_reset=False
            )

        assert result == 45.0

    def test_uses_current_when_no_previous_data(self) -> None:
        """Uses current value when no reset and no previous data."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator.apply_reset_logic("other_field", 50.0, {}, was_reset=False)

        assert result == 50.0


class TestFieldResetApplicatorApplyResetValue:
    """Tests for FieldResetApplicator._apply_reset_value."""

    def test_clears_t_yes_bid(self) -> None:
        """Clears t_yes_bid field."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator._apply_reset_value("t_yes_bid", 50.0)

        assert result is None

    def test_clears_t_yes_ask(self) -> None:
        """Clears t_yes_ask field."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator._apply_reset_value("t_yes_ask", 55.0)

        assert result is None

    def test_clears_weather_explanation(self) -> None:
        """Clears weather_explanation field."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator._apply_reset_value("weather_explanation", "Some explanation")

        assert result is None

    def test_clears_last_rule_applied(self) -> None:
        """Clears last_rule_applied field."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator._apply_reset_value("last_rule_applied", "rule_1")

        assert result is None

    def test_clears_maxT(self) -> None:
        """Clears maxT field."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator._apply_reset_value("maxT", 75.0)

        assert result is None

    def test_clears_minT(self) -> None:
        """Clears minT field."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator._apply_reset_value("minT", 32.0)

        assert result is None

    def test_returns_current_for_non_clear_fields(self) -> None:
        """Returns current value for non-clear fields."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator._apply_reset_value("max_temp_f", 75.0)

        assert result == 75.0


class TestFieldResetApplicatorPreserveExistingValue:
    """Tests for FieldResetApplicator._preserve_existing_value."""

    def test_uses_previous_when_current_is_none(self) -> None:
        """Uses previous value when current is None."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator._preserve_existing_value("max_temp_f", None, {"max_temp_f": 75.0})

        assert result == 75.0

    def test_uses_current_when_not_none(self) -> None:
        """Uses current value when not None."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator._preserve_existing_value("max_temp_f", 80.0, {"max_temp_f": 75.0})

        assert result == 80.0

    def test_uses_current_when_no_previous(self) -> None:
        """Uses current value when field not in previous data."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator._preserve_existing_value("max_temp_f", 80.0, {})

        assert result == 80.0

    def test_uses_none_when_current_none_and_no_previous(self) -> None:
        """Uses None when current is None and no previous data."""
        applicator = FieldResetApplicator()

        with patch("common.dawn_reset_service_helpers.field_reset_applicator.logger"):
            result = applicator._preserve_existing_value("max_temp_f", None, {})

        assert result is None


class TestFieldResetApplicatorClearOnResetFields:
    """Tests for FieldResetApplicator.CLEAR_ON_RESET_FIELDS constant."""

    def test_contains_expected_fields(self) -> None:
        """Contains expected fields."""
        expected_fields = {
            "t_yes_bid",
            "t_yes_ask",
            "weather_explanation",
            "last_rule_applied",
            "maxT",
            "minT",
            "maxT24",
            "minT24",
        }

        assert FieldResetApplicator.CLEAR_ON_RESET_FIELDS == expected_fields
