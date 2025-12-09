"""Shared exception types for the trade store package."""


class TradeStoreError(RuntimeError):
    """Base error for trade store operations."""


class OrderMetadataError(TradeStoreError):
    """Raised when stored order metadata is missing or malformed."""


class TradeStoreShutdownError(TradeStoreError):
    """Raised when the Redis connection cannot be closed cleanly."""
