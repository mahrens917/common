"""Sequence tracking state management"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class TrackingState:
    """Manages sequence tracking state for subscriptions"""

    def __init__(self, service_name: str):
        """
        Initialize tracking state

        Args:
            service_name: Name of the service for logging
        """
        self.service_name = service_name
        self.sid_to_last_seq: Dict[int, int] = {}
        self.sid_to_gap_count: Dict[int, int] = {}

    def initialize_sid(self, sid: int, seq: int) -> None:
        """
        Initialize sequence tracking for a new SID

        Args:
            sid: Subscription ID
            seq: Initial sequence number
        """
        self.sid_to_last_seq[sid] = seq
        self.sid_to_gap_count[sid] = 0
        logger.debug(f"{self.service_name} sequence validator: Initialized SID {sid} with seq {seq}")

    def update_sequence(self, sid: int, seq: int) -> None:
        """
        Update sequence number for SID

        Args:
            sid: Subscription ID
            seq: New sequence number
        """
        self.sid_to_last_seq[sid] = seq

    def increment_gap_count(self, sid: int, gap_size: int) -> None:
        """
        Increment gap count for SID

        Args:
            sid: Subscription ID
            gap_size: Size of the gap to add
        """
        self.sid_to_gap_count[sid] += gap_size

    def reset_gap_count(self, sid: int) -> None:
        """
        Reset gap count for SID

        Args:
            sid: Subscription ID
        """
        self.sid_to_gap_count[sid] = 0

    def get_last_seq(self, sid: int) -> int:
        """Get last sequence number for SID"""
        return self.sid_to_last_seq[sid]

    def get_gap_count(self, sid: int) -> int:
        """Get gap count for SID"""
        return self.sid_to_gap_count[sid]

    def has_sid(self, sid: int) -> bool:
        """Check if SID is being tracked"""
        return sid in self.sid_to_last_seq

    def reset_sid(self, sid: int) -> None:
        """
        Reset sequence tracking for a subscription ID

        Args:
            sid: Subscription ID to reset
        """
        if sid in self.sid_to_last_seq:
            del self.sid_to_last_seq[sid]
            del self.sid_to_gap_count[sid]
            logger.debug(f"{self.service_name} sequence validator: Reset SID {sid}")

    def reset_all(self) -> None:
        """Reset all sequence tracking"""
        self.sid_to_last_seq.clear()
        self.sid_to_gap_count.clear()
        logger.debug(f"{self.service_name} sequence validator: Reset all SIDs")
