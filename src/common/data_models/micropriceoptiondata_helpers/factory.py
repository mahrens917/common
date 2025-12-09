"""Factory methods for creating MicroPriceOptionData instances."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..market_data import MicroPriceOptionData

from ..micro_price_helpers.calculations import MicroPriceCalculator
from ..micro_price_helpers.conversion import MicroPriceConversionHelpers


class MicroPriceOptionDataFactory:
    """Factory for creating MicroPriceOptionData from various sources."""

    @staticmethod
    def from_enhanced_option_data(enhanced_option: Any, cls: type) -> "MicroPriceOptionData":
        """
        Create MicroPriceOptionData from enhanced option data.

        Args:
            enhanced_option: Enhanced option data object with required fields
            cls: MicroPriceOptionData class reference

        Returns:
            MicroPriceOptionData instance
        """
        helpers = MicroPriceConversionHelpers
        instrument_name = helpers.resolve_instrument_name(enhanced_option)
        underlying = helpers.determine_underlying(enhanced_option, instrument_name)
        expiry = helpers.determine_expiry(enhanced_option)
        option_type = helpers.resolve_option_type(enhanced_option)
        best_bid, best_ask = helpers.extract_prices(enhanced_option)
        bid_size, ask_size = helpers.extract_sizes(enhanced_option)
        timestamp = helpers.resolve_timestamp(enhanced_option)

        (
            absolute_spread,
            relative_spread,
            i_raw,
            p_raw,
            g,
            h,
        ) = MicroPriceCalculator.compute_micro_price_metrics(best_bid, best_ask, bid_size, ask_size)

        return cls(
            instrument_name=instrument_name,
            underlying=underlying,
            strike=enhanced_option.strike,
            expiry=expiry,
            option_type=option_type,
            best_bid=best_bid,
            best_ask=best_ask,
            best_bid_size=bid_size,
            best_ask_size=ask_size,
            timestamp=timestamp,
            absolute_spread=absolute_spread,
            relative_spread=relative_spread,
            i_raw=i_raw,
            p_raw=p_raw,
            g=g,
            h=h,
        )
