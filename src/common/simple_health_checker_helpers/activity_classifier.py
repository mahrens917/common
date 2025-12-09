"""Activity classification for log health checks."""


class ActivityClassifier:
    """Classifies log activity based on time since last log entry."""

    def __init__(self, active_threshold_seconds: int = 3600, fresh_threshold_seconds: int = 86400):
        """
        Initialize activity classifier.

        Args:
            active_threshold_seconds: Threshold for "active" classification (default 1 hour)
            fresh_threshold_seconds: Threshold for "fresh" classification (default 24 hours)
        """
        self.active_threshold_seconds = active_threshold_seconds
        self.fresh_threshold_seconds = fresh_threshold_seconds

    def classify_log_activity(self, seconds_since_last_log: int) -> str:
        """
        Classify log activity level based on time since last log entry.

        Args:
            seconds_since_last_log: Seconds since last log activity

        Returns:
            Activity status string matching desired output format
        """
        if seconds_since_last_log < self.active_threshold_seconds:
            return f"Active ({seconds_since_last_log}s old)"
        elif seconds_since_last_log < self.fresh_threshold_seconds:
            return f"Fresh ({seconds_since_last_log}s old)"
        else:
            return f"Stale ({seconds_since_last_log}s old)"
