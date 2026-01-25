"""Tests for llm_extractor prompts module."""

from common.llm_extractor.prompts import EXTRACTION_PROMPT, build_user_content


class TestExtractionPrompt:
    """Tests for the EXTRACTION_PROMPT constant."""

    def test_contains_category_list(self) -> None:
        """Test that prompt contains category names."""
        assert "Crypto" in EXTRACTION_PROMPT
        assert "Politics" in EXTRACTION_PROMPT
        assert "Sports" in EXTRACTION_PROMPT

    def test_contains_all_field_names(self) -> None:
        """Test that prompt references all extraction fields."""
        assert "category" in EXTRACTION_PROMPT
        assert "underlying" in EXTRACTION_PROMPT
        assert "subject" in EXTRACTION_PROMPT
        assert "entity" in EXTRACTION_PROMPT
        assert "scope" in EXTRACTION_PROMPT
        assert "floor_strike" in EXTRACTION_PROMPT
        assert "cap_strike" in EXTRACTION_PROMPT
        assert "parent_entity" in EXTRACTION_PROMPT
        assert "parent_scope" in EXTRACTION_PROMPT
        assert "is_conjunction" in EXTRACTION_PROMPT
        assert "conjunction_scopes" in EXTRACTION_PROMPT
        assert "is_union" in EXTRACTION_PROMPT
        assert "union_scopes" in EXTRACTION_PROMPT

    def test_specifies_json_output_format(self) -> None:
        """Test that prompt specifies JSON output format."""
        assert "Return JSON" in EXTRACTION_PROMPT
        assert '"markets"' in EXTRACTION_PROMPT


class TestBuildUserContent:
    """Tests for build_user_content."""

    def test_builds_single_market(self) -> None:
        """Test building content for a single market."""
        markets = [{"id": "cond-1", "title": "BTC above $100k"}]
        content = build_user_content(markets)
        assert "[ID: cond-1]" in content
        assert "Title: BTC above $100k" in content

    def test_builds_multiple_markets_with_separator(self) -> None:
        """Test that multiple markets are separated by ---."""
        markets = [
            {"id": "m1", "title": "Market 1"},
            {"id": "m2", "title": "Market 2"},
        ]
        content = build_user_content(markets)
        assert "---" in content
        assert "[ID: m1]" in content
        assert "[ID: m2]" in content

    def test_includes_description_when_present(self) -> None:
        """Test that description is included when present."""
        markets = [{"id": "m1", "title": "T1", "description": "Some description"}]
        content = build_user_content(markets)
        assert "Description: Some description" in content

    def test_truncates_long_description(self) -> None:
        """Test that descriptions are truncated to 500 chars."""
        long_desc = "x" * 600
        markets = [{"id": "m1", "title": "T1", "description": long_desc}]
        content = build_user_content(markets)
        assert len(content) < 700

    def test_includes_tokens_when_present(self) -> None:
        """Test that tokens/outcomes are included when present."""
        markets = [{"id": "m1", "title": "T1", "tokens": '["Yes", "No"]'}]
        content = build_user_content(markets)
        assert "Outcomes:" in content

    def test_excludes_optional_fields_when_absent(self) -> None:
        """Test that optional fields are not included when absent."""
        markets = [{"id": "m1", "title": "T1"}]
        content = build_user_content(markets)
        assert "Description:" not in content
        assert "Outcomes:" not in content
