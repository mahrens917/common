from __future__ import annotations

"""Order payload helpers shared across Kalshi trading components."""


from typing import Dict

from ..data_models.trading import OrderRequest, OrderSide, OrderType

# Constants
_MAX_PRICE = 99


def build_order_payload(order_request: OrderRequest) -> Dict[str, int | str]:
    """Convert an OrderRequest into the REST payload expected by Kalshi."""

    payload: Dict[str, int | str] = {
        "ticker": order_request.ticker,
        "action": order_request.action.value,
        "side": order_request.side.value,
        "count": order_request.count,
        "client_order_id": order_request.client_order_id,
        "type": order_request.order_type.value,
        "time_in_force": order_request.time_in_force.value,
    }

    price_cents = order_request.yes_price_cents
    if price_cents is None:
        raise ValueError(
            "Order requests must provide yes_price_cents before payload construction; "
            "do not rely on implicit fallbacks."
        )

    if price_cents > _MAX_PRICE:
        raise TypeError(f"Order price must be between 0-99 cents, received {price_cents}")
    if price_cents < 0:
        raise TypeError(f"Order price must be non-negative, received {price_cents}")
    if price_cents == 0 and order_request.order_type != OrderType.MARKET:
        raise ValueError("Only market orders may specify a zero yes_price_cents")

    if order_request.side == OrderSide.YES:
        price_field = "yes_price"
    else:
        price_field = "no_price"
    payload[price_field] = price_cents

    if order_request.expiration_ts is not None:
        payload["expiration_ts"] = order_request.expiration_ts

    return payload


__all__ = ["build_order_payload"]
