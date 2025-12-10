import pytest

from common.data_models.trading import OrderAction, OrderSide, OrderStatus, OrderType
from common.order_response_parser import (
    parse_kalshi_order_response,
    validate_order_response_schema,
)
from common.order_response_parser_exceptions import (
    EmptyOrderDataError,
    EmptyRejectionReasonError,
    EmptyResponseError,
    MissingTickerError,
)

_CONST_45 = 45
_CONST_75 = 75
_TEST_COUNT_2 = 2
_TEST_COUNT_4 = 4
DEFAULT_FILL_COUNT = _TEST_COUNT_2
DEFAULT_INITIAL_COUNT = _TEST_COUNT_2
DEFAULT_FILL_PRICE = _CONST_75
DEFAULT_FEE_COUNT = _TEST_COUNT_4
SINGLE_FILL_COUNT = 1


def _base_order_payload(**overrides):
    payload = {
        "order_id": "ord-123",
        "client_order_id": "cid-456",
        "status": "filled",
        "ticker": "TEMP-NYC-2024",
        "side": "yes",
        "action": "buy",
        "type": "limit",
        "fill_count": DEFAULT_FILL_COUNT,
        "initial_count": DEFAULT_INITIAL_COUNT,
        "created_time": "2024-01-01T00:00:00Z",
        "maker_fill_cost": 150,
        "maker_fees": 4,
        "fills": [
            {
                "price": DEFAULT_FILL_PRICE,
                "count": DEFAULT_FILL_COUNT,
                "timestamp": "2024-01-01T00:00:00Z",
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_parse_successful_order_response():
    order = parse_kalshi_order_response(
        _base_order_payload(),
        trade_rule="TEMP_DECLINE",
        trade_reason="Entering weather position",
    )

    assert order.order_id == "ord-123"
    assert order.status is OrderStatus.FILLED
    assert order.side is OrderSide.YES
    assert order.action is OrderAction.BUY
    assert order.order_type is OrderType.LIMIT
    assert order.filled_count == _TEST_COUNT_2
    assert order.remaining_count == 0
    assert order.average_fill_price_cents == DEFAULT_FILL_PRICE
    assert order.fees_cents == DEFAULT_FEE_COUNT
    assert len(order.fills) == 1


def test_parse_allows_zero_fill_without_price():
    payload = _base_order_payload(
        status="resting",
        fill_count=0,
        maker_fill_cost=0,
        fills=[],
    )

    order = parse_kalshi_order_response(
        payload,
        trade_rule="TEMP_DECLINE",
        trade_reason="Waiting for execution",
    )

    assert order.status is OrderStatus.PENDING
    assert order.average_fill_price_cents is None
    assert order.remaining_count == _TEST_COUNT_2


def test_parse_missing_required_field_raises():
    payload = _base_order_payload()
    payload.pop("order_id")

    with pytest.raises(ValueError, match="Missing required fields"):
        parse_kalshi_order_response(payload, "TEMP_DECLINE", "Entering weather position")


def test_parse_invalid_status_raises():
    payload = _base_order_payload(status="unknown")
    with pytest.raises(ValueError, match="Invalid order status"):
        parse_kalshi_order_response(payload, "TEMP_DECLINE", "Entering weather position")


def test_parse_rejection_reason_returns_message():
    payload = _base_order_payload(
        status="rejected",
        fill_count=0,
        maker_fill_cost=0,
        fills=[],
        rejection_reason="Order rejected by exchange",
    )

    order = parse_kalshi_order_response(
        payload,
        trade_rule="TEMP_DECLINE",
        trade_reason="Entering weather position",
    )

    assert order.status is OrderStatus.REJECTED
    assert order.rejection_reason == "Order rejected by exchange"


def test_parse_rejected_order_without_reason_raises():
    payload = _base_order_payload(
        status="rejected",
        fill_count=0,
        maker_fill_cost=0,
        fills=[],
    )

    with pytest.raises(ValueError, match="missing 'rejection_reason'"):
        parse_kalshi_order_response(
            payload,
            trade_rule="TEMP_DECLINE",
            trade_reason="Entering weather position",
        )


def test_parse_validates_fill_structure():
    payload = _base_order_payload(fills=[{"count": 1}])
    with pytest.raises(ValueError, match="Fill missing 'price'"):
        parse_kalshi_order_response(payload, "TEMP_DECLINE", "Entering weather position")


def test_parse_uses_remaining_count_when_provided():
    payload = _base_order_payload(
        fill_count=1,
        remaining_count=4,
        maker_fill_cost=0,
        fills=[
            {
                "price": 60,
                "count": 1,
                "timestamp": "2024-01-01T00:05:00Z",
            }
        ],
    )
    payload.pop("initial_count", None)

    order = parse_kalshi_order_response(
        payload,
        trade_rule="TEMP_DECLINE",
        trade_reason="Monitoring remaining contracts",
    )

    assert order.remaining_count == _TEST_COUNT_4
    assert order.average_fill_price_cents is None
    assert order.fills[0].timestamp.isoformat() == "2024-01-01T00:05:00+00:00"


def test_parse_defaults_total_count_when_missing():
    payload = _base_order_payload(
        initial_count=None,
        remaining_count=None,
        fill_count=1,
        maker_fill_cost=45,
        fills=[
            {
                "price": 45,
                "count": 1,
                "timestamp": "2024-01-01T00:00:00Z",
            }
        ],
    )
    payload.pop("initial_count", None)
    payload.pop("remaining_count", None)

    order = parse_kalshi_order_response(
        payload,
        trade_rule="TEMP_DECLINE",
        trade_reason="Default total count guard",
    )

    assert order.remaining_count == 0
    assert order.filled_count == SINGLE_FILL_COUNT
    assert order.average_fill_price_cents == _CONST_45


def test_parse_missing_created_time_raises():
    payload = _base_order_payload()
    payload.pop("created_time")

    with pytest.raises(ValueError, match="Missing required field 'created_time'"):
        parse_kalshi_order_response(payload, "RULE", "REASON")


def test_parse_invalid_fill_timestamp_raises():
    payload = _base_order_payload(
        fills=[
            {"price": 70, "count": 2, "timestamp": "not-a-timestamp"},
        ]
    )

    with pytest.raises(ValueError, match="Invalid fill timestamp format"):
        parse_kalshi_order_response(payload, "RULE", "REASON")


def test_parse_fill_count_mismatch_raises():
    payload = _base_order_payload(
        fill_count=3,
        fills=[
            {"price": 70, "count": 1, "timestamp": "2024-01-01T00:00:00Z"},
        ],
    )

    with pytest.raises(ValueError, match="Fills count mismatch"):
        parse_kalshi_order_response(payload, "RULE", "REASON")


def test_parse_invalid_side_action_type_raise():
    payload = _base_order_payload(side="both", action="hold", type="straddle")

    with pytest.raises(ValueError, match="Invalid order side"):
        parse_kalshi_order_response(payload, "RULE", "REASON")


def test_validate_order_response_schema_success():
    order_payload = {"order": {"order_id": "123"}}
    result = validate_order_response_schema(order_payload)
    assert result == {"order_id": "123"}


def test_validate_order_response_schema_errors():
    with pytest.raises(ValueError, match="missing 'order'"):
        validate_order_response_schema({"unexpected": {}})

    with pytest.raises(ValueError, match="expected dict"):
        validate_order_response_schema({"order": ["invalid"]})


def test_parse_empty_order_data_raises():
    with pytest.raises(EmptyOrderDataError):
        parse_kalshi_order_response({}, "RULE_TEST", "Valid test reason")


def test_parse_empty_order_id_raises():
    payload = _base_order_payload(order_id="")
    with pytest.raises(ValueError):
        parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")


def test_parse_empty_client_order_id_raises():
    payload = _base_order_payload(client_order_id="")
    with pytest.raises(ValueError):
        parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")


def test_parse_empty_ticker_raises():
    payload = _base_order_payload(ticker="")
    with pytest.raises(MissingTickerError):
        parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")


def test_parse_invalid_created_time_format_raises():
    payload = _base_order_payload(created_time="invalid-date")
    with pytest.raises(ValueError):
        parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")


def test_parse_invalid_fill_count_type_raises():
    payload = _base_order_payload(fill_count="not-a-number")
    with pytest.raises(ValueError):
        parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")


def test_parse_invalid_order_count_type_raises():
    payload = _base_order_payload(initial_count="not-a-number")
    with pytest.raises(ValueError):
        parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")


def test_parse_invalid_remaining_count_type_raises():
    payload = _base_order_payload()
    payload.pop("initial_count")
    payload["remaining_count"] = "not-a-number"
    with pytest.raises(ValueError):
        parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")


def test_parse_invalid_maker_fees_raises():
    payload = _base_order_payload(maker_fees="invalid")
    with pytest.raises(ValueError):
        parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")


def test_parse_empty_rejection_reason_raises():
    payload = _base_order_payload(
        status="rejected", fill_count=0, maker_fill_cost=0, fills=[], rejection_reason=""
    )
    with pytest.raises(EmptyRejectionReasonError):
        parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")


def test_parse_whitespace_rejection_reason_raises():
    payload = _base_order_payload(
        status="rejected", fill_count=0, maker_fill_cost=0, fills=[], rejection_reason="   "
    )
    with pytest.raises(EmptyRejectionReasonError):
        parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")


def test_parse_invalid_fill_count_in_fill_raises():
    payload = _base_order_payload(fills=[{"price": 70, "count": "not-a-number"}])
    with pytest.raises(ValueError):
        parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")


def test_parse_fills_uses_fallback_timestamp():
    payload = _base_order_payload(fills=[{"price": 75, "count": 2}])  # No timestamp provided
    order = parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")
    assert order.fills[0].timestamp.isoformat() == "2024-01-01T00:00:00+00:00"


def test_parse_uses_count_field_for_total():
    payload = _base_order_payload()
    payload.pop("initial_count")
    payload["count"] = 5
    payload["fill_count"] = 2
    payload["maker_fill_cost"] = 0
    payload.pop("fills")
    order = parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")
    assert order.remaining_count == 3


def test_parse_uses_quantity_field_for_total():
    payload = _base_order_payload()
    payload.pop("initial_count")
    payload["quantity"] = 10
    payload["fill_count"] = 3
    payload["maker_fill_cost"] = 0
    payload.pop("fills")
    order = parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")
    assert order.remaining_count == 7


def test_parse_executed_status():
    payload = _base_order_payload(status="executed")
    order = parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")
    assert order.status is OrderStatus.EXECUTED


def test_parse_canceled_status():
    payload = _base_order_payload(status="canceled", fill_count=0, maker_fill_cost=0, fills=[])
    order = parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")
    assert order.status is OrderStatus.CANCELLED


def test_parse_no_side_action_type():
    payload = _base_order_payload(action="sell", type="market")
    order = parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")
    assert order.action is OrderAction.SELL
    assert order.order_type is OrderType.MARKET


def test_validate_empty_response_raises():
    with pytest.raises(EmptyResponseError):
        validate_order_response_schema({})


def test_validate_none_response_raises():
    with pytest.raises(EmptyResponseError):
        validate_order_response_schema(None)


def test_parse_unreliable_maker_cost_returns_none():
    payload = _base_order_payload(fill_count=2, maker_fill_cost=None)
    order = parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")
    assert order.average_fill_price_cents is None


def test_parse_zero_maker_cost_returns_none():
    payload = _base_order_payload(fill_count=2, maker_fill_cost=0)
    order = parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")
    assert order.average_fill_price_cents is None


def test_parse_negative_maker_cost_returns_none():
    payload = _base_order_payload(fill_count=2, maker_fill_cost=-100)
    order = parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")
    assert order.average_fill_price_cents is None


def test_parse_non_numeric_maker_cost_returns_none():
    payload = _base_order_payload(fill_count=2, maker_fill_cost="invalid")
    order = parse_kalshi_order_response(payload, "RULE_TEST", "Valid test reason")
    assert order.average_fill_price_cents is None
