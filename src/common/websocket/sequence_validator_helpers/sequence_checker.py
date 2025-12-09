"""Sequence number validation logic"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class SequenceGapError(Exception):
    """Raised when a sequence gap is detected that requires reconnection."""

    pass


class SequenceChecker:
    """Checks sequence numbers and detects gaps"""

    def __init__(self, service_name: str, max_gap_tolerance: int, tracking_state):
        """
        Initialize sequence checker

        Args:
            service_name: Name of the service for logging
            max_gap_tolerance: Maximum sequence gap before raising exception
            tracking_state: TrackingState instance
        """
        self.service_name = service_name
        self.max_gap_tolerance = max_gap_tolerance
        self.tracking_state = tracking_state

    def validate_sequence(self, sid: int, seq: int) -> Tuple[bool, Optional[int]]:
        """
        Validate sequence number for a subscription ID

        Args:
            sid: Subscription ID
            seq: Sequence number

        Returns:
            Tuple of (is_valid, gap_size) where gap_size is None if no gap

        Raises:
            SequenceGapError: If gap exceeds tolerance threshold
        """
        if not self.tracking_state.has_sid(sid):
            # First message for this SID - accept any sequence as starting point
            self.tracking_state.initialize_sid(sid, seq)
            return True, None

        expected_seq = self.tracking_state.get_last_seq(sid) + 1

        if seq == expected_seq:
            # Perfect sequence - reset gap counter
            self.tracking_state.update_sequence(sid, seq)
            self.tracking_state.reset_gap_count(sid)
            return True, None

        elif seq > expected_seq:
            # Gap detected
            gap_size = seq - expected_seq
            self.tracking_state.increment_gap_count(sid, gap_size)

            logger.warning(
                f"{self.service_name} sequence gap detected for SID {sid}: "
                f"expected {expected_seq}, got {seq} (gap: {gap_size}, "
                f"total gaps: {self.tracking_state.get_gap_count(sid)})"
            )

            # Check if gap tolerance exceeded
            if self.tracking_state.get_gap_count(sid) > self.max_gap_tolerance:
                error_msg = (
                    f"{self.service_name} sequence gap tolerance exceeded for SID {sid}: "
                    f"total gaps {self.tracking_state.get_gap_count(sid)} > {self.max_gap_tolerance}"
                )
                logger.error(error_msg)
                raise SequenceGapError(error_msg)

            # Update sequence number to continue processing
            self.tracking_state.update_sequence(sid, seq)
            return False, gap_size

        else:
            # Duplicate or out-of-order message
            logger.warning(
                f"{self.service_name} out-of-order message for SID {sid}: "
                f"expected {expected_seq}, got {seq} (duplicate or reordered)"
            )
            # Don't update sequence number for duplicates
            return False, None
