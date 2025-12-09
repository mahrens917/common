"""
Price data collection from Redis.

Fetches BTC and ETH prices from DeribitStore.
"""

import asyncio
from typing import Dict, Optional


class PriceDataCollector:
    """Collects cryptocurrency price data."""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client

    async def collect_price_data(self) -> Dict[str, Optional[float]]:
        """Collect BTC and ETH prices."""
        from src.common.redis_protocol.market_store import DeribitStore

        market_store = DeribitStore(self.redis_client)
        btc_task = market_store.get_usdc_micro_price("BTC")
        eth_task = market_store.get_usdc_micro_price("ETH")
        btc_price, eth_price = await asyncio.gather(btc_task, eth_task, return_exceptions=True)

        if isinstance(btc_price, BaseException):
            btc_price = None
        if isinstance(eth_price, BaseException):
            eth_price = None

        return {"btc_price": btc_price, "eth_price": eth_price}
