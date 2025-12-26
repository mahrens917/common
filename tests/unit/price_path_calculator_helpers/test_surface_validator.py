"""Tests for surface_validator module."""

import pytest

from common.price_path_calculator_helpers.surface_validator import (
    PricePathComputationError,
    ensure_path_metrics,
)


class TestPricePathComputationError:
    """Tests for PricePathComputationError exception."""

    def test_error_is_exception(self) -> None:
        """Test that PricePathComputationError is an Exception."""
        error = PricePathComputationError("test error")
        assert isinstance(error, Exception)

    def test_error_message(self) -> None:
        """Test error message is preserved."""
        error = PricePathComputationError("custom message")
        assert str(error) == "custom message"


class TestEnsurePathMetrics:
    """Tests for ensure_path_metrics function."""

    def test_surface_without_ensure_path_metrics_attribute(self) -> None:
        """Test surface without ensure_path_metrics attribute passes."""

        class MockSurface:
            pass

        surface = MockSurface()
        ensure_path_metrics(surface, "btc")

    def test_surface_with_none_ensure_path_metrics(self) -> None:
        """Test surface with None ensure_path_metrics passes."""

        class MockSurface:
            ensure_path_metrics = None

        surface = MockSurface()
        ensure_path_metrics(surface, "btc")

    def test_surface_with_callable_ensure_path_metrics_success(self) -> None:
        """Test surface with callable ensure_path_metrics that succeeds."""

        class MockSurface:
            def ensure_path_metrics(self) -> None:
                pass

        surface = MockSurface()
        ensure_path_metrics(surface, "btc")

    def test_surface_with_non_callable_ensure_path_metrics(self) -> None:
        """Test surface with non-callable ensure_path_metrics raises error."""

        class MockSurface:
            ensure_path_metrics = "not_callable"

        surface = MockSurface()
        with pytest.raises(PricePathComputationError, match="non-callable"):
            ensure_path_metrics(surface, "btc")

    def test_surface_with_callable_that_raises_runtime_error(self) -> None:
        """Test surface with callable that raises RuntimeError."""

        class MockSurface:
            def ensure_path_metrics(self) -> None:
                raise RuntimeError("Runtime failure")

        surface = MockSurface()
        with pytest.raises(PricePathComputationError, match="Failed to generate metrics"):
            ensure_path_metrics(surface, "eth")

    def test_surface_with_callable_that_raises_value_error(self) -> None:
        """Test surface with callable that raises ValueError."""

        class MockSurface:
            def ensure_path_metrics(self) -> None:
                raise ValueError("Invalid value")

        surface = MockSurface()
        with pytest.raises(PricePathComputationError, match="Failed to generate metrics"):
            ensure_path_metrics(surface, "btc")

    def test_surface_with_callable_that_raises_type_error(self) -> None:
        """Test surface with callable that raises TypeError."""

        class MockSurface:
            def ensure_path_metrics(self) -> None:
                raise TypeError("Type error")

        surface = MockSurface()
        with pytest.raises(PricePathComputationError, match="Failed to generate metrics"):
            ensure_path_metrics(surface, "sol")

    def test_error_message_includes_currency(self) -> None:
        """Test error message includes uppercase currency."""

        class MockSurface:
            ensure_path_metrics = 123

        surface = MockSurface()
        with pytest.raises(PricePathComputationError, match="BTC"):
            ensure_path_metrics(surface, "btc")
