import pytest

from src.common.redis_schema import kalshi as redis_kalshi
from src.common.redis_schema.markets import KalshiMarketCategory, KalshiMarketKey


def test_describe_kalshi_ticker_known_prefix() -> None:
    descriptor = redis_kalshi.describe_kalshi_ticker("kxbtc-dec25")

    assert descriptor.category is KalshiMarketCategory.BINARY
    assert descriptor.ticker == "KXBTC-DEC25"
    assert descriptor.underlying == "KXBTC"
    assert descriptor.expiry_token == "DEC25"
    assert (
        descriptor.key
        == KalshiMarketKey(category=KalshiMarketCategory.BINARY, ticker="KXBTC-DEC25").key()
    )


def test_describe_kalshi_ticker_custom_category() -> None:
    descriptor = redis_kalshi.describe_kalshi_ticker(" custom-market ")

    assert descriptor.category is KalshiMarketCategory.CUSTOM
    assert descriptor.underlying is None
    assert descriptor.expiry_token is None


def test_describe_kalshi_ticker_rejects_empty() -> None:
    with pytest.raises(ValueError):
        redis_kalshi.describe_kalshi_ticker("")


def test_build_and_parse_kalshi_market_key_roundtrip() -> None:
    descriptor = redis_kalshi.describe_kalshi_ticker("kxeth-jan26")
    key = redis_kalshi.build_kalshi_market_key("kxeth-jan26")

    assert key == descriptor.key

    parsed = redis_kalshi.parse_kalshi_market_key(key)
    assert parsed == descriptor


@pytest.mark.parametrize(
    "key",
    [
        "markets:kalshi:binary",  # missing ticker
        "reference:kalshi:binary:kxbtc-dec25",  # wrong namespace
    ],
)
def test_parse_kalshi_market_key_invalid_formats(key: str) -> None:
    with pytest.raises(ValueError):
        redis_kalshi.parse_kalshi_market_key(key)


def test_parse_kalshi_market_key_rejects_mismatched_normalization() -> None:
    key = "markets:kalshi:binary:KXBTC-OTHER"

    with pytest.raises(ValueError):
        redis_kalshi.parse_kalshi_market_key(key)


def test_is_supported_kalshi_ticker() -> None:
    assert redis_kalshi.is_supported_kalshi_ticker("KXBTC-DEC25") is True
    assert redis_kalshi.is_supported_kalshi_ticker("eth-jan26") is True
    assert redis_kalshi.is_supported_kalshi_ticker("unsupported") is False
    assert redis_kalshi.is_supported_kalshi_ticker("  ") is False
