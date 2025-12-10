"""Tests for message counter."""

from __future__ import annotations

from common.metadata_store_auto_updater_helpers.time_window_updater_helpers.message_counter import (
    count_messages_in_windows,
)


class TestCountMessagesInWindows:
    """Tests for count_messages_in_windows function."""

    def test_counts_messages_in_last_hour(self) -> None:
        """Counts messages within last hour window."""
        hash_data = {
            "2025-01-15 11:30:00": "5",  # Within hour
            "2025-01-15 10:00:00": "10",  # Outside hour
        }

        hour, sixty_five, sixty = count_messages_in_windows(
            hash_data,
            "2025-01-15 11:00:00",  # hour ago
            "2025-01-15 10:55:00",  # 65 min ago
            "2025-01-15 11:59:00",  # 60 sec ago
        )

        assert hour == 5

    def test_counts_messages_in_65_minute_window(self) -> None:
        """Counts messages within 65 minute window."""
        hash_data = {
            "2025-01-15 11:30:00": "5",
            "2025-01-15 11:00:00": "3",
        }

        _, sixty_five, _ = count_messages_in_windows(
            hash_data,
            "2025-01-15 11:20:00",
            "2025-01-15 10:55:00",  # 65 min ago - both should be counted
            "2025-01-15 11:59:00",
        )

        assert sixty_five == 8

    def test_counts_messages_in_60_second_window(self) -> None:
        """Counts messages within 60 second window."""
        hash_data = {
            "2025-01-15 12:00:00": "2",
            "2025-01-15 11:59:30": "1",  # Within 60 seconds
            "2025-01-15 11:58:00": "10",  # Outside 60 seconds
        }

        _, _, sixty = count_messages_in_windows(
            hash_data,
            "2025-01-15 11:00:00",
            "2025-01-15 10:55:00",
            "2025-01-15 11:59:00",  # 60 sec ago
        )

        assert sixty == 3  # 2 + 1

    def test_handles_bytes_keys_and_values(self) -> None:
        """Handles bytes-encoded keys and values from Redis."""
        hash_data = {
            b"2025-01-15 12:00:00": b"5",
        }

        hour, sixty_five, sixty = count_messages_in_windows(
            hash_data,
            "2025-01-15 11:00:00",
            "2025-01-15 10:55:00",
            "2025-01-15 11:59:00",
        )

        assert hour == 5
        assert sixty_five == 5
        assert sixty == 5

    def test_handles_invalid_message_count(self) -> None:
        """Treats invalid message counts as zero."""
        hash_data = {
            "2025-01-15 12:00:00": "not_a_number",
            "2025-01-15 12:00:01": "5",
        }

        hour, _, _ = count_messages_in_windows(
            hash_data,
            "2025-01-15 11:00:00",
            "2025-01-15 10:55:00",
            "2025-01-15 11:59:00",
        )

        assert hour == 5  # Only the valid one

    def test_handles_empty_hash_data(self) -> None:
        """Returns zeros for empty hash data."""
        hour, sixty_five, sixty = count_messages_in_windows(
            {},
            "2025-01-15 11:00:00",
            "2025-01-15 10:55:00",
            "2025-01-15 11:59:00",
        )

        assert hour == 0
        assert sixty_five == 0
        assert sixty == 0

    def test_accumulates_across_multiple_entries(self) -> None:
        """Accumulates counts from multiple entries in window."""
        hash_data = {
            "2025-01-15 12:00:00": "1",
            "2025-01-15 12:00:01": "2",
            "2025-01-15 12:00:02": "3",
        }

        hour, _, _ = count_messages_in_windows(
            hash_data,
            "2025-01-15 11:00:00",
            "2025-01-15 10:55:00",
            "2025-01-15 11:59:00",
        )

        assert hour == 6
