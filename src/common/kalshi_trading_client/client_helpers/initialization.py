from __future__ import annotations

"""Client initialization and configuration loading."""


import importlib
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from src.kalshi.api.client import KalshiClient

from common.backoff_manager import BackoffManager
from common.trading import WeatherStationResolver
from common.trading.notifier_adapter import TradeNotifierAdapter

from ..services import OrderService, PortfolioService, TradeCollectionController
from ..services.order_helpers.dependencies_factory import OrderServiceDependenciesFactory

if TYPE_CHECKING:
    from common.redis_protocol.trade_store import TradeStore

logger = logging.getLogger(__name__)


class ClientInitializer:
    """Handles client initialization and dependency setup."""

    @staticmethod
    def initialize_kalshi_client(
        kalshi_client: Optional[KalshiClient], trade_store: TradeStore
    ) -> KalshiClient:
        """Initialize or create KalshiClient with trade store attachment."""
        if kalshi_client is not None:
            attach = getattr(kalshi_client, "attach_trade_store", None)
            if callable(attach):
                attach(trade_store)
            return kalshi_client
        return KalshiClient(trade_store=trade_store)

    @staticmethod
    def initialize_backoff_manager(
        backoff_manager: Optional[BackoffManager], network_health_monitor
    ) -> BackoffManager:
        """Initialize or create BackoffManager."""
        return backoff_manager or BackoffManager(network_health_monitor)

    @staticmethod
    def initialize_weather_resolver(
        resolver: Optional[WeatherStationResolver],
    ) -> WeatherStationResolver:
        """Initialize or create WeatherStationResolver."""
        return resolver or WeatherStationResolver()

    @staticmethod
    def load_config() -> Dict[str, Dict]:
        """Load PnL configuration from common module."""
        module = importlib.import_module("common.kalshi_trading_client")
        loader = getattr(module, "load_pnl_config")
        return loader()

    @staticmethod
    def extract_config_values(config: Dict[str, Dict]) -> Dict[str, Any]:
        """Extract configuration values into a dictionary."""
        return {
            "batch_size": config["trade_collection"]["batch_size"],
            "collection_interval": config["trade_collection"]["collection_interval_seconds"],
            "max_retries": config["trade_collection"]["max_retries"],
            "retry_delay": config["trade_collection"]["retry_delay_seconds"],
            "ticker_pattern": config["market_filters"]["ticker_pattern"],
            "supported_rules": config["market_filters"]["supported_rules"],
            "supported_categories": config["market_filters"].get(
                "supported_categories", ["weather"]
            ),
        }

    @staticmethod
    def create_services(
        kalshi_client: KalshiClient,
        trade_store_getter,
        notifier: TradeNotifierAdapter,
        weather_resolver: WeatherStationResolver,
        order_poller_factory,
        trade_finalizer_factory,
        telegram_handler,
    ) -> tuple[PortfolioService, OrderService, TradeCollectionController]:
        """Create and configure service instances."""
        portfolio = PortfolioService(kalshi_client=kalshi_client)
        order_service_deps = OrderServiceDependenciesFactory.create(
            kalshi_client,
            trade_store_getter,
            notifier,
            weather_resolver,
            order_poller_factory,
            trade_finalizer_factory,
            telegram_handler,
        )
        orders = OrderService(dependencies=order_service_deps)
        trade_collection = TradeCollectionController(
            trade_store_getter=trade_store_getter,
            logger=logger,
        )
        return portfolio, orders, trade_collection
