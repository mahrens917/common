import logging
from typing import Any, Dict, List, Optional, Tuple

from .data_models.trading import PortfolioPosition
from .emergency_position_manager import EmergencyPositionManager
from .kalshi_trading_client import KalshiTradingClient
from .market_lifecycle_monitor_helpers import expiry_checker as _expiry_module
from .market_lifecycle_monitor_helpers.dependencies_factory import (
    MarketLifecycleMonitorDependencies,
    MarketLifecycleMonitorDependenciesFactory,
)
from .market_lifecycle_monitor_helpers.property_bridge import PropertyBridge
from .market_lifecycle_monitor_helpers.state_tracker import MarketInfo, SettlementInfo
from .time_utils import get_current_utc

logger = logging.getLogger(__name__)


class MarketLifecycleMonitor:
    def __init__(
        self,
        trading_client: KalshiTradingClient,
        emergency_manager: Optional[EmergencyPositionManager] = None,
        closure_warning_hours: float = 2.0,
        *,
        dependencies: Optional[MarketLifecycleMonitorDependencies] = None,
    ):
        deps = dependencies or MarketLifecycleMonitorDependenciesFactory.create(
            trading_client, emergency_manager, closure_warning_hours
        )
        self.scanner = deps.scanner
        self.expiry_checker = deps.expiry_checker
        self.state_tracker = deps.state_tracker
        self.registrar = deps.registrar
        self.settlement_checker = deps.settlement_checker
        self.settlement_validator = deps.settlement_validator
        self.close_detector = deps.close_detector
        self.settlement_fetcher = deps.settlement_fetcher
        self.notifier = deps.notifier
        self.orchestrator = deps.orchestrator
        self.trading_client = trading_client
        self.emergency_manager = emergency_manager
        self._closure_warning_hours = closure_warning_hours
        self._property_bridge = PropertyBridge(
            self.state_tracker, self.scanner, self.settlement_fetcher, self.registrar
        )
        _expiry_module.get_current_utc = lambda: get_current_utc()
        logger.info(
            f"[MarketLifecycleMonitor] Initialized with {closure_warning_hours}h closure warning"
        )

    @property
    def monitored_markets(self) -> Dict[str, MarketInfo]:
        return self._property_bridge.monitored_markets

    @monitored_markets.setter
    def monitored_markets(self, markets: Dict[str, MarketInfo]) -> None:
        self._property_bridge.monitored_markets = markets

    @property
    def settlement_cache(self) -> Dict[str, SettlementInfo]:
        return self._property_bridge.settlement_cache

    @settlement_cache.setter
    def settlement_cache(self, cache: Dict[str, SettlementInfo]) -> None:
        self._property_bridge.settlement_cache = cache

    @property
    def _fetch_market_data(self):
        return self._property_bridge.fetch_market_data

    @_fetch_market_data.setter
    def _fetch_market_data(self, fetcher):
        self._property_bridge.fetch_market_data = fetcher

    @property
    def _fetch_settlement_info(self):
        return self._property_bridge.fetch_settlement_info

    @_fetch_settlement_info.setter
    def _fetch_settlement_info(self, fetcher):
        self._property_bridge.fetch_settlement_info = fetcher

    def _parse_market_info(self, market_data: Dict[str, Any]) -> MarketInfo:
        return self.state_tracker.parse_market_info(market_data)

    async def register_market(self, ticker: str) -> Optional[MarketInfo]:
        return await self.registrar.register_market(ticker)

    async def update_market_states(self) -> Dict[str, MarketInfo]:
        return await self.orchestrator.market_updater.update_all_markets()

    async def check_closure_warnings(self) -> List[MarketInfo]:
        return self.orchestrator.get_closing_soon_markets()

    async def handle_market_closure(self, ticker: str) -> Tuple[bool, str]:
        return await self.close_detector.handle_market_closure(ticker)

    async def check_settlements(self) -> Dict[str, SettlementInfo]:
        return await self.settlement_checker.check_settlements()

    async def validate_settlement_pnl(
        self, ticker: str, position_before_settlement: PortfolioPosition
    ) -> Tuple[bool, str, Optional[int]]:
        return await self.settlement_validator.validate_settlement_pnl(
            ticker, position_before_settlement
        )

    async def monitor_lifecycle_events(self) -> Dict[str, Any]:
        return await self.orchestrator.monitor_lifecycle_events()
