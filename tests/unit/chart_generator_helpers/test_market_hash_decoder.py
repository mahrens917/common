"""Tests for chart_generator_helpers.market_hash_decoder module."""

import pytest

from common.chart_generator_helpers.market_hash_decoder import MarketHashDecoder


class TestMarketHashDecoderDecodeWeatherMarketHash:
    """Tests for decode_weather_market_hash method."""

    def test_decodes_bytes_keys_and_values(self) -> None:
        """Test decoding bytes to strings."""
        decoder = MarketHashDecoder()
        data = {b"ticker": b"KXMIA-25JAN01", b"price": b"50"}

        result = decoder.decode_weather_market_hash(data)

        assert result == {"ticker": "KXMIA-25JAN01", "price": "50"}

    def test_handles_string_keys_and_values(self) -> None:
        """Test handles string keys and values."""
        decoder = MarketHashDecoder()
        data = {"ticker": "KXMIA-25JAN01", "price": "50"}

        result = decoder.decode_weather_market_hash(data)

        assert result == {"ticker": "KXMIA-25JAN01", "price": "50"}

    def test_handles_mixed_bytes_and_strings(self) -> None:
        """Test handles mixed bytes and strings."""
        decoder = MarketHashDecoder()
        data = {b"ticker": "KXMIA-25JAN01", "price": b"50"}

        result = decoder.decode_weather_market_hash(data)

        assert result == {"ticker": "KXMIA-25JAN01", "price": "50"}

    def test_handles_empty_dict(self) -> None:
        """Test handles empty dictionary."""
        decoder = MarketHashDecoder()

        result = decoder.decode_weather_market_hash({})

        assert result == {}


class TestMarketHashDecoderExtractStrikeInfo:
    """Tests for extract_strike_info method."""

    def test_extracts_all_fields(self) -> None:
        """Test extracting all strike fields."""
        decoder = MarketHashDecoder()
        decoded = {
            "strike_type": "between",
            "floor_strike": "70",
            "cap_strike": "80",
        }

        strike_type, floor, cap = decoder.extract_strike_info(decoded)

        assert strike_type == "between"
        assert floor == 70.0
        assert cap == 80.0

    def test_lowercase_strike_type(self) -> None:
        """Test strike type is lowercased."""
        decoder = MarketHashDecoder()
        decoded = {
            "strike_type": "BETWEEN",
            "floor_strike": "70",
            "cap_strike": "80",
        }

        strike_type, floor, cap = decoder.extract_strike_info(decoded)

        assert strike_type == "between"

    def test_missing_strike_type(self) -> None:
        """Test missing strike type returns empty string."""
        decoder = MarketHashDecoder()
        decoded = {
            "floor_strike": "70",
            "cap_strike": "80",
        }

        strike_type, floor, cap = decoder.extract_strike_info(decoded)

        assert strike_type == ""
        assert floor == 70.0
        assert cap == 80.0

    def test_missing_floor_strike(self) -> None:
        """Test missing floor strike returns None."""
        decoder = MarketHashDecoder()
        decoded = {
            "strike_type": "greater",
            "cap_strike": "80",
        }

        strike_type, floor, cap = decoder.extract_strike_info(decoded)

        assert strike_type == "greater"
        assert floor is None
        assert cap == 80.0

    def test_missing_cap_strike(self) -> None:
        """Test missing cap strike returns None."""
        decoder = MarketHashDecoder()
        decoded = {
            "strike_type": "less",
            "floor_strike": "70",
        }

        strike_type, floor, cap = decoder.extract_strike_info(decoded)

        assert strike_type == "less"
        assert floor == 70.0
        assert cap is None

    def test_empty_decoded(self) -> None:
        """Test empty decoded dictionary."""
        decoder = MarketHashDecoder()

        strike_type, floor, cap = decoder.extract_strike_info({})

        assert strike_type == ""
        assert floor is None
        assert cap is None
