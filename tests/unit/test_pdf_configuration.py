"""Tests for pdf_configuration module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from common.pdf_configuration import (
    NDIM_2D,
    PDFConfigurationCurrencyUnset,
    PDFConfigurationMissing,
    _deep_merge_dict,
    _normalize_currency,
    _resolve_currency,
    currency_context,
    reset_current_currency,
    set_current_currency,
)


class TestConstants:
    """Tests for module constants."""

    def test_ndim_2d(self) -> None:
        """Test NDIM_2D constant."""
        assert NDIM_2D == 2


class TestNormalizeCurrency:
    """Tests for _normalize_currency function."""

    def test_uppercase_conversion(self) -> None:
        """Test converts to uppercase."""
        assert _normalize_currency("btc") == "BTC"
        assert _normalize_currency("eth") == "ETH"

    def test_strips_whitespace(self) -> None:
        """Test strips whitespace."""
        assert _normalize_currency("  BTC  ") == "BTC"

    def test_empty_raises(self) -> None:
        """Test raises on empty currency."""
        with pytest.raises(ValueError) as exc_info:
            _normalize_currency("")

        assert "empty" in str(exc_info.value)

    def test_whitespace_only_raises(self) -> None:
        """Test raises on whitespace-only currency."""
        with pytest.raises(ValueError):
            _normalize_currency("   ")


class TestDeepMergeDict:
    """Tests for _deep_merge_dict function."""

    def test_simple_merge(self) -> None:
        """Test simple key merge."""
        base = {"a": 1, "b": 2}
        overlay = {"b": 3, "c": 4}

        result = _deep_merge_dict(base, overlay)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self) -> None:
        """Test nested dict merge."""
        base = {"outer": {"a": 1, "b": 2}}
        overlay = {"outer": {"b": 3, "c": 4}}

        result = _deep_merge_dict(base, overlay)

        assert result == {"outer": {"a": 1, "b": 3, "c": 4}}

    def test_list_replacement(self) -> None:
        """Test lists are replaced not merged."""
        base = {"items": [1, 2, 3]}
        overlay = {"items": [4, 5]}

        result = _deep_merge_dict(base, overlay)

        assert result == {"items": [4, 5]}

    def test_does_not_modify_original(self) -> None:
        """Test original dicts are not modified."""
        base = {"a": 1}
        overlay = {"a": 2}

        _deep_merge_dict(base, overlay)

        assert base == {"a": 1}
        assert overlay == {"a": 2}


class TestResolveCurrency:
    """Tests for _resolve_currency function."""

    def test_uses_provided_currency(self) -> None:
        """Test uses provided currency argument."""
        result = _resolve_currency("btc")

        assert result == "BTC"

    def test_raises_when_no_currency(self) -> None:
        """Test raises when no currency provided or in context."""
        # Reset context first
        token = set_current_currency(None)
        try:
            with pytest.raises(PDFConfigurationCurrencyUnset):
                _resolve_currency(None)
        finally:
            reset_current_currency(token)

    def test_uses_context_currency(self) -> None:
        """Test uses currency from context when not provided."""
        token = set_current_currency("ETH")
        try:
            result = _resolve_currency(None)
            assert result == "ETH"
        finally:
            reset_current_currency(token)


class TestCurrencyContext:
    """Tests for currency context functions."""

    def test_set_and_reset(self) -> None:
        """Test setting and resetting currency."""
        original_token = set_current_currency(None)
        try:
            token = set_current_currency("BTC")
            assert _resolve_currency(None) == "BTC"

            reset_current_currency(token)
        finally:
            reset_current_currency(original_token)

    def test_context_manager(self) -> None:
        """Test currency_context context manager."""
        original_token = set_current_currency(None)
        try:
            with currency_context("ETH"):
                assert _resolve_currency(None) == "ETH"
        finally:
            reset_current_currency(original_token)

    def test_nested_context(self) -> None:
        """Test nested currency contexts."""
        original_token = set_current_currency(None)
        try:
            with currency_context("BTC"):
                assert _resolve_currency(None) == "BTC"
                with currency_context("ETH"):
                    assert _resolve_currency(None) == "ETH"
                assert _resolve_currency(None) == "BTC"
        finally:
            reset_current_currency(original_token)


class TestPDFConfigurationExceptions:
    """Tests for exception classes."""

    def test_pdf_configuration_missing(self) -> None:
        """Test PDFConfigurationMissing is FileNotFoundError."""
        error = PDFConfigurationMissing("Config not found")

        assert isinstance(error, FileNotFoundError)
        assert "Config not found" in str(error)

    def test_pdf_configuration_currency_unset(self) -> None:
        """Test PDFConfigurationCurrencyUnset is RuntimeError."""
        error = PDFConfigurationCurrencyUnset("No currency")

        assert isinstance(error, RuntimeError)
        assert "No currency" in str(error)
