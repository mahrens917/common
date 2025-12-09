"""Redis market key construction logic."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from src.common.exceptions import ValidationError
from src.common.time_helpers.expiry_conversions import parse_expiry_datetime

from ....redis_schema import DeribitInstrumentDescriptor

if TYPE_CHECKING:
    from ....data_models.instrument import Instrument

logger = logging.getLogger(__name__)


class MarketKeyBuilder:
    """Builds Redis keys for market instruments."""

    @staticmethod
    def determine_market_key(instrument: "Instrument", original_key: Optional[str]) -> str:
        if original_key:
            logger.debug("Using provided market key: %s", original_key)
            return original_key

        if not instrument.expiry:
            raise ValueError(f"Instrument {instrument} missing expiry")

        try:
            expiry_dt = parse_expiry_datetime(instrument.expiry)
        except ValueError as exc:
            raise ValidationError(f"Invalid expiry '{instrument.expiry}'") from exc

        descriptor = _build_descriptor(instrument, expiry_dt)
        logger.debug(
            "Constructed Redis key %s for instrument type %s",
            descriptor.key,
            descriptor.instrument_type.value,
        )
        return descriptor.key

    @staticmethod
    def format_key(
        currency: str,
        expiry: str,
        strike: Optional[float] = None,
        option_type: Optional[str] = None,
    ) -> str:
        if strike is None and option_type is None:
            key = f"market:{currency}_{expiry}"
            logger.debug("Formatted spot price key with underscore: %s", key)
            return key

        key = f"market:{currency}-{expiry}"
        if strike is not None:
            strike_str = str(int(strike)) if strike.is_integer() else str(strike)
            key += f"-{strike_str}"
            if option_type:
                key += f"-{option_type}"

        logger.debug("Formatted key: %s", key)
        return key


def format_key(
    currency: str,
    expiry: str,
    strike: Optional[float] = None,
    option_type: Optional[str] = None,
) -> str:
    """Convenience alias for MarketKeyBuilder.format_key."""
    return MarketKeyBuilder.format_key(currency, expiry, strike=strike, option_type=option_type)


def _build_descriptor(instrument: "Instrument", expiry_dt: datetime) -> DeribitInstrumentDescriptor:
    tzinfo = expiry_dt.tzinfo if expiry_dt.tzinfo is not None else timezone.utc
    expiry_with_tz = expiry_dt.replace(tzinfo=tzinfo)
    expiration_timestamp = int(expiry_with_tz.timestamp())

    if instrument.is_future:
        kind = "future"
        strike_value = None
    else:
        kind = "option"
        strike_value = instrument.strike

    quote_currency = getattr(instrument, "quote_currency", None)
    normalized_quote_currency = str(quote_currency).upper() if quote_currency else "USD"

    return DeribitInstrumentDescriptor.from_instrument_data(
        kind=kind,
        base_currency=str(instrument.currency).upper(),
        quote_currency=normalized_quote_currency,
        expiration_timestamp=expiration_timestamp,
        strike=strike_value,
        option_type=instrument.option_type,
    )
