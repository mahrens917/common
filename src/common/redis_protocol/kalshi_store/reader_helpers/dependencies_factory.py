from __future__ import annotations

"""Dependency factory for KalshiMarketReader."""


import logging
from dataclasses import dataclass

from ..metadata import KalshiMetadataAdapter
from . import (
    ExpiryChecker,
    MarketAggregator,
    MarketFilter,
    MarketLookup,
    MetadataExtractor,
    OrderbookReader,
    SnapshotReader,
    TickerParser,
)


@dataclass
class KalshiMarketReaderDependencies:
    """Container for all KalshiMarketReader dependencies."""

    ticker_parser: TickerParser
    market_filter: MarketFilter
    metadata_extractor: MetadataExtractor
    orderbook_reader: OrderbookReader
    market_aggregator: MarketAggregator
    expiry_checker: ExpiryChecker
    snapshot_reader: SnapshotReader
    market_lookup: MarketLookup


class KalshiMarketReaderDependenciesFactory:
    """Factory for creating KalshiMarketReader dependencies."""

    @staticmethod
    def create(logger: logging.Logger, metadata_adapter: KalshiMetadataAdapter) -> KalshiMarketReaderDependencies:
        """Create all dependencies for KalshiMarketReader."""
        ticker_parser = TickerParser()
        market_filter = MarketFilter(logger)
        metadata_extractor = MetadataExtractor(logger)
        orderbook_reader = OrderbookReader(logger)
        market_aggregator = MarketAggregator()
        expiry_checker = ExpiryChecker(logger)
        snapshot_reader = SnapshotReader(logger, metadata_extractor, metadata_adapter)
        market_lookup = MarketLookup(logger, metadata_extractor, orderbook_reader, ticker_parser)

        return KalshiMarketReaderDependencies(
            ticker_parser=ticker_parser,
            market_filter=market_filter,
            metadata_extractor=metadata_extractor,
            orderbook_reader=orderbook_reader,
            market_aggregator=market_aggregator,
            expiry_checker=expiry_checker,
            snapshot_reader=snapshot_reader,
            market_lookup=market_lookup,
        )
