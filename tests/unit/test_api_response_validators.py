from datetime import datetime, timezone

import pytest

from src.common import api_response_validators as validators


def test_validate_portfolio_balance_response_success():
    response = {"balance": 12345}
    result = validators.validate_portfolio_balance_response(response)
    assert result == {"balance": 12345}


@pytest.mark.parametrize(
    "response, message",
    [
        ({}, "Empty response"),
        ({"wrong": 1}, "Missing 'balance'"),
        ({"balance": "abc"}, "Balance must be numeric"),
        ({"balance": -2_000_000_000}, "unreasonably negative"),
    ],
)
def test_validate_portfolio_balance_response_errors(response, message):
    with pytest.raises((TypeError, ValueError), match=message):
        validators.validate_portfolio_balance_response(response)


def make_market(**overrides):
    base = {
        "ticker": "TEST",
        "event_ticker": "EVT",
        "title": "Market",
        "open_time": datetime.now(timezone.utc).isoformat(),
        "close_time": datetime.now(timezone.utc).isoformat(),
        "status": "open",
        "volume": 0,
        "volume_24h": 0,
    }
    base.update(overrides)
    return base


def test_validate_market_object_success():
    market = make_market(yes_bid=10, yes_ask=20)
    assert validators.validate_market_object(market) == market


@pytest.mark.parametrize(
    "modifier, message",
    [
        (lambda m: m.pop("ticker"), "Missing required fields"),
        (lambda m: m.__setitem__("status", "bad"), "Invalid status"),
        (lambda m: m.__setitem__("open_time", "bad"), "Invalid timestamp"),
        (lambda m: m.__setitem__("volume", -1), "cannot be negative"),
        (lambda m: m.__setitem__("yes_bid", 200), "must be between 0-100"),
    ],
)
def test_validate_market_object_errors(modifier, message):
    market = make_market()
    modifier(market)
    with pytest.raises(ValueError, match=message):
        validators.validate_market_object(market)


def test_validate_markets_response_success():
    response = {"markets": [make_market()], "cursor": "next"}
    result = validators.validate_markets_response(response)
    assert result["cursor"] == "next"
    assert result["markets"][0]["ticker"] == "TEST"


def test_validate_markets_response_errors():
    with pytest.raises(ValueError, match="Empty response"):
        validators.validate_markets_response({})

    with pytest.raises(ValueError, match="Missing 'markets'"):
        validators.validate_markets_response({"cursor": "abc"})

    with pytest.raises(TypeError, match="Markets must be a list"):
        validators.validate_markets_response({"markets": "not-a-list"})

    with pytest.raises(TypeError, match="must be numeric"):
        validators.validate_markets_response({"markets": [make_market(volume="bad")]})

    with pytest.raises(ValueError, match="Cursor must be string"):
        validators.validate_markets_response({"markets": [make_market()], "cursor": 12})


def test_validate_event_response_success():
    response = {
        "event": {"ticker": "EVT", "title": "Event", "category": "weather", "series_ticker": "SER"}
    }
    result = validators.validate_event_response(response)
    assert result["ticker"] == "EVT"


def test_validate_event_response_with_markets():
    response = {
        "event": {
            "ticker": "EVT",
            "title": "Event",
            "category": "weather",
            "series_ticker": "SER",
            "markets": [make_market()],
        }
    }
    result = validators.validate_event_response(response)
    assert result["markets"][0]["ticker"] == "TEST"


def test_validate_event_response_errors():
    with pytest.raises(ValueError, match="Empty response"):
        validators.validate_event_response({})

    with pytest.raises(ValueError, match="Missing 'event'"):
        validators.validate_event_response({"wrong": {}})

    with pytest.raises(TypeError, match="must be dict"):
        validators.validate_event_response({"event": "bad"})

    with pytest.raises(ValueError, match="Missing required fields"):
        validators.validate_event_response({"event": {"ticker": "EVT"}})

    with pytest.raises((TypeError, ValueError), match="must be string"):
        validators.validate_event_response(
            {
                "event": {
                    "ticker": 1,
                    "title": "title",
                    "category": "weather",
                    "series_ticker": "SER",
                }
            }
        )

    with pytest.raises(TypeError, match="must be list"):
        validators.validate_event_response(
            {
                "event": {
                    "ticker": "EVT",
                    "title": "Event",
                    "category": "weather",
                    "series_ticker": "SER",
                    "markets": "bad",
                }
            }
        )


def test_validate_series_response_success():
    response = {
        "series": [
            {
                "ticker": "SER",
                "title": "Series",
                "category": "weather",
                "frequency": "daily",
                "status": "active",
            }
        ]
    }
    result = validators.validate_series_response(response)
    assert result[0]["ticker"] == "SER"


def test_validate_series_response_errors():
    with pytest.raises(ValueError, match="Empty response"):
        validators.validate_series_response({})

    with pytest.raises(ValueError, match="Missing 'series'"):
        validators.validate_series_response({"cursor": "a"})

    with pytest.raises(TypeError, match="Series must be a list"):
        validators.validate_series_response({"series": "not-a-list"})

    with pytest.raises((TypeError, ValueError), match="must be dict"):
        validators.validate_series_response({"series": ["not-a-dict"]})

    with pytest.raises(ValueError, match="missing required fields"):
        validators.validate_series_response({"series": [{"ticker": "SER"}]})

    with pytest.raises(TypeError, match="frequency must be string"):
        validators.validate_series_response(
            {
                "series": [
                    {"ticker": "SER", "title": "Series", "category": "weather", "frequency": 123}
                ]
            }
        )

    with pytest.raises(ValueError, match="Invalid status"):
        validators.validate_series_response(
            {
                "series": [
                    {
                        "ticker": "SER",
                        "title": "Series",
                        "category": "weather",
                        "status": "wrong",
                    }
                ]
            }
        )


def _limit_order_payload(**overrides):
    payload = {
        "order_id": "1",
        "market_ticker": "MKT",
        "status": "canceled",
        "side": "yes",
        "type": "limit",
        "action": "buy",
        "count": 1,
        "created_time": datetime.now(timezone.utc).isoformat(),
        "yes_price": 55,
    }
    payload.update(overrides)
    return payload


def test_validate_cancel_order_response_success_wrapped():
    order = _limit_order_payload()
    result = validators.validate_cancel_order_response({"order": order})
    assert result is order


def test_validate_cancel_order_response_success_market_side_no():
    order = _limit_order_payload(side="no", type="market")
    del order["yes_price"]
    result = validators.validate_cancel_order_response(order)
    assert result["side"] == "no"
    assert "no_price" not in result


@pytest.mark.parametrize(
    "modifier, message",
    [
        (lambda o: o.pop("order_id"), "Missing required fields"),
        (lambda o: o.__setitem__("status", "open"), "Expected status"),
        (lambda o: o.__setitem__("side", "maybe"), "Invalid side"),
        (lambda o: o.__setitem__("type", "weird"), "Invalid type"),
        (lambda o: o.__setitem__("action", "hold"), "Invalid action"),
        (lambda o: o.__setitem__("count", 0), "must be positive"),
        (lambda o: o.__setitem__("created_time", "bad"), "Invalid created_time"),
        (lambda o: (o.__setitem__("type", "limit"), o.pop("yes_price")), "must have yes_price"),
        (lambda o: o.__setitem__("yes_price", 120), "must be between 1-99"),
    ],
)
def test_validate_cancel_order_response_errors(modifier, message):
    order = _limit_order_payload()
    modifier(order)
    with pytest.raises(ValueError, match=message):
        validators.validate_cancel_order_response(order)


def test_validate_exchange_status_response_success():
    result = validators.validate_exchange_status_response(
        {"trading_active": True, "exchange_active": False}
    )
    assert result["exchange_active"] is False


def test_validate_exchange_status_response_errors():
    with pytest.raises(ValueError, match="Empty response"):
        validators.validate_exchange_status_response({})

    with pytest.raises(ValueError, match="Missing required fields"):
        validators.validate_exchange_status_response({"trading_active": True})

    with pytest.raises(TypeError, match="must be boolean"):
        validators.validate_exchange_status_response(
            {"trading_active": "yes", "exchange_active": True}
        )
