"""Tests for price_path_calculator_helpers.surface_loader module."""

from unittest.mock import MagicMock

import pytest

from common.price_path_calculator_helpers.surface_loader import (
    PricePathComputationError,
    SurfaceLoader,
)


class TestPricePathComputationError:
    """Tests for PricePathComputationError exception."""

    def test_is_exception(self) -> None:
        """Test is an Exception subclass."""
        error = PricePathComputationError("test error")
        assert isinstance(error, Exception)

    def test_stores_message(self) -> None:
        """Test stores error message."""
        error = PricePathComputationError("surface not found")
        assert str(error) == "surface not found"


class TestSurfaceLoaderLoadSurface:
    """Tests for load_surface method."""

    def test_loads_fitted_surface(self) -> None:
        """Test loads and returns fitted surface."""
        mock_surface = MagicMock()
        mock_surface.is_fitted = True

        loader_fn = MagicMock(return_value=mock_surface)
        ensure_fn = MagicMock()

        loader = SurfaceLoader()
        result = loader.load_surface("BTC", loader_fn, ensure_fn)

        assert result is mock_surface
        loader_fn.assert_called_once_with("BTC")
        ensure_fn.assert_called_once_with(mock_surface, "BTC")

    def test_raises_when_surface_none(self) -> None:
        """Test raises when loader returns None."""
        loader_fn = MagicMock(return_value=None)
        ensure_fn = MagicMock()

        loader = SurfaceLoader()

        with pytest.raises(PricePathComputationError) as exc_info:
            loader.load_surface("ETH", loader_fn, ensure_fn)

        assert "No GP surface available" in str(exc_info.value)
        assert "ETH" in str(exc_info.value)

    def test_raises_when_surface_not_fitted(self) -> None:
        """Test raises when surface is not fitted."""
        mock_surface = MagicMock()
        mock_surface.is_fitted = False

        loader_fn = MagicMock(return_value=mock_surface)
        ensure_fn = MagicMock()

        loader = SurfaceLoader()

        with pytest.raises(PricePathComputationError) as exc_info:
            loader.load_surface("SOL", loader_fn, ensure_fn)

        assert "not fitted" in str(exc_info.value)
        assert "SOL" in str(exc_info.value)

    def test_calls_ensure_metrics_fn(self) -> None:
        """Test calls ensure_metrics_fn with surface and currency."""
        mock_surface = MagicMock()
        mock_surface.is_fitted = True

        loader_fn = MagicMock(return_value=mock_surface)
        ensure_fn = MagicMock()

        loader = SurfaceLoader()
        loader.load_surface("DOGE", loader_fn, ensure_fn)

        ensure_fn.assert_called_once_with(mock_surface, "DOGE")

    def test_uppercase_currency_in_error(self) -> None:
        """Test error messages use uppercase currency."""
        loader_fn = MagicMock(return_value=None)
        ensure_fn = MagicMock()

        loader = SurfaceLoader()

        with pytest.raises(PricePathComputationError) as exc_info:
            loader.load_surface("btc", loader_fn, ensure_fn)

        assert "BTC" in str(exc_info.value)

    def test_passes_currency_to_loader(self) -> None:
        """Test passes currency string to loader function."""
        mock_surface = MagicMock()
        mock_surface.is_fitted = True

        loader_fn = MagicMock(return_value=mock_surface)
        ensure_fn = MagicMock()

        loader = SurfaceLoader()
        loader.load_surface("XRP", loader_fn, ensure_fn)

        loader_fn.assert_called_once_with("XRP")

    def test_ensure_fn_not_called_when_none(self) -> None:
        """Test ensure_fn not called when surface is None."""
        loader_fn = MagicMock(return_value=None)
        ensure_fn = MagicMock()

        loader = SurfaceLoader()

        with pytest.raises(PricePathComputationError):
            loader.load_surface("BTC", loader_fn, ensure_fn)

        ensure_fn.assert_not_called()

    def test_ensure_fn_not_called_when_not_fitted(self) -> None:
        """Test ensure_fn not called when surface not fitted."""
        mock_surface = MagicMock()
        mock_surface.is_fitted = False

        loader_fn = MagicMock(return_value=mock_surface)
        ensure_fn = MagicMock()

        loader = SurfaceLoader()

        with pytest.raises(PricePathComputationError):
            loader.load_surface("BTC", loader_fn, ensure_fn)

        ensure_fn.assert_not_called()
