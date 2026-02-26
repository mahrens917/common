"""
Kalshi subscription tracking for WebSocket connections

This module provides subscription management functionality for Kalshi WebSocket services,
tracking subscribed markets, subscription IDs, and service status.
"""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Set, TypeVar

from .connection import RedisConnectionManager
from .subscription_helpers import (
    ConnectionManager,
    KeyProvider,
    MarketSubscriptionManager,
    ServiceStatusManager,
    SubscriptionIdManager,
)

_DEFAULT_SERVICE_PREFIX = "ws"

T = TypeVar("T")


def _normalize_subscription_mapping(
    subscriptions: Dict[str, Any] | Sequence[Any],
    market_tickers: Optional[Sequence[str]],
) -> Dict[str, Any]:
    if isinstance(subscriptions, dict) and market_tickers is None:
        return dict(subscriptions)
    if market_tickers is None:
        raise ValueError("market_tickers must be provided when subscription_ids is a sequence")
    mapping: Dict[str, Any] = {}
    for ticker, sub_id in zip(market_tickers, subscriptions):
        mapping[str(ticker)] = sub_id
    return mapping


def _resolve_market_list(
    positional: Optional[Sequence[str]],
    keyword: Optional[Sequence[str]],
) -> Sequence[str]:
    if keyword is not None:
        return keyword
    if positional is None:
        _none_guard_value = ()
        return _none_guard_value
    return positional


class SubscriptionConnectionMixin:
    """Encapsulates connection-aware action execution."""

    _connection_manager: ConnectionManager

    async def _execute_with_connection(
        self,
        action: str,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        await self._connection_manager.ensure_connection_or_raise(action)
        return await func(*args, **kwargs)


class MarketSubscriptionMixin:
    _market_subscription_manager: MarketSubscriptionManager
    _execute_with_connection: Callable[..., Awaitable[Any]]

    async def get_subscribed_markets(self) -> Set[str]:
        return await self._execute_with_connection(
            "get_subscribed_markets",
            self._market_subscription_manager.get_subscribed_markets,
        )

    async def add_subscribed_market(self, market_ticker: str, *, category: Optional[str] = None) -> bool:
        return await self._execute_with_connection(
            f"add_subscribed_market {market_ticker}",
            self._market_subscription_manager.add_subscribed_market,
            market_ticker,
            category=category,
        )

    async def bulk_add_subscribed_markets(self, market_tickers: List[str]) -> int:
        return await self._execute_with_connection(
            "bulk_add_subscribed_markets",
            self._market_subscription_manager.bulk_add_subscribed_markets,
            market_tickers,
        )

    async def remove_subscribed_market(self, market_ticker: str, *, category: Optional[str] = None) -> bool:
        return await self._execute_with_connection(
            f"remove_subscribed_market {market_ticker}",
            self._market_subscription_manager.remove_subscribed_market,
            market_ticker,
            category=category,
        )


class SubscriptionIdMixin:
    _subscription_id_manager: SubscriptionIdManager
    _execute_with_connection: Callable[..., Awaitable[Any]]

    async def record_subscription_ids(
        self,
        subscriptions: Dict[str, Any] | Sequence[Any],
        market_tickers: Optional[Sequence[str]] = None,
    ) -> None:
        normalized = _normalize_subscription_mapping(subscriptions, market_tickers)
        await self._execute_with_connection(
            "record_subscription_ids",
            self._subscription_id_manager.record_subscription_ids,
            normalized,
        )

    async def fetch_subscription_ids(
        self,
        markets: Optional[Sequence[str]] = None,
        *,
        market_tickers: Optional[Sequence[str]] = None,
    ) -> Dict[str, str]:
        target_markets = _resolve_market_list(markets, market_tickers)
        return await self._execute_with_connection(
            "fetch_subscription_ids",
            self._subscription_id_manager.fetch_subscription_ids,
            target_markets,
        )

    async def clear_subscription_ids(
        self,
        markets: Optional[Sequence[str]] = None,
        *,
        market_tickers: Optional[Sequence[str]] = None,
    ) -> None:
        target_markets = _resolve_market_list(markets, market_tickers)
        await self._execute_with_connection(
            "clear_subscription_ids",
            self._subscription_id_manager.clear_subscription_ids,
            target_markets,
        )


class ServiceStatusMixin:
    _service_status_manager: ServiceStatusManager
    _execute_with_connection: Callable[..., Awaitable[Any]]

    async def update_service_status(self, service: str, status: Dict[str, Any]) -> bool:
        return await self._execute_with_connection(
            f"update_service_status {service}",
            self._service_status_manager.update_service_status,
            service,
            status,
        )

    async def get_service_status(self, service: str) -> Optional[str]:
        return await self._execute_with_connection(
            f"get_service_status {service}",
            self._service_status_manager.get_service_status,
            service,
        )


class KalshiSubscriptionTracker(SubscriptionConnectionMixin, MarketSubscriptionMixin, SubscriptionIdMixin, ServiceStatusMixin):
    """Manages WebSocket subscription state for Kalshi markets."""

    SUBSCRIPTIONS_KEY: Optional[str] = None

    def __init__(
        self,
        redis_connection: RedisConnectionManager,
        logger_instance: logging.Logger,
        service_prefix: Optional[str] = None,
    ) -> None:
        if service_prefix is not None and service_prefix not in ("rest", "ws"):
            raise TypeError("service_prefix must be 'rest' or 'ws' when provided")
        self._initialize_tracker_components(redis_connection, logger_instance, service_prefix)

    def _initialize_tracker_components(
        self,
        redis_connection: RedisConnectionManager,
        logger_instance: logging.Logger,
        service_prefix: Optional[str],
    ) -> None:
        self.logger = logger_instance
        self.service_prefix = service_prefix
        self._connection_manager = ConnectionManager(redis_connection, logger_instance)
        resolved_prefix = _DEFAULT_SERVICE_PREFIX if not service_prefix else service_prefix
        self._key_provider = KeyProvider(resolved_prefix)
        self.SUBSCRIPTIONS_KEY = self._key_provider.subscriptions_key
        self._market_subscription_manager = MarketSubscriptionManager(
            self._connection_manager.get_redis,
            self._key_provider.subscriptions_key,
            resolved_prefix,
        )
        self._subscription_id_manager = SubscriptionIdManager(
            self._connection_manager.get_redis,
            self._key_provider.subscription_ids_key,
            resolved_prefix,
        )
        self._service_status_manager = ServiceStatusManager(
            self._connection_manager.get_redis,
            self._key_provider.service_status_key,
        )
