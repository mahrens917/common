"""Portfolio operations for Kalshi API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List

from common.data_models.trading import OrderSide, PortfolioBalance, PortfolioPosition

from .exceptions import (
    InvalidAveragePriceError,
    InvalidPositionPayloadError,
    InvalidPositionSideError,
    PortfolioBalanceEmptyError,
    PortfolioBalanceInvalidTypeError,
    PortfolioBalanceMissingTimestampError,
    PortfolioBalanceTimestampNotNumericError,
    PortfolioPositionsEmptyError,
    PortfolioPositionsMissingFieldError,
    PortfolioPositionsNotListError,
    PositionEntryNotObjectError,
    PositionMissingAveragePriceError,
)

if TYPE_CHECKING:
    from .request_builder import RequestBuilder


class PortfolioOperations:
    """Handles portfolio-related API operations."""

    def __init__(self, request_builder: RequestBuilder) -> None:
        self._request_builder = request_builder

    async def get_balance(self) -> PortfolioBalance:
        """Get current portfolio balance."""
        method_upper, url, kwargs, op = self._request_builder.build_request_context(
            method="GET",
            path="/trade-api/v2/portfolio/balance",
            params={},
            json_payload=None,
            operation_name="get_portfolio_balance",
        )
        payload = await self._request_builder.execute_request(method_upper, url, kwargs, "/trade-api/v2/portfolio/balance", op)
        if not payload:
            raise PortfolioBalanceEmptyError()
        balance_value = payload.get("balance")
        if not isinstance(balance_value, int):
            raise PortfolioBalanceInvalidTypeError(payload)
        updated_ts = payload.get("updated_ts")
        if updated_ts is None:
            raise PortfolioBalanceMissingTimestampError()
        if not isinstance(updated_ts, (int, float)):
            raise PortfolioBalanceTimestampNotNumericError()
        if updated_ts < 10**12:
            updated_ts_ms = int(updated_ts * 1000)
        else:
            updated_ts_ms = int(updated_ts)
        timestamp = datetime.fromtimestamp(updated_ts_ms / 1000, timezone.utc)
        return PortfolioBalance(balance_cents=balance_value, timestamp=timestamp, currency="USD")

    async def get_positions(self) -> List[PortfolioPosition]:
        """Get current portfolio positions."""
        method_upper, url, kwargs, op = self._request_builder.build_request_context(
            method="GET",
            path="/trade-api/v2/portfolio/positions",
            params={},
            json_payload=None,
            operation_name="get_portfolio_positions",
        )
        payload = await self._request_builder.execute_request(method_upper, url, kwargs, "/trade-api/v2/portfolio/positions", op)
        raw_positions = _validate_positions_payload(payload)
        return [_parse_position_entry(item) for item in raw_positions]


def _validate_positions_payload(payload: Any) -> List[Dict[str, Any]]:
    if payload is None:
        raise PortfolioPositionsEmptyError()
    if "market_positions" not in payload:
        raise PortfolioPositionsMissingFieldError(payload)
    raw_positions = payload["market_positions"]
    if not isinstance(raw_positions, list):
        raise PortfolioPositionsNotListError()
    return raw_positions


def _parse_position_entry(item: Any) -> PortfolioPosition:
    if not isinstance(item, dict):
        raise PositionEntryNotObjectError()
    try:
        ticker = item["ticker"]
        position_count = int(item["position"])
        side_raw = item["side"].lower()
        market_value_raw = item.get("market_value")
        if market_value_raw is None:
            market_value = 0
        else:
            market_value = int(market_value_raw)
        unrealized_raw = item.get("unrealized_pnl")
        if unrealized_raw is None:
            unrealized = 0
        else:
            unrealized = int(unrealized_raw)
        average_price_raw = item.get("average_price")
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidPositionPayloadError(item, exc) from exc
    if average_price_raw is None:
        raise PositionMissingAveragePriceError()
    try:
        average_price = int(average_price_raw)
    except (TypeError, ValueError) as exc:
        raise InvalidAveragePriceError(average_price_raw, exc) from exc
    try:
        side = OrderSide(side_raw)
    except ValueError as exc:
        raise InvalidPositionSideError(side_raw, exc) from exc
    return PortfolioPosition(
        ticker=ticker,
        position_count=position_count,
        side=side,
        market_value_cents=market_value,
        unrealized_pnl_cents=unrealized,
        average_price_cents=average_price,
        last_updated=datetime.now(timezone.utc),
    )
