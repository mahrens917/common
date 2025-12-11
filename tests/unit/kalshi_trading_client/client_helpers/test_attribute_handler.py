"""Tests for attribute_handler module."""

from unittest.mock import MagicMock

import pytest

from common.kalshi_trading_client.client_helpers import attribute_handler
from common.kalshi_trading_client.client_helpers.attribute_handler import (
    AttributeHandler,
)


@pytest.fixture
def mock_orders_service():
    """Create a mock orders service."""
    service = MagicMock()
    service.update_notifier = MagicMock()
    service.update_telegram_handler = MagicMock()
    return service


@pytest.fixture
def mock_notifier():
    """Create a mock notifier."""
    return MagicMock()


@pytest.fixture
def mock_telegram_handler():
    """Create a mock telegram handler."""
    return MagicMock()


def test_handle_notifier_update_with_service(mock_orders_service, mock_notifier):
    """Test handle_notifier_update updates service when provided."""
    AttributeHandler.handle_notifier_update(mock_orders_service, mock_notifier)
    mock_orders_service.update_notifier.assert_called_once_with(mock_notifier)


def test_handle_notifier_update_without_service(mock_notifier):
    """Test handle_notifier_update does nothing when service is None."""
    AttributeHandler.handle_notifier_update(None, mock_notifier)


def test_handle_telegram_handler_update_with_service(mock_orders_service, mock_telegram_handler):
    """Test handle_telegram_handler_update updates service when provided."""
    AttributeHandler.handle_telegram_handler_update(mock_orders_service, mock_telegram_handler)
    mock_orders_service.update_telegram_handler.assert_called_once_with(mock_telegram_handler)


def test_handle_telegram_handler_update_without_service(mock_telegram_handler):
    """Test handle_telegram_handler_update does nothing when service is None."""
    AttributeHandler.handle_telegram_handler_update(None, mock_telegram_handler)
