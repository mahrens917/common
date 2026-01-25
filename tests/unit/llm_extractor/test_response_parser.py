"""Tests for llm_extractor _response_parser module."""

import json

import pytest

from common.llm_extractor._response_parser import parse_batch_response, parse_single_item, parse_strike_value, strip_markdown_json


class TestStripMarkdownJson:
    """Tests for strip_markdown_json."""

    def test_returns_plain_json_unchanged(self) -> None:
        """Test that plain JSON is returned as-is."""
        text = '{"key": "value"}'
        assert strip_markdown_json(text) == text

    def test_strips_json_code_block(self) -> None:
        """Test stripping ```json code blocks."""
        text = '```json\n{"key": "value"}\n```'
        assert strip_markdown_json(text) == '{"key": "value"}'

    def test_strips_plain_code_block(self) -> None:
        """Test stripping ``` code blocks without language."""
        text = '```\n{"key": "value"}\n```'
        assert strip_markdown_json(text) == '{"key": "value"}'

    def test_handles_whitespace(self) -> None:
        """Test handling leading/trailing whitespace."""
        text = '  \n{"key": "value"}\n  '
        assert strip_markdown_json(text) == '{"key": "value"}'


class TestParseStrikeValue:
    """Tests for parse_strike_value."""

    def test_returns_none_for_none(self) -> None:
        """Test that None input returns None."""
        assert parse_strike_value(None) is None

    def test_parses_int(self) -> None:
        """Test parsing integer value."""
        assert parse_strike_value(3500) == 3500.0

    def test_parses_float(self) -> None:
        """Test parsing float value."""
        assert parse_strike_value(3500.5) == 3500.5

    def test_parses_string(self) -> None:
        """Test parsing string value."""
        assert parse_strike_value("3500") == 3500.0

    def test_raises_for_invalid_type(self) -> None:
        """Test that invalid types raise TypeError."""
        with pytest.raises(TypeError):
            parse_strike_value([3500])


class TestParseSingleItem:
    """Tests for parse_single_item."""

    def test_parses_complete_item(self) -> None:
        """Test parsing a complete market item."""
        item = {
            "category": "Crypto",
            "underlying": "btc",
            "subject": "btc",
            "entity": "BTC price",
            "scope": "above 100000",
            "floor_strike": 100000,
            "cap_strike": None,
            "parent_entity": None,
            "parent_scope": None,
            "is_conjunction": False,
            "conjunction_scopes": [],
            "is_union": False,
            "union_scopes": [],
        }
        result = parse_single_item(item, "cond-123", "poly")
        assert result.market_id == "cond-123"
        assert result.platform == "poly"
        assert result.category == "Crypto"
        assert result.underlying == "BTC"
        assert result.subject == "BTC"
        assert result.entity == "BTC price"
        assert result.scope == "above 100000"
        assert result.floor_strike == 100000.0
        assert result.cap_strike is None

    def test_uppercases_underlying_and_subject(self) -> None:
        """Test that underlying and subject are uppercased."""
        item = {
            "category": "Sports",
            "underlying": "nyk",
            "subject": "mahomes",
            "entity": "NYK wins",
            "scope": "win game",
            "floor_strike": None,
            "cap_strike": None,
        }
        result = parse_single_item(item, "m1", "kalshi")
        assert result.underlying == "NYK"
        assert result.subject == "MAHOMES"

    def test_parses_conjunction(self) -> None:
        """Test parsing a conjunction market."""
        item = {
            "category": "Crypto",
            "underlying": "btc",
            "subject": "btc",
            "entity": "BTC and ETH prices",
            "scope": "both above threshold",
            "floor_strike": None,
            "cap_strike": None,
            "is_conjunction": True,
            "conjunction_scopes": ["BTC above 100000", "ETH above 5000"],
            "is_union": False,
            "union_scopes": [],
        }
        result = parse_single_item(item, "m2", "poly")
        assert result.is_conjunction is True
        assert result.conjunction_scopes == ("BTC above 100000", "ETH above 5000")

    def test_parses_union(self) -> None:
        """Test parsing a union market."""
        item = {
            "category": "Crypto",
            "underlying": "btc",
            "subject": "btc",
            "entity": "BTC or ETH price",
            "scope": "either above 100000",
            "floor_strike": None,
            "cap_strike": None,
            "is_conjunction": False,
            "conjunction_scopes": [],
            "is_union": True,
            "union_scopes": ["BTC above 100000", "ETH above 100000"],
        }
        result = parse_single_item(item, "m3", "poly")
        assert result.is_union is True
        assert result.union_scopes == ("BTC above 100000", "ETH above 100000")

    def test_raises_for_invalid_category(self) -> None:
        """Test that invalid category raises ValueError."""
        item = {
            "category": "InvalidCategory",
            "underlying": "BTC",
            "subject": "BTC",
            "entity": "x",
            "scope": "y",
        }
        with pytest.raises(ValueError, match="Invalid category"):
            parse_single_item(item, "m1", "poly")

    def test_raises_for_missing_underlying(self) -> None:
        """Test that missing underlying raises ValueError."""
        item = {
            "category": "Crypto",
            "subject": "BTC",
            "entity": "x",
            "scope": "y",
        }
        with pytest.raises(ValueError, match="underlying"):
            parse_single_item(item, "m1", "poly")

    def test_parses_parent_fields(self) -> None:
        """Test parsing parent_entity and parent_scope."""
        item = {
            "category": "Sports",
            "underlying": "lal",
            "subject": "lal",
            "entity": "LAL game 7 win",
            "scope": "beat Celtics in game 7",
            "floor_strike": None,
            "cap_strike": None,
            "parent_entity": "LAL series",
            "parent_scope": "win series",
        }
        result = parse_single_item(item, "m1", "poly")
        assert result.parent_entity == "LAL series"
        assert result.parent_scope == "win series"


class TestParseBatchResponse:
    """Tests for parse_batch_response."""

    def test_parses_batch_with_multiple_markets(self) -> None:
        """Test parsing a batch response with multiple markets."""
        response = json.dumps(
            {
                "markets": [
                    {
                        "id": "cond-1",
                        "category": "Crypto",
                        "underlying": "BTC",
                        "subject": "BTC",
                        "entity": "BTC price",
                        "scope": "above 100000",
                        "floor_strike": 100000,
                        "cap_strike": None,
                        "is_conjunction": False,
                        "conjunction_scopes": [],
                        "is_union": False,
                        "union_scopes": [],
                    },
                    {
                        "id": "cond-2",
                        "category": "Economics",
                        "underlying": "FED",
                        "subject": "RATE",
                        "entity": "Fed rate",
                        "scope": "cut 25bp",
                        "floor_strike": None,
                        "cap_strike": None,
                        "is_conjunction": False,
                        "conjunction_scopes": [],
                        "is_union": False,
                        "union_scopes": [],
                    },
                ]
            }
        )
        results = parse_batch_response(response, "poly")
        assert len(results) == 2
        assert "cond-1" in results
        assert "cond-2" in results
        assert results["cond-1"].category == "Crypto"
        assert results["cond-2"].category == "Economics"

    def test_raises_for_missing_markets_key(self) -> None:
        """Test that missing 'markets' key raises KeyError."""
        response = json.dumps({"data": []})
        with pytest.raises(KeyError, match="markets"):
            parse_batch_response(response, "poly")

    def test_skips_items_without_id(self) -> None:
        """Test that items without 'id' are skipped."""
        response = json.dumps(
            {
                "markets": [
                    {
                        "category": "Crypto",
                        "underlying": "BTC",
                        "subject": "BTC",
                        "entity": "BTC price",
                        "scope": "above 100000",
                    },
                ]
            }
        )
        results = parse_batch_response(response, "poly")
        assert len(results) == 0

    def test_skips_items_with_invalid_fields(self) -> None:
        """Test that items with invalid fields are skipped (not raised)."""
        response = json.dumps(
            {
                "markets": [
                    {
                        "id": "valid-1",
                        "category": "Crypto",
                        "underlying": "BTC",
                        "subject": "BTC",
                        "entity": "BTC price",
                        "scope": "above 100000",
                        "floor_strike": None,
                        "cap_strike": None,
                    },
                    {
                        "id": "invalid-1",
                        "category": "NotACategory",
                        "underlying": "X",
                        "subject": "X",
                        "entity": "x",
                        "scope": "y",
                    },
                ]
            }
        )
        results = parse_batch_response(response, "poly")
        assert len(results) == 1
        assert "valid-1" in results

    def test_handles_markdown_wrapped_response(self) -> None:
        """Test parsing response wrapped in markdown code block."""
        inner = json.dumps(
            {
                "markets": [
                    {
                        "id": "m1",
                        "category": "Finance",
                        "underlying": "SPY",
                        "subject": "SPY",
                        "entity": "SPY price",
                        "scope": "above 500",
                        "floor_strike": 500,
                        "cap_strike": None,
                        "is_conjunction": False,
                        "conjunction_scopes": [],
                        "is_union": False,
                        "union_scopes": [],
                    }
                ]
            }
        )
        response = f"```json\n{inner}\n```"
        results = parse_batch_response(response, "kalshi")
        assert len(results) == 1
        assert results["m1"].platform == "kalshi"
