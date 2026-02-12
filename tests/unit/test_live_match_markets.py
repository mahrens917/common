"""Tests for scripts/live_match_markets.py.

Pure-function unit tests.  The script under test has deep import chains
(KalshiStore, PolyStore, redis_protocol) that require live Redis.
We use ``importlib.util`` to load only the script file and inject
lightweight stubs for the heavy dependencies it imports at module level.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Load the script in isolation.  We stub out only the specific imports that
# ``live_match_markets.py`` performs at module level so that no Redis or
# network connection is needed.
# ---------------------------------------------------------------------------
_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "live_match_markets.py"

# Pre-create stub modules for imports that the script triggers
_stubs: dict[str, types.ModuleType] = {}


def _stub(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    _stubs[name] = mod
    return mod


# Replicate the MarketExtraction dataclass so we don't trigger
# common.llm_extractor.__init__ (which pulls in Redis).
from dataclasses import dataclass


@dataclass(frozen=True)
class MarketExtraction:
    """Minimal copy for testing."""

    market_id: str
    platform: str
    category: str
    underlying: str
    strike_type: str | None = None
    floor_strike: float | None = None
    cap_strike: float | None = None
    close_time: str | None = None


# scripts.match_display — imported by live_match_markets
_match_display = _stub("scripts.match_display")
_match_display.print_field_extraction_results = MagicMock()
_match_display.print_field_match_results = MagicMock()
_match_display.print_near_misses = MagicMock()

# common.llm_extractor — stub to avoid redis_protocol chain
_llm_extractor = _stub("common.llm_extractor")
_llm_extractor.MarketExtraction = MarketExtraction
_llm_extractor.PolyExtractor = MagicMock()

# common.redis_protocol.kalshi_store — imported for KalshiStore
_kalshi_store = _stub("common.redis_protocol.kalshi_store")
_kalshi_store.KalshiStore = MagicMock()

# poly.store.poly_store — dynamically imported by the script
_poly_store = _stub("poly")
_poly_store_sub = _stub("poly.store")
_poly_store_mod = _stub("poly.store.poly_store")
_poly_store_mod.PolyStore = MagicMock()

# Ensure the ``scripts`` package itself exists
if "scripts" not in sys.modules:
    _scripts_pkg = types.ModuleType("scripts")
    _scripts_pkg.__path__ = [str(Path(__file__).resolve().parents[2] / "scripts")]
    sys.modules["scripts"] = _scripts_pkg

# Insert stubs BEFORE the import
_originals = {}
for name, mod in _stubs.items():
    _originals[name] = sys.modules.get(name)
    sys.modules[name] = mod

# Now load the script as a module
_spec = importlib.util.spec_from_file_location("scripts.live_match_markets", _SCRIPT)
_module = importlib.util.module_from_spec(_spec)
sys.modules["scripts.live_match_markets"] = _module
_spec.loader.exec_module(_module)

# Restore original modules (if any) so other tests are unaffected
for name, orig in _originals.items():
    if orig is None:
        sys.modules.pop(name, None)
    else:
        sys.modules[name] = orig

# Re-export the symbols we test
_parse_iso_datetime = _module._parse_iso_datetime
_parse_float = _module._parse_float
_is_effectively_infinite = _module._is_effectively_infinite
_normalize_cap = _module._normalize_cap
_values_within_tolerance = _module._values_within_tolerance
_strikes_overlap = _module._strikes_overlap
_get_kalshi_underlying = _module._get_kalshi_underlying
_poly_market_to_extractor_input = _module._poly_market_to_extractor_input
_compute_expiry_delta_min = _module._compute_expiry_delta_min
_effective_poly_cap = _module._effective_poly_cap
_classify_match = _module._classify_match
_strike_pct_delta = _module._strike_pct_delta
_match_single_kalshi = _module._match_single_kalshi
match_by_category_and_strike = _module.match_by_category_and_strike
fetch_kalshi_from_redis = _module.fetch_kalshi_from_redis
fetch_poly_from_redis = _module.fetch_poly_from_redis
extract_poly_fields = _module.extract_poly_fields
main = _module.main
NEAR_MISS_EXPIRY_LIMIT_MINUTES = _module.NEAR_MISS_EXPIRY_LIMIT_MINUTES


class TestParseIsoDatetime:
    """Tests for _parse_iso_datetime."""

    def test_valid_iso(self):
        result = _parse_iso_datetime("2025-01-15T10:00:00Z")
        assert result.year == 2025
        assert result.month == 1

    def test_empty_string_returns_now(self):
        result = _parse_iso_datetime("")
        assert result.tzinfo == timezone.utc

    def test_invalid_returns_now(self):
        result = _parse_iso_datetime("not-a-date")
        assert result.tzinfo == timezone.utc


class TestParseFloat:
    """Tests for _parse_float."""

    def test_valid_float(self):
        assert _parse_float("3.14") == 3.14

    def test_none(self):
        assert _parse_float(None) is None

    def test_empty_string(self):
        assert _parse_float("") is None

    def test_inf_string(self):
        assert _parse_float("inf") is None

    def test_non_numeric(self):
        assert _parse_float("abc") is None

    def test_int_value(self):
        assert _parse_float(42) == 42.0


class TestIsEffectivelyInfinite:
    """Tests for _is_effectively_infinite."""

    def test_none(self):
        assert _is_effectively_infinite(None) is False

    def test_inf(self):
        assert _is_effectively_infinite(float("inf")) is True

    def test_large_value(self):
        assert _is_effectively_infinite(2e10) is True

    def test_normal_value(self):
        assert _is_effectively_infinite(100.0) is False


class TestNormalizeCap:
    """Tests for _normalize_cap."""

    def test_none_stays_none(self):
        assert _normalize_cap(None) is None

    def test_inf_becomes_none(self):
        assert _normalize_cap(float("inf")) is None

    def test_normal_stays(self):
        assert _normalize_cap(100.0) == 100.0


class TestValuesWithinTolerance:
    """Tests for _values_within_tolerance."""

    def test_equal_values(self):
        assert _values_within_tolerance(100.0, 100.0, 0.001) is True

    def test_within_tolerance(self):
        assert _values_within_tolerance(100.0, 100.05, 0.001) is True

    def test_outside_tolerance(self):
        assert _values_within_tolerance(100.0, 200.0, 0.001) is False


class TestStrikesOverlap:
    """Tests for _strikes_overlap."""

    def test_both_binary(self):
        assert _strikes_overlap(None, None, None, None) is True

    def test_different_shapes(self):
        assert _strikes_overlap(100.0, None, None, 200.0) is False

    def test_matching_floors(self):
        assert _strikes_overlap(100.0, None, 100.0, None) is True

    def test_mismatched_floors(self):
        assert _strikes_overlap(100.0, None, 200.0, None) is False

    def test_matching_caps(self):
        assert _strikes_overlap(None, 100.0, None, 100.0) is True

    def test_inf_caps_normalized(self):
        assert _strikes_overlap(100.0, float("inf"), 100.0, 2e11) is True

    def test_floor_and_cap_match(self):
        assert _strikes_overlap(50.0, 100.0, 50.0, 100.0) is True


class TestStrikePctDelta:
    """Tests for _strike_pct_delta."""

    def test_both_none(self):
        assert _strike_pct_delta(None, None) is None

    def test_one_none(self):
        assert _strike_pct_delta(100.0, None) is None

    def test_both_inf(self):
        assert _strike_pct_delta(float("inf"), float("inf")) == 0.0

    def test_one_inf(self):
        assert _strike_pct_delta(float("inf"), 100.0) is None

    def test_equal_values(self):
        assert _strike_pct_delta(100.0, 100.0) == 0.0

    def test_different_values(self):
        result = _strike_pct_delta(100.0, 110.0)
        assert result is not None
        assert abs(result - 0.0909) < 0.001


class TestGetKalshiUnderlying:
    """Tests for _get_kalshi_underlying."""

    def test_crypto_ticker(self):
        assert _get_kalshi_underlying({"market_ticker": "KXETHD-26JAN2123-T3509.99"}) == "ETH"

    def test_non_kx_ticker(self):
        assert _get_kalshi_underlying({"market_ticker": "ABC-123"}) == ""

    def test_no_ticker(self):
        assert _get_kalshi_underlying({}) == ""


class TestPolyMarketToExtractorInput:
    """Tests for _poly_market_to_extractor_input."""

    def test_basic_fields(self):
        result = _poly_market_to_extractor_input({"condition_id": "abc", "title": "Test"})
        assert result == {"id": "abc", "title": "Test"}

    def test_with_description(self):
        result = _poly_market_to_extractor_input({"condition_id": "abc", "title": "Test", "description": "Desc"})
        assert result["description"] == "Desc"

    def test_with_tokens(self):
        import orjson

        tokens = orjson.dumps([{"outcome": "Yes"}, {"outcome": "No"}])
        result = _poly_market_to_extractor_input({"condition_id": "abc", "title": "Test", "tokens": tokens})
        assert "tokens" in result

    def test_invalid_tokens_ignored(self):
        result = _poly_market_to_extractor_input({"condition_id": "abc", "title": "Test", "tokens": "invalid"})
        assert "tokens" not in result


class TestComputeExpiryDeltaMin:
    """Tests for _compute_expiry_delta_min."""

    def test_same_expiry(self):
        expiry = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        poly = {"end_date": "2025-01-15T12:00:00Z"}
        assert _compute_expiry_delta_min(expiry, poly) == 0.0

    def test_one_hour_apart(self):
        expiry = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        poly = {"end_date": "2025-01-15T13:00:00Z"}
        assert _compute_expiry_delta_min(expiry, poly) == 60.0


class TestEffectivePolyCap:
    """Tests for _effective_poly_cap."""

    def test_cap_present(self):
        fields = MagicMock(cap_strike=100.0, floor_strike=50.0)
        assert _effective_poly_cap(fields) == 100.0

    def test_floor_only_gets_inf(self):
        fields = MagicMock(cap_strike=None, floor_strike=50.0)
        assert _effective_poly_cap(fields) == float("inf")

    def test_no_strikes(self):
        fields = MagicMock(cap_strike=None, floor_strike=None)
        assert _effective_poly_cap(fields) is None


class TestClassifyMatch:
    """Tests for _classify_match."""

    def test_match_appended(self):
        matches, near_misses = [], []
        fields = MagicMock(floor_strike=100.0, cap_strike=None, market_id="p1")
        kalshi_expiry = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        poly_market = {"end_date": "2025-01-15T12:00:00Z"}
        _classify_match({}, fields, poly_market, (100.0, None), kalshi_expiry, matches, near_misses)
        assert len(matches) == 1
        assert len(near_misses) == 0

    def test_near_miss_strike_rejected(self):
        matches, near_misses = [], []
        fields = MagicMock(floor_strike=200.0, cap_strike=None, market_id="p1")
        kalshi_expiry = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        poly_market = {"end_date": "2025-01-15T12:00:00Z"}
        _classify_match({}, fields, poly_market, (100.0, None), kalshi_expiry, matches, near_misses)
        assert len(matches) == 0
        assert len(near_misses) == 1

    def test_near_miss_expiry_within_limit(self):
        matches, near_misses = [], []
        fields = MagicMock(floor_strike=100.0, cap_strike=None, market_id="p1")
        kalshi_expiry = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        poly_market = {"end_date": "2025-01-15T22:00:00Z"}
        _classify_match({}, fields, poly_market, (100.0, None), kalshi_expiry, matches, near_misses)
        assert len(matches) == 0
        assert len(near_misses) == 1

    def test_skip_when_both_rejected_and_too_far(self):
        matches, near_misses = [], []
        fields = MagicMock(floor_strike=200.0, cap_strike=None, market_id="p1")
        kalshi_expiry = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        poly_market = {"end_date": "2025-01-20T12:00:00Z"}
        _classify_match({}, fields, poly_market, (100.0, None), kalshi_expiry, matches, near_misses)
        assert len(matches) == 0
        assert len(near_misses) == 0


class TestMatchByCategoryAndStrike:
    """Tests for match_by_category_and_strike."""

    def test_empty_inputs(self):
        matches, near_misses = match_by_category_and_strike([], [], [])
        assert matches == []
        assert near_misses == []

    def test_no_category_match(self):
        kalshi = [{"category": "sports", "market_ticker": "KXSPT-ABC", "close_time": "2025-01-15T12:00:00Z"}]
        poly_fields = [MarketExtraction(market_id="p1", platform="poly", category="crypto", underlying="ETH", floor_strike=100.0)]
        poly_markets = [{"condition_id": "p1"}]
        matches, _ = match_by_category_and_strike(kalshi, poly_fields, poly_markets)
        assert matches == []

    def test_matching_category_and_strike(self):
        kalshi = [
            {
                "category": "crypto",
                "market_ticker": "KXETHD-26JAN2123-T3509.99",
                "close_time": "2025-01-15T12:00:00Z",
                "floor_strike": "100",
                "cap_strike": None,
            }
        ]
        poly_fields = [MarketExtraction(market_id="p1", platform="poly", category="crypto", underlying="ETH", floor_strike=100.0)]
        poly_markets = [{"condition_id": "p1", "end_date": "2025-01-15T12:00:00Z"}]
        matches, near_misses = match_by_category_and_strike(kalshi, poly_fields, poly_markets)
        assert len(matches) == 1
        assert len(near_misses) == 0


class TestMatchSingleKalshi:
    """Tests for _match_single_kalshi."""

    def test_match_found(self):
        kalshi = {
            "category": "crypto",
            "market_ticker": "KXETHD-26JAN2123-T3509.99",
            "close_time": "2025-01-15T12:00:00Z",
            "floor_strike": "100",
            "cap_strike": None,
        }
        poly_fields = MarketExtraction(market_id="p1", platform="poly", category="crypto", underlying="ETH", floor_strike=100.0)
        poly_by_key = {("crypto", "ETH"): [poly_fields]}
        poly_lookup = {"p1": {"condition_id": "p1", "end_date": "2025-01-15T12:00:00Z"}}
        matches, near_misses = [], []
        _match_single_kalshi(kalshi, poly_by_key, poly_lookup, matches, near_misses)
        assert len(matches) == 1

    def test_no_key_match(self):
        kalshi = {
            "category": "sports",
            "market_ticker": "KXSPT-ABC",
            "close_time": "2025-01-15T12:00:00Z",
            "floor_strike": "100",
            "cap_strike": None,
        }
        poly_by_key = {("crypto", "ETH"): [MagicMock()]}
        matches, near_misses = [], []
        _match_single_kalshi(kalshi, poly_by_key, {}, matches, near_misses)
        assert len(matches) == 0


class TestStrikesOverlapCaps:
    """Additional _strikes_overlap tests for cap mismatch."""

    def test_cap_mismatch(self):
        assert _strikes_overlap(None, 100.0, None, 200.0) is False


class TestFetchKalshiFromRedis:
    """Tests for fetch_kalshi_from_redis."""

    async def test_fetches_markets(self):
        from unittest.mock import AsyncMock

        mock_redis = AsyncMock()
        _kalshi_store.KalshiStore.reset_mock()
        mock_store_instance = AsyncMock()
        mock_store_instance.get_all_markets = AsyncMock(return_value=[{"id": "1"}])
        _kalshi_store.KalshiStore.return_value = mock_store_instance
        result = await fetch_kalshi_from_redis(mock_redis)
        assert result == [{"id": "1"}]


class TestFetchPolyFromRedis:
    """Tests for fetch_poly_from_redis."""

    async def test_fetches_markets(self):
        from unittest.mock import AsyncMock

        mock_redis = AsyncMock()
        _poly_store_mod.PolyStore.reset_mock()
        mock_store_instance = AsyncMock()
        mock_store_instance.get_markets_by_volume = AsyncMock(return_value=[{"id": "p1"}])
        _poly_store_mod.PolyStore.return_value = mock_store_instance
        result = await fetch_poly_from_redis(mock_redis)
        assert result == [{"id": "p1"}]


class TestExtractPolyFields:
    """Tests for extract_poly_fields."""

    async def test_extracts_fields(self):
        from unittest.mock import AsyncMock

        mock_redis = AsyncMock()
        expected = [MarketExtraction(market_id="p1", platform="poly", category="crypto", underlying="ETH")]
        _llm_extractor.PolyExtractor.reset_mock()
        mock_extractor = AsyncMock()
        mock_extractor.extract_batch = AsyncMock(return_value=expected)
        _llm_extractor.PolyExtractor.return_value = mock_extractor
        result = await extract_poly_fields([{"condition_id": "p1", "title": "Test"}], mock_redis)
        assert result == expected

    async def test_respects_limit(self):
        from unittest.mock import AsyncMock

        mock_redis = AsyncMock()
        _llm_extractor.PolyExtractor.reset_mock()
        mock_extractor = AsyncMock()
        mock_extractor.extract_batch = AsyncMock(return_value=[])
        _llm_extractor.PolyExtractor.return_value = mock_extractor
        markets = [{"condition_id": f"p{i}", "title": f"M{i}"} for i in range(10)]
        await extract_poly_fields(markets, mock_redis, limit=3)
        call_args = mock_extractor.extract_batch.call_args
        assert len(call_args[0][0]) == 3


class TestMain:
    """Tests for the main async entry point."""

    async def test_no_kalshi_markets_returns_early(self):
        from unittest.mock import AsyncMock, patch

        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()
        with patch.object(_module, "Redis") as mock_redis_cls:
            mock_redis_cls.from_url.return_value = mock_redis
            with patch.object(_module, "fetch_kalshi_from_redis", new_callable=AsyncMock, return_value=[]):
                with patch.object(_module, "fetch_poly_from_redis", new_callable=AsyncMock, return_value=[{"id": "1"}]):
                    await main("redis://localhost")
        mock_redis.aclose.assert_awaited_once()

    async def test_no_poly_markets_returns_early(self):
        from unittest.mock import AsyncMock, patch

        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()
        with patch.object(_module, "Redis") as mock_redis_cls:
            mock_redis_cls.from_url.return_value = mock_redis
            with patch.object(_module, "fetch_kalshi_from_redis", new_callable=AsyncMock, return_value=[{"id": "1"}]):
                with patch.object(_module, "fetch_poly_from_redis", new_callable=AsyncMock, return_value=[]):
                    await main("redis://localhost")
        mock_redis.aclose.assert_awaited_once()

    async def test_extract_fields_mode(self):
        from unittest.mock import AsyncMock, patch

        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()
        with patch.object(_module, "Redis") as mock_redis_cls:
            mock_redis_cls.from_url.return_value = mock_redis
            with patch.object(_module, "fetch_kalshi_from_redis", new_callable=AsyncMock, return_value=[{"id": "1"}]):
                with patch.object(_module, "fetch_poly_from_redis", new_callable=AsyncMock, return_value=[{"id": "p1"}]):
                    with patch.object(_module, "extract_poly_fields", new_callable=AsyncMock, return_value=[]):
                        await main("redis://localhost", extract_fields=True)

    async def test_default_matching_mode(self):
        from unittest.mock import AsyncMock, patch

        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()
        mock_extractor = AsyncMock()
        mock_extractor.extract_batch = AsyncMock(return_value=[])
        with patch.object(_module, "Redis") as mock_redis_cls:
            mock_redis_cls.from_url.return_value = mock_redis
            with patch.object(_module, "fetch_kalshi_from_redis", new_callable=AsyncMock, return_value=[{"id": "1"}]):
                with patch.object(_module, "fetch_poly_from_redis", new_callable=AsyncMock, return_value=[{"id": "p1"}]):
                    _llm_extractor.PolyExtractor.return_value = mock_extractor
                    await main("redis://localhost")

    async def test_exclude_crypto_mode(self):
        from unittest.mock import AsyncMock, patch

        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()
        fields = [MarketExtraction(market_id="p1", platform="poly", category="crypto", underlying="ETH")]
        mock_extractor = AsyncMock()
        mock_extractor.extract_batch = AsyncMock(return_value=fields)
        with patch.object(_module, "Redis") as mock_redis_cls:
            mock_redis_cls.from_url.return_value = mock_redis
            with patch.object(
                _module,
                "fetch_kalshi_from_redis",
                new_callable=AsyncMock,
                return_value=[{"category": "crypto", "market_ticker": "KXETHD", "close_time": "2025-01-15"}],
            ):
                with patch.object(_module, "fetch_poly_from_redis", new_callable=AsyncMock, return_value=[{"id": "p1"}]):
                    _llm_extractor.PolyExtractor.return_value = mock_extractor
                    await main("redis://localhost", exclude_crypto=True)
