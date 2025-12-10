from datetime import datetime, timezone

from common.redis_protocol.kalshi_store import utils


def test_utils_reexports_normalise_trade_timestamp_string_and_numeric():
    iso = utils.normalise_trade_timestamp("2020-09-13T00:00:00Z")
    assert iso.endswith("+00:00")

    ts = datetime(2020, 9, 13, tzinfo=timezone.utc).timestamp()
    iso_numeric = utils.normalise_trade_timestamp(ts)
    assert iso_numeric.startswith("2020-09-13")
