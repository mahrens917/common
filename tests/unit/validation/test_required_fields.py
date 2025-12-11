"""Tests for required fields validation."""

import pytest

from common.validation.required_fields import validate_required_fields


class TestValidateRequiredFields:
    """Tests for validate_required_fields function."""

    def test_passes_when_all_fields_present(self):
        """Pass validation when all required fields are present."""
        payload = {"field1": "value1", "field2": "value2", "field3": "value3"}
        required = ["field1", "field2"]
        validate_required_fields(payload, required)

    def test_raises_when_field_missing(self):
        """Raise ValueError when required field is missing."""
        payload = {"field1": "value1"}
        required = ["field1", "field2"]
        with pytest.raises(ValueError, match="Payload missing required field"):
            validate_required_fields(payload, required)

    def test_raises_custom_exception_type(self):
        """Raise custom exception type when specified."""
        payload = {"field1": "value1"}
        required = ["field1", "field2"]
        with pytest.raises(KeyError):
            validate_required_fields(payload, required, error_cls=KeyError)

    def test_uses_custom_error_factory(self):
        """Use custom error factory when provided."""

        def custom_factory(missing_fields, payload):
            return RuntimeError(f"Custom error for {missing_fields}")

        payload = {"field1": "value1"}
        required = ["field1", "field2"]
        with pytest.raises(RuntimeError, match="Custom error"):
            validate_required_fields(payload, required, on_missing=custom_factory)

    def test_raises_type_error_on_non_mapping(self):
        """Raise TypeError when payload is not a mapping."""
        payload = 12345
        required = ["field1"]
        with pytest.raises(TypeError, match="payload must be a Mapping"):
            validate_required_fields(payload, required)

    def test_sorts_missing_fields_in_error_message(self):
        """Sort missing fields alphabetically in error message."""
        payload = {"field1": "value1"}
        required = ["field3", "field1", "field2"]
        with pytest.raises(ValueError, match="field2, field3"):
            validate_required_fields(payload, required)
