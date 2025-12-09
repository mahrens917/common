"""Session ID generation for tracking purposes."""


class SessionIdGenerator:
    """Generates unique session IDs for tracking."""

    def __init__(self):
        """Initialize ID generator."""
        self._next_session_id = 1

    def generate(self) -> str:
        """
        Generate unique session ID.

        Returns:
            Formatted session ID string
        """
        session_id = f"session_{self._next_session_id:04d}"
        self._next_session_id += 1
        return session_id
