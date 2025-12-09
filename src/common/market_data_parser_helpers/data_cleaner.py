"""Data cleaning helpers for market data."""

import logging
from typing import Dict

from ..market_data_parser import (
    DateTimeCorruptionError,
    DeribitInstrumentParser,
    ParsingError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class DataCleaner:
    """Cleans and validates market data."""

    @staticmethod
    def clean_and_parse_market_data(raw_data: Dict, expected_symbol: str) -> Dict:
        """
        Parse and clean market data, skipping invalid contracts.

        Args:
            raw_data: Raw market data dictionary
            expected_symbol: Expected symbol (BTC or ETH)

        Returns:
            Dictionary with cleaned, validated data
        """
        cleaned_data = {}

        for i, contract_name in enumerate(raw_data["contract_names"]):
            try:
                parsed = DeribitInstrumentParser.parse_instrument(
                    contract_name, strict_symbol=expected_symbol
                )

                # Store validated data
                cleaned_data[i] = {
                    "contract_name": contract_name,
                    "symbol": parsed.symbol,
                    "expiry": parsed.expiry_date,
                    "strike": parsed.strike,
                    "option_type": parsed.option_type,
                    "instrument_type": parsed.instrument_type,
                }

            except (
                ParsingError,
                ValidationError,
                DateTimeCorruptionError,
            ):
                logger.warning(f"Skipping invalid contract {contract_name}")
                continue

        return cleaned_data
