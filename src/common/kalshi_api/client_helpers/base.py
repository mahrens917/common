"""Shared helpers for Kalshi API operation classes."""

from typing import Any


class ClientOperationBase:
    """Provide a shared client reference for API helper classes."""

    def __init__(self, client: Any) -> None:
        self.client = client


__all__ = ["ClientOperationBase"]
