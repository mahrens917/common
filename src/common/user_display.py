"""
User-Friendly Display Module

Provides clean, emoji-enhanced progress messages for user-facing output.
Separates user display from technical logging.
"""

from typing import Iterable, Optional, Tuple

from common.exceptions import DataError
from common.user_display_helpers.message_formatter import (
    format_completion,
    format_data_loading,
    format_error,
    format_kalshi_targets,
    format_market_updates,
    format_probability_calculation,
    format_service_ready,
    format_startup_message,
    format_step_complete,
    format_step_message,
    format_warning,
)
from common.user_display_helpers.metric_display import (
    format_error_confidence_summary,
    format_surface_quality,
    format_timing_summary,
)
from common.user_display_helpers.progress_tracker import ProgressTracker

# Performance monitoring is no longer available since pdf_generator was removed
PERFORMANCE_MONITORING_AVAILABLE = False


class UserDisplay:
    """
    Handles user-friendly progress display with emojis and clean formatting.
    Separates user-facing messages from technical logging.
    """

    def __init__(self):
        self._tracker = ProgressTracker()

    @property
    def start_time(self) -> Optional[float]:
        """Expose tracker start time for tests."""
        return self._tracker.start_time

    @property
    def current_step(self) -> int:
        """Expose current step for tests."""
        return self._tracker.current_step

    @property
    def total_steps(self) -> int:
        """Expose configured total steps."""
        return self._tracker.total_steps

    def show_startup(self, currencies: list):
        """Show startup message"""
        print(format_startup_message(currencies))
        self._tracker.start_session()

    def show_service_ready(self):
        """Show service initialization complete"""
        print(format_service_ready())

    def show_step(self, step_num: int, description: str, details: str = ""):
        """Show pipeline step progress"""
        self._tracker.update_step(step_num)
        print(format_step_message(step_num, description, details))

    def show_step_complete(self, step_num: int, description: str, result: str = ""):
        """Show step completion"""
        print(format_step_complete(step_num, description, result))

    def show_data_loading(self, currency: str, options_count: int, futures_count: int):
        """Show data loading results"""
        print(format_data_loading(options_count, futures_count))

    def show_surface_quality(self, currency: str, r_squared_values: list, expiry_labels: list):
        """Show surface quality metrics"""
        try:
            output = format_surface_quality(r_squared_values, expiry_labels)
        except DataError as exc:  # policy_guard: allow-silent-handler
            raise ValueError(str(exc)) from exc
        print(output)

    def show_kalshi_targets(self, count: int):
        """Show Kalshi targets loaded"""
        print(format_kalshi_targets(count))

    def show_probability_calculation(self, currency: str, successful: int, total: int):
        """Show probability calculation results"""
        print(format_probability_calculation(currency, successful, total))

    def show_market_updates(self, successful: int, total: int):
        """Show market update results"""
        print(format_market_updates(successful, total))

    def show_completion(self, currency: str, total_calculations: int, processing_time: float):
        """Show completion summary"""
        print(format_completion(currency, total_calculations, processing_time))

    def show_error_confidence_summary(self, avg_error: Optional[float], avg_confidence: Optional[float]):
        """Show error and confidence summary"""
        print(format_error_confidence_summary(avg_error, avg_confidence))

    def show_total_time(self):
        """End performance monitoring session without displaying total time"""
        # Placeholder for future performance monitoring integration
        pass

    def show_timing_summary(
        self,
        phase_timings: Iterable[Tuple[str, float]],
        sum_seconds: float,
        total_seconds: float,
    ) -> None:
        """Render a structured execution timing summary with millisecond precision."""
        output = format_timing_summary(phase_timings, sum_seconds, total_seconds)
        if output:
            print(output)

    def show_error(self, message: str):
        """Show error message"""
        print(format_error(message))

    def show_warning(self, message: str):
        """Show warning message"""
        print(format_warning(message))


# Global instance for easy access
_user_display = UserDisplay()


def get_user_display() -> UserDisplay:
    """Get the global user display instance"""
    return _user_display


def show_progress(step_num: int, description: str, details: str = ""):
    """Convenience function to show progress"""
    _user_display.show_step(step_num, description, details)


def show_completion(step_num: int, description: str, result: str = ""):
    """Convenience function to show completion"""
    _user_display.show_step_complete(step_num, description, result)


def show_startup(currencies: list):
    """Convenience function to show startup"""
    _user_display.show_startup(currencies)


def show_service_ready():
    """Convenience function to show service ready"""
    _user_display.show_service_ready()


def show_error(message: str):
    """Convenience function to show error"""
    _user_display.show_error(message)


def show_warning(message: str):
    """Convenience function to show warning"""
    _user_display.show_warning(message)
