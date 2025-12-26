"""Tests for daily_max_state_helpers.confidence_calculator module."""

import pytest

from common.daily_max_state_helpers.confidence_calculator import ConfidenceCalculator


class TestConfidenceCalculatorGetConfidenceLevel:
    """Tests for get_confidence_level static method."""

    def test_returns_high_for_0_1_precision(self) -> None:
        """Test returns HIGH for 0.1 precision."""
        result = ConfidenceCalculator.get_confidence_level(0.1)
        assert result == "HIGH"

    def test_returns_medium_for_1_0_precision(self) -> None:
        """Test returns MEDIUM for 1.0 precision."""
        result = ConfidenceCalculator.get_confidence_level(1.0)
        assert result == "MEDIUM"

    def test_raises_for_unknown_precision(self) -> None:
        """Test raises ValueError for unknown precision."""
        with pytest.raises(ValueError) as exc_info:
            ConfidenceCalculator.get_confidence_level(0.5)

        assert "Unknown precision" in str(exc_info.value)

    def test_raises_for_none_precision(self) -> None:
        """Test raises ValueError for None precision."""
        with pytest.raises(ValueError) as exc_info:
            ConfidenceCalculator.get_confidence_level(None)

        assert "Unknown precision" in str(exc_info.value)

    def test_raises_for_zero_precision(self) -> None:
        """Test raises ValueError for 0 precision."""
        with pytest.raises(ValueError) as exc_info:
            ConfidenceCalculator.get_confidence_level(0.0)

        assert "Unknown precision" in str(exc_info.value)


class TestConfidenceCalculatorGetSafetyMarginC:
    """Tests for get_safety_margin_c static method."""

    def test_returns_0_for_high_confidence(self) -> None:
        """Test returns 0.0 for HIGH confidence (0.1 precision)."""
        result = ConfidenceCalculator.get_safety_margin_c(0.1)
        assert result == 0.0

    def test_returns_0_5_for_medium_confidence(self) -> None:
        """Test returns 0.5 for MEDIUM confidence (1.0 precision)."""
        result = ConfidenceCalculator.get_safety_margin_c(1.0)
        assert result == 0.5

    def test_raises_for_unknown_precision(self) -> None:
        """Test raises ValueError for unknown precision."""
        with pytest.raises(ValueError) as exc_info:
            ConfidenceCalculator.get_safety_margin_c(2.0)

        assert "Unknown precision" in str(exc_info.value)

    def test_raises_for_none_precision(self) -> None:
        """Test raises ValueError for None precision."""
        with pytest.raises(ValueError) as exc_info:
            ConfidenceCalculator.get_safety_margin_c(None)

        assert "Unknown precision" in str(exc_info.value)

    def test_margin_is_float(self) -> None:
        """Test margin is returned as float."""
        result = ConfidenceCalculator.get_safety_margin_c(0.1)
        assert isinstance(result, float)

    def test_medium_margin_is_float(self) -> None:
        """Test medium margin is returned as float."""
        result = ConfidenceCalculator.get_safety_margin_c(1.0)
        assert isinstance(result, float)
