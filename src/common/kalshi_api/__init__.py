"""Kalshi API client library.

This module provides the canonical Kalshi API client implementation.
Import KalshiClient and KalshiConfig from here for API access.

Internal modules:
- authentication: Request signing with RSA-PSS
- client_helpers: Component initialization and operations
- order_operations: Order CRUD operations
- portfolio_operations: Portfolio queries
- request_builder: HTTP request construction
- request_executor: Retry logic and error handling
- response_parser: API response parsing
- session_manager: HTTP session lifecycle
"""

from .client import KalshiClient, KalshiConfig
from .client_helpers.errors import KalshiClientError

__all__ = [
    "KalshiClient",
    "KalshiClientError",
    "KalshiConfig",
]


# For internal use - lazy import of helpers
def __getattr__(name):
    """Lazy import internal helpers to avoid circular imports."""
    if name == "AuthenticationHelper":
        from .authentication import AuthenticationHelper

        return AuthenticationHelper
    if name == "OrderOperations":
        from .order_operations import OrderOperations

        return OrderOperations
    if name == "PortfolioOperations":
        from .portfolio_operations import PortfolioOperations

        return PortfolioOperations
    if name == "RequestBuilder":
        from .request_builder import RequestBuilder

        return RequestBuilder
    if name == "ResponseParser":
        from .response_parser import ResponseParser

        return ResponseParser
    if name == "SessionManager":
        from .session_manager import SessionManager

        return SessionManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
