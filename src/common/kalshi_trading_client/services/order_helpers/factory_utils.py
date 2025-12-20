"""Helper utilities for OrderServiceDependenciesFactory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .dependencies_factory import OrderServiceDependencies, build_operation_helpers


@dataclass(frozen=True)
class _DefaultDependencies:
    """Default dependency values for factory."""

    validator: object
    parser: object
    metadata_resolver: object
    fee_calculator: object
    canceller: object
    fills_fetcher: object
    metadata_fetcher: object
    order_creator: object
    poller: object


def _resolve_dep(provided_deps: dict, key: str, fallback_value):
    """Resolve a single dependency from provided dict or use fallback.

    Returns the provided value if it exists and is truthy, otherwise
    returns the fallback value. Uses explicit check to avoid silent fallbacks.
    """
    value = provided_deps.get(key)
    if value is not None:
        return value
    return fallback_value


def _resolve_all_deps(provided_deps: dict, defaults: _DefaultDependencies) -> dict:
    """Resolve all dependencies from provided dict or use defaults."""
    defaults_dict = {
        "validator": defaults.validator,
        "parser": defaults.parser,
        "metadata_resolver": defaults.metadata_resolver,
        "fee_calculator": defaults.fee_calculator,
        "canceller": defaults.canceller,
        "fills_fetcher": defaults.fills_fetcher,
        "metadata_fetcher": defaults.metadata_fetcher,
        "order_creator": defaults.order_creator,
        "poller": defaults.poller,
    }
    return {key: _resolve_dep(provided_deps, key, fallback_value) for key, fallback_value in defaults_dict.items()}


def create_or_use_dependencies(
    provided_deps: dict[str, Any],
    defaults: _DefaultDependencies,
) -> OrderServiceDependencies:
    """Create dependencies or use provided ones."""

    resolved = _resolve_all_deps(provided_deps, defaults)

    validation_ops, fills_ops, metadata_ops = build_operation_helpers(
        resolved["validator"],
        resolved["parser"],
        resolved["canceller"],
        resolved["fills_fetcher"],
        resolved["metadata_resolver"],
        resolved["fee_calculator"],
        resolved["metadata_fetcher"],
    )

    required_keys = ("kalshi_client", "trade_store_getter", "notifier", "telegram_handler")
    missing = [key for key in required_keys if key not in provided_deps or provided_deps.get(key) is None]
    if missing:
        raise TypeError(f"Missing required dependencies: {', '.join(missing)}")

    kalshi_client = provided_deps["kalshi_client"]
    trade_store_getter = provided_deps["trade_store_getter"]
    notifier = provided_deps["notifier"]
    telegram_handler = provided_deps["telegram_handler"]

    return OrderServiceDependencies(
        kalshi_client=kalshi_client,
        trade_store_getter=trade_store_getter,
        notifier=notifier,
        telegram_handler=telegram_handler,
        validator=resolved["validator"],
        parser=resolved["parser"],
        metadata_resolver=resolved["metadata_resolver"],
        fee_calculator=resolved["fee_calculator"],
        canceller=resolved["canceller"],
        fills_fetcher=resolved["fills_fetcher"],
        metadata_fetcher=resolved["metadata_fetcher"],
        order_creator=resolved["order_creator"],
        poller=resolved["poller"],
        validation_ops=_resolve_dep(provided_deps, "validation_ops", validation_ops),
        fills_ops=_resolve_dep(provided_deps, "fills_ops", fills_ops),
        metadata_ops=_resolve_dep(provided_deps, "metadata_ops", metadata_ops),
    )
