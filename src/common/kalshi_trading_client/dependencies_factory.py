"""Dependency factory for KalshiTradingClient."""

from dataclasses import dataclass
from typing import Any, Optional

from src.kalshi.api.client import KalshiClient

from ..redis_protocol.trade_store import TradeStore
from ..trading import TradeStoreManager, WeatherStationResolver
from ..trading.notifier_adapter import TradeNotifierAdapter


@dataclass
class KalshiTradingClientDependencies:
    """Dependencies for KalshiTradingClient."""

    kalshi_client: KalshiClient
    backoff_manager: Any
    trade_store: TradeStore
    trade_store_manager: Optional[TradeStoreManager]
    telegram_handler: Any
    notifier: Optional[TradeNotifierAdapter]
    weather_station_resolver: Optional[WeatherStationResolver]


@dataclass(frozen=True)
class DependencyCreationConfig:
    """Configuration for creating or using dependencies."""

    kalshi_client: Optional[KalshiClient] = None
    backoff_manager: Any = None
    network_health_monitor: Any = None
    trade_store: Optional[TradeStore] = None
    telegram_handler: Any = None
    weather_station_resolver: Optional[WeatherStationResolver] = None
    trade_store_manager: Optional[TradeStoreManager] = None
    notifier: Optional[TradeNotifierAdapter] = None


class KalshiTradingClientDependenciesFactory:
    """Factory for creating KalshiTradingClient dependencies."""

    @staticmethod
    def create(
        kalshi_client: Optional[KalshiClient] = None,
        backoff_manager=None,
        network_health_monitor=None,
        trade_store: Optional[TradeStore] = None,
        telegram_handler=None,
        weather_station_resolver: Optional[WeatherStationResolver] = None,
    ) -> KalshiTradingClientDependencies:
        """
        Create all dependencies for KalshiTradingClient.

        Args:
            kalshi_client: Optional Kalshi API client
            backoff_manager: Optional backoff manager
            network_health_monitor: Optional network health monitor
            trade_store: Optional trade store instance (required)
            telegram_handler: Optional telegram handler
            weather_station_resolver: Optional weather station resolver

        Returns:
            KalshiTradingClientDependencies instance

        Raises:
            ValueError: If trade_store is None
        """
        from .client_helpers import ClientInitializer

        if trade_store is None:
            raise ValueError("KalshiTradingClient requires a trade store instance")

        initialized_kalshi_client = ClientInitializer.initialize_kalshi_client(
            kalshi_client, trade_store
        )
        initialized_backoff_manager = ClientInitializer.initialize_backoff_manager(
            backoff_manager, network_health_monitor
        )
        trade_store_manager = TradeStoreManager(
            kalshi_client=initialized_kalshi_client, store_supplier=lambda: trade_store
        )
        notifier = TradeNotifierAdapter()
        initialized_weather_station_resolver = ClientInitializer.initialize_weather_resolver(
            weather_station_resolver
        )

        return KalshiTradingClientDependencies(
            kalshi_client=initialized_kalshi_client,
            backoff_manager=initialized_backoff_manager,
            trade_store=trade_store,
            trade_store_manager=trade_store_manager,
            telegram_handler=telegram_handler,
            notifier=notifier,
            weather_station_resolver=initialized_weather_station_resolver,
        )

    @staticmethod
    def create_or_use(config: DependencyCreationConfig) -> KalshiTradingClientDependencies:
        """Create dependencies only if not all are provided."""
        if all([config.trade_store_manager, config.notifier, config.weather_station_resolver]):
            from .client_helpers import ClientInitializer

            if config.trade_store is None:
                raise ValueError("KalshiTradingClient requires a trade store instance")

            initialized_kalshi_client = ClientInitializer.initialize_kalshi_client(
                config.kalshi_client, config.trade_store
            )
            initialized_backoff_manager = ClientInitializer.initialize_backoff_manager(
                config.backoff_manager, config.network_health_monitor
            )

            return KalshiTradingClientDependencies(
                kalshi_client=initialized_kalshi_client,
                backoff_manager=initialized_backoff_manager,
                trade_store=config.trade_store,
                trade_store_manager=config.trade_store_manager,
                telegram_handler=config.telegram_handler,
                notifier=config.notifier,
                weather_station_resolver=config.weather_station_resolver,
            )

        return KalshiTradingClientDependenciesFactory.create(
            config.kalshi_client,
            config.backoff_manager,
            config.network_health_monitor,
            config.trade_store,
            config.telegram_handler,
            config.weather_station_resolver,
        )
