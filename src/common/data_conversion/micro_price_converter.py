"""
Centralized micro price conversion utilities.

This module provides the single source of truth for converting Instrument objects
to MicroPriceOptionData objects, ensuring consistency between production and testing
code paths.

Business Purpose:
- Convert raw market instrument data to micro price format for GP analysis
- Apply consistent mathematical transformations across all code paths
- Enforce data integrity with fail-fast validation
- Eliminate code duplication between production and testing utilities
"""

import logging
from typing import List

from ..data_models.instrument import Instrument
from ..data_models.market_data import MicroPriceOptionData

logger = logging.getLogger(__name__)


class MicroPriceConverter:
    """
    Centralized converter for Instrument → MicroPriceOptionData transformation.

    This class provides the single source of truth for all micro price conversion
    logic, ensuring consistency between production data loading and testing utilities.
    """

    @staticmethod
    def convert_instrument_to_micro_price_option_data(instrument: Instrument, currency: str) -> MicroPriceOptionData:
        """
        Convert an Instrument object to MicroPriceOptionData with micro price calculations.

        This is the authoritative implementation of the conversion logic that was
        previously duplicated in multiple locations. All conversions should use
        this method to ensure consistency.
        """
        from .micro_price_helpers import FieldResolver, FieldValidator, MetricsCalculator

        FieldValidator.validate_required_fields(instrument)
        bid_price, ask_price, bid_size, ask_size = FieldValidator.extract_prices_and_sizes(instrument)
        strike_value = instrument.strike
        if strike_value is None:
            raise ValueError(f"Instrument {instrument.instrument_name} missing strike")
        strike = float(strike_value)

        option_type_value = instrument.option_type
        if option_type_value is None:
            raise ValueError(f"Instrument {instrument.instrument_name} missing option_type")
        option_type = str(option_type_value)
        expiry = FieldResolver.resolve_expiry_datetime(instrument.expiry)

        instrument_name = FieldResolver.resolve_instrument_name(instrument)
        (
            absolute_spread,
            i_raw,
            p_raw,
            g,
            h,
            relative_spread,
        ) = MetricsCalculator.compute_micro_price_metrics(bid_price, ask_price, bid_size, ask_size, instrument_name)

        current_timestamp = FieldResolver.resolve_quote_timestamp(instrument)

        return MicroPriceOptionData(
            instrument_name=instrument_name,
            underlying=currency,
            strike=strike,
            expiry=expiry,
            option_type=option_type,
            best_bid=bid_price,
            best_ask=ask_price,
            best_bid_size=bid_size,
            best_ask_size=ask_size,
            timestamp=current_timestamp,
            absolute_spread=absolute_spread,
            relative_spread=relative_spread,
            i_raw=i_raw,
            p_raw=p_raw,
            g=g,
            h=h,
            implied_volatility=instrument.implied_volatility,
            bid_iv=instrument.bid_iv,
            ask_iv=instrument.ask_iv,
        )

    @staticmethod
    def convert_instruments_to_micro_price_data(instruments: List[Instrument], currency: str = "BTC") -> List[MicroPriceOptionData]:
        """
        Convert a list of Instrument objects to MicroPriceOptionData objects.

        This is a convenience method that applies the single-instrument conversion
        to a list of instruments, with proper error handling and filtering.
        """
        from .micro_price_helpers import BatchConverter

        return BatchConverter.convert_instruments_to_micro_price_data(
            instruments,
            currency,
            MicroPriceConverter.convert_instrument_to_micro_price_option_data,
        )
