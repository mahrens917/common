"""Tests for llm_extractor _response_parser module."""

import json

import pytest

from common.llm_extractor._response_parser import (
    ExtraDataInResponse,
    _parse_json_with_recovery,
    parse_kalshi_dedup_response,
    parse_kalshi_underlying_batch_response,
    parse_kalshi_underlying_response,
    parse_poly_batch_response,
    parse_poly_extraction_response,
    parse_strike_value,
    strip_markdown_json,
    validate_poly_extraction,
)


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

    def test_parses_negative_value(self) -> None:
        """Test parsing negative value."""
        assert parse_strike_value(-5.5) == -5.5
        assert parse_strike_value("-5.5") == -5.5

    def test_raises_for_invalid_type(self) -> None:
        """Test that invalid types raise TypeError."""
        with pytest.raises(TypeError):
            parse_strike_value([3500])


class TestParseKalshiUnderlyingResponse:
    """Tests for parse_kalshi_underlying_response."""

    def test_parses_valid_response(self) -> None:
        """Test parsing a valid response."""
        response = '{"underlying": "BTC"}'
        assert parse_kalshi_underlying_response(response) == "BTC"

    def test_uppercases_underlying(self) -> None:
        """Test that underlying is uppercased."""
        response = '{"underlying": "btc"}'
        assert parse_kalshi_underlying_response(response) == "BTC"

    def test_handles_markdown_wrapped(self) -> None:
        """Test handling markdown-wrapped response."""
        response = '```json\n{"underlying": "ETH"}\n```'
        assert parse_kalshi_underlying_response(response) == "ETH"

    def test_returns_none_for_missing_underlying(self) -> None:
        """Test that missing underlying returns None."""
        response = '{"other": "value"}'
        assert parse_kalshi_underlying_response(response) is None

    def test_raises_for_invalid_json(self) -> None:
        """Test that invalid JSON raises JSONDecodeError."""
        response = "not json"
        with pytest.raises(json.JSONDecodeError):
            parse_kalshi_underlying_response(response)


class TestParseKalshiUnderlyingBatchResponse:
    """Tests for parse_kalshi_underlying_batch_response."""

    def test_parses_valid_batch(self) -> None:
        """Test parsing a valid batch response."""
        response = json.dumps(
            {
                "markets": [
                    {"id": "m1", "underlying": "BTC"},
                    {"id": "m2", "underlying": "ETH"},
                ]
            }
        )
        results, failed = parse_kalshi_underlying_batch_response(response, ["m1", "m2"])
        assert results == {"m1": "BTC", "m2": "ETH"}
        assert failed == []

    def test_uppercases_underlyings(self) -> None:
        """Test that underlyings are uppercased."""
        response = json.dumps({"markets": [{"id": "m1", "underlying": "btc"}]})
        results, _ = parse_kalshi_underlying_batch_response(response, ["m1"])
        assert results["m1"] == "BTC"

    def test_returns_failed_ids_for_missing(self) -> None:
        """Test that missing IDs are returned as failed."""
        response = json.dumps({"markets": [{"id": "m1", "underlying": "BTC"}]})
        results, failed = parse_kalshi_underlying_batch_response(response, ["m1", "m2"])
        assert "m1" in results
        assert "m2" in failed

    def test_handles_id_correction(self) -> None:
        """Test that ID correction works for case differences."""
        response = json.dumps({"markets": [{"id": "M1", "underlying": "BTC"}]})  # LLM uppercased
        results, failed = parse_kalshi_underlying_batch_response(response, ["m1"])  # Original lowercase
        assert "m1" in results
        assert results["m1"] == "BTC"
        assert failed == []

    def test_returns_empty_for_missing_markets_key(self) -> None:
        """Test that missing 'markets' key returns all IDs as failed."""
        response = json.dumps({"data": []})
        results, failed = parse_kalshi_underlying_batch_response(response, ["m1", "m2"])
        assert results == {}
        assert failed == ["m1", "m2"]

    def test_skips_items_without_underlying(self) -> None:
        """Test that items without underlying are skipped."""
        response = json.dumps(
            {
                "markets": [
                    {"id": "m1", "underlying": "BTC"},
                    {"id": "m2"},  # Missing underlying
                ]
            }
        )
        results, failed = parse_kalshi_underlying_batch_response(response, ["m1", "m2"])
        assert results == {"m1": "BTC"}
        assert "m2" in failed


class TestParseKalshiDedupResponse:
    """Tests for parse_kalshi_dedup_response."""

    def test_parses_valid_response_with_groups(self) -> None:
        """Test parsing a valid response with duplicate groups."""
        response = json.dumps(
            {
                "groups": [
                    {"canonical": "BTC", "aliases": ["BITCOIN", "XBT"]},
                    {"canonical": "ETH", "aliases": ["ETHEREUM"]},
                ]
            }
        )
        mapping = parse_kalshi_dedup_response(response)
        assert mapping["BITCOIN"] == "BTC"
        assert mapping["XBT"] == "BTC"
        assert mapping["ETHEREUM"] == "ETH"

    def test_returns_empty_dict_for_no_duplicates(self) -> None:
        """Test that no duplicates returns empty dict."""
        response = '{"groups": []}'
        assert parse_kalshi_dedup_response(response) == {}

    def test_uppercases_all_values(self) -> None:
        """Test that all values are uppercased."""
        response = json.dumps({"groups": [{"canonical": "btc", "aliases": ["bitcoin"]}]})
        mapping = parse_kalshi_dedup_response(response)
        assert mapping["BITCOIN"] == "BTC"

    def test_raises_for_invalid_json(self) -> None:
        """Test that invalid JSON raises JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            parse_kalshi_dedup_response("not json")


class TestValidatePolyExtraction:
    """Tests for validate_poly_extraction."""

    def test_valid_extraction_passes(self) -> None:
        """Test that a valid extraction passes validation."""
        extraction = {
            "category": "Crypto",
            "underlying": "BTC",
            "strike_type": "greater",
            "floor_strike": 100000,
            "cap_strike": None,
        }
        valid_categories = {"Crypto", "Sports"}
        valid_underlyings = {"BTC", "ETH"}
        is_valid, error = validate_poly_extraction(extraction, valid_categories, valid_underlyings)
        assert is_valid
        assert error == ""

    def test_invalid_category_fails(self) -> None:
        """Test that invalid category fails validation."""
        extraction = {
            "category": "InvalidCategory",
            "underlying": "BTC",
            "strike_type": "greater",
        }
        is_valid, error = validate_poly_extraction(extraction, {"Crypto"}, {"BTC"})
        assert not is_valid
        assert "invalid category" in error

    def test_invalid_underlying_fails(self) -> None:
        """Test that invalid underlying fails validation."""
        extraction = {
            "category": "Crypto",
            "underlying": "UNKNOWN",
            "strike_type": "greater",
        }
        is_valid, error = validate_poly_extraction(extraction, {"Crypto"}, {"BTC"})
        assert not is_valid
        assert "invalid underlying" in error

    def test_invalid_strike_type_fails(self) -> None:
        """Test that invalid strike_type fails validation."""
        extraction = {
            "category": "Crypto",
            "underlying": "BTC",
            "strike_type": "invalid_type",
        }
        is_valid, error = validate_poly_extraction(extraction, {"Crypto"}, {"BTC"})
        assert not is_valid
        assert "invalid strike_type" in error

    def test_non_numeric_floor_strike_raises(self) -> None:
        """Test that non-numeric floor_strike raises ValueError."""
        extraction = {
            "category": "Crypto",
            "underlying": "BTC",
            "strike_type": "greater",
            "floor_strike": "not a number",
        }
        with pytest.raises(ValueError, match="floor_strike not numeric"):
            validate_poly_extraction(extraction, {"Crypto"}, {"BTC"})

    def test_non_numeric_cap_strike_raises(self) -> None:
        """Test that non-numeric cap_strike raises ValueError."""
        extraction = {
            "category": "Crypto",
            "underlying": "BTC",
            "strike_type": "less",
            "cap_strike": "not a number",
        }
        with pytest.raises(ValueError, match="cap_strike not numeric"):
            validate_poly_extraction(extraction, {"Crypto"}, {"BTC"})

    def test_cap_not_greater_than_floor_fails(self) -> None:
        """Test that cap <= floor fails validation."""
        extraction = {
            "category": "Crypto",
            "underlying": "BTC",
            "strike_type": "between",
            "floor_strike": 100000,
            "cap_strike": 100000,
        }
        is_valid, error = validate_poly_extraction(extraction, {"Crypto"}, {"BTC"})
        assert not is_valid
        assert "cap_strike" in error and "must be >" in error

    def test_cap_less_than_floor_fails(self) -> None:
        """Test that cap < floor fails validation."""
        extraction = {
            "category": "Crypto",
            "underlying": "BTC",
            "strike_type": "between",
            "floor_strike": 100000,
            "cap_strike": 90000,
        }
        is_valid, error = validate_poly_extraction(extraction, {"Crypto"}, {"BTC"})
        assert not is_valid
        assert "cap_strike" in error and "must be >" in error

    def test_negative_strikes_valid(self) -> None:
        """Test that negative strikes are valid."""
        extraction = {
            "category": "Economics",
            "underlying": "FED",
            "strike_type": "between",
            "floor_strike": -1.0,
            "cap_strike": 0.5,
        }
        is_valid, error = validate_poly_extraction(extraction, {"Economics"}, {"FED"})
        assert is_valid

    def test_null_strikes_valid(self) -> None:
        """Test that null strikes are valid."""
        extraction = {
            "category": "Crypto",
            "underlying": "BTC",
            "strike_type": "greater",
            "floor_strike": None,
            "cap_strike": None,
        }
        is_valid, error = validate_poly_extraction(extraction, {"Crypto"}, {"BTC"})
        assert is_valid


class TestParsePolyExtractionResponse:
    """Tests for parse_poly_extraction_response."""

    def test_parses_valid_response(self) -> None:
        """Test parsing a valid response."""
        response = json.dumps(
            {
                "category": "Crypto",
                "underlying": "BTC",
                "strike_type": "greater",
                "floor_strike": 100000,
                "cap_strike": None,
            }
        )
        extraction, error = parse_poly_extraction_response(response, "m1", {"Crypto"}, {"BTC"})
        assert extraction is not None
        assert extraction.market_id == "m1"
        assert extraction.category == "Crypto"
        assert extraction.underlying == "BTC"
        assert extraction.strike_type == "greater"
        assert extraction.floor_strike == 100000.0
        assert error == ""

    def test_returns_none_for_invalid_category(self) -> None:
        """Test that invalid category returns None."""
        response = json.dumps(
            {
                "category": "Invalid",
                "underlying": "BTC",
                "strike_type": "greater",
            }
        )
        extraction, error = parse_poly_extraction_response(response, "m1", {"Crypto"}, {"BTC"})
        assert extraction is None
        assert "invalid category" in error

    def test_raises_for_invalid_json(self) -> None:
        """Test that invalid JSON raises JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            parse_poly_extraction_response("not json", "m1", {"Crypto"}, {"BTC"})


class TestParsePolyBatchResponse:
    """Tests for parse_poly_batch_response."""

    def test_parses_valid_batch(self) -> None:
        """Test parsing a valid batch response."""
        response = json.dumps(
            {
                "markets": [
                    {
                        "id": "m1",
                        "category": "Crypto",
                        "underlying": "BTC",
                        "strike_type": "greater",
                        "floor_strike": 100000,
                        "cap_strike": None,
                    },
                    {
                        "id": "m2",
                        "category": "Sports",
                        "underlying": "NFL",
                        "strike_type": "between",
                        "floor_strike": 10,
                        "cap_strike": 20,
                    },
                ]
            }
        )
        extractions, failed = parse_poly_batch_response(response, {"Crypto", "Sports"}, {"BTC", "NFL"})
        assert len(extractions) == 2
        assert "m1" in extractions
        assert "m2" in extractions
        assert len(failed) == 0

    def test_separates_valid_and_invalid(self) -> None:
        """Test that valid and invalid items are separated."""
        response = json.dumps(
            {
                "markets": [
                    {
                        "id": "valid",
                        "category": "Crypto",
                        "underlying": "BTC",
                        "strike_type": "greater",
                    },
                    {
                        "id": "invalid",
                        "category": "Invalid",
                        "underlying": "BTC",
                        "strike_type": "greater",
                    },
                ]
            }
        )
        extractions, failed = parse_poly_batch_response(response, {"Crypto"}, {"BTC"})
        assert len(extractions) == 1
        assert "valid" in extractions
        assert "invalid" in failed

    def test_raises_for_invalid_json(self) -> None:
        """Test that invalid JSON raises JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            parse_poly_batch_response("not json", {"Crypto"}, {"BTC"}, ["m1", "m2"])

    def test_handles_id_correction(self) -> None:
        """Test that ID correction works."""
        response = json.dumps(
            {
                "markets": [
                    {
                        "id": "COND-1",  # LLM uppercased it
                        "category": "Crypto",
                        "underlying": "BTC",
                        "strike_type": "greater",
                    },
                ]
            }
        )
        extractions, _ = parse_poly_batch_response(response, {"Crypto"}, {"BTC"}, ["cond-1"])  # Original was lowercase
        assert "cond-1" in extractions


class TestExtraDataInResponse:
    """Tests for ExtraDataInResponse exception."""

    def test_raises_on_extra_data(self) -> None:
        """Test that extra data raises ExtraDataInResponse by default."""
        text = '{"key": "value"}Wait, I need to reconsider...'
        with pytest.raises(ExtraDataInResponse) as exc_info:
            _parse_json_with_recovery(text)
        assert "Wait" in exc_info.value.extra_text

    def test_allows_extra_data_when_enabled(self) -> None:
        """Test that extra data is recovered when allow_extra_data=True."""
        text = '{"key": "value"}Some extra text'
        result = _parse_json_with_recovery(text, allow_extra_data=True)
        assert result == {"key": "value"}


class TestDedupValidation:
    """Tests for dedup response validation with original underlyings."""

    def test_filters_invalid_canonical(self) -> None:
        """Test that invalid canonical is filtered out."""
        response = json.dumps({"groups": [{"canonical": "INVALID", "aliases": ["BTC"]}]})
        result = parse_kalshi_dedup_response(response, original_underlyings={"BTC", "ETH"})
        assert result == {}

    def test_filters_invalid_alias(self) -> None:
        """Test that invalid aliases are filtered out."""
        response = json.dumps({"groups": [{"canonical": "BTC", "aliases": ["BITCOIN", "INVALID"]}]})
        result = parse_kalshi_dedup_response(response, original_underlyings={"BTC", "BITCOIN"})
        assert result == {"BITCOIN": "BTC"}

    def test_keeps_valid_mappings(self) -> None:
        """Test that valid mappings are kept."""
        response = json.dumps({"groups": [{"canonical": "BTC", "aliases": ["BITCOIN"]}]})
        result = parse_kalshi_dedup_response(response, original_underlyings={"BTC", "BITCOIN"})
        assert result == {"BITCOIN": "BTC"}

    def test_no_validation_without_original(self) -> None:
        """Test that no validation happens without original_underlyings."""
        response = json.dumps({"groups": [{"canonical": "BTC", "aliases": ["BITCOIN", "XBT"]}]})
        result = parse_kalshi_dedup_response(response)
        assert result == {"BITCOIN": "BTC", "XBT": "BTC"}
