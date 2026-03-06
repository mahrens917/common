"""Validate Kalshi credentials."""

from .errors import KalshiClientError


def extract_and_validate_credentials(credentials) -> str:
    """Extract and validate private key from credentials."""
    try:
        return credentials.require_private_key()
    except RuntimeError as exc:
        raise KalshiClientError(str(exc)) from exc
