"""Stack trace utilities for session debugging."""

import traceback


def get_stack_trace() -> str:
    """
    Get current stack trace for debugging.

    Returns:
        Formatted stack trace string
    """
    return "".join(traceback.format_stack()[-3:-1])  # Skip this method and caller
