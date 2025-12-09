"""Shared base for connection manager helper classes."""

import logging

from ....kalshi_store.connection import RedisConnectionManager


class ConnectionHelperBase:
    """Provides common initialization for helpers that wrap RedisConnectionManager."""

    def __init__(self, logger: logging.Logger, connection_manager: RedisConnectionManager):
        self.logger = logger
        self._connection = connection_manager

    @property
    def connection(self) -> RedisConnectionManager:
        return self._connection


__all__ = ["ConnectionHelperBase"]
