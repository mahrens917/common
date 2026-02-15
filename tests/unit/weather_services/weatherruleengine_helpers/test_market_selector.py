"""Tests for weather_services.weatherruleengine_helpers.market_selector module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.weather_services.weatherruleengine_helpers.market_selector import (
    MarketSelector,
)


class TestMarketSelectorInit:
    """Tests for MarketSelector initialization."""

    def test_stores_repository(self) -> None:
        """Test stores repository reference."""
        mock_repo = MagicMock()
        selector = MarketSelector(mock_repo)

        assert selector._repository is mock_repo


class TestMarketSelectorSelectTargetMarket:
    """Tests for select_target_market method."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_markets(self) -> None:
        """Test returns None when no markets found."""
        mock_repo = MagicMock()

        async def empty_iter(*_args, **_kwargs):
            for _ in []:
                yield

        mock_repo.iter_city_markets = empty_iter

        selector = MarketSelector(mock_repo)
        result = await selector.select_target_market("MIA", day_code="25DEC26", max_temp_f=75.0)

        assert result is None

    @pytest.mark.asyncio
    async def test_selects_greater_market(self) -> None:
        """Test selects greater strike type market."""
        mock_repo = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.strike_type = "greater"

        async def iter_markets(*args, **kwargs):
            yield mock_snapshot

        mock_repo.iter_city_markets = iter_markets

        with patch("common.weather_services.weatherruleengine_helpers.market_selector.MarketEvaluator") as mock_evaluator:
            mock_evaluator.extract_strike_values.return_value = (None, 72.0)
            mock_evaluator.evaluate_greater_market.return_value = True

            selector = MarketSelector(mock_repo)
            result = await selector.select_target_market("MIA", day_code=None, max_temp_f=75.0)

            assert result is mock_snapshot
            mock_evaluator.evaluate_greater_market.assert_called_once()

    @pytest.mark.asyncio
    async def test_selects_between_market(self) -> None:
        """Test selects between strike type market."""
        mock_repo = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.strike_type = "between"

        async def iter_markets(*args, **kwargs):
            yield mock_snapshot

        mock_repo.iter_city_markets = iter_markets

        with patch("common.weather_services.weatherruleengine_helpers.market_selector.MarketEvaluator") as mock_evaluator:
            mock_evaluator.extract_strike_values.return_value = (78.0, 72.0)
            mock_evaluator.evaluate_between_market.return_value = (mock_snapshot, 78.0, 72.0)

            selector = MarketSelector(mock_repo)
            result = await selector.select_target_market("MIA", day_code=None, max_temp_f=75.0)

            assert result is mock_snapshot
            mock_evaluator.evaluate_between_market.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_non_matching_greater_market(self) -> None:
        """Test skips greater market that doesn't match."""
        mock_repo = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.strike_type = "greater"

        async def iter_markets(*args, **kwargs):
            yield mock_snapshot

        mock_repo.iter_city_markets = iter_markets

        with patch("common.weather_services.weatherruleengine_helpers.market_selector.MarketEvaluator") as mock_evaluator:
            mock_evaluator.extract_strike_values.return_value = (None, 72.0)
            mock_evaluator.evaluate_greater_market.return_value = False

            selector = MarketSelector(mock_repo)
            result = await selector.select_target_market("MIA", day_code=None, max_temp_f=70.0)

            assert result is None

    @pytest.mark.asyncio
    async def test_passes_day_code_to_repository(self) -> None:
        """Test passes day_code to repository."""
        mock_repo = MagicMock()
        called_kwargs = {}

        async def iter_markets(*_args, **kwargs):
            nonlocal called_kwargs
            called_kwargs = kwargs
            for _ in []:
                yield

        mock_repo.iter_city_markets = iter_markets

        selector = MarketSelector(mock_repo)
        await selector.select_target_market("NYC", day_code="25DEC31", max_temp_f=40.0)

        assert called_kwargs.get("day_code") == "25DEC31"

    @pytest.mark.asyncio
    async def test_evaluates_multiple_markets(self) -> None:
        """Test evaluates multiple markets and selects best."""
        mock_repo = MagicMock()
        snapshot1 = MagicMock()
        snapshot1.strike_type = "greater"
        snapshot2 = MagicMock()
        snapshot2.strike_type = "greater"

        async def iter_markets(*args, **kwargs):
            yield snapshot1
            yield snapshot2

        mock_repo.iter_city_markets = iter_markets

        with patch("common.weather_services.weatherruleengine_helpers.market_selector.MarketEvaluator") as mock_evaluator:
            mock_evaluator.extract_strike_values.side_effect = [(None, 70.0), (None, 73.0)]
            mock_evaluator.evaluate_greater_market.side_effect = [True, True]

            selector = MarketSelector(mock_repo)
            result = await selector.select_target_market("MIA", day_code=None, max_temp_f=75.0)

            # Should have evaluated both
            assert mock_evaluator.evaluate_greater_market.call_count == 2

    @pytest.mark.asyncio
    async def test_selects_less_market(self) -> None:
        """Test selects less strike type market."""
        mock_repo = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.strike_type = "less"

        async def iter_markets(*args, **kwargs):
            yield mock_snapshot

        mock_repo.iter_city_markets = iter_markets

        with patch("common.weather_services.weatherruleengine_helpers.market_selector.MarketEvaluator") as mock_evaluator:
            mock_evaluator.extract_strike_values.return_value = (78.0, None)
            mock_evaluator.evaluate_less_market.return_value = True

            selector = MarketSelector(mock_repo)
            result = await selector.select_target_market("MIA", day_code=None, max_temp_f=75.0)

            assert result is mock_snapshot
            mock_evaluator.evaluate_less_market.assert_called_once()

    @pytest.mark.asyncio
    async def test_between_wins_over_greater(self) -> None:
        """Test between market wins over qualifying greater market."""
        mock_repo = MagicMock()
        greater_snapshot = MagicMock()
        greater_snapshot.strike_type = "greater"
        between_snapshot = MagicMock()
        between_snapshot.strike_type = "between"

        async def iter_markets(*args, **kwargs):
            yield greater_snapshot
            yield between_snapshot

        mock_repo.iter_city_markets = iter_markets

        with patch("common.weather_services.weatherruleengine_helpers.market_selector.MarketEvaluator") as mock_evaluator:
            mock_evaluator.extract_strike_values.side_effect = [(None, 70.0), (78.0, 72.0)]
            mock_evaluator.evaluate_greater_market.return_value = True
            mock_evaluator.evaluate_between_market.return_value = (between_snapshot, 78.0, 72.0)

            selector = MarketSelector(mock_repo)
            result = await selector.select_target_market("MIA", day_code=None, max_temp_f=75.0)

            assert result is between_snapshot
