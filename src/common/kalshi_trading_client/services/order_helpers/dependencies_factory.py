from __future__ import annotations

"""Dependency factory for OrderService."""


from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from ....order_execution import OrderPoller, TradeFinalizer
from ....redis_protocol.trade_store import TradeStore
from ....trading import WeatherStationResolver
from ....trading.notifier_adapter import TradeNotifierAdapter
from . import (
    FeeCalculator,
    FillsFetcher,
    FillsOperations,
    MetadataFetcher,
    MetadataOperations,
    MetadataResolver,
    OrderCanceller,
    OrderCreator,
    OrderParser,
    OrderPollerCoordinator,
    OrderValidator,
    ValidationOperations,
)


@dataclass(frozen=True)
class OrderServiceRequiredDeps:
    """Required dependencies for OrderService (cannot be None)."""

    kalshi_client: object
    trade_store_getter: Callable[[], Awaitable[TradeStore]]
    notifier: TradeNotifierAdapter
    weather_resolver: WeatherStationResolver
    order_poller_factory: Callable[[], OrderPoller]
    trade_finalizer_factory: Callable[[], TradeFinalizer]
    telegram_handler: object = None


@dataclass(frozen=True)
class OrderServiceOptionalDeps:
    """Optional dependencies for OrderService (will be created if None)."""

    validator: Optional[OrderValidator] = None
    parser: Optional[OrderParser] = None
    metadata_resolver: Optional[MetadataResolver] = None
    fee_calculator: Optional[FeeCalculator] = None
    canceller: Optional[OrderCanceller] = None
    fills_fetcher: Optional[FillsFetcher] = None
    metadata_fetcher: Optional[MetadataFetcher] = None
    order_creator: Optional[OrderCreator] = None
    poller: Optional[OrderPollerCoordinator] = None
    validation_ops: Optional[ValidationOperations] = None
    fills_ops: Optional[FillsOperations] = None
    metadata_ops: Optional[MetadataOperations] = None


def build_operation_helpers(
    validator: OrderValidator,
    parser: OrderParser,
    canceller: OrderCanceller,
    fills_fetcher: FillsFetcher,
    metadata_resolver: MetadataResolver,
    fee_calculator: FeeCalculator,
    metadata_fetcher: MetadataFetcher,
) -> tuple[ValidationOperations, FillsOperations, MetadataOperations]:
    """Build operation helper instances."""
    validation_ops = ValidationOperations(validator, parser)
    fills_ops = FillsOperations(canceller, fills_fetcher)
    metadata_ops = MetadataOperations(metadata_resolver, fee_calculator, metadata_fetcher)
    return validation_ops, fills_ops, metadata_ops


@dataclass
class OrderServiceDependencies:
    """Container for all OrderService dependencies."""

    kalshi_client: object
    trade_store_getter: Callable[[], Awaitable[TradeStore]]
    notifier: TradeNotifierAdapter
    telegram_handler: object
    validator: OrderValidator
    parser: OrderParser
    metadata_resolver: MetadataResolver
    fee_calculator: FeeCalculator
    canceller: OrderCanceller
    fills_fetcher: FillsFetcher
    metadata_fetcher: MetadataFetcher
    order_creator: OrderCreator
    poller: OrderPollerCoordinator
    validation_ops: ValidationOperations
    fills_ops: FillsOperations
    metadata_ops: MetadataOperations


def _create_validators(validator, parser):
    """Create validator and parser if not provided."""
    return validator or OrderValidator(), parser or OrderParser()


def _create_resolvers_and_calculators(metadata_resolver, fee_calculator, weather_resolver):
    """Create metadata resolver and fee calculator if not provided."""
    resolver = metadata_resolver or MetadataResolver(weather_resolver)
    calculator = fee_calculator or FeeCalculator()
    return resolver, calculator


def _create_fetchers(canceller, fills_fetcher, metadata_fetcher, kalshi_client, trade_store_getter, telegram_handler):
    """Create canceller, fills fetcher, and metadata fetcher if not provided."""
    cancel = canceller or OrderCanceller(kalshi_client)
    fills = fills_fetcher or FillsFetcher(kalshi_client)
    metadata = metadata_fetcher or MetadataFetcher(trade_store_getter, telegram_handler)
    return cancel, fills, metadata


@dataclass(frozen=True)
class _CoordinatorCreationContext:
    """Context for creating coordinators."""

    order_creator: Optional[OrderCreator]
    poller: Optional[OrderPollerCoordinator]
    kalshi_client: object
    trade_store_getter: Callable[[], Awaitable[TradeStore]]
    notifier: TradeNotifierAdapter
    metadata_resolver: MetadataResolver
    validator: OrderValidator
    order_poller_factory: Callable[[], OrderPoller]
    trade_finalizer_factory: Callable[[], TradeFinalizer]


def _create_coordinators(
    ctx: _CoordinatorCreationContext,
) -> tuple[OrderCreator, OrderPollerCoordinator]:
    """Create order creator and poller coordinator if not provided."""
    creator = ctx.order_creator or OrderCreator(
        ctx.kalshi_client,
        ctx.trade_store_getter,
        ctx.notifier,
        ctx.metadata_resolver,
        ctx.validator,
    )
    poll_coord = ctx.poller or OrderPollerCoordinator(ctx.kalshi_client, ctx.order_poller_factory, ctx.trade_finalizer_factory)
    return creator, poll_coord


def _create_or_use_dependencies(
    required: OrderServiceRequiredDeps,
    optional: OrderServiceOptionalDeps,
) -> OrderServiceDependencies:
    """Create dependencies or use provided ones - module level helper."""
    validator, parser = _create_validators(optional.validator, optional.parser)
    metadata_resolver, fee_calculator = _create_resolvers_and_calculators(
        optional.metadata_resolver, optional.fee_calculator, required.weather_resolver
    )
    canceller, fills_fetcher, metadata_fetcher = _create_fetchers(
        optional.canceller,
        optional.fills_fetcher,
        optional.metadata_fetcher,
        required.kalshi_client,
        required.trade_store_getter,
        required.telegram_handler,
    )

    coordinator_ctx = _CoordinatorCreationContext(
        order_creator=optional.order_creator,
        poller=optional.poller,
        kalshi_client=required.kalshi_client,
        trade_store_getter=required.trade_store_getter,
        notifier=required.notifier,
        metadata_resolver=metadata_resolver,
        validator=validator,
        order_poller_factory=required.order_poller_factory,
        trade_finalizer_factory=required.trade_finalizer_factory,
    )
    order_creator, poller = _create_coordinators(coordinator_ctx)

    validation_ops = optional.validation_ops
    fills_ops = optional.fills_ops
    metadata_ops = optional.metadata_ops

    if validation_ops is None or fills_ops is None or metadata_ops is None:
        validation_ops, fills_ops, metadata_ops = build_operation_helpers(
            validator,
            parser,
            canceller,
            fills_fetcher,
            metadata_resolver,
            fee_calculator,
            metadata_fetcher,
        )

    return OrderServiceDependencies(
        kalshi_client=required.kalshi_client,
        trade_store_getter=required.trade_store_getter,
        notifier=required.notifier,
        telegram_handler=required.telegram_handler,
        validator=validator,
        parser=parser,
        metadata_resolver=metadata_resolver,
        fee_calculator=fee_calculator,
        canceller=canceller,
        fills_fetcher=fills_fetcher,
        metadata_fetcher=metadata_fetcher,
        order_creator=order_creator,
        poller=poller,
        validation_ops=validation_ops,
        fills_ops=fills_ops,
        metadata_ops=metadata_ops,
    )


class OrderServiceDependenciesFactory:
    """Factory for creating OrderService dependencies."""

    @staticmethod
    def create(
        kalshi_client,
        trade_store_getter: Callable[[], Awaitable[TradeStore]],
        notifier: TradeNotifierAdapter,
        weather_resolver: WeatherStationResolver,
        order_poller_factory: Callable[[], OrderPoller],
        trade_finalizer_factory: Callable[[], TradeFinalizer],
        telegram_handler=None,
    ) -> OrderServiceDependencies:
        """Create all dependencies for OrderService."""
        validator = OrderValidator()
        parser = OrderParser()
        metadata_resolver = MetadataResolver(weather_resolver)
        fee_calculator = FeeCalculator()
        canceller = OrderCanceller(kalshi_client)
        fills_fetcher = FillsFetcher(kalshi_client)
        metadata_fetcher = MetadataFetcher(trade_store_getter, telegram_handler)
        order_creator = OrderCreator(kalshi_client, trade_store_getter, notifier, metadata_resolver, validator)
        poller = OrderPollerCoordinator(kalshi_client, order_poller_factory, trade_finalizer_factory)
        validation_ops, fills_ops, metadata_ops = build_operation_helpers(
            validator,
            parser,
            canceller,
            fills_fetcher,
            metadata_resolver,
            fee_calculator,
            metadata_fetcher,
        )
        return OrderServiceDependencies(
            kalshi_client=kalshi_client,
            trade_store_getter=trade_store_getter,
            notifier=notifier,
            telegram_handler=telegram_handler,
            validator=validator,
            parser=parser,
            metadata_resolver=metadata_resolver,
            fee_calculator=fee_calculator,
            canceller=canceller,
            fills_fetcher=fills_fetcher,
            metadata_fetcher=metadata_fetcher,
            order_creator=order_creator,
            poller=poller,
            validation_ops=validation_ops,
            fills_ops=fills_ops,
            metadata_ops=metadata_ops,
        )

    @staticmethod
    def create_or_use(
        required: OrderServiceRequiredDeps,
        optional: Optional[OrderServiceOptionalDeps] = None,
    ) -> OrderServiceDependencies:
        """Create dependencies or use provided ones."""
        if optional is None:
            optional = OrderServiceOptionalDeps()
        return _create_or_use_dependencies(required, optional)
