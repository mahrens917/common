from __future__ import annotations

from datetime import timezone

from src.common.redis_protocol.trade_store.optional_field_extractor import OptionalFieldExtractor


def test_extract_coerces_optional_fields():
    payload = {
        "weather_station": "STATION-1",
        "last_yes_bid": 100,
        "last_yes_ask": 105,
        "last_price_update": "2025-01-01T12:30:00",
        "settlement_price_cents": "150",
        "settlement_time": "2025-01-02T01:15:00+00:00",
    }

    extracted = OptionalFieldExtractor.extract(payload)
    assert extracted["weather_station"] == "STATION-1"
    assert extracted["last_yes_bid"] == 100
    assert extracted["last_yes_ask"] == 105
    assert extracted["last_price_update"].tzinfo == timezone.utc
    assert extracted["settlement_time"].tzinfo == timezone.utc
    assert extracted["settlement_price_cents"] == 150


def test_extract_handles_missing_values():
    extracted = OptionalFieldExtractor.extract({})
    assert extracted["weather_station"] is None
    assert extracted["last_yes_bid"] is None
    assert extracted["last_yes_ask"] is None
    assert extracted["last_price_update"] is None
    assert extracted["settlement_time"] is None
    assert extracted["settlement_price_cents"] is None
