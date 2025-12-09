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
    """
    Bridge class to provide property access to underlying components.

    This class exposes properties from various lifecycle monitor components
    through a unified interface.
    """

    def __init__(
        self,
        state_tracker: "StateTracker",
        scanner: "MarketScanner",
        settlement_fetcher: "SettlementFetcher",
        registrar: "MarketRegistrar",
    ):
        """
        Initialize property bridge.

        Args:
            state_tracker: State tracker instance
            scanner: Market scanner instance
            settlement_fetcher: Settlement fetcher instance
            registrar: Market registrar instance
        """
        self._state_tracker = state_tracker
        self._scanner = scanner
        self._settlement_fetcher = settlement_fetcher
        self._registrar = registrar

    @property
    def monitored_markets(self) -> Dict[str, "MarketInfo"]:
        """
        Get tracked markets from state tracker.

        Returns:
            Dictionary mapping market tickers to MarketInfo objects
        """
        return self._state_tracker.monitored_markets

    @monitored_markets.setter
    def monitored_markets(self, markets: Dict[str, "MarketInfo"]) -> None:
        """
        Set tracked markets on state tracker.

        Args:
            markets: Dictionary mapping market tickers to MarketInfo objects
        """
        self._state_tracker.monitored_markets = markets

    @property
    def settlement_cache(self) -> Dict[str, "SettlementInfo"]:
        """
        Get settlement cache from settlement fetcher.

        Returns:
            Dictionary mapping market tickers to SettlementInfo objects
        """
        return self._state_tracker.settlement_cache

    @settlement_cache.setter
    def settlement_cache(self, cache: Dict[str, "SettlementInfo"]) -> None:
        """
        Set settlement cache on settlement fetcher.

        Args:
            cache: Dictionary mapping market tickers to SettlementInfo objects
        """
        self._state_tracker.settlement_cache = cache

    @property
    def fetch_market_data(self) -> Optional[Callable]:
        """
        Get market data fetch function from scanner.

        Returns:
            Callable for fetching market data or None
        """
        return getattr(self._scanner, "fetch_market_data", None)

    @fetch_market_data.setter
    def fetch_market_data(self, fetcher: Callable) -> None:
        """
        Set market data fetch function on scanner.

        Args:
            fetcher: Callable for fetching market data
        """
        self._scanner.fetch_market_data = fetcher

    @property
    def fetch_settlement_info(self) -> Optional[Callable]:
        """
        Get settlement info fetch function from settlement fetcher.

        Returns:
            Callable for fetching settlement info or None
        """
        return getattr(self._settlement_fetcher, "fetch_settlement_info", None)

    @fetch_settlement_info.setter
    def fetch_settlement_info(self, fetcher: Callable) -> None:
        """
        Set settlement info fetch function on settlement fetcher.

        Args:
            fetcher: Callable for fetching settlement info
        """
        self._settlement_fetcher.fetch_settlement_info = fetcher
