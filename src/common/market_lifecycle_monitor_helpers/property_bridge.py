"""Property bridge for MarketLifecycleMonitor component access."""

import logging
from typing import TYPE_CHECKING, Callable, Dict, Optional

if TYPE_CHECKING:
    from .market_registrar import MarketRegistrar
    from .market_scanner import MarketScanner
    from .settlement_fetcher import SettlementFetcher
    from .state_tracker import MarketInfo, SettlementInfo, StateTracker

logger = logging.getLogger(__name__)


class PropertyBridge:
    def __init__(
        self,
        state_tracker: "StateTracker",
        scanner: "MarketScanner",
        settlement_fetcher: "SettlementFetcher",
        registrar: "MarketRegistrar",
    ):
        self._state_tracker = state_tracker
        self._scanner = scanner
        self._settlement_fetcher = settlement_fetcher
        self._registrar = registrar

    @property
    def monitored_markets(self) -> Dict[str, "MarketInfo"]:
        return self._state_tracker.monitored_markets

    @monitored_markets.setter
    def monitored_markets(self, markets: Dict[str, "MarketInfo"]) -> None:
        self._state_tracker.monitored_markets = markets

    @property
    def settlement_cache(self) -> Dict[str, "SettlementInfo"]:
        return self._state_tracker.settlement_cache

    @settlement_cache.setter
    def settlement_cache(self, cache: Dict[str, "SettlementInfo"]) -> None:
        self._state_tracker.settlement_cache = cache

    @property
    def fetch_market_data(self) -> Optional[Callable]:
        return getattr(self._scanner, "fetch_market_data", None)

    @fetch_market_data.setter
    def fetch_market_data(self, fetcher: Callable) -> None:
        self._scanner.fetch_market_data = fetcher

    @property
    def fetch_settlement_info(self) -> Optional[Callable]:
        return getattr(self._settlement_fetcher, "fetch_settlement_info", None)

    @fetch_settlement_info.setter
    def fetch_settlement_info(self, fetcher: Callable) -> None:
        self._settlement_fetcher.fetch_settlement_info = fetcher
