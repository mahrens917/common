"""Tests for subscription_factory module."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from common.redis_protocol.kalshi_store import subscription_factory
from common.redis_protocol.kalshi_store.subscription_factory import (
    KalshiSubscriptionTrackerDependencies,
    KalshiSubscriptionTrackerFactory,
)


@pytest.fixture
def mock_redis_connection():
    """Create a mock redis connection."""
    return MagicMock()


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock(spec=logging.Logger)


def test_dependencies_dataclass_creation():
    """Test creating KalshiSubscriptionTrackerDependencies."""
    deps = KalshiSubscriptionTrackerDependencies(
        connection_manager=MagicMock(),
        key_provider=MagicMock(),
        market_subscription_manager=MagicMock(),
        subscription_id_manager=MagicMock(),
        service_status_manager=MagicMock(),
    )
    assert deps.connection_manager is not None
    assert deps.key_provider is not None
    assert deps.market_subscription_manager is not None
    assert deps.subscription_id_manager is not None
    assert deps.service_status_manager is not None


def test_factory_has_create_method():
    """Test factory has create method."""
    assert hasattr(KalshiSubscriptionTrackerFactory, "create")
    assert callable(KalshiSubscriptionTrackerFactory.create)


@patch.object(subscription_factory, "ServiceStatusManager")
@patch.object(subscription_factory, "SubscriptionIdManager")
@patch.object(subscription_factory, "MarketSubscriptionManager")
@patch.object(subscription_factory, "KeyProvider")
@patch.object(subscription_factory, "ConnectionManager")
def test_factory_create_with_service_prefix(
    mock_conn_mgr_cls,
    mock_key_prov_cls,
    mock_market_sub_cls,
    mock_sub_id_cls,
    mock_status_cls,
    mock_redis_connection,
    mock_logger,
):
    """Test factory creates all dependencies with service prefix."""
    service_prefix = "test_ws"

    # Setup mocks
    mock_conn_instance = MagicMock()
    mock_conn_mgr_cls.return_value = mock_conn_instance
    mock_key_instance = MagicMock()
    mock_key_instance.subscriptions_key = "subs_key"
    mock_key_instance.subscription_ids_key = "ids_key"
    mock_key_instance.service_status_key = "status_key"
    mock_key_prov_cls.return_value = mock_key_instance
    mock_conn_instance.get_redis = MagicMock()
    mock_market_instance = MagicMock()
    mock_market_sub_cls.return_value = mock_market_instance
    mock_sub_id_instance = MagicMock()
    mock_sub_id_cls.return_value = mock_sub_id_instance
    mock_status_instance = MagicMock()
    mock_status_cls.return_value = mock_status_instance

    deps = KalshiSubscriptionTrackerFactory.create(
        mock_redis_connection, mock_logger, service_prefix
    )

    assert isinstance(deps, KalshiSubscriptionTrackerDependencies)
    assert deps.connection_manager == mock_conn_instance
    assert deps.key_provider == mock_key_instance
    assert deps.market_subscription_manager == mock_market_instance
    assert deps.subscription_id_manager == mock_sub_id_instance
    assert deps.service_status_manager == mock_status_instance

    # Verify calls
    mock_conn_mgr_cls.assert_called_once_with(mock_redis_connection, mock_logger)
    mock_key_prov_cls.assert_called_once_with(service_prefix)


@patch.object(subscription_factory, "ServiceStatusManager")
@patch.object(subscription_factory, "SubscriptionIdManager")
@patch.object(subscription_factory, "MarketSubscriptionManager")
@patch.object(subscription_factory, "KeyProvider")
@patch.object(subscription_factory, "ConnectionManager")
def test_factory_create_without_service_prefix(
    mock_conn_mgr_cls,
    mock_key_prov_cls,
    mock_market_sub_cls,
    mock_sub_id_cls,
    mock_status_cls,
    mock_redis_connection,
    mock_logger,
):
    """Test factory creates all dependencies without service prefix (uses default)."""
    # Setup mocks
    mock_conn_instance = MagicMock()
    mock_conn_mgr_cls.return_value = mock_conn_instance
    mock_key_instance = MagicMock()
    mock_key_instance.subscriptions_key = "subs_key"
    mock_key_instance.subscription_ids_key = "ids_key"
    mock_key_instance.service_status_key = "status_key"
    mock_key_prov_cls.return_value = mock_key_instance
    mock_conn_instance.get_redis = MagicMock()
    mock_market_instance = MagicMock()
    mock_market_sub_cls.return_value = mock_market_instance
    mock_sub_id_instance = MagicMock()
    mock_sub_id_cls.return_value = mock_sub_id_instance
    mock_status_instance = MagicMock()
    mock_status_cls.return_value = mock_status_instance

    deps = KalshiSubscriptionTrackerFactory.create(
        mock_redis_connection, mock_logger, None
    )

    assert isinstance(deps, KalshiSubscriptionTrackerDependencies)
    assert deps.connection_manager == mock_conn_instance
    assert deps.key_provider == mock_key_instance
    assert deps.market_subscription_manager == mock_market_instance
    assert deps.subscription_id_manager == mock_sub_id_instance
    assert deps.service_status_manager == mock_status_instance

    # Verify default "ws" is used
    mock_key_prov_cls.assert_called_once_with("ws")


@patch.object(subscription_factory, "ServiceStatusManager")
@patch.object(subscription_factory, "SubscriptionIdManager")
@patch.object(subscription_factory, "MarketSubscriptionManager")
@patch.object(subscription_factory, "KeyProvider")
@patch.object(subscription_factory, "ConnectionManager")
def test_factory_create_with_empty_string_prefix(
    mock_conn_mgr_cls,
    mock_key_prov_cls,
    mock_market_sub_cls,
    mock_sub_id_cls,
    mock_status_cls,
    mock_redis_connection,
    mock_logger,
):
    """Test factory creates all dependencies with empty string prefix."""
    # Setup mocks
    mock_conn_instance = MagicMock()
    mock_conn_mgr_cls.return_value = mock_conn_instance
    mock_key_instance = MagicMock()
    mock_key_instance.subscriptions_key = "subs_key"
    mock_key_instance.subscription_ids_key = "ids_key"
    mock_key_instance.service_status_key = "status_key"
    mock_key_prov_cls.return_value = mock_key_instance
    mock_conn_instance.get_redis = MagicMock()
    mock_market_instance = MagicMock()
    mock_market_sub_cls.return_value = mock_market_instance
    mock_sub_id_instance = MagicMock()
    mock_sub_id_cls.return_value = mock_sub_id_instance
    mock_status_instance = MagicMock()
    mock_status_cls.return_value = mock_status_instance

    deps = KalshiSubscriptionTrackerFactory.create(
        mock_redis_connection, mock_logger, ""
    )

    assert isinstance(deps, KalshiSubscriptionTrackerDependencies)
    assert deps.connection_manager == mock_conn_instance
    assert deps.key_provider == mock_key_instance
    assert deps.market_subscription_manager == mock_market_instance
    assert deps.subscription_id_manager == mock_sub_id_instance
    assert deps.service_status_manager == mock_status_instance

    # Verify default "ws" is used for empty string
    mock_key_prov_cls.assert_called_once_with("ws")
