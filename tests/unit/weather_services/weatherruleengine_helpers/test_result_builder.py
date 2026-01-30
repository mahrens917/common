"""Tests for result_builder module."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.weather_services.weatherruleengine_helpers.result_builder import ResultBuilder


@dataclass
class MockMidpointSignalResult:
    """Mock result class for testing."""

    station_icao: str
    market_key: str
    ticker: str
    max_temp_f: float
    explanation: str


@pytest.fixture
def mock_repository() -> MagicMock:
    """Create a mock MarketRepository."""
    repo = MagicMock()
    repo.set_market_fields = AsyncMock()
    return repo


@pytest.fixture
def mock_snapshot() -> MagicMock:
    """Create a mock MarketSnapshot."""
    snapshot = MagicMock()
    snapshot.key = "market_key_123"
    snapshot.ticker = "HIGHNY-24DEC25-T45"
    return snapshot


class TestResultBuilder:
    """Tests for ResultBuilder class."""

    def test_init(self, mock_repository: MagicMock) -> None:
        """Test ResultBuilder initialization."""
        builder = ResultBuilder(mock_repository)
        assert builder._repository is mock_repository

    @pytest.mark.asyncio
    async def test_apply_market_fields_and_return_result(self, mock_repository: MagicMock, mock_snapshot: MagicMock) -> None:
        """Test applying market fields and returning result."""
        builder = ResultBuilder(mock_repository)

        result = await builder.apply_market_fields_and_return_result(
            target_snapshot=mock_snapshot,
            station_icao="KJFK",
            max_temp_f=75.0,
            result_class=MockMidpointSignalResult,
        )

        assert isinstance(result, MockMidpointSignalResult)
        assert result.station_icao == "KJFK"
        assert result.market_key == "market_key_123"
        assert result.ticker == "HIGHNY-24DEC25-T45"
        assert result.max_temp_f == 75.0
        assert "MIDPOINT" in result.explanation
        assert "75.0" in result.explanation

    @pytest.mark.asyncio
    async def test_apply_market_fields_calls_repository(self, mock_repository: MagicMock, mock_snapshot: MagicMock) -> None:
        """Test that repository.set_market_fields is called correctly."""
        builder = ResultBuilder(mock_repository)

        await builder.apply_market_fields_and_return_result(
            target_snapshot=mock_snapshot,
            station_icao="KORD",
            max_temp_f=80.0,
            result_class=MockMidpointSignalResult,
        )

        mock_repository.set_market_fields.assert_called_once()
        call_args = mock_repository.set_market_fields.call_args
        assert call_args[0][0] == "market_key_123"
        fields = call_args[0][1]
        assert fields["t_ask"] == "99"
        assert fields["last_rule_applied"] == "rule_4"
        assert fields["intended_action"] == "BUY"
        assert fields["intended_side"] == "YES"
        assert fields["rule_triggered"] == "rule_4"
        assert "80.0" in fields["weather_explanation"]
