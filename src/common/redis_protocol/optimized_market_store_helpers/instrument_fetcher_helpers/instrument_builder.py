"""Instrument object construction from Redis data."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from common.truthy import pick_if

from ....redis_schema import DeribitInstrumentType
from ....time_utils import DERIBIT_EXPIRY_HOUR
from ..instrument_name_builder import InstrumentNameBuilder

logger = logging.getLogger(__name__)


def _coerce_number(value: Any) -> Optional[float]:
    """Coerce value to float or None."""
    if value is None:
        return None
    try:
        return float(value)
    except (  # policy_guard: allow-silent-handler
        TypeError,
        ValueError,
    ):
        return None


def _ensure_str_keys(payload: Dict[Any, Any]) -> Dict[str, Any]:
    """Normalize Redis payload keys to str."""
    if not payload:
        return {}
    if all(isinstance(key, str) for key in payload):
        return payload
    normalized: Dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(key, (bytes, bytearray)):
            normalized[key.decode("utf-8")] = value
        else:
            normalized[str(key)] = value
    return normalized


class InstrumentBuilder:
    """Builds instrument objects from Redis data."""

    @staticmethod
    def build_instruments(scan_results: List[tuple]) -> List:
        """Build instrument objects from scan results."""
        from ....data_models.instrument import Instrument

        instruments: List[Instrument] = []
        for key, descriptor, data in scan_results:
            instrument = InstrumentBuilder._build_single_instrument(key, descriptor, data)
            if instrument:
                instruments.append(instrument)
        return instruments

    @staticmethod
    def _build_single_instrument(key: str, descriptor: Any, data: Dict[str, Any]) -> Optional[Any]:
        """Build a single instrument object."""
        if not descriptor.expiry_iso:
            logger.debug("KEY_SCAN_DEBUG: Descriptor %s missing expiry", descriptor)
            return None

        normalized_data = _ensure_str_keys(data)

        try:
            expiry_dt = datetime.fromisoformat(f"{descriptor.expiry_iso}T{DERIBIT_EXPIRY_HOUR:02d}:00:00+00:00")
        except ValueError as exc:  # policy_guard: allow-silent-handler
            logger.warning(
                "KEY_SCAN_DEBUG: Failed to parse expiry %s for key %s (%s)",
                descriptor.expiry_iso,
                key,
                exc,
            )
            return None

        strike_value = float(descriptor.strike) if descriptor.strike is not None else None
        option_type = None
        if descriptor.option_kind:
            option_type = pick_if(descriptor.option_kind.startswith("c"), lambda: "call", lambda: "put")

        from ....data_models.instrument import Instrument

        return Instrument(
            instrument_name=InstrumentNameBuilder.derive_instrument_name(descriptor, strike_value=strike_value, option_type=option_type),
            currency=descriptor.currency.upper(),
            expiry=expiry_dt,
            strike=strike_value,
            option_type=option_type,
            is_future=descriptor.instrument_type == DeribitInstrumentType.FUTURE,
            best_bid=_coerce_number(normalized_data.get("best_bid")),
            best_ask=_coerce_number(normalized_data.get("best_ask")),
            best_bid_size=_coerce_number(normalized_data.get("best_bid_size")),
            best_ask_size=_coerce_number(normalized_data.get("best_ask_size")),
            implied_volatility=_coerce_number(normalized_data.get("implied_volatility")),
        )
