"""Shared status line output helper to keep formatting consistent."""

from src.common.output_utils import output


def emit_status_line(message: str = "", *, log: bool = True) -> None:
    """Print a status line to console with consistent flags."""
    output(message, headers=False, log=log, plain_log=log)


__all__ = ["emit_status_line"]
