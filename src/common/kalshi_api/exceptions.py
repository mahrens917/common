"""API helpers exception classes."""

from typing import Any, Optional

from .client_helpers.errors import KalshiClientError


# Key/credential exceptions
class PrivateKeyNotRSAError(KalshiClientError):
    """Loaded private key is not RSA."""

    def __init__(self) -> None:
        super().__init__("Loaded private key is not RSA")


# Trade store exceptions
class TradeStoreNotProvidedError(KalshiClientError):
    """Trade store must not be None."""

    def __init__(self) -> None:
        super().__init__("Trade store must not be None")


class TradeStoreNotConfiguredError(KalshiClientError):
    """Kalshi trade store is not configured."""

    def __init__(self) -> None:
        super().__init__("Kalshi trade store is not configured")


class TradeStoreInitializationError(KalshiClientError):
    """Failed to initialize trade store."""

    def __init__(self, cause: Optional[BaseException] = None) -> None:
        super().__init__("Failed to initialize trade store")
        self.__cause__ = cause


class TradeMetadataFetchError(KalshiClientError):
    """Failed to fetch trade metadata for order."""

    def __init__(self, order_id: str, cause: Optional[BaseException] = None) -> None:
        super().__init__(f"Failed to fetch trade metadata for order {order_id}")
        self.order_id = order_id
        self.__cause__ = cause


class TradeMetadataMissingError(KalshiClientError):
    """Trade metadata missing for order."""

    def __init__(self, order_id: str) -> None:
        super().__init__(f"Trade metadata missing for order {order_id}")
        self.order_id = order_id


# Order exceptions
class OrderCreationMissingIdError(KalshiClientError):
    """Order creation response missing 'order_id'."""

    def __init__(self) -> None:
        super().__init__("Order creation response missing 'order_id'")


class OrderIdRequiredError(KalshiClientError):
    """Order ID must be provided."""

    def __init__(self, operation: str = "") -> None:
        if operation:
            msg = f"Order ID must be provided for {operation}"
        else:
            msg = "Order ID must be provided"
        super().__init__(msg)
        self.operation = operation


# Fills exceptions
class FillsResponseNotObjectError(KalshiClientError):
    """Fills response was not a JSON object."""

    def __init__(self) -> None:
        super().__init__("Fills response was not a JSON object")


class FillsResponseNotListError(KalshiClientError):
    """Fills response was not a list."""

    def __init__(self) -> None:
        super().__init__("Fills response was not a list")


class FillEntryNotObjectError(KalshiClientError):
    """Fill entry must be a JSON object."""

    def __init__(self) -> None:
        super().__init__("Fill entry must be a JSON object")


# Portfolio exceptions
class PortfolioBalanceEmptyError(KalshiClientError):
    """Empty response from portfolio balance API."""

    def __init__(self) -> None:
        super().__init__("Empty response from portfolio balance API")


class PortfolioBalanceInvalidTypeError(KalshiClientError):
    """Portfolio balance must be integer cents."""

    def __init__(self, received: Any) -> None:
        super().__init__(f"Portfolio balance must be integer cents, received: {received}")
        self.received = received


class PortfolioBalanceMissingTimestampError(KalshiClientError):
    """Portfolio balance response missing 'updated_ts' field."""

    def __init__(self) -> None:
        super().__init__("Portfolio balance response missing 'updated_ts' field")


class PortfolioBalanceTimestampNotNumericError(KalshiClientError):
    """Portfolio balance 'updated_ts' must be numeric."""

    def __init__(self) -> None:
        super().__init__("Portfolio balance 'updated_ts' must be numeric")


class PortfolioBalanceTimestampInvalidError(KalshiClientError):
    """Portfolio balance 'updated_ts' must be milliseconds since epoch."""

    def __init__(self) -> None:
        super().__init__("Portfolio balance 'updated_ts' must be milliseconds since epoch")


class PortfolioPositionsEmptyError(KalshiClientError):
    """Empty response from portfolio positions API."""

    def __init__(self) -> None:
        super().__init__("Empty response from portfolio positions API")


class PortfolioPositionsMissingFieldError(KalshiClientError):
    """Portfolio positions response missing 'positions'."""

    def __init__(self, payload: Any) -> None:
        super().__init__(f"Portfolio positions response missing 'positions': {payload}")
        self.payload = payload


class PortfolioPositionsNotListError(KalshiClientError):
    """Portfolio positions 'positions' must be a list."""

    def __init__(self) -> None:
        super().__init__("Portfolio positions 'positions' must be a list")


class PositionEntryNotObjectError(KalshiClientError):
    """Position entry must be a JSON object."""

    def __init__(self) -> None:
        super().__init__("Position entry must be a JSON object")


class InvalidPositionPayloadError(KalshiClientError):
    """Invalid position payload."""

    def __init__(self, item: Any, cause: Optional[BaseException] = None) -> None:
        super().__init__(f"Invalid position payload: {item}")
        self.item = item
        self.__cause__ = cause


class PositionMissingAveragePriceError(KalshiClientError):
    """Position payload missing 'average_price'."""

    def __init__(self) -> None:
        super().__init__("Position payload missing 'average_price'")


class InvalidAveragePriceError(KalshiClientError):
    """Invalid average price."""

    def __init__(self, average_price: Any, cause: Optional[BaseException] = None) -> None:
        super().__init__(f"Invalid average price: {average_price}")
        self.average_price = average_price
        self.__cause__ = cause


class InvalidPositionSideError(KalshiClientError):
    """Invalid position side."""

    def __init__(self, side: Any, cause: Optional[BaseException] = None) -> None:
        super().__init__(f"Invalid position side '{side}'")
        self.side = side
        self.__cause__ = cause


__all__ = [
    "PrivateKeyNotRSAError",
    "TradeStoreNotProvidedError",
    "TradeStoreNotConfiguredError",
    "TradeStoreInitializationError",
    "TradeMetadataFetchError",
    "TradeMetadataMissingError",
    "OrderCreationMissingIdError",
    "OrderIdRequiredError",
    "FillsResponseNotObjectError",
    "FillsResponseNotListError",
    "FillEntryNotObjectError",
    "PortfolioBalanceEmptyError",
    "PortfolioBalanceInvalidTypeError",
    "PortfolioBalanceMissingTimestampError",
    "PortfolioBalanceTimestampNotNumericError",
    "PortfolioBalanceTimestampInvalidError",
    "PortfolioPositionsEmptyError",
    "PortfolioPositionsMissingFieldError",
    "PortfolioPositionsNotListError",
    "PositionEntryNotObjectError",
    "InvalidPositionPayloadError",
    "PositionMissingAveragePriceError",
    "InvalidAveragePriceError",
    "InvalidPositionSideError",
]
