"""Validation for Deribit market keys."""

from src.common.config_loader import load_config

from ..markets import DeribitInstrumentDescriptor, DeribitInstrumentKey

VALIDATION_CONFIG = load_config("validation_constants.json")


class DeribitKeyValidator:
    """Validates Deribit market key format and structure."""

    @staticmethod
    def validate_key_format(key: str) -> None:
        """Validate basic key format."""
        if not key or not key.strip():
            raise TypeError("Key must be a non-empty string")

    @staticmethod
    def validate_key_parts(parts: list, key: str) -> None:
        """Validate key has minimum required parts."""
        if len(parts) < VALIDATION_CONFIG["field_counts"]["expected_parts"]:
            raise TypeError(f"Unexpected Deribit key format: {key!r}")

    @staticmethod
    def validate_namespace(parts: list, key: str) -> None:
        """Validate key is in Deribit markets namespace."""
        if parts[0] != "markets" or parts[1] != "deribit":
            raise ValueError(f"Key is not within the Deribit markets namespace: {key!r}")

    @staticmethod
    def validate_normalized_form(descriptor: DeribitInstrumentDescriptor, key: str) -> None:
        """Validate key matches its normalized form."""
        expected_key = DeribitInstrumentKey(
            instrument_type=descriptor.instrument_type,
            currency=descriptor.currency,
            expiry_iso=descriptor.expiry_iso,
            strike=descriptor.strike,
            option_kind=descriptor.option_kind,
            quote_currency=descriptor.quote_currency,
        ).key()

        if expected_key != key:
            raise TypeError(f"Deribit key {key!r} does not match normalized form {expected_key!r}")
