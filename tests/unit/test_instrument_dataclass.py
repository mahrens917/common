from __future__ import annotations

from datetime import datetime, timezone

import pytest

from common.data_models.instrument import Instrument

_CENTS_1692532800 = 1692532800


def test_instrument_validates_name_and_expiry():
    with pytest.raises(ValueError):
        Instrument(instrument_name="", expiry=datetime.now(timezone.utc))

    with pytest.raises(TypeError):
        Instrument(instrument_name="TEST", expiry=object())  # type: ignore[arg-type]


def test_expiry_timestamp_accepts_datetime_and_numeric():
    dt = datetime(2024, 8, 20, 12, tzinfo=timezone.utc)
    inst_dt = Instrument(instrument_name="TEST", expiry=dt)
    assert inst_dt.expiry_timestamp == int(dt.timestamp())

    inst_numeric = Instrument(instrument_name="TEST", expiry=1692532800)
    assert inst_numeric.expiry_timestamp == _CENTS_1692532800


def test_expiry_timestamp_parses_iso_strings():
    inst_iso = Instrument(instrument_name="TEST", expiry="2024-08-20T12:00:00Z")
    assert inst_iso.expiry_timestamp == int(
        datetime(2024, 8, 20, 12, tzinfo=timezone.utc).timestamp()
    )

    with pytest.raises(ValueError):
        _ = Instrument(instrument_name="TEST", expiry="invalid").expiry_timestamp
