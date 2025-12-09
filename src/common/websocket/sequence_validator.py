"""
Sequence validation utilities for WebSocket message ordering.

Provides common sequence number validation logic for both Deribit and Kalshi
WebSocket services to ensure message ordering integrity and detect gaps.
"""

from typing import Any, Dict, Optional, Tuple

from .sequence_validator_helpers import SequenceChecker, StatsCalculator, TrackingState


class SequenceValidator:
    """
    Validates WebSocket message sequence numbers to ensure ordering integrity.

    Tracks sequence numbers per subscription ID and detects gaps that may
    indicate message loss or connection issues requiring reconnection.
    """

    def __init__(self, service_name: str, max_gap_tolerance: int = 10):
        """
        Initialize sequence validator.

        Args:
            service_name: Name of the service (e.g., 'deribit', 'kalshi')
            max_gap_tolerance: Maximum sequence gap before raising exception
        """
        self.service_name = service_name
        self.max_gap_tolerance = max_gap_tolerance

        # Initialize helpers
        self._tracking_state = TrackingState(service_name)
        self._sequence_checker = SequenceChecker(
            service_name, max_gap_tolerance, self._tracking_state
        )
        self._stats_calculator = StatsCalculator(
            service_name, max_gap_tolerance, self._tracking_state
        )

    @property
    def sid_to_last_seq(self) -> Dict[int, int]:
        """Expose last sequence tracking for tests."""
        return self._tracking_state.sid_to_last_seq

    @property
    def sid_to_gap_count(self) -> Dict[int, int]:
        """Expose gap tracking for tests."""
        return self._tracking_state.sid_to_gap_count

    def validate_sequence(self, sid: int, seq: int) -> Tuple[bool, Optional[int]]:
        """
        Validate sequence number for a subscription ID.

        Args:
            sid: Subscription ID
            seq: Sequence number

        Returns:
            Tuple of (is_valid, gap_size) where gap_size is None if no gap

        Raises:
            SequenceGapError: If gap exceeds tolerance threshold
        """
        return self._sequence_checker.validate_sequence(sid, seq)

    def reset_sid(self, sid: int) -> None:
        """
        Reset sequence tracking for a subscription ID.

        Args:
            sid: Subscription ID to reset
        """
        self._tracking_state.reset_sid(sid)

    def reset_all(self) -> None:
        """Reset all sequence tracking."""
        self._tracking_state.reset_all()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get sequence validation statistics.

        Returns:
            Dictionary with validation statistics
        """
        return self._stats_calculator.get_stats()

    def log_stats(self) -> None:
        """Log current sequence validation statistics."""
        self._stats_calculator.log_stats()


class DeribitSequenceValidator(SequenceValidator):
    """Deribit-specific sequence validator with custom gap tolerance."""

    def __init__(self, max_gap_tolerance: int = 5):
        """Initialize Deribit sequence validator with tighter gap tolerance."""
        super().__init__("deribit", max_gap_tolerance)


class KalshiSequenceValidator(SequenceValidator):
    """Kalshi-specific sequence validator with custom gap tolerance."""

    def __init__(self, max_gap_tolerance: int = 10):
        """Initialize Kalshi sequence validator with standard gap tolerance."""
        super().__init__("kalshi", max_gap_tolerance)
