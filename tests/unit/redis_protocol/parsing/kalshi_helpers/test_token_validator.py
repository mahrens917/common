import pytest

from src.common.redis_protocol.parsing.kalshi_helpers.token_validator import (
    parse_token_components,
    validate_and_normalize_token,
)


class TestTokenValidator:
    def test_validate_and_normalize_token_valid(self):
        """Test valid token normalization."""
        assert validate_and_normalize_token("  25jan15  ") == "25JAN15"

    def test_validate_and_normalize_token_invalid(self):
        """Test invalid token normalization."""
        assert validate_and_normalize_token(None) is None
        assert validate_and_normalize_token("") is None
        assert validate_and_normalize_token("1234") is None  # Too short

    def test_parse_token_components_valid(self):
        """Test valid token parsing."""
        month, prefix, remainder = parse_token_components("25JAN15")
        assert month == 1
        assert prefix == "25"
        assert remainder == "15"

    def test_parse_token_components_invalid_month(self):
        """Test parsing with invalid month."""
        with pytest.raises(ValueError, match="Unknown month code"):
            parse_token_components("25XXX15")

    def test_parse_token_components_invalid_prefix(self):
        """Test parsing with non-digit prefix."""
        with pytest.raises(TypeError, match="Invalid prefix"):
            parse_token_components("XXJAN15")
