"""Tests for common utils numeric module."""

from __future__ import annotations

import pytest

from src.common.utils.numeric import (
    coerce_float_default,
    coerce_float_optional,
    coerce_float_strict,
    coerce_int_default,
    coerce_int_optional,
    coerce_int_strict,
)


class TestCoerceFloatStrict:
    """Tests for coerce_float_strict function."""

    def test_float_returns_unchanged(self) -> None:
        """Float input returns unchanged."""
        assert coerce_float_strict(3.14) == 3.14

    def test_int_converts_to_float(self) -> None:
        """Int input converts to float."""
        assert coerce_float_strict(42) == 42.0
        assert isinstance(coerce_float_strict(42), float)

    def test_string_converts_to_float(self) -> None:
        """String input converts to float."""
        assert coerce_float_strict("3.14") == 3.14

    def test_bytes_converts_to_float(self) -> None:
        """Bytes input converts to float."""
        assert coerce_float_strict(b"3.14") == 3.14

    def test_bytearray_converts_to_float(self) -> None:
        """Bytearray input converts to float."""
        assert coerce_float_strict(bytearray(b"3.14")) == 3.14

    def test_invalid_string_raises_value_error(self) -> None:
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot convert"):
            coerce_float_strict("invalid")

    def test_none_raises_value_error(self) -> None:
        """None raises ValueError."""
        with pytest.raises(ValueError, match="Cannot convert"):
            coerce_float_strict(None)


class TestCoerceFloatOptional:
    """Tests for coerce_float_optional function."""

    def test_float_returns_unchanged(self) -> None:
        """Float input returns unchanged."""
        assert coerce_float_optional(3.14) == 3.14

    def test_int_converts_to_float(self) -> None:
        """Int input converts to float."""
        assert coerce_float_optional(42) == 42.0

    def test_string_converts_to_float(self) -> None:
        """String input converts to float."""
        assert coerce_float_optional("3.14") == 3.14

    def test_bytes_converts_to_float(self) -> None:
        """Bytes input converts to float."""
        assert coerce_float_optional(b"3.14") == 3.14

    def test_bytearray_converts_to_float(self) -> None:
        """Bytearray input converts to float."""
        assert coerce_float_optional(bytearray(b"3.14")) == 3.14

    def test_none_returns_none(self) -> None:
        """None input returns None."""
        assert coerce_float_optional(None) is None

    def test_invalid_string_returns_none(self) -> None:
        """Invalid string returns None."""
        assert coerce_float_optional("invalid") is None


class TestCoerceFloatDefault:
    """Tests for coerce_float_default function."""

    def test_valid_value_returns_converted(self) -> None:
        """Valid value returns converted float."""
        assert coerce_float_default("3.14", 0.0) == 3.14

    def test_invalid_value_returns_default(self) -> None:
        """Invalid value returns default."""
        assert coerce_float_default("invalid", 0.0) == 0.0

    def test_none_returns_default(self) -> None:
        """None returns default."""
        assert coerce_float_default(None, -1.0) == -1.0


class TestCoerceIntStrict:
    """Tests for coerce_int_strict function."""

    def test_int_returns_unchanged(self) -> None:
        """Int input returns unchanged."""
        assert coerce_int_strict(42) == 42

    def test_float_truncates_to_int(self) -> None:
        """Float input truncates to int."""
        assert coerce_int_strict(3.9) == 3
        assert isinstance(coerce_int_strict(3.9), int)

    def test_string_converts_to_int(self) -> None:
        """String input converts to int."""
        assert coerce_int_strict("42") == 42

    def test_bytes_converts_to_int(self) -> None:
        """Bytes input converts to int."""
        assert coerce_int_strict(b"42") == 42

    def test_bytearray_converts_to_int(self) -> None:
        """Bytearray input converts to int."""
        assert coerce_int_strict(bytearray(b"42")) == 42

    def test_invalid_string_raises_value_error(self) -> None:
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot convert"):
            coerce_int_strict("invalid")

    def test_none_raises_value_error(self) -> None:
        """None raises ValueError."""
        with pytest.raises(ValueError, match="Cannot convert"):
            coerce_int_strict(None)


class TestCoerceIntOptional:
    """Tests for coerce_int_optional function."""

    def test_int_returns_unchanged(self) -> None:
        """Int input returns unchanged."""
        assert coerce_int_optional(42) == 42

    def test_float_truncates_to_int(self) -> None:
        """Float input truncates to int."""
        assert coerce_int_optional(3.9) == 3

    def test_string_converts_to_int(self) -> None:
        """String input converts to int."""
        assert coerce_int_optional("42") == 42

    def test_bytes_converts_to_int(self) -> None:
        """Bytes input converts to int."""
        assert coerce_int_optional(b"42") == 42

    def test_bytearray_converts_to_int(self) -> None:
        """Bytearray input converts to int."""
        assert coerce_int_optional(bytearray(b"42")) == 42

    def test_none_returns_none(self) -> None:
        """None input returns None."""
        assert coerce_int_optional(None) is None

    def test_invalid_string_returns_none(self) -> None:
        """Invalid string returns None."""
        assert coerce_int_optional("invalid") is None


class TestCoerceIntDefault:
    """Tests for coerce_int_default function."""

    def test_valid_value_returns_converted(self) -> None:
        """Valid value returns converted int."""
        assert coerce_int_default("42", 0) == 42

    def test_invalid_value_returns_default(self) -> None:
        """Invalid value returns default."""
        assert coerce_int_default("invalid", 0) == 0

    def test_none_returns_default(self) -> None:
        """None returns default."""
        assert coerce_int_default(None, -1) == -1
