import logging
from unittest.mock import Mock

import pytest

from common.redis_protocol.trade_store.store_helpers.dependencies_factory import (
    TradeStoreDependencies,
    TradeStoreDependenciesFactory,
)


class TestTradeStoreDependenciesFactory:
    def test_create(self):
        logger = Mock(spec=logging.Logger)
        base_connection = Mock()
        get_redis = Mock()
        timezone = Mock()

        deps = TradeStoreDependenciesFactory.create(
            logger=logger,
            base_connection=base_connection,
            get_redis=get_redis,
            timezone=timezone,
        )

        assert isinstance(deps, TradeStoreDependencies)
        assert deps.connection_mgr is not None
        assert deps.pool_acquirer is not None
        assert deps.executor is not None
        assert deps.deps is not None
        assert deps.keys is not None
        assert deps.codec is not None
        assert deps.repository is not None
        assert deps.metadata_store is not None
        assert deps.queries is not None
        assert deps.pnl is not None
        assert deps.price_updater is not None
