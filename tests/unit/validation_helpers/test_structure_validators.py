"""Tests for validation_helpers.structure_validators module."""

import pytest

from common.validation_helpers.exceptions import ValidationError
from common.validation_helpers.structure_validators import StructureValidators


class TestValidateListNotEmpty:
    """Tests for validate_list_not_empty method."""

    def test_valid_non_empty_list(self) -> None:
        """Test returns True for non-empty list."""
        result = StructureValidators.validate_list_not_empty([1, 2, 3])
        assert result is True

    def test_valid_single_element_list(self) -> None:
        """Test returns True for single element list."""
        result = StructureValidators.validate_list_not_empty(["single"])
        assert result is True

    def test_none_list_raises_error(self) -> None:
        """Test raises ValidationError for None list."""
        with pytest.raises(ValidationError, match="list cannot be None"):
            StructureValidators.validate_list_not_empty(None)

    def test_none_list_with_custom_name(self) -> None:
        """Test raises ValidationError with custom name."""
        with pytest.raises(ValidationError, match="items cannot be None"):
            StructureValidators.validate_list_not_empty(None, "items")

    def test_empty_list_raises_error(self) -> None:
        """Test raises ValidationError for empty list."""
        with pytest.raises(ValidationError, match="list cannot be empty"):
            StructureValidators.validate_list_not_empty([])

    def test_empty_list_with_custom_name(self) -> None:
        """Test raises ValidationError with custom name for empty list."""
        with pytest.raises(ValidationError, match="entries cannot be empty"):
            StructureValidators.validate_list_not_empty([], "entries")


class TestValidateDictionaryHasKeys:
    """Tests for validate_dictionary_has_keys method."""

    def test_valid_dict_with_all_keys(self) -> None:
        """Test returns True when all required keys present."""
        data = {"key1": "value1", "key2": "value2"}
        result = StructureValidators.validate_dictionary_has_keys(data, ["key1", "key2"])
        assert result is True

    def test_valid_dict_with_extra_keys(self) -> None:
        """Test returns True when extra keys present."""
        data = {"key1": "value1", "key2": "value2", "key3": "value3"}
        result = StructureValidators.validate_dictionary_has_keys(data, ["key1", "key2"])
        assert result is True

    def test_none_dict_raises_error(self) -> None:
        """Test raises ValidationError for None dict."""
        with pytest.raises(ValidationError, match="dictionary cannot be None"):
            StructureValidators.validate_dictionary_has_keys(None, ["key1"])

    def test_none_dict_with_custom_name(self) -> None:
        """Test raises ValidationError with custom name."""
        with pytest.raises(ValidationError, match="config cannot be None"):
            StructureValidators.validate_dictionary_has_keys(None, ["key1"], "config")

    def test_missing_single_key_raises_error(self) -> None:
        """Test raises ValidationError for missing key."""
        data = {"key1": "value1"}
        with pytest.raises(ValidationError, match="missing required keys"):
            StructureValidators.validate_dictionary_has_keys(data, ["key1", "key2"])

    def test_missing_multiple_keys_raises_error(self) -> None:
        """Test raises ValidationError for multiple missing keys."""
        data = {"key1": "value1"}
        with pytest.raises(ValidationError, match="missing required keys.*key2.*key3"):
            StructureValidators.validate_dictionary_has_keys(data, ["key1", "key2", "key3"])

    def test_empty_required_keys(self) -> None:
        """Test returns True when no required keys."""
        data = {"key1": "value1"}
        result = StructureValidators.validate_dictionary_has_keys(data, [])
        assert result is True

    def test_empty_dict_with_required_keys(self) -> None:
        """Test raises ValidationError for empty dict with required keys."""
        with pytest.raises(ValidationError, match="missing required keys"):
            StructureValidators.validate_dictionary_has_keys({}, ["key1"])
