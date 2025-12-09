"""Tests for stats calculator module."""

from unittest.mock import MagicMock, patch

from src.common.websocket.sequence_validator_helpers.stats_calculator import (
    StatsCalculator,
)


class TestStatsCalculator:
    """Tests for StatsCalculator class."""

    def test_init_stores_parameters(self) -> None:
        """Stores initialization parameters."""
        mock_state = MagicMock()
        calculator = StatsCalculator("deribit", 10, mock_state)

        assert calculator.service_name == "deribit"
        assert calculator.max_gap_tolerance == 10
        assert calculator.tracking_state is mock_state

    def test_get_stats_empty_state(self) -> None:
        """Returns stats for empty state."""
        mock_state = MagicMock()
        mock_state.sid_to_last_seq = {}
        mock_state.sid_to_gap_count = {}
        calculator = StatsCalculator("deribit", 10, mock_state)

        stats = calculator.get_stats()

        assert stats["service_name"] == "deribit"
        assert stats["total_sids"] == 0
        assert stats["total_gaps"] == 0
        assert stats["max_gap_tolerance"] == 10
        assert stats["sids_with_gaps"] == 0

    def test_get_stats_with_data(self) -> None:
        """Returns stats for populated state."""
        mock_state = MagicMock()
        mock_state.sid_to_last_seq = {1: 100, 2: 200, 3: 300}
        mock_state.sid_to_gap_count = {1: 5, 2: 0, 3: 10}
        calculator = StatsCalculator("deribit", 10, mock_state)

        stats = calculator.get_stats()

        assert stats["total_sids"] == 3
        assert stats["total_gaps"] == 15
        assert stats["sids_with_gaps"] == 2
        assert stats["avg_gaps_per_sid"] == 5.0
        assert stats["max_gaps_for_sid"] == 10

    def test_get_stats_no_gaps(self) -> None:
        """Returns stats when no gaps."""
        mock_state = MagicMock()
        mock_state.sid_to_last_seq = {1: 100, 2: 200}
        mock_state.sid_to_gap_count = {1: 0, 2: 0}
        calculator = StatsCalculator("deribit", 10, mock_state)

        stats = calculator.get_stats()

        assert stats["sids_with_gaps"] == 0
        assert stats["max_gaps_for_sid"] == 0

    def test_log_stats_empty_state(self) -> None:
        """Logs debug message for empty state."""
        mock_state = MagicMock()
        mock_state.sid_to_last_seq = {}
        mock_state.sid_to_gap_count = {}
        calculator = StatsCalculator("deribit", 10, mock_state)

        with patch(
            "src.common.websocket.sequence_validator_helpers.stats_calculator.logger"
        ) as mock_logger:
            calculator.log_stats()

            mock_logger.debug.assert_called_once()

    def test_log_stats_with_data(self) -> None:
        """Logs info message with stats."""
        mock_state = MagicMock()
        mock_state.sid_to_last_seq = {1: 100}
        mock_state.sid_to_gap_count = {1: 5}
        calculator = StatsCalculator("deribit", 10, mock_state)

        with patch(
            "src.common.websocket.sequence_validator_helpers.stats_calculator.logger"
        ) as mock_logger:
            calculator.log_stats()

            mock_logger.info.assert_called_once()
