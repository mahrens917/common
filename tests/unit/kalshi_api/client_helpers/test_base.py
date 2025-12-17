"""Tests for kalshi_api client_helpers base."""

from unittest.mock import MagicMock

from common.kalshi_api.client_helpers.base import ClientOperationBase


def test_init():
    client = MagicMock()
    base = ClientOperationBase(client)
    assert base.client is client
