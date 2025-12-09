"""Batch conversion utilities for multiple instruments."""

import logging
from typing import TYPE_CHECKING, List

from ...data_models.instrument import Instrument

if TYPE_CHECKING:
    from ...data_models.market_data import MicroPriceOptionData

logger = logging.getLogger(__name__)


class BatchConverter:
    """Handles batch conversion of multiple instruments."""

    @staticmethod
    def convert_instruments_to_micro_price_data(
        instruments: List[Instrument],
        currency: str,
        converter_func,
    ) -> List["MicroPriceOptionData"]:
        """
        Convert a list of Instrument objects to MicroPriceOptionData objects.

        Args:
            instruments: List of Instrument objects to convert
            currency: Currency for the underlying asset (default: BTC)
            converter_func: Function to convert single instrument

        Returns:
            List of MicroPriceOptionData objects with valid conversions

        Raises:
            Exception: If no valid instruments provided (fail-fast principle)
        """
        # Fail-fast validation: empty input should raise exception immediately
        if not instruments or len(instruments) == 0:
            raise ValueError("Insufficient valid instruments: empty input list provided")

        micro_price_options = []
        conversion_failures: List[str] = []
        invalid_results: List[str] = []

        for instrument in instruments:
            try:
                # Use the centralized conversion logic
                micro_price_option = converter_func(instrument, currency)

            except (
                ValueError,
                TypeError,
                OSError,
            ) as conversion_error:
                conversion_failures.append(str(conversion_error))
                logger.warning(
                    "Failed to convert option to MicroPriceOptionData: %s",
                    conversion_error,
                    exc_info=True,
                )
                continue

            # Validate micro price calculations
            if not micro_price_option.is_valid():
                invalid_results.append(
                    f"{micro_price_option.strike}/{micro_price_option.expiry}: {micro_price_option.get_validation_errors()}"
                )
                logger.warning(
                    "Invalid micro price data for option %s/%s: %s",
                    micro_price_option.strike,
                    micro_price_option.expiry,
                    micro_price_option.get_validation_errors(),
                )
                continue

            micro_price_options.append(micro_price_option)

        # Fail-fast validation: if no valid conversions occurred, raise exception
        if len(micro_price_options) == 0:
            raise ValueError(
                f"Insufficient valid instruments: no valid conversions from {len(instruments)} input instruments"
            )

        if conversion_failures or invalid_results:
            logger.info(
                "Micro price conversion completed with %d failures and %d invalid results",
                len(conversion_failures),
                len(invalid_results),
            )

        return micro_price_options
