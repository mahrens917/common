"""Market data exceptions."""

from . import ApplicationError, DataError


class MarketError(ApplicationError):
    """Base market error."""

    pass


class InvalidMarketDataError(MarketError, DataError):
    """Market data is invalid."""

    pass
