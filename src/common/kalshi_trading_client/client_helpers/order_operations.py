from __future__ import annotations

"""Order operations (create, cancel, polling, fills)."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from common.data_models.trading import OrderRequest, OrderResponse
    from common.order_execution import OrderPoller, TradeFinalizer
    from common.trading.polling_workflow import PollingOutcome

from ..services import OrderService


async def create_order(order_service: OrderService, order_request: OrderRequest) -> OrderResponse:
    """Create a new order."""
    return await order_service.create_order(order_request)


async def create_order_with_polling(
    order_service: OrderService,
    order_request: OrderRequest,
    timeout_seconds: int,
    cancel_order_func,
) -> OrderResponse:
    """Create order and poll for completion."""
    order_response = await order_service.create_order(order_request)
    return await order_service.complete_order_with_polling(
        order_request,
        order_response,
        timeout_seconds,
        cancel_order_func,
    )


async def cancel_order(order_service: OrderService, order_id: str) -> bool:
    """Cancel an existing order."""
    return await order_service.cancel_order(order_id)


async def get_fills(order_service: OrderService, order_id: str) -> List[Dict[str, Any]]:
    """Get fills for a specific order."""
    return await order_service.get_fills(order_id)


async def get_all_fills(
    order_service: OrderService,
    min_ts: Optional[int],
    max_ts: Optional[int],
    ticker: Optional[str],
    cursor: Optional[str],
) -> Dict[str, Any]:
    """Get all fills with optional filters."""
    return await order_service.get_all_fills(min_ts, max_ts, ticker, cursor)


def validate_order_request(order_service: OrderService, order_request: OrderRequest) -> None:
    """Validate an order request."""
    order_service.validate_order_request(order_request)


def parse_order_response(
    order_service: OrderService,
    response_data: Dict[str, Any],
    operation_name: str,
    trade_rule: str,
    trade_reason: str,
) -> OrderResponse:
    """Parse raw API response into OrderResponse."""
    return order_service.parse_order_response(response_data, operation_name, trade_rule, trade_reason)


def has_sufficient_balance_for_trade_with_fees(
    order_service: OrderService,
    cached_balance_cents: int,
    trade_cost_cents: int,
    fees_cents: int,
) -> bool:
    """Check if balance is sufficient for trade including fees."""
    return order_service.has_sufficient_balance_for_trade_with_fees(cached_balance_cents, trade_cost_cents, fees_cents)


def build_order_poller(order_service: OrderService) -> OrderPoller:
    """Build an order poller instance."""
    return order_service.build_order_poller()


def build_trade_finalizer(order_service: OrderService) -> TradeFinalizer:
    """Build a trade finalizer instance."""
    return order_service.build_trade_finalizer()


def apply_polling_outcome(order_service: OrderService, order_response: OrderResponse, outcome: PollingOutcome) -> None:
    """Apply polling outcome to order response."""
    order_service.apply_polling_outcome(order_response, outcome)


async def calculate_order_fees(market_ticker: str, quantity: int, price_cents: int) -> int:
    """Calculate fees for an order (delegates to canonical fee calculator)."""
    from common.kalshi_trading_client.services.order_helpers.fee_calculator import calculate_order_fees as _calculate_order_fees

    return await _calculate_order_fees(market_ticker, quantity, price_cents)


async def get_trade_metadata_from_order(order_service: OrderService, order_id: str) -> tuple[str, str]:
    """Get trade metadata from an order."""
    return await order_service.get_trade_metadata_from_order(order_id)


class OrderOperations:
    """Handles order-related operations."""

    create_order = staticmethod(create_order)
    create_order_with_polling = staticmethod(create_order_with_polling)
    cancel_order = staticmethod(cancel_order)
    get_fills = staticmethod(get_fills)
    get_all_fills = staticmethod(get_all_fills)
    validate_order_request = staticmethod(validate_order_request)
    parse_order_response = staticmethod(parse_order_response)
    has_sufficient_balance_for_trade_with_fees = staticmethod(has_sufficient_balance_for_trade_with_fees)
    build_order_poller = staticmethod(build_order_poller)
    build_trade_finalizer = staticmethod(build_trade_finalizer)
    apply_polling_outcome = staticmethod(apply_polling_outcome)
    calculate_order_fees = staticmethod(calculate_order_fees)
    get_trade_metadata_from_order = staticmethod(get_trade_metadata_from_order)
