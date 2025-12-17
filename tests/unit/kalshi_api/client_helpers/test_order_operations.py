"""Tests for kalshi_api client_helpers order_operations re-export."""

from common.kalshi_api.client_helpers.order_operations import OrderOperations


def test_re_export():
    # Just verify the import works
    assert OrderOperations is not None
