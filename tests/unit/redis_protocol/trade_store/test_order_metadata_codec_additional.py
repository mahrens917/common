from datetime import datetime

import pytest

from src.common.redis_protocol.trade_store.errors import OrderMetadataError
from src.common.redis_protocol.trade_store.order_metadata_codec import OrderMetadataCodec


def _fixed_time():
    return datetime(2024, 1, 1, 12, 0, 0)


def test_order_metadata_codec_encode_and_decode():
    codec = OrderMetadataCodec(_fixed_time)
    payload = codec.encode(
        order_id="ord-1",
        trade_rule="rule",
        trade_reason="because reasons",
        market_category="crypto",
        weather_station="station",
    )
    decoded = codec.decode(payload, order_id="ord-1")
    assert decoded["trade_rule"] == "rule"
    assert decoded["market_category"] == "crypto"
    assert decoded["weather_station"] == "station"

    # decode accepts bytes and rejects missing fields
    payload_bytes = payload.encode("utf-8")
    decoded = codec.decode(payload_bytes, order_id="ord-1")
    assert decoded["trade_reason"] == "because reasons"

    with pytest.raises(OrderMetadataError):
        codec.encode(
            order_id="ord-1",
            trade_rule="",
            trade_reason="because",
            market_category=None,
            weather_station=None,
        )
    with pytest.raises(OrderMetadataError):
        codec.encode(
            order_id="ord-1",
            trade_rule="r",
            trade_reason="",
            market_category=None,
            weather_station=None,
        )
    with pytest.raises(OrderMetadataError):
        codec.encode(
            order_id="ord-1",
            trade_rule="r",
            trade_reason="sh",
            market_category="",
            weather_station=None,
        )

    with pytest.raises(TypeError):
        codec.decode(123, order_id="ord-1")  # type: ignore[arg-type]
    with pytest.raises(OrderMetadataError):
        codec.decode("{}", order_id="ord-1")
    with pytest.raises(OrderMetadataError):
        codec.decode('{"trade_rule":"r","trade_reason":"b"}', order_id="ord-1")
