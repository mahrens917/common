"""Message counting logic for time windows."""

from __future__ import annotations

from typing import Any, Dict


def count_messages_in_windows(
    hash_data: Dict[Any, Any],
    hour_ago_str: str,
    sixty_five_minutes_ago_str: str,
    sixty_seconds_ago_str: str,
) -> tuple[int, int, int]:
    """
    Count messages in different time windows.

    Args:
        hash_data: Redis hash data
        hour_ago_str: Hour ago threshold
        sixty_five_minutes_ago_str: 65 minutes ago threshold
        sixty_seconds_ago_str: 60 seconds ago threshold

    Returns:
        Tuple of (messages_last_hour, messages_last_65_minutes, messages_last_60_seconds)
    """
    messages_last_hour = 0
    messages_last_65_minutes = 0
    messages_last_60_seconds = 0

    for datetime_str, message_count_str in hash_data.items():
        datetime_str = datetime_str.decode() if isinstance(datetime_str, bytes) else datetime_str
        message_count_str = message_count_str.decode() if isinstance(message_count_str, bytes) else message_count_str

        try:
            message_count = int(message_count_str)
        except (  # policy_guard: allow-silent-handler
            ValueError,
            TypeError,
        ):
            message_count = 0

        if datetime_str >= hour_ago_str:
            messages_last_hour += message_count
        if datetime_str >= sixty_five_minutes_ago_str:
            messages_last_65_minutes += message_count
        if datetime_str >= sixty_seconds_ago_str:
            messages_last_60_seconds += message_count

    return messages_last_hour, messages_last_65_minutes, messages_last_60_seconds
