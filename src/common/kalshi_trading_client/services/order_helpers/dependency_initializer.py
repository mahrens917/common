"""Initialize OrderService dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import (
        FeeCalculator,
        FillsFetcher,
        MetadataFetcher,
        MetadataResolver,
        OrderCanceller,
        OrderCreator,
        OrderParser,
        OrderPollerCoordinator,
        OrderValidator,
    )
    from .dependencies_factory import OrderServiceOptionalDeps, OrderServiceRequiredDeps


@dataclass(frozen=True)
class DependencyContainer:
    """Container for OrderService dependencies."""

    validator: "OrderValidator"
    parser: "OrderParser"
    metadata_resolver: "MetadataResolver"
    fee_calculator: "FeeCalculator"
    canceller: "OrderCanceller"
    fills_fetcher: "FillsFetcher"
    metadata_fetcher: "MetadataFetcher"
    order_creator: "OrderCreator"
    poller: "OrderPollerCoordinator"


def initialize_dependencies(
    required: "OrderServiceRequiredDeps",
    optional: "OrderServiceOptionalDeps | None" = None,
) -> DependencyContainer:
    """Initialize dependencies using factory if not provided."""
    from .dependencies_factory import OrderServiceDependenciesFactory

    deps = OrderServiceDependenciesFactory.create_or_use(required, optional)
    return DependencyContainer(
        validator=deps.validator,
        parser=deps.parser,
        metadata_resolver=deps.metadata_resolver,
        fee_calculator=deps.fee_calculator,
        canceller=deps.canceller,
        fills_fetcher=deps.fills_fetcher,
        metadata_fetcher=deps.metadata_fetcher,
        order_creator=deps.order_creator,
        poller=deps.poller,
    )
