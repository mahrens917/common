"""
Moon phase calculation utilities.

Calculates current lunar phase and returns appropriate emoji.
"""

from datetime import datetime, timezone


class MoonPhaseCalculator:
    """Calculates moon phase based on lunar cycle."""

    @staticmethod
    def get_moon_phase_emoji() -> str:
        """Get the current moon phase emoji based on the lunar cycle."""
        try:
            # Known new moon date: January 11, 2024 11:57 UTC
            known_new_moon = datetime(2024, 1, 11, 11, 57, tzinfo=timezone.utc)

            # Current UTC time
            now = datetime.now(timezone.utc)

            # Calculate days since known new moon
            days_since_new_moon = (now - known_new_moon).total_seconds() / (24 * 3600)

            # Lunar cycle is approximately 29.53059 days
            lunar_cycle_days = 29.53059

            # Calculate current position in lunar cycle (0-1)
            cycle_position = (days_since_new_moon % lunar_cycle_days) / lunar_cycle_days

            # Convert to phase index (0-7 for 8 phases)
            phase_index = int(cycle_position * 8) % 8

            # Moon phase emojis in order
            moon_phases = [
                "🌑",  # 0: New Moon
                "🌒",  # 1: Waxing Crescent
                "🌓",  # 2: First Quarter
                "🌔",  # 3: Waxing Gibbous
                "🌕",  # 4: Full Moon
                "🌖",  # 5: Waning Gibbous
                "🌗",  # 6: Last Quarter
                "🌘",  # 7: Waning Crescent
            ]

            return moon_phases[phase_index]

        except (  # policy_guard: allow-silent-handler
            ValueError,
            OverflowError,
            ZeroDivisionError,
            TypeError,
        ):
            # Use a generic moon icon if calculation fails
            return "🌙"
