"""Errors for distributed locking."""


class LockUnavailableError(Exception):
    """Raised when a distributed lock cannot be acquired."""

    pass
