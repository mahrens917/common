"""Exception classes for order response parsing.

These exceptions capture specific error conditions during order response parsing
and store contextual data as attributes for debugging.
"""

from typing import Any, Dict, List

from src.common.exceptions import APIError


class EmptyOrderDataError(APIError):
    """Empty order data received from Kalshi API."""

    pass


class MissingOrderFieldsError(ValueError):
    """Missing required fields in Kalshi order response."""

    def __init__(self, missing: List[str], available: List[str]) -> None:
        super().__init__("Missing required fields in Kalshi order response")
        self.missing = missing
        self.available = available


class InvalidOrderStatusError(ValueError):
    """Invalid order status from Kalshi API."""

    def __init__(self, status: str, valid: List[str]) -> None:
        super().__init__("Invalid order status from Kalshi API")
        self.status = status
        self.valid = valid


class MissingFillCountError(ValueError):
    """Missing required field 'fill_count' in order response."""

    def __init__(self, available: List[str]) -> None:
        super().__init__("Missing required field 'fill_count' in order response")
        self.available = available


class InvalidFillCountError(ValueError):
    """Invalid fill_count value in order response."""

    def __init__(self, value: Any) -> None:
        super().__init__("Invalid fill_count value in order response")
        self.value = value


class InvalidOrderCountError(ValueError):
    """Invalid count field value in order response."""

    def __init__(self, field: str, value: Any) -> None:
        super().__init__("Invalid count field value in order response")
        self.field = field
        self.value = value


class MissingCreatedTimeError(ValueError):
    """Missing required field 'created_time' in order response."""

    def __init__(self, available: List[str]) -> None:
        super().__init__("Missing required field 'created_time' in order response")
        self.available = available


class InvalidCreatedTimeError(ValueError):
    """Invalid timestamp format in 'created_time'."""

    def __init__(self, value: Any) -> None:
        super().__init__("Invalid timestamp format in 'created_time'")
        self.value = value


class MissingRejectionReasonError(ValueError):
    """Rejected order response missing 'rejection_reason' field."""

    def __init__(self, available: List[str]) -> None:
        super().__init__("Rejected order response missing 'rejection_reason' field")
        self.available = available


class EmptyRejectionReasonError(APIError):
    """Rejected order response must include a non-empty 'rejection_reason'."""

    pass


class MissingFillFieldError(ValueError):
    """Fill missing required field."""

    def __init__(self, field: str, fill_data: Dict[str, Any]) -> None:
        super().__init__("Fill missing required field")
        self.field = field
        self.fill_data = fill_data


class InvalidFillFieldError(ValueError):
    """Invalid fill field value."""

    def __init__(self, field: str, value: Any) -> None:
        super().__init__("Invalid fill field value")
        self.field = field
        self.value = value


class FillCountMismatchError(ValueError):
    """Fills count mismatch - sum of fills doesn't match filled_count."""

    def __init__(self, total: int, expected: int) -> None:
        super().__init__("Fills count mismatch")
        self.total = total
        self.expected = expected


class EmptyOrderIdError(ValueError):
    """Order ID cannot be empty."""

    pass


class EmptyClientOrderIdError(ValueError):
    """Client order ID cannot be empty."""

    pass


class MissingTickerError(APIError):
    """Order response missing ticker value."""

    pass


class InvalidOrderEnumError(APIError):
    """Invalid order enum field in response."""

    def __init__(self, field: str, value: Any) -> None:
        super().__init__("Invalid order enum field in response")
        self.field = field
        self.value = value


class EmptyResponseError(APIError):
    """Empty response received from Kalshi API."""

    pass


class MissingOrderWrapperError(ValueError):
    """Invalid response structure - missing 'order' wrapper."""

    def __init__(self, keys: List[str]) -> None:
        super().__init__("Invalid response structure - missing 'order' wrapper")
        self.keys = keys


class InvalidOrderDataTypeError(ValueError):
    """Invalid order data type - expected dict."""

    def __init__(self, actual: type) -> None:
        super().__init__("Invalid order data type - expected dict")
        self.actual = actual


class InvalidMakerFeesError(ValueError):
    """Invalid maker_fees value in order response."""

    def __init__(self, value: Any) -> None:
        super().__init__("Invalid maker_fees value in order response")
        self.value = value
