from common.redis_protocol.kalshi_store.reader_helpers.ticker_parser import TickerParser


def test_normalize_ticker_bytes_and_string():
    assert TickerParser.normalize_ticker(b"abc") == "abc"
    assert TickerParser.normalize_ticker("XYZ") == "XYZ"


def test_is_market_for_currency_matches_patterns():
    """Test that currency matching uses precise KXBTC/KXETH patterns."""
    assert TickerParser.is_market_for_currency("KXBTC-TEST", "btc") is True
    assert TickerParser.is_market_for_currency("KXBTCD-DAILY", "BTC") is True
    assert TickerParser.is_market_for_currency("KXETH-TICKER", "ETH") is True
    # Non-KX prefixed tickers don't match (precise matching)
    assert TickerParser.is_market_for_currency("foo-BTC", "BTC") is False
    assert TickerParser.is_market_for_currency("", "BTC") is False


def test_iter_currency_markets_filters():
    data = [b"KXBTC-TK1", b"OTHER"]
    result = list(TickerParser.iter_currency_markets(data, "btc"))
    assert "KXBTC-TK1" in result
