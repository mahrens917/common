from datetime import datetime, timezone

import pytest

from common.market_data_parser import (
    DateTimeCorruptionError,
    DeribitInstrumentParser,
    MarketDataValidator,
    ParsedInstrument,
    ParsingError,
    ValidationError,
)

_CONST_2025 = 2025
_CONST_2099 = 2099
_TEST_COUNT_2 = 2
_TEST_COUNT_9 = 9


@pytest.fixture(autouse=True)
def fixed_current_time(monkeypatch):
    monkeypatch.setattr(
        "common.time_utils.get_current_utc",
        lambda: datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def test_parse_option_and_future():
    option = DeribitInstrumentParser.parse_instrument("BTC-25JAN25-100000-C")
    assert option.symbol == "BTC"
    assert option.option_type == "call"
    assert option.instrument_type == "option"
    assert option.expiry_date.year == _CONST_2025

    future = DeribitInstrumentParser.parse_instrument("ETH-8JUN25")
    assert future.instrument_type == "future"
    assert future.symbol == "ETH"
    assert future.strike is None
    normalized = DeribitInstrumentParser.parse_instrument(" eth-8jun25-1500-p ")
    assert normalized.symbol == "ETH"
    assert normalized.option_type == "put"


def test_validate_ticker_format_errors():
    valid, error = DeribitInstrumentParser.validate_ticker_format("BTC-25JAN25-100000-C")
    assert valid is True and error == ""

    valid, error = DeribitInstrumentParser.validate_ticker_format("XYZ-1JAN25-1000-C")
    assert not valid
    assert "Unsupported symbol" in error


def test_strict_symbol_validation():
    with pytest.raises(ValidationError):
        DeribitInstrumentParser.parse_instrument("ETH-25JAN25-3000-C", strict_symbol="BTC")


def test_invalid_ticker_format_raises():
    with pytest.raises(ParsingError):
        DeribitInstrumentParser.parse_instrument("INVALID")
    with pytest.raises(ParsingError):
        DeribitInstrumentParser.parse_instrument(None)  # type: ignore[arg-type]


def test_market_data_validator_reports_inconsistent_lengths():
    data = {
        "strikes": [50000.0],
        "expiries": [datetime(2025, 6, 8, 8, tzinfo=timezone.utc)],
        "implied_volatilities": [0.5, 0.4],
        "contract_names": ["BTC-8JUN25-50000-C"],
    }

    report = MarketDataValidator.validate_options_data(data, "BTC")
    assert not report["valid"]
    assert any("Inconsistent data lengths" in issue for issue in report["issues"])


def test_validate_and_parse_market_data_success():
    raw_data = {
        "strikes": [50000.0, 55000.0],
        "expiries": [
            datetime(2025, 6, 8, 8, tzinfo=timezone.utc),
            datetime(2025, 6, 8, 8, tzinfo=timezone.utc),
        ],
        "implied_volatilities": [0.5, 0.6],
        "contract_names": ["BTC-8JUN25-50000-C", "BTC-8JUN25-55000-P"],
    }

    parsed = MarketDataValidator.validate_and_parse_market_data(raw_data, "BTC")
    assert len(parsed) == _TEST_COUNT_2
    assert parsed[0]["option_type"] == "call"
    assert parsed[1]["option_type"] == "put"


def test_validate_and_parse_market_data_invalid_symbol():
    raw_data = {
        "strikes": [50000.0],
        "expiries": [datetime(2025, 6, 8, 8, tzinfo=timezone.utc)],
        "implied_volatilities": [0.5],
        "contract_names": ["ETH-8JUN25-50000-C"],
    }

    with pytest.raises(ValidationError):
        MarketDataValidator.validate_and_parse_market_data(raw_data, "BTC")


def test_date_parsing_out_of_range_and_mismatch():
    with pytest.raises(ParsingError):
        DeribitInstrumentParser.parse_instrument("BTC-1JAN40-100000-C")

    report = MarketDataValidator.validate_options_data(
        {
            "strikes": [50000.0],
            "expiries": [datetime(2520, 6, 8, 8, tzinfo=timezone.utc)],
            "implied_volatilities": [0.5],
            "contract_names": ["BTC-8JUN25-50000-C"],
        },
        "BTC",
    )

    assert any("Expiry mismatch" in issue or "corrupted" in issue for issue in report["issues"])
    assert report["stats"]["date_errors"] >= 1


def test_parse_spot_ticker_and_invalid_quote_currency():
    spot = DeribitInstrumentParser.parse_instrument("BTC_USDC")
    assert spot.instrument_type == "spot"
    assert spot.expiry_date.year == _CONST_2099
    assert spot.strike is None and spot.option_type is None

    with pytest.raises(ParsingError):
        DeribitInstrumentParser.parse_instrument("BTC_GBP")


def test_extract_symbol_from_ticker_handles_invalid_inputs():
    assert DeribitInstrumentParser.extract_symbol_from_ticker("ETH-1JAN25-2000-C") == "ETH"
    assert DeribitInstrumentParser.extract_symbol_from_ticker("XYZ-1JAN25-2000-C") is None
    assert DeribitInstrumentParser.extract_symbol_from_ticker(None) is None


def test_validate_options_data_missing_keys():
    report = MarketDataValidator.validate_options_data(
        {
            "strikes": [50000.0],
            "expiries": [datetime(2025, 6, 8, 8, tzinfo=timezone.utc)],
            "implied_volatilities": [0.5],
        },
        "BTC",
    )

    assert report["valid"] is False
    assert any("Missing required key" in issue for issue in report["issues"])


def test_parsed_instrument_enforces_type_constraints():
    expiry = datetime(2025, 1, 1, 8, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        ParsedInstrument(
            symbol="BTC",
            expiry_date=expiry,
            strike=25000.0,
            option_type=None,
            instrument_type="future",
            raw_ticker="BTC-1JAN25",
        )


def test_validate_options_data_symbol_mismatch_stats():
    data = {
        "strikes": [50000.0],
        "expiries": [datetime(2025, 6, 8, 8, tzinfo=timezone.utc)],
        "implied_volatilities": [0.5],
        "contract_names": ["ETH-8JUN25-50000-C"],
    }

    report = MarketDataValidator.validate_options_data(data, "BTC")
    assert report["valid"] is False
    assert report["stats"]["symbol_mismatches"] == 1


def test_validate_options_data_high_error_rate_flag():
    base_contract = "BTC-8JUN25-50000-C"
    contracts = [base_contract] + ["INVALID"] * 4
    data = {
        "strikes": [50000.0 for _ in contracts],
        "expiries": [datetime(2025, 6, 8, 8, tzinfo=timezone.utc) for _ in contracts],
        "implied_volatilities": [0.5 for _ in contracts],
        "contract_names": contracts,
    }

    report = MarketDataValidator.validate_options_data(data, "BTC")
    assert report["valid"] is False
    assert any("High error rate" in issue for issue in report["issues"])


def test_validate_and_parse_market_data_detects_corruption():
    raw_data = {
        "strikes": [50000.0],
        "expiries": [datetime(2099, 12, 31, 8, tzinfo=timezone.utc)],
        "implied_volatilities": [0.5],
        "contract_names": ["BTC_USDC"],
    }

    with pytest.raises(DateTimeCorruptionError):
        MarketDataValidator.validate_and_parse_market_data(raw_data, "BTC")


def test_parse_instrument_invalid_month():
    with pytest.raises(ParsingError):
        DeribitInstrumentParser.parse_instrument("BTC-1XYZ25-1000-C")


def test_validate_options_data_expiry_mismatch_flagged():
    data = {
        "strikes": [50000.0],
        "expiries": [datetime(2025, 6, 8, 10, tzinfo=timezone.utc)],
        "implied_volatilities": [0.5],
        "contract_names": ["BTC-8JUN25-50000-C"],
    }

    report = MarketDataValidator.validate_options_data(data, "BTC")
    assert report["stats"]["date_errors"] >= 1
    assert any("Expiry mismatch" in issue for issue in report["issues"])


def test_validate_and_parse_market_data_skips_invalid_entries():
    valid_contracts = ["BTC-8JUN25-50000-C"] * 9
    raw_data = {
        "strikes": [50000.0] * 9 + [51000.0],
        "expiries": [datetime(2025, 6, 8, 8, tzinfo=timezone.utc) for _ in range(9)] + [datetime(2025, 6, 8, 8, tzinfo=timezone.utc)],
        "implied_volatilities": [0.5] * 10,
        "contract_names": valid_contracts + ["INVALID"],
    }

    cleaned = MarketDataValidator.validate_and_parse_market_data(raw_data, "BTC")
    assert len(cleaned) == _TEST_COUNT_9
    assert all(entry["contract_name"] == "BTC-8JUN25-50000-C" for entry in cleaned.values())
