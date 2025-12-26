"""Tests for chart_generator_helpers.kalshi_strike_collector module."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator_helpers.kalshi_strike_collector import KalshiStrikeCollector


class TestKalshiStrikeCollectorInit:
    """Tests for KalshiStrikeCollector initialization."""

    def test_initializes_components(self) -> None:
        """Test initializes all required components."""
        with patch("common.chart_generator_helpers.kalshi_strike_collector.get_schema_config"):
            collector = KalshiStrikeCollector()

            assert collector.schema is not None
            assert collector.hash_decoder is not None
            assert collector.strike_accumulator is not None
            assert collector.expiration_validator is not None
            assert collector.gatherer is not None


class TestKalshiStrikeCollectorGetKalshiStrikesForStation:
    """Tests for get_kalshi_strikes_for_station method."""

    @pytest.mark.asyncio
    async def test_returns_sorted_strikes(self) -> None:
        """Test returns sorted strikes."""
        mock_redis = MagicMock()
        strikes = {75.0, 72.0, 78.0}

        with patch("common.chart_generator_helpers.kalshi_strike_collector.get_schema_config"):
            with patch.object(KalshiStrikeCollector, "__init__", lambda self: None):
                collector = KalshiStrikeCollector.__new__(KalshiStrikeCollector)
                collector.gatherer = MagicMock()
                collector.gatherer.gather_strikes_for_tokens = AsyncMock(return_value=(strikes, True))

                result = await collector.get_kalshi_strikes_for_station(mock_redis, "KMIA", ["MIA"], None)

                assert result == [72.0, 75.0, 78.0]  # Sorted

    @pytest.mark.asyncio
    async def test_raises_on_no_strikes(self) -> None:
        """Test raises RuntimeError when no strikes found."""
        mock_redis = MagicMock()

        with patch("common.chart_generator_helpers.kalshi_strike_collector.get_schema_config"):
            with patch.object(KalshiStrikeCollector, "__init__", lambda self: None):
                collector = KalshiStrikeCollector.__new__(KalshiStrikeCollector)
                collector.gatherer = MagicMock()
                collector.gatherer.gather_strikes_for_tokens = AsyncMock(return_value=(set(), True))

                with pytest.raises(RuntimeError) as exc_info:
                    await collector.get_kalshi_strikes_for_station(mock_redis, "KMIA", ["MIA"], None)

                assert "No Kalshi strikes available" in str(exc_info.value)
                assert "KMIA" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_on_no_primary_found(self) -> None:
        """Test raises RuntimeError when no primary data found."""
        mock_redis = MagicMock()
        strikes = {72.0, 75.0}

        with patch("common.chart_generator_helpers.kalshi_strike_collector.get_schema_config"):
            with patch.object(KalshiStrikeCollector, "__init__", lambda self: None):
                collector = KalshiStrikeCollector.__new__(KalshiStrikeCollector)
                collector.gatherer = MagicMock()
                collector.gatherer.gather_strikes_for_tokens = AsyncMock(return_value=(strikes, False))  # primary_found = False

                with pytest.raises(RuntimeError) as exc_info:
                    await collector.get_kalshi_strikes_for_station(mock_redis, "KJFK", ["NYC"], None)

                assert "No primary Kalshi strike data" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_passes_correct_parameters(self) -> None:
        """Test passes correct parameters to gatherer."""
        mock_redis = MagicMock()
        strikes = {72.0, 75.0}

        with patch("common.chart_generator_helpers.kalshi_strike_collector.get_schema_config"):
            with patch.object(KalshiStrikeCollector, "__init__", lambda self: None):
                collector = KalshiStrikeCollector.__new__(KalshiStrikeCollector)
                collector.gatherer = MagicMock()
                collector.gatherer.gather_strikes_for_tokens = AsyncMock(return_value=(strikes, True))

                await collector.get_kalshi_strikes_for_station(mock_redis, "KMIA", ["MIA", "MIAMI"], "MIA")

                collector.gatherer.gather_strikes_for_tokens.assert_called_once()
                call_kwargs = collector.gatherer.gather_strikes_for_tokens.call_args[1]
                assert call_kwargs["redis_client"] is mock_redis
                assert call_kwargs["tokens"] == ["MIA", "MIAMI"]

    @pytest.mark.asyncio
    async def test_handles_multiple_tokens(self) -> None:
        """Test handles multiple city tokens."""
        mock_redis = MagicMock()
        strikes = {72.0, 75.0, 78.0}

        with patch("common.chart_generator_helpers.kalshi_strike_collector.get_schema_config"):
            with patch.object(KalshiStrikeCollector, "__init__", lambda self: None):
                collector = KalshiStrikeCollector.__new__(KalshiStrikeCollector)
                collector.gatherer = MagicMock()
                collector.gatherer.gather_strikes_for_tokens = AsyncMock(return_value=(strikes, True))

                result = await collector.get_kalshi_strikes_for_station(mock_redis, "KJFK", ["NYC", "NEWYORK", "JFK"], None)

                assert len(result) == 3
                call_kwargs = collector.gatherer.gather_strikes_for_tokens.call_args[1]
                assert call_kwargs["tokens"] == ["NYC", "NEWYORK", "JFK"]
