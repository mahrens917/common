"""Dependency resolution for TradeStore initialization."""

import importlib
import sys
from typing import Any, Callable

from .... import config_loader as config_loader_module
from .... import time_utils as time_utils_module


def _get_module_attr(name: str, default_value: Any) -> Any:
    """
    Resolve a module-level attribute used for dependency injection in tests.

    The helper looks within the current module and the package root so unit
    tests can monkey-patch helpers without depending on import order.
    """
    module = sys.modules.get("common.redis_protocol.trade_store.store")
    if module is not None and hasattr(module, name):
        value = getattr(module, name)
        if value is not None:
            return value

    package = sys.modules.get("common.redis_protocol.trade_store")
    if package is not None and hasattr(package, name):
        value = getattr(package, name)
        if value is not None:
            return value

    return default_value


class DependencyResolver:
    """Resolve external dependencies for TradeStore components."""

    @staticmethod
    def get_timezone_loader() -> Callable[[], object]:
        """Get timezone configuration loader."""
        return _get_module_attr(
            "load_configured_timezone", time_utils_module.load_configured_timezone
        )

    @staticmethod
    def get_timestamp_provider() -> Callable[[], Any]:
        """Get current UTC timestamp provider."""
        return _get_module_attr("get_current_utc", time_utils_module.get_current_utc)

    @staticmethod
    def get_start_date_loader() -> Callable[[], Any]:
        """Get historical start date loader."""
        return _get_module_attr(
            "get_historical_start_date", config_loader_module.get_historical_start_date
        )

    @staticmethod
    def get_timezone_date_loader() -> Callable[[object], Any]:
        """Get timezone-aware date loader."""
        return _get_module_attr(
            "get_timezone_aware_date", time_utils_module.get_timezone_aware_date
        )

    @staticmethod
    def get_redis_pool_getter():
        """Get Redis pool factory from trade_store module."""
        from ... import get_redis_pool

        module = importlib.import_module("common.redis_protocol.trade_store")
        return getattr(module, "get_redis_pool", get_redis_pool)

    @staticmethod
    def get_redis_class():
        """Get Redis client class for instantiation."""
        import redis.asyncio

        module = importlib.import_module("common.redis_protocol.trade_store")
        module_cls = getattr(module, "Redis", None)

        # Avoid using monkey-patched sentinel value
        from ..store import ORIGINAL_REDIS_CLASS

        if module_cls is not None and module_cls is not ORIGINAL_REDIS_CLASS:
            return module_cls

        return getattr(redis.asyncio, "Redis")
