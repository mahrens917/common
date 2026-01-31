"""Tests for llm_extractor prompts module."""

from common.llm_extractor.prompts import (
    build_kalshi_dedup_prompt,
    build_kalshi_underlying_batch_prompt,
    build_kalshi_underlying_prompt,
    build_kalshi_underlying_user_content,
    build_poly_batch_user_content,
    build_poly_prompt,
    build_poly_user_content,
)


class TestBuildKalshiUnderlyingPrompt:
    """Tests for build_kalshi_underlying_prompt."""

    def test_includes_empty_list_when_no_underlyings(self) -> None:
        """Test that empty underlyings list is rendered as []."""
        prompt = build_kalshi_underlying_prompt([])
        assert "[]" in prompt

    def test_includes_existing_underlyings(self) -> None:
        """Test that existing underlyings are included."""
        prompt = build_kalshi_underlying_prompt(["BTC", "ETH"])
        assert "BTC" in prompt
        assert "ETH" in prompt

    def test_specifies_json_output_format(self) -> None:
        """Test that prompt specifies JSON output format."""
        prompt = build_kalshi_underlying_prompt([])
        assert '{"underlying":' in prompt

    def test_contains_example_underlyings(self) -> None:
        """Test that prompt contains example underlyings."""
        prompt = build_kalshi_underlying_prompt([])
        assert "BTC" in prompt
        assert "ETH" in prompt
        assert "FED" in prompt

    def test_contains_station_qualified_weather_examples(self) -> None:
        """Test that weather examples use CITY_STATION format."""
        for prompt_fn in (build_kalshi_underlying_prompt, build_kalshi_underlying_batch_prompt):
            prompt = prompt_fn([])
            assert "NYC_KNYC" in prompt
            assert "CHI_KMDW" in prompt
            assert "WEATHER STATION RULE" in prompt
            assert "CITY_STATION" in prompt


class TestBuildKalshiUnderlyingUserContent:
    """Tests for build_kalshi_underlying_user_content."""

    def test_includes_title(self) -> None:
        """Test that title is included."""
        content = build_kalshi_underlying_user_content(
            title="Will BTC be above $100k?",
            rules_primary="",
            category="Crypto",
        )
        assert "Title: Will BTC be above $100k?" in content

    def test_includes_category(self) -> None:
        """Test that category is included."""
        content = build_kalshi_underlying_user_content(
            title="Test",
            rules_primary="",
            category="Crypto",
        )
        assert "Category: Crypto" in content

    def test_includes_rules_when_present(self) -> None:
        """Test that rules are included when present."""
        content = build_kalshi_underlying_user_content(
            title="Test",
            rules_primary="If BTC closes above...",
            category="Crypto",
        )
        assert "Rules: If BTC closes above..." in content

    def test_excludes_rules_when_empty(self) -> None:
        """Test that rules line is excluded when empty."""
        content = build_kalshi_underlying_user_content(
            title="Test",
            rules_primary="",
            category="Crypto",
        )
        assert "Rules:" not in content

    def test_truncates_long_rules(self) -> None:
        """Test that rules are truncated to 500 chars."""
        long_rules = "x" * 600
        content = build_kalshi_underlying_user_content(
            title="Test",
            rules_primary=long_rules,
            category="Crypto",
        )
        assert len(content) < 700


class TestBuildKalshiDedupPrompt:
    """Tests for build_kalshi_dedup_prompt."""

    def test_includes_category(self) -> None:
        """Test that category is included."""
        prompt = build_kalshi_dedup_prompt("Crypto", ["BTC", "BITCOIN"])
        assert "Crypto" in prompt

    def test_includes_underlyings(self) -> None:
        """Test that underlyings are included."""
        prompt = build_kalshi_dedup_prompt("Crypto", ["BTC", "BITCOIN", "XBT"])
        assert "BTC" in prompt
        assert "BITCOIN" in prompt
        assert "XBT" in prompt

    def test_specifies_json_output_format(self) -> None:
        """Test that prompt specifies JSON output format."""
        prompt = build_kalshi_dedup_prompt("Crypto", ["BTC"])
        assert '"groups"' in prompt
        assert '"canonical"' in prompt
        assert '"aliases"' in prompt

    def test_includes_station_dedup_guidance(self) -> None:
        """Test that dedup prompt distinguishes same-city different-station."""
        prompt = build_kalshi_dedup_prompt("Weather", ["NYC_KNYC", "NYC_KLGA"])
        assert "NYC_KNYC and NYC_KLGA" in prompt
        assert "do NOT group" in prompt
        assert "NEWYORK_KNYC" in prompt


class TestBuildPolyPrompt:
    """Tests for build_poly_prompt."""

    def test_includes_valid_categories(self) -> None:
        """Test that valid categories are included."""
        prompt = build_poly_prompt(["Crypto", "Sports"], ["BTC", "NFL"])
        assert "Crypto" in prompt
        assert "Sports" in prompt

    def test_includes_valid_underlyings(self) -> None:
        """Test that valid underlyings are included."""
        prompt = build_poly_prompt(["Crypto"], ["BTC", "ETH"])
        assert "BTC" in prompt
        assert "ETH" in prompt

    def test_includes_valid_strike_types(self) -> None:
        """Test that valid strike types are included."""
        prompt = build_poly_prompt([], [])
        assert '"greater"' in prompt
        assert '"less"' in prompt
        assert '"between"' in prompt

    def test_specifies_json_output_format(self) -> None:
        """Test that prompt specifies JSON output format."""
        prompt = build_poly_prompt([], [])
        assert '"category"' in prompt
        assert '"underlying"' in prompt
        assert '"strike_type"' in prompt
        assert '"floor_strike"' in prompt
        assert '"cap_strike"' in prompt

    def test_emphasizes_validation_constraints(self) -> None:
        """Test that prompt emphasizes validation constraints."""
        prompt = build_poly_prompt([], [])
        assert "MUST be from the provided lists" in prompt


class TestBuildPolyUserContent:
    """Tests for build_poly_user_content."""

    def test_includes_title(self) -> None:
        """Test that title is included."""
        content = build_poly_user_content(
            title="Will BTC reach $100k?",
            description="",
        )
        assert "Title: Will BTC reach $100k?" in content

    def test_includes_description_when_present(self) -> None:
        """Test that description is included when present."""
        content = build_poly_user_content(
            title="Test",
            description="This market resolves YES if...",
        )
        assert "Description: This market resolves YES if..." in content

    def test_excludes_description_when_empty(self) -> None:
        """Test that description line is excluded when empty."""
        content = build_poly_user_content(
            title="Test",
            description="",
        )
        assert "Description:" not in content

    def test_truncates_long_description(self) -> None:
        """Test that description is truncated to 500 chars."""
        long_desc = "x" * 600
        content = build_poly_user_content(
            title="Test",
            description=long_desc,
        )
        assert len(content) < 700


class TestBuildPolyBatchUserContent:
    """Tests for build_poly_batch_user_content."""

    def test_builds_single_market(self) -> None:
        """Test building content for a single market."""
        markets = [{"id": "cond-1", "title": "BTC above $100k"}]
        content = build_poly_batch_user_content(markets)
        assert "[ID: cond-1]" in content
        assert "Title: BTC above $100k" in content

    def test_builds_multiple_markets_with_separator(self) -> None:
        """Test that multiple markets are separated by ---."""
        markets = [
            {"id": "m1", "title": "Market 1"},
            {"id": "m2", "title": "Market 2"},
        ]
        content = build_poly_batch_user_content(markets)
        assert "---" in content
        assert "[ID: m1]" in content
        assert "[ID: m2]" in content

    def test_includes_description_when_present(self) -> None:
        """Test that description is included when present."""
        markets = [{"id": "m1", "title": "T1", "description": "Some description"}]
        content = build_poly_batch_user_content(markets)
        assert "Description: Some description" in content

    def test_truncates_long_description(self) -> None:
        """Test that descriptions are truncated to 500 chars."""
        long_desc = "x" * 600
        markets = [{"id": "m1", "title": "T1", "description": long_desc}]
        content = build_poly_batch_user_content(markets)
        assert len(content) < 700

    def test_excludes_description_when_absent(self) -> None:
        """Test that description is not included when absent."""
        markets = [{"id": "m1", "title": "T1"}]
        content = build_poly_batch_user_content(markets)
        assert "Description:" not in content
