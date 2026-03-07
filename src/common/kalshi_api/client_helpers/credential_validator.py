"""Credential validation utilities for Kalshi API clients."""

from .errors import KalshiClientError


def extract_and_validate_credentials(credentials):
    """Extract and validate the private key from a credentials object."""
    try:
        return credentials.require_private_key()
    except RuntimeError as exc:
        raise KalshiClientError(str(exc)) from exc
