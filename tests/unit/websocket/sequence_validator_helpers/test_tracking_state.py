"""Tests for tracking state module."""

from common.websocket.sequence_validator_helpers.tracking_state import (
    TrackingState,
)


class TestTrackingState:
    """Tests for TrackingState class."""

    def test_init_creates_empty_dicts(self) -> None:
        """Initializes with empty tracking dicts."""
        state = TrackingState("test_service")

        assert state.sid_to_last_seq == {}
        assert state.sid_to_gap_count == {}

    def test_initialize_sid_sets_sequence(self) -> None:
        """Initialize SID sets the sequence number."""
        state = TrackingState("test_service")

        state.initialize_sid(123, 100)

        assert state.sid_to_last_seq[123] == 100

    def test_initialize_sid_sets_gap_count_to_zero(self) -> None:
        """Initialize SID sets gap count to zero."""
        state = TrackingState("test_service")

        state.initialize_sid(123, 100)

        assert state.sid_to_gap_count[123] == 0

    def test_update_sequence(self) -> None:
        """Update sequence changes the stored value."""
        state = TrackingState("test_service")
        state.initialize_sid(123, 100)

        state.update_sequence(123, 150)

        assert state.sid_to_last_seq[123] == 150

    def test_increment_gap_count(self) -> None:
        """Increment gap count adds to the count."""
        state = TrackingState("test_service")
        state.initialize_sid(123, 100)

        state.increment_gap_count(123, 5)

        assert state.sid_to_gap_count[123] == 5

    def test_increment_gap_count_accumulates(self) -> None:
        """Increment gap count accumulates."""
        state = TrackingState("test_service")
        state.initialize_sid(123, 100)

        state.increment_gap_count(123, 5)
        state.increment_gap_count(123, 3)

        assert state.sid_to_gap_count[123] == 8

    def test_reset_gap_count(self) -> None:
        """Reset gap count sets count to zero."""
        state = TrackingState("test_service")
        state.initialize_sid(123, 100)
        state.increment_gap_count(123, 10)

        state.reset_gap_count(123)

        assert state.sid_to_gap_count[123] == 0

    def test_get_last_seq(self) -> None:
        """Get last seq returns the stored sequence."""
        state = TrackingState("test_service")
        state.initialize_sid(123, 100)

        result = state.get_last_seq(123)

        assert result == 100

    def test_get_gap_count(self) -> None:
        """Get gap count returns the stored count."""
        state = TrackingState("test_service")
        state.initialize_sid(123, 100)
        state.increment_gap_count(123, 7)

        result = state.get_gap_count(123)

        assert result == 7

    def test_has_sid_returns_false_for_unknown(self) -> None:
        """Has SID returns False for unknown SID."""
        state = TrackingState("test_service")

        result = state.has_sid(999)

        assert result is False

    def test_has_sid_returns_true_for_known(self) -> None:
        """Has SID returns True for known SID."""
        state = TrackingState("test_service")
        state.initialize_sid(123, 100)

        result = state.has_sid(123)

        assert result is True

    def test_reset_sid_removes_tracking(self) -> None:
        """Reset SID removes tracking for the SID."""
        state = TrackingState("test_service")
        state.initialize_sid(123, 100)

        state.reset_sid(123)

        assert 123 not in state.sid_to_last_seq
        assert 123 not in state.sid_to_gap_count

    def test_reset_sid_ignores_unknown_sid(self) -> None:
        """Reset SID does nothing for unknown SID."""
        state = TrackingState("test_service")

        state.reset_sid(999)

    def test_reset_all_clears_all_tracking(self) -> None:
        """Reset all clears all tracking data."""
        state = TrackingState("test_service")
        state.initialize_sid(1, 100)
        state.initialize_sid(2, 200)
        state.initialize_sid(3, 300)

        state.reset_all()

        assert state.sid_to_last_seq == {}
        assert state.sid_to_gap_count == {}
