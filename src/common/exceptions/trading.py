"""Trading-specific exceptions."""

from . import ApplicationError


class TradingError(ApplicationError):
    """Base trading error."""

    pass
