"""Tests for simple value coercion re-exports."""

import pytest

from src.common import value_coercion


@pytest.mark.parametrize("value, otherwise_val", [(True, False), (0, 1)])
def test_bool_or_else_delegates(monkeypatch, value, otherwise_val):
    called = {}

    def fake_bool(val, defval):
        called["args"] = (val, defval)
        return defval if not val else val

    monkeypatch.setattr(value_coercion.utils_coercion, "bool_or_default", fake_bool)

    result = value_coercion.bool_or_else(value, otherwise_val)
    assert called["args"] == (value, otherwise_val)
    assert isinstance(result, (bool, int))


def test_sequence_and_mapping_delegations(monkeypatch):
    monkeypatch.setattr(
        value_coercion.utils_coercion, "coerce_sequence", lambda candidate: list(candidate)
    )
    monkeypatch.setattr(
        value_coercion.utils_coercion, "coerce_mapping", lambda candidate: dict(candidate)
    )

    assert value_coercion.coerce_sequence(("a",)) == ["a"]
    assert value_coercion.coerce_mapping([("a", 1)]) == {"a": 1}


def test_numeric_and_int_coercions(monkeypatch):
    monkeypatch.setattr(
        value_coercion.utils_coercion, "convert_numeric_field", lambda value: float(value)
    )
    monkeypatch.setattr(
        value_coercion.utils_coercion,
        "float_or_default",
        lambda value, otherwise_val, **kwargs: float(value),
    )
    monkeypatch.setattr(
        value_coercion.utils_coercion, "int_or_default", lambda value, otherwise_val: int(value)
    )

    assert value_coercion.convert_numeric_field("5") == 5.0
    assert value_coercion.float_or_else("2.5") == 2.5
    assert value_coercion.int_or_else("3") == 3


def test_string_and_optional_float_delegations(monkeypatch):
    monkeypatch.setattr(
        value_coercion.utils_coercion,
        "string_or_default",
        lambda value, otherwise_val="", trim=False: str(value).strip(),
    )
    monkeypatch.setattr(
        value_coercion.utils_coercion,
        "_to_optional_float",
        lambda value, context="": float(value) if value is not None else None,
    )

    assert value_coercion.string_or_else(" text ", otherwise="") == "text"
    assert value_coercion.to_optional_float("1.23", context="test") == 1.23
