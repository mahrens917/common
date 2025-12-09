"""
Market Lifecycle Monitor for Kalshi Live Trading Tests

This module provides market closure detection, settlement scenario validation,
and market state monitoring for live trading tests. Ensures positions are
properly managed through market lifecycle events.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .data_models.trading import PortfolioPosition
from .emergency_position_manager import EmergencyPositionManager
from .kalshi_trading_client import KalshiTradingClient
from .market_lifecycle_monitor_helpers import expiry_checker as _expiry_module
from .market_lifecycle_monitor_helpers.dependencies_factory import (
    MarketLifecycleMonitorDependenciesFactory,  # gitleaks:allow
)
from .market_lifecycle_monitor_helpers.dependencies_factory import (
    MarketLifecycleMonitorDependencies,
)
from .market_lifecycle_monitor_helpers.property_bridge import PropertyBridge
from .market_lifecycle_monitor_helpers.state_tracker import (
    MarketInfo,
    SettlementInfo,
)
from .time_utils import get_current_utc

logger = logging.getLogger(__name__)


class MarketLifecycleMonitor:
    """Monitor market lifecycle events and manage positions accordingly."""

    def __init__(
        self,
        trading_client: KalshiTradingClient,
        emergency_manager: Optional[EmergencyPositionManager] = None,
        closure_warning_hours: float = 2.0,
        *,
        dependencies: Optional[MarketLifecycleMonitorDependencies] = None,
    ):
        """Initialize market lifecycle monitor."""
        deps = dependencies or MarketLifecycleMonitorDependenciesFactory.create(  # gitleaks:allow
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

        # Property bridge for state access
        self._property_bridge = PropertyBridge(
            self.state_tracker, self.scanner, self.settlement_fetcher, self.registrar
        )

        # Ensure expiry helpers respect patched get_current_utc from this module
        _expiry_module.get_current_utc = lambda: get_current_utc()

        logger.info(
            f"[MarketLifecycleMonitor] Initialized with {closure_warning_hours}h closure warning"
        )

    @property
    def monitored_markets(self) -> Dict[str, MarketInfo]:
        """Get tracked markets."""
        return self._property_bridge.monitored_markets

    @monitored_markets.setter
    def monitored_markets(self, markets: Dict[str, MarketInfo]) -> None:
        """Allow tests to replace the monitored markets mapping."""
        self._property_bridge.monitored_markets = markets

    @property
    def settlement_cache(self) -> Dict[str, SettlementInfo]:
        """Get settlement cache."""
        return self._property_bridge.settlement_cache

    @settlement_cache.setter
    def settlement_cache(self, cache: Dict[str, SettlementInfo]) -> None:
        """Allow tests to replace the cached settlements mapping."""
        self._property_bridge.settlement_cache = cache

    @property
    def _fetch_market_data(self):
        """Access the underlying market fetcher for monkeypatching."""
        return self._property_bridge.fetch_market_data

    @_fetch_market_data.setter
    def _fetch_market_data(self, fetcher):
        self._property_bridge.fetch_market_data = fetcher

    @property
    def _fetch_settlement_info(self):
        """Access the settlement fetcher for monkeypatching."""
        return self._property_bridge.fetch_settlement_info

    @_fetch_settlement_info.setter
    def _fetch_settlement_info(self, fetcher):
        self._property_bridge.fetch_settlement_info = fetcher

    def _parse_market_info(self, market_data: Dict[str, Any]) -> MarketInfo:
        """Parse raw market data into MarketInfo."""
        return self.state_tracker.parse_market_info(market_data)

    async def register_market(self, ticker: str) -> Optional[MarketInfo]:
        """Register a market for lifecycle monitoring."""
        return await self.registrar.register_market(ticker)

    async def update_market_states(self) -> Dict[str, MarketInfo]:
        """Update states for all monitored markets."""
        return await self.orchestrator.market_updater.update_all_markets()

    async def check_closure_warnings(self) -> List[MarketInfo]:
        """Check for markets approaching closure."""
        return self.orchestrator.get_closing_soon_markets()

    async def handle_market_closure(self, ticker: str) -> Tuple[bool, str]:
        """Handle market closure by closing any open positions."""
        return await self.close_detector.handle_market_closure(ticker)

    async def check_settlements(self) -> Dict[str, SettlementInfo]:
        """Check for market settlements and calculate final P&L."""
        return await self.settlement_checker.check_settlements()

    async def validate_settlement_pnl(
        self, ticker: str, position_before_settlement: PortfolioPosition
    ) -> Tuple[bool, str, Optional[int]]:
        """Validate P&L calculation after market settlement."""
        return await self.settlement_validator.validate_settlement_pnl(
            ticker, position_before_settlement
        )

    async def monitor_lifecycle_events(self) -> Dict[str, Any]:
        """Monitor all lifecycle events for registered markets."""
        return await self.orchestrator.monitor_lifecycle_events()
