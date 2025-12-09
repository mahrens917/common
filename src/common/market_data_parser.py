"""
Unified market data parsing utilities for Deribit instruments.

This module provides consistent, validated parsing for tickers, dates, and market data
to eliminate datetime corruption bugs (years 2520/2620) and replace 23+ inconsistent
parsing implementations across the codebase.

Key Features:
- Robust regex-based validation for BTC/ETH option tickers
- Proper datetime parsing preventing year corruption
- Currency isolation and validation
- Strike price and option type validation
- Comprehensive error handling with detailed error messages

Usage:
    from .market_data_parser import DeribitInstrumentParser

    # Parse a ticker
    parsed = DeribitInstrumentParser.parse_instrument("BTC-25JAN25-100000-C")
    print(f"Symbol: {parsed.symbol}, Expiry: {parsed.expiry_date}, Strike: {parsed.strike}")

    # Validate ticker format
    is_valid, error = DeribitInstrumentParser.validate_ticker_format("BTC-25JAN25-100000-C")
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# Constants
_PRECISION_HIGH = 0.1


class ParsingError(Exception):
    """Base exception for parsing issues"""

    pass


class ValidationError(ParsingError):
    """Validation issues with parsed data"""

    pass


class DateTimeCorruptionError(ParsingError):
    """DateTime parsing corruption detected (e.g., years 2520/2620)"""

    pass


@dataclass
class ParsedInstrument:
    """Validated parsed instrument data"""

    symbol: str  # BTC, ETH
    expiry_date: datetime  # 2025-06-08 08:00:00 UTC
    strike: Optional[float]  # 105500.0 (None for futures)
    option_type: Optional[str]  # 'call', 'put' (None for futures)
    instrument_type: str  # 'option', 'future'
    raw_ticker: str  # Original ticker string

    def __post_init__(self):
        """Validate parsed data"""
        from .market_data_parser_helpers.parsed_instrument_validator import (
            ParsedInstrumentValidator,
        )

        # Validate instrument-type-specific fields
        if self.instrument_type == "option":
            ParsedInstrumentValidator.validate_option_fields(
                self.strike, self.option_type, self.raw_ticker
            )
        elif self.instrument_type == "future":
            ParsedInstrumentValidator.validate_future_fields(
                self.strike, self.option_type, self.raw_ticker
            )
        elif self.instrument_type == "spot":
            ParsedInstrumentValidator.validate_spot_fields(
                self.strike, self.option_type, self.raw_ticker
            )

        # Critical validation: Prevent datetime corruption
        ParsedInstrumentValidator.validate_expiry_year(self.expiry_date, self.raw_ticker)


class DeribitInstrumentParser:
    """Centralized parser for Deribit instrument names and dates"""

    @classmethod
    def parse_instrument(cls, ticker: Any, strict_symbol: Optional[str] = None) -> ParsedInstrument:
        """
        Parse Deribit instrument ticker into validated components.

        Args:
            ticker: Deribit ticker (e.g., 'BTC-8JUN25-105500-P', 'BTC-8JUN25')
            strict_symbol: If provided, validates ticker matches this symbol

        Returns:
            ParsedInstrument with validated data

        Raises:
            ParsingError: If ticker is malformed or doesn't match strict_symbol
            DateTimeCorruptionError: If datetime parsing would create corrupted years
        """
        from .market_data_parser_helpers.instrument_parser import (
            FutureParser,
            OptionParser,
            SpotParser,
        )
        from .market_data_parser_helpers.pattern_matcher import TickerPatternMatcher
        from .market_data_parser_helpers.symbol_validator import SymbolValidator

        if not ticker or not isinstance(ticker, str):
            raise ParsingError(f"Invalid ticker format: {ticker}")

        ticker = ticker.strip().upper()

        # Try option pattern first
        option_match = TickerPatternMatcher.match_option(ticker)
        if option_match:
            symbol, date_part, strike_str, option_type = option_match
            SymbolValidator.validate_symbol(symbol, strict_symbol)
            return OptionParser.parse(symbol, date_part, strike_str, option_type, ticker)

        # Try future pattern
        future_match = TickerPatternMatcher.match_future(ticker)
        if future_match:
            symbol, date_part = future_match
            SymbolValidator.validate_symbol(symbol, strict_symbol)
            return FutureParser.parse(symbol, date_part, ticker)

        # Try spot pattern
        spot_match = TickerPatternMatcher.match_spot(ticker)
        if spot_match:
            base_symbol, quote_currency = spot_match
            SymbolValidator.validate_symbol(base_symbol, strict_symbol)
            return SpotParser.parse(base_symbol, quote_currency, ticker)

        raise ParsingError(f"Unrecognized ticker format: {ticker}")

    @classmethod
    def validate_ticker_format(cls, ticker: str) -> Tuple[bool, str]:
        """
        Validate ticker format without full parsing.

        Returns:
            (is_valid, error_message)
        """
        try:
            cls.parse_instrument(ticker)
        except (
            ParsingError,
            ValidationError,
            DateTimeCorruptionError,
        ) as e:
            return False, str(e)
        else:
            return True, ""

    @classmethod
    def extract_symbol_from_ticker(cls, ticker: str) -> Optional[str]:
        """
        Extract symbol from ticker without full validation.

        Returns:
            Symbol or None if extraction fails
        """
        from .market_data_parser_helpers.symbol_validator import SymbolValidator

        return SymbolValidator.extract_symbol_from_ticker(ticker)


class MarketDataValidator:
    """Validates market data consistency and quality"""

    @staticmethod
    def validate_options_data(options_data: Dict[str, Any], expected_symbol: str) -> Dict[str, Any]:
        """Validate options data structure and content.
        Args: options_data (dict containing options data), expected_symbol (BTC or ETH)
        Returns: Validation report with issues found"""
        from .market_data_parser_helpers.contract_validator import ContractValidator
        from .market_data_parser_helpers.structure_validator import StructureValidator

        report: Dict[str, Any] = {
            "valid": True,
            "issues": [],
            "stats": {
                "total_contracts": 0,
                "valid_contracts": 0,
                "symbol_mismatches": 0,
                "date_errors": 0,
                "price_errors": 0,
                "corrupted_years": 0,
            },
        }
        try:
            # Validate structure
            structure_issues = StructureValidator.validate_required_keys(options_data)
            if structure_issues:
                report["issues"].extend(structure_issues)
                report["valid"] = False
                return report
            # Validate data lengths
            lengths_valid, length_issues = StructureValidator.validate_data_lengths(options_data)
            if not lengths_valid:
                report["issues"].extend(length_issues)
                report["valid"] = False
                return report
            report["stats"]["total_contracts"] = len(options_data["contract_names"])
            # Validate individual contracts
            valid_count, contract_issues, contract_stats = ContractValidator.validate_all_contracts(
                options_data, expected_symbol
            )
            report["issues"].extend(contract_issues)
            report["stats"]["valid_contracts"] = valid_count
            for key, value in contract_stats.items():
                report["stats"][key] += value
            # Set overall validity
            error_rate = (
                report["stats"]["total_contracts"] - report["stats"]["valid_contracts"]
            ) / max(1, report["stats"]["total_contracts"])
            if error_rate > _PRECISION_HIGH:  # More than 10% errors
                report["valid"] = False
                report["issues"].append(f"High error rate: {error_rate:.1%}")
            # Critical: Any corrupted years make the data invalid
            if report["stats"]["corrupted_years"] > 0:
                report["valid"] = False
                report["issues"].append(
                    f"CRITICAL: Found {report['stats']['corrupted_years']} contracts with corrupted years"
                )
        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            report["valid"] = False
            report["issues"].append(f"Validation failed")
        else:
            return report

        return report

    @staticmethod
    def validate_and_parse_market_data(raw_data: Dict, expected_symbol: str) -> Dict:
        """Complete validation and parsing pipeline for market data.
        Steps: 1) Validate ticker formats 2) Parse datetime 3) Check currency contamination
        4) Validate consistency 5) Return clean data
        Args: raw_data (raw market data dict), expected_symbol (BTC or ETH)
        Returns: Dictionary with cleaned, validated data
        Raises: ValidationError (validation fails), DateTimeCorruptionError (datetime corruption)"""
        from .market_data_parser_helpers.data_cleaner import DataCleaner

        validation_report = MarketDataValidator.validate_options_data(raw_data, expected_symbol)
        if not validation_report["valid"]:
            if validation_report["stats"]["corrupted_years"] > 0:
                raise DateTimeCorruptionError(
                    f"Datetime corruption detected: {validation_report['issues']}"
                )
            else:
                raise ValidationError(f"Data validation failed: {validation_report['issues']}")
        return DataCleaner.clean_and_parse_market_data(raw_data, expected_symbol)
