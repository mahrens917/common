"""Comprehensive unit tests for dependencies_factory.py."""

import logging
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from common.redis_protocol.kalshi_store.dependencies_factory import (
    KalshiStoreDependencies,
    KalshiStoreDependenciesFactory,
)


@pytest.fixture
def mock_logger():
    """Mock logger instance."""
    return Mock(spec=logging.Logger)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    return AsyncMock()


@pytest.fixture
def mock_weather_resolver():
    """Mock WeatherStationResolver."""
    resolver = Mock()
    resolver.resolve = Mock(return_value={"station": "KJFK", "name": "JFK Airport"})
    return resolver


@pytest.fixture
def mock_update_callback():
    """Mock update trade prices callback."""
    return Mock()


class TestKalshiStoreDependencies:
    """Tests for KalshiStoreDependencies dataclass."""

    def test_dataclass_creation(self):
        """Test creating KalshiStoreDependencies with all required fields."""
        connection = Mock()
        metadata = Mock()
        reader = Mock()
        writer = Mock()
        subscription = Mock()
        cleaner = Mock()
        orderbook = Mock()
        property_mgr = Mock()
        conn_delegator = Mock()
        metadata_delegator = Mock()
        subscription_delegator = Mock()
        query_delegator = Mock()
        write_delegator = Mock()
        orderbook_delegator = Mock()
        cleanup_delegator = Mock()
        utility_delegator = Mock()
        storage_delegator = Mock()
        attr_resolver = Mock()

        deps = KalshiStoreDependencies(
            connection=connection,
            metadata=metadata,
            reader=reader,
            writer=writer,
            subscription=subscription,
            cleaner=cleaner,
            orderbook=orderbook,
            property_mgr=property_mgr,
            conn_delegator=conn_delegator,
            metadata_delegator=metadata_delegator,
            subscription_delegator=subscription_delegator,
            query_delegator=query_delegator,
            write_delegator=write_delegator,
            orderbook_delegator=orderbook_delegator,
            cleanup_delegator=cleanup_delegator,
            utility_delegator=utility_delegator,
            storage_delegator=storage_delegator,
            attr_resolver=attr_resolver,
        )

        assert deps.connection is connection
        assert deps.metadata is metadata
        assert deps.reader is reader
        assert deps.writer is writer
        assert deps.subscription is subscription
        assert deps.cleaner is cleaner
        assert deps.orderbook is orderbook
        assert deps.property_mgr is property_mgr
        assert deps.conn_delegator is conn_delegator
        assert deps.metadata_delegator is metadata_delegator
        assert deps.subscription_delegator is subscription_delegator
        assert deps.query_delegator is query_delegator
        assert deps.write_delegator is write_delegator
        assert deps.orderbook_delegator is orderbook_delegator
        assert deps.cleanup_delegator is cleanup_delegator
        assert deps.utility_delegator is utility_delegator
        assert deps.storage_delegator is storage_delegator
        assert deps.attr_resolver is attr_resolver


class TestKalshiStoreDependenciesFactory:
    """Tests for KalshiStoreDependenciesFactory."""

    @patch("common.redis_protocol.kalshi_store.dependencies_factory.factory_helpers")
    def test_create_returns_dependencies_container(
        self, mock_helpers, mock_logger, mock_redis, mock_weather_resolver, mock_update_callback
    ):
        """Test that create returns a properly initialized KalshiStoreDependencies."""
        # Setup mock core components
        mock_connection = Mock()
        mock_metadata = Mock()
        mock_reader = Mock()
        mock_writer = Mock()
        mock_subscription = Mock()
        mock_cleaner = Mock()
        mock_orderbook = Mock()

        mock_helpers.create_core_components.return_value = {
            "connection": mock_connection,
            "metadata": mock_metadata,
            "reader": mock_reader,
            "writer": mock_writer,
            "subscription": mock_subscription,
            "cleaner": mock_cleaner,
            "orderbook": mock_orderbook,
        }

        # Setup mock delegators
        mock_property_mgr = Mock()
        mock_conn_delegator = Mock()
        mock_metadata_delegator = Mock()
        mock_subscription_delegator = Mock()
        mock_query_delegator = Mock()
        mock_write_delegator = Mock()
        mock_orderbook_delegator = Mock()
        mock_cleanup_delegator = Mock()
        mock_utility_delegator = Mock()
        mock_storage_delegator = Mock()

        mock_helpers.create_delegators.return_value = {
            "property_mgr": mock_property_mgr,
            "conn_delegator": mock_conn_delegator,
            "metadata_delegator": mock_metadata_delegator,
            "subscription_delegator": mock_subscription_delegator,
            "query_delegator": mock_query_delegator,
            "write_delegator": mock_write_delegator,
            "orderbook_delegator": mock_orderbook_delegator,
            "cleanup_delegator": mock_cleanup_delegator,
            "utility_delegator": mock_utility_delegator,
            "storage_delegator": mock_storage_delegator,
        }

        # Setup mock attribute resolver
        mock_attr_resolver = Mock()
        mock_helpers.create_attribute_resolver.return_value = mock_attr_resolver

        # Execute
        result = KalshiStoreDependenciesFactory.create(
            logger=mock_logger,
            redis=mock_redis,
            service_prefix="ws",
            weather_resolver=mock_weather_resolver,
            update_trade_prices_callback=mock_update_callback,
        )

        # Verify
        assert isinstance(result, KalshiStoreDependencies)
        assert result.connection is mock_connection
        assert result.metadata is mock_metadata
        assert result.reader is mock_reader
        assert result.writer is mock_writer
        assert result.subscription is mock_subscription
        assert result.cleaner is mock_cleaner
        assert result.orderbook is mock_orderbook
        assert result.property_mgr is mock_property_mgr
        assert result.conn_delegator is mock_conn_delegator
        assert result.metadata_delegator is mock_metadata_delegator
        assert result.subscription_delegator is mock_subscription_delegator
        assert result.query_delegator is mock_query_delegator
        assert result.write_delegator is mock_write_delegator
        assert result.orderbook_delegator is mock_orderbook_delegator
        assert result.cleanup_delegator is mock_cleanup_delegator
        assert result.utility_delegator is mock_utility_delegator
        assert result.storage_delegator is mock_storage_delegator
        assert result.attr_resolver is mock_attr_resolver

    @patch("common.redis_protocol.kalshi_store.dependencies_factory.factory_helpers")
    def test_create_calls_helper_functions_in_order(
        self, mock_helpers, mock_logger, mock_redis, mock_weather_resolver, mock_update_callback
    ):
        """Test that create calls helper functions in the correct order."""
        # Setup mocks
        mock_core = {
            "connection": Mock(),
            "metadata": Mock(),
            "reader": Mock(),
            "writer": Mock(),
            "subscription": Mock(),
            "cleaner": Mock(),
            "orderbook": Mock(),
        }
        mock_delegators = {
            "property_mgr": Mock(),
            "conn_delegator": Mock(),
            "metadata_delegator": Mock(),
            "subscription_delegator": Mock(),
            "query_delegator": Mock(),
            "write_delegator": Mock(),
            "orderbook_delegator": Mock(),
            "cleanup_delegator": Mock(),
            "utility_delegator": Mock(),
            "storage_delegator": Mock(),
        }
        mock_attr_resolver = Mock()

        mock_helpers.create_core_components.return_value = mock_core
        mock_helpers.create_delegators.return_value = mock_delegators
        mock_helpers.create_attribute_resolver.return_value = mock_attr_resolver

        # Execute
        KalshiStoreDependenciesFactory.create(
            logger=mock_logger,
            redis=mock_redis,
            service_prefix="rest",
            weather_resolver=mock_weather_resolver,
            update_trade_prices_callback=mock_update_callback,
        )

        # Verify call order and arguments
        mock_helpers.create_core_components.assert_called_once_with(
            mock_logger, mock_redis, "rest", mock_weather_resolver, mock_update_callback
        )
        mock_helpers.create_delegators.assert_called_once_with(mock_core, mock_weather_resolver)
        mock_helpers.create_attribute_resolver.assert_called_once_with(mock_delegators)

    @patch("common.redis_protocol.kalshi_store.dependencies_factory.factory_helpers")
    def test_create_with_none_redis(
        self, mock_helpers, mock_logger, mock_weather_resolver, mock_update_callback
    ):
        """Test create with None redis client."""
        mock_core = {
            "connection": Mock(),
            "metadata": Mock(),
            "reader": Mock(),
            "writer": Mock(),
            "subscription": Mock(),
            "cleaner": Mock(),
            "orderbook": Mock(),
        }
        mock_delegators = {
            "property_mgr": Mock(),
            "conn_delegator": Mock(),
            "metadata_delegator": Mock(),
            "subscription_delegator": Mock(),
            "query_delegator": Mock(),
            "write_delegator": Mock(),
            "orderbook_delegator": Mock(),
            "cleanup_delegator": Mock(),
            "utility_delegator": Mock(),
            "storage_delegator": Mock(),
        }
        mock_attr_resolver = Mock()

        mock_helpers.create_core_components.return_value = mock_core
        mock_helpers.create_delegators.return_value = mock_delegators
        mock_helpers.create_attribute_resolver.return_value = mock_attr_resolver

        result = KalshiStoreDependenciesFactory.create(
            logger=mock_logger,
            redis=None,
            service_prefix=None,
            weather_resolver=mock_weather_resolver,
            update_trade_prices_callback=mock_update_callback,
        )

        assert isinstance(result, KalshiStoreDependencies)
        mock_helpers.create_core_components.assert_called_once_with(
            mock_logger, None, None, mock_weather_resolver, mock_update_callback
        )

    @patch("common.redis_protocol.kalshi_store.dependencies_factory.factory_helpers")
    def test_create_with_none_service_prefix(
        self, mock_helpers, mock_logger, mock_redis, mock_weather_resolver, mock_update_callback
    ):
        """Test create with None service_prefix."""
        mock_core = {
            "connection": Mock(),
            "metadata": Mock(),
            "reader": Mock(),
            "writer": Mock(),
            "subscription": Mock(),
            "cleaner": Mock(),
            "orderbook": Mock(),
        }
        mock_delegators = {
            "property_mgr": Mock(),
            "conn_delegator": Mock(),
            "metadata_delegator": Mock(),
            "subscription_delegator": Mock(),
            "query_delegator": Mock(),
            "write_delegator": Mock(),
            "orderbook_delegator": Mock(),
            "cleanup_delegator": Mock(),
            "utility_delegator": Mock(),
            "storage_delegator": Mock(),
        }
        mock_attr_resolver = Mock()

        mock_helpers.create_core_components.return_value = mock_core
        mock_helpers.create_delegators.return_value = mock_delegators
        mock_helpers.create_attribute_resolver.return_value = mock_attr_resolver

        result = KalshiStoreDependenciesFactory.create(
            logger=mock_logger,
            redis=mock_redis,
            service_prefix=None,
            weather_resolver=mock_weather_resolver,
            update_trade_prices_callback=mock_update_callback,
        )

        assert isinstance(result, KalshiStoreDependencies)
        mock_helpers.create_core_components.assert_called_once()
        call_args = mock_helpers.create_core_components.call_args
        assert call_args[0][2] is None

    @patch("common.redis_protocol.kalshi_store.dependencies_factory.factory_helpers")
    def test_create_passes_weather_resolver_correctly(
        self, mock_helpers, mock_logger, mock_redis, mock_weather_resolver, mock_update_callback
    ):
        """Test that weather_resolver is passed to both core and delegators."""
        mock_core = {
            "connection": Mock(),
            "metadata": Mock(),
            "reader": Mock(),
            "writer": Mock(),
            "subscription": Mock(),
            "cleaner": Mock(),
            "orderbook": Mock(),
        }
        mock_delegators = {
            "property_mgr": Mock(),
            "conn_delegator": Mock(),
            "metadata_delegator": Mock(),
            "subscription_delegator": Mock(),
            "query_delegator": Mock(),
            "write_delegator": Mock(),
            "orderbook_delegator": Mock(),
            "cleanup_delegator": Mock(),
            "utility_delegator": Mock(),
            "storage_delegator": Mock(),
        }
        mock_attr_resolver = Mock()

        mock_helpers.create_core_components.return_value = mock_core
        mock_helpers.create_delegators.return_value = mock_delegators
        mock_helpers.create_attribute_resolver.return_value = mock_attr_resolver

        KalshiStoreDependenciesFactory.create(
            logger=mock_logger,
            redis=mock_redis,
            service_prefix="ws",
            weather_resolver=mock_weather_resolver,
            update_trade_prices_callback=mock_update_callback,
        )

        # Verify weather_resolver passed to core components
        call_args = mock_helpers.create_core_components.call_args
        assert call_args[0][3] is mock_weather_resolver

        # Verify weather_resolver passed to delegators
        call_args = mock_helpers.create_delegators.call_args
        assert call_args[0][1] is mock_weather_resolver

    @patch("common.redis_protocol.kalshi_store.dependencies_factory.factory_helpers")
    def test_create_static_method(
        self, mock_helpers, mock_logger, mock_redis, mock_weather_resolver, mock_update_callback
    ):
        """Test that create is a static method and can be called without instance."""
        mock_core = {
            "connection": Mock(),
            "metadata": Mock(),
            "reader": Mock(),
            "writer": Mock(),
            "subscription": Mock(),
            "cleaner": Mock(),
            "orderbook": Mock(),
        }
        mock_delegators = {
            "property_mgr": Mock(),
            "conn_delegator": Mock(),
            "metadata_delegator": Mock(),
            "subscription_delegator": Mock(),
            "query_delegator": Mock(),
            "write_delegator": Mock(),
            "orderbook_delegator": Mock(),
            "cleanup_delegator": Mock(),
            "utility_delegator": Mock(),
            "storage_delegator": Mock(),
        }
        mock_attr_resolver = Mock()

        mock_helpers.create_core_components.return_value = mock_core
        mock_helpers.create_delegators.return_value = mock_delegators
        mock_helpers.create_attribute_resolver.return_value = mock_attr_resolver

        # Call as static method
        result = KalshiStoreDependenciesFactory.create(
            logger=mock_logger,
            redis=mock_redis,
            service_prefix="rest",
            weather_resolver=mock_weather_resolver,
            update_trade_prices_callback=mock_update_callback,
        )

        assert isinstance(result, KalshiStoreDependencies)

    @patch("common.redis_protocol.kalshi_store.dependencies_factory.factory_helpers")
    def test_create_with_ws_service_prefix(
        self, mock_helpers, mock_logger, mock_redis, mock_weather_resolver, mock_update_callback
    ):
        """Test create with 'ws' service prefix."""
        mock_core = {
            "connection": Mock(),
            "metadata": Mock(),
            "reader": Mock(),
            "writer": Mock(),
            "subscription": Mock(),
            "cleaner": Mock(),
            "orderbook": Mock(),
        }
        mock_delegators = {
            "property_mgr": Mock(),
            "conn_delegator": Mock(),
            "metadata_delegator": Mock(),
            "subscription_delegator": Mock(),
            "query_delegator": Mock(),
            "write_delegator": Mock(),
            "orderbook_delegator": Mock(),
            "cleanup_delegator": Mock(),
            "utility_delegator": Mock(),
            "storage_delegator": Mock(),
        }
        mock_attr_resolver = Mock()

        mock_helpers.create_core_components.return_value = mock_core
        mock_helpers.create_delegators.return_value = mock_delegators
        mock_helpers.create_attribute_resolver.return_value = mock_attr_resolver

        result = KalshiStoreDependenciesFactory.create(
            logger=mock_logger,
            redis=mock_redis,
            service_prefix="ws",
            weather_resolver=mock_weather_resolver,
            update_trade_prices_callback=mock_update_callback,
        )

        assert isinstance(result, KalshiStoreDependencies)
        call_args = mock_helpers.create_core_components.call_args
        assert call_args[0][2] == "ws"

    @patch("common.redis_protocol.kalshi_store.dependencies_factory.factory_helpers")
    def test_create_with_rest_service_prefix(
        self, mock_helpers, mock_logger, mock_redis, mock_weather_resolver, mock_update_callback
    ):
        """Test create with 'rest' service prefix."""
        mock_core = {
            "connection": Mock(),
            "metadata": Mock(),
            "reader": Mock(),
            "writer": Mock(),
            "subscription": Mock(),
            "cleaner": Mock(),
            "orderbook": Mock(),
        }
        mock_delegators = {
            "property_mgr": Mock(),
            "conn_delegator": Mock(),
            "metadata_delegator": Mock(),
            "subscription_delegator": Mock(),
            "query_delegator": Mock(),
            "write_delegator": Mock(),
            "orderbook_delegator": Mock(),
            "cleanup_delegator": Mock(),
            "utility_delegator": Mock(),
            "storage_delegator": Mock(),
        }
        mock_attr_resolver = Mock()

        mock_helpers.create_core_components.return_value = mock_core
        mock_helpers.create_delegators.return_value = mock_delegators
        mock_helpers.create_attribute_resolver.return_value = mock_attr_resolver

        result = KalshiStoreDependenciesFactory.create(
            logger=mock_logger,
            redis=mock_redis,
            service_prefix="rest",
            weather_resolver=mock_weather_resolver,
            update_trade_prices_callback=mock_update_callback,
        )

        assert isinstance(result, KalshiStoreDependencies)
        call_args = mock_helpers.create_core_components.call_args
        assert call_args[0][2] == "rest"
