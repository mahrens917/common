"""
Progress Tracker Module

Handles step tracking and timing for user display.
"""

import time


class ProgressTracker:
    """Tracks progress through pipeline steps with timing."""

    def __init__(self):
        self.start_time = None
        self.current_step = 0
        self.total_steps = 6  # Standard pipeline steps

    def start_session(self):
        """Start timing session."""
        self.start_time = time.time()

    def update_step(self, step_num: int):
        """Update current step number."""
        self.current_step = step_num

    def has_started(self) -> bool:
        """Check if timing session has started."""
        return self.start_time is not None

    def reset(self):
        """Reset tracker state."""
        self.start_time = None
        self.current_step = 0
