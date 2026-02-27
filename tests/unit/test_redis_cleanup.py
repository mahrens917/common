"""Tests for centralized Redis sorted set cleanup."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_cleanup import (
    _ASOS_RETENTION_SECONDS,
    _DEFAULT_HISTORY_RETENTION_SECONDS,
    _REALTIME_RETENTION_SECONDS,
    _WEATHER_STATION_RETENTION_SECONDS,
    _get_retention_seconds,
    _scan_keys,
    prune_sorted_set_keys,
)
from common.redis_protocol.config import DATA_CUTOFF_SECONDS, HISTORY_TTL_SECONDS

_NOW = 1_700_000_000.0


class TestGetRetentionSeconds:
    """Tests for _get_retention_seconds prefix matching."""

    def test_trades_key(self):
        assert _get_retention_seconds("trades:TICKER-ABC") == DATA_CUTOFF_SECONDS

    def test_deribit_realtime(self):
        assert _get_retention_seconds("history:deribit_realtime") == _REALTIME_RETENTION_SECONDS

    def test_kalshi_realtime(self):
        assert _get_retention_seconds("history:kalshi_realtime") == _REALTIME_RETENTION_SECONDS

    def test_btc_history(self):
        assert _get_retention_seconds("history:btc") == HISTORY_TTL_SECONDS

    def test_eth_history(self):
        assert _get_retention_seconds("history:eth") == HISTORY_TTL_SECONDS

    def test_crossarb_history(self):
        assert _get_retention_seconds("history:crossarb:BTC-ETH") == HISTORY_TTL_SECONDS

    def test_asos_history(self):
        assert _get_retention_seconds("history:asos") == _ASOS_RETENTION_SECONDS

    def test_asos_station_history(self):
        assert _get_retention_seconds("history:asos:KJFK") == _ASOS_RETENTION_SECONDS

    def test_default_history(self):
        """Unmatched history: keys fall through to default retention."""
        assert _get_retention_seconds("history:kalshi") == _DEFAULT_HISTORY_RETENTION_SECONDS
        assert _get_retention_seconds("history:deribit") == _DEFAULT_HISTORY_RETENTION_SECONDS

    def test_weather_station_history(self):
        assert _get_retention_seconds("weather:station_history:KAUS") == _WEATHER_STATION_RETENTION_SECONDS

    def test_balance_key_skipped(self):
        assert _get_retention_seconds("balance:kalshi") is None

    def test_trades_by_date_skipped(self):
        """trades:by_* keys are regular sets, not sorted sets."""
        assert _get_retention_seconds("trades:by_date:2026-02-20") is None
        assert _get_retention_seconds("trades:by_station:KAUS") is None
        assert _get_retention_seconds("trades:by_rule:peak") is None
        assert _get_retention_seconds("trades:by_category:weather") is None

    def test_unknown_key_skipped(self):
        assert _get_retention_seconds("some_other_key") is None

    def test_first_match_wins_over_default(self):
        """history:btc should match btc-specific retention, not default."""
        assert _get_retention_seconds("history:btc") == HISTORY_TTL_SECONDS
        assert _get_retention_seconds("history:btc") != _DEFAULT_HISTORY_RETENTION_SECONDS


class TestScanKeys:
    """Tests for _scan_keys helper."""

    @pytest.mark.asyncio
    async def test_single_page(self):
        redis = MagicMock()
        redis.scan = AsyncMock(return_value=(0, [b"trades:ABC", b"trades:DEF"]))

        result = await _scan_keys(redis, "trades:*")

        assert result == {"trades:ABC", "trades:DEF"}
        redis.scan.assert_awaited_once_with(0, match="trades:*", count=500)

    @pytest.mark.asyncio
    async def test_multi_page(self):
        redis = MagicMock()
        redis.scan = AsyncMock(
            side_effect=[
                (42, [b"trades:A"]),
                (0, [b"trades:B"]),
            ]
        )

        result = await _scan_keys(redis, "trades:*")

        assert result == {"trades:A", "trades:B"}
        assert redis.scan.await_count == 2

    @pytest.mark.asyncio
    async def test_string_keys(self):
        redis = MagicMock()
        redis.scan = AsyncMock(return_value=(0, ["history:kalshi"]))

        result = await _scan_keys(redis, "history:*")

        assert result == {"history:kalshi"}

    @pytest.mark.asyncio
    async def test_empty_result(self):
        redis = MagicMock()
        redis.scan = AsyncMock(return_value=(0, []))

        result = await _scan_keys(redis, "trades:*")

        assert result == set()


class TestPruneSortedSetKeys:
    """Tests for prune_sorted_set_keys."""

    def _make_redis(self, scan_results=None, prune_results=None, card_results=None):
        redis = MagicMock()
        redis.scan = AsyncMock(return_value=(0, scan_results or []))

        prune_pipe = MagicMock()
        prune_pipe.zremrangebyscore = MagicMock()
        prune_pipe.execute = AsyncMock(return_value=prune_results or [])

        card_pipe = MagicMock()
        card_pipe.zcard = MagicMock()
        card_pipe.execute = AsyncMock(return_value=card_results or [])

        delete_pipe = MagicMock()
        delete_pipe.delete = MagicMock()
        delete_pipe.execute = AsyncMock(return_value=[])

        redis.pipeline = MagicMock(side_effect=[prune_pipe, card_pipe, delete_pipe])

        return redis, prune_pipe, card_pipe, delete_pipe

    @pytest.mark.asyncio
    async def test_no_keys_found(self):
        redis = MagicMock()
        redis.scan = AsyncMock(return_value=(0, []))

        result = await prune_sorted_set_keys(redis, _NOW)

        assert result == 0

    @pytest.mark.asyncio
    async def test_prunes_with_correct_cutoff(self):
        redis, prune_pipe, card_pipe, _ = self._make_redis(
            scan_results=[b"trades:ABC"],
            prune_results=[3],
            card_results=[5],
        )

        result = await prune_sorted_set_keys(redis, _NOW)

        assert result == 1
        prune_pipe.zremrangebyscore.assert_called_once_with("trades:ABC", "-inf", str(_NOW - DATA_CUTOFF_SECONDS))

    @pytest.mark.asyncio
    async def test_deletes_empty_keys(self):
        redis, prune_pipe, card_pipe, delete_pipe = self._make_redis(
            scan_results=[b"history:kalshi"],
            prune_results=[2],
            card_results=[0],
        )

        result = await prune_sorted_set_keys(redis, _NOW)

        assert result == 2  # 1 pruned + 1 deleted
        delete_pipe.delete.assert_called_once_with("history:kalshi")

    @pytest.mark.asyncio
    async def test_skips_balance_keys(self):
        redis = MagicMock()
        redis.scan = AsyncMock(
            side_effect=[
                (0, []),  # trades:*
                (0, []),  # history:*
                (0, []),  # weather:station_history:*
            ]
        )

        result = await prune_sorted_set_keys(redis, _NOW)

        assert result == 0

    @pytest.mark.asyncio
    async def test_no_deletes_when_keys_nonempty(self):
        redis, prune_pipe, card_pipe, delete_pipe = self._make_redis(
            scan_results=[b"trades:XYZ"],
            prune_results=[0],
            card_results=[10],
        )

        result = await prune_sorted_set_keys(redis, _NOW)

        assert result == 0
        # delete pipeline should not be created (only 2 pipelines: prune + card)
        assert redis.pipeline.call_count == 2

    @pytest.mark.asyncio
    async def test_multiple_keys_mixed_results(self):
        redis = MagicMock()
        redis.scan = AsyncMock(
            side_effect=[
                (0, [b"trades:A"]),
                (0, [b"history:kalshi", b"history:deribit"]),
                (0, [b"weather:station_history:KAUS"]),
            ]
        )

        prune_pipe = MagicMock()
        prune_pipe.zremrangebyscore = MagicMock()
        prune_pipe.execute = AsyncMock(return_value=[5, 0, 3, 1])

        card_pipe = MagicMock()
        card_pipe.zcard = MagicMock()
        card_pipe.execute = AsyncMock(return_value=[2, 10, 0, 0])

        delete_pipe = MagicMock()
        delete_pipe.delete = MagicMock()
        delete_pipe.execute = AsyncMock(return_value=[1, 1])

        redis.pipeline = MagicMock(side_effect=[prune_pipe, card_pipe, delete_pipe])

        result = await prune_sorted_set_keys(redis, _NOW)

        # 3 pruned (results 5, 3, 1 are > 0) + 2 deleted (cards 0, 0)
        assert result == 5
        assert delete_pipe.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_scans_all_patterns(self):
        redis = MagicMock()
        redis.scan = AsyncMock(return_value=(0, []))

        await prune_sorted_set_keys(redis, _NOW)

        assert redis.scan.await_count == 3
        patterns = [call.kwargs["match"] for call in redis.scan.call_args_list]
        assert "trades:*" in patterns
        assert "history:*" in patterns
        assert "weather:station_history:*" in patterns

    @pytest.mark.asyncio
    async def test_returns_zero_when_nothing_pruned_or_deleted(self):
        redis, prune_pipe, card_pipe, _ = self._make_redis(
            scan_results=[b"trades:A", b"trades:B"],
            prune_results=[0, 0],
            card_results=[5, 3],
        )

        result = await prune_sorted_set_keys(redis, _NOW)

        assert result == 0

    @pytest.mark.asyncio
    async def test_realtime_key_uses_short_retention(self):
        redis, prune_pipe, card_pipe, _ = self._make_redis(
            scan_results=[b"history:deribit_realtime"],
            prune_results=[1],
            card_results=[5],
        )

        await prune_sorted_set_keys(redis, _NOW)

        prune_pipe.zremrangebyscore.assert_called_once_with("history:deribit_realtime", "-inf", str(_NOW - _REALTIME_RETENTION_SECONDS))

    @pytest.mark.asyncio
    async def test_asos_key_uses_48h_retention(self):
        redis, prune_pipe, card_pipe, _ = self._make_redis(
            scan_results=[b"history:asos:KJFK"],
            prune_results=[1],
            card_results=[5],
        )

        await prune_sorted_set_keys(redis, _NOW)

        prune_pipe.zremrangebyscore.assert_called_once_with("history:asos:KJFK", "-inf", str(_NOW - _ASOS_RETENTION_SECONDS))
