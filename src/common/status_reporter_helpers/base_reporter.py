"""Shared base reporter utilities."""


class WriterBackedReporter:
    """Provides a writer-backed reporter initialization."""

    def __init__(self, writer):
        self._writer = writer


__all__ = ["WriterBackedReporter"]
