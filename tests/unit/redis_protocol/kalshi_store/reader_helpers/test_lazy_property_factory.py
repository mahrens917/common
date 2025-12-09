"""Tests for lazy property factory module."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.common.redis_protocol.kalshi_store.reader_helpers.lazy_property_factory import (
    create_query_handler,
    create_snapshot_retriever,
    create_status_checker,
)


class TestCreateStatusChecker:
    """Tests for create_status_checker function."""

    def test_creates_status_checker(self) -> None:
        """Creates MarketStatusChecker instance."""
        conn_wrapper = MagicMock()
        ticker_parser = MagicMock()
        expiry_checker = MagicMock()
        get_market_key_fn = MagicMock()

        result = create_status_checker(
            conn_wrapper, ticker_parser, expiry_checker, get_market_key_fn
        )

        assert result is not None


class TestCreateSnapshotRetriever:
    """Tests for create_snapshot_retriever function."""

    def test_creates_snapshot_retriever(self) -> None:
        """Creates SnapshotRetriever instance."""
        conn_wrapper = MagicMock()
        snapshot_reader = MagicMock()
        get_market_key_fn = MagicMock()

        result = create_snapshot_retriever(conn_wrapper, snapshot_reader, get_market_key_fn)

        assert result is not None


class TestCreateQueryHandler:
    """Tests for create_query_handler function."""

    def test_creates_query_handler(self) -> None:
        """Creates MarketQueryHandler instance."""
        conn_wrapper = MagicMock()
        market_lookup = MagicMock()
        market_filter = MagicMock()
        market_aggregator = MagicMock()
        snapshot_reader = MagicMock()
        logger = MagicMock()
        get_market_key_fn = MagicMock()

        result = create_query_handler(
            conn_wrapper,
            market_lookup,
            market_filter,
            market_aggregator,
            snapshot_reader,
            logger,
            get_market_key_fn,
        )

        assert result is not None
