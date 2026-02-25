"""Fail-fast Kalshi REST client with trading helpers - slim coordinator."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from common.config.shared import get_kalshi_credentials
from common.data_models.trading import BatchOrderResult, OrderRequest, PortfolioBalance

from .client_bindings import bind_client_methods
from .client_helpers import (
    ComponentInitializer,
    CredentialValidator,
    FillsOperations,
    KeyLoader,
    MarketStatusOperations,
    SeriesOperations,
)
from .client_helpers.errors import KalshiClientError

__all__ = ["KalshiClient", "KalshiClientError", "KalshiConfig"]

DEFAULT_KALSHI_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_KALSHI_CONNECT_TIMEOUT_SECONDS = 10
DEFAULT_KALSHI_SOCK_READ_TIMEOUT_SECONDS = 20
DEFAULT_KALSHI_NETWORK_MAX_RETRIES = 3
DEFAULT_KALSHI_BACKOFF_BASE_SECONDS = 1.0
DEFAULT_KALSHI_BACKOFF_MAX_SECONDS = 30.0

if TYPE_CHECKING:
    from common.redis_protocol.trade_store import TradeStore


@dataclass(frozen=True)
class KalshiConfig:
    """Configuration for Kalshi API client."""

    base_url: str = "https://api.elections.kalshi.com"
    request_timeout_seconds: int = DEFAULT_KALSHI_REQUEST_TIMEOUT_SECONDS
    connect_timeout_seconds: int = DEFAULT_KALSHI_CONNECT_TIMEOUT_SECONDS
    sock_read_timeout_seconds: int = DEFAULT_KALSHI_SOCK_READ_TIMEOUT_SECONDS
    network_max_retries: int = DEFAULT_KALSHI_NETWORK_MAX_RETRIES
    network_backoff_base_seconds: float = DEFAULT_KALSHI_BACKOFF_BASE_SECONDS
    network_backoff_max_seconds: float = DEFAULT_KALSHI_BACKOFF_MAX_SECONDS


def _session(self):
    if "_session_manager" not in self.__dict__:
        raise RuntimeError("KalshiClient is not initialized")
    manager = getattr(self, "_session_manager", None)
    if manager is None:
        raise RuntimeError("KalshiClient is not initialized")

    cached_session = self.__dict__.get("_cached_session")
    if cached_session is not None:
        return cached_session

    session_obj = manager.session
    self.__dict__["_cached_session"] = session_obj
    return session_obj


def _session_setter(self, value) -> None:
    if "_session_manager" not in self.__dict__:
        self.__dict__["_cached_session"] = value
        return
    manager = getattr(self, "_session_manager", None)
    if manager is None:
        raise RuntimeError("KalshiClient is not initialized")
    manager.set_session(value)
    self.__dict__["_cached_session"] = value


class KalshiClient:
    """Authenticated client for the Kalshi trading API - slim coordinator."""

    _config: KalshiConfig
    _access_key: str
    _private_key: Any
    _logger: logging.Logger
    _session_manager: Any
    _auth_helper: Any
    _request_builder: Any
    _response_parser: Any
    _portfolio_ops: Any
    _order_ops: Any
    _series_ops: SeriesOperations
    _fills_ops: FillsOperations
    _market_status_ops: MarketStatusOperations
    _trade_store: Optional["TradeStore"]
    _initialized: bool

    def __init__(
        self,
        config: KalshiConfig | None = None,
        *,
        trade_store: Optional["TradeStore"] = None,
    ) -> None:
        self._config = config if config else KalshiConfig()
        credentials = get_kalshi_credentials(require_secret=False)
        self._access_key = credentials.key_id
        private_key_b64 = CredentialValidator.extract_and_validate(credentials)
        private_key = KeyLoader.load_private_key(private_key_b64)
        self._private_key = private_key
        self._logger = logging.getLogger(__name__)

        initializer = ComponentInitializer(self._config)
        components = initializer.initialize(credentials.key_id, private_key)

        self.__dict__.update(
            {
                "_session_manager": components["session_manager"],
                "_auth_helper": components["auth_helper"],
                "_request_builder": components["request_builder"],
                "_response_parser": components["response_parser"],
                "_portfolio_ops": components["portfolio_ops"],
                "_order_ops": components["order_ops"],
                "_series_ops": SeriesOperations(self),
                "_fills_ops": FillsOperations(self),
                "_market_status_ops": MarketStatusOperations(self),
            }
        )
        self._trade_store: Optional["TradeStore"] = None
        self._initialized = False
        self.__dict__["_cached_session"] = None
        self.__dict__["_cached_session_lock"] = components["session_manager"].session_lock

        if trade_store is not None:
            self.attach_trade_store(trade_store)

    async def initialize(self) -> None:
        """Initialize the client's HTTP session."""
        raise NotImplementedError

    async def close(self) -> None:
        """Close the client's HTTP session."""
        raise NotImplementedError

    async def api_request(
        self,
        *,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        operation_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute a raw API request."""
        raise NotImplementedError

    async def get_fills(self, order_id: str) -> list[dict[str, Any]]:
        """Get fills for an order."""
        raise NotImplementedError

    async def batch_create_orders(self, order_requests: list[OrderRequest]) -> list[BatchOrderResult]:
        """Submit a batch of orders in a single API call."""
        raise NotImplementedError

    async def get_exchange_status(self) -> dict[str, bool]:
        """Get exchange status."""
        raise NotImplementedError

    async def get_portfolio_balance(self) -> PortfolioBalance:
        """Get current portfolio balance."""
        raise NotImplementedError

    def attach_trade_store(self, trade_store: Optional[Any]) -> None:
        """Attach a trade store to the client."""
        raise NotImplementedError

    # Methods are dynamically attached below to keep this coordinator lean.

    # Property accessors are attached dynamically below to keep the class concise.


bind_client_methods(KalshiClient, _session, _session_setter)
