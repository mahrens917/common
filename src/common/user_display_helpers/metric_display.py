"""Timing summary formatting for CI and pipeline metrics."""

from __future__ import annotations

_DYNAMIC_TOLERANCE_MIN_SECONDS = 1.0
_DYNAMIC_TOLERANCE_FRACTION = 0.02


def _format_table(rows: list[tuple[str, float]], total_seconds: float, status: str, note: str) -> str:
    """Format a timing table with phase rows, total, and status line."""
    lines = [f"  {name}: {secs:.3f}s" for name, secs in rows]
    lines.append(f"  TOTAL: {total_seconds:.3f}s")
    status_line = f"STATUS: {status}"
    if note:
        status_line = f"{status_line} ({note})"
    lines.append(status_line)
    return "\n".join(lines)


def format_timing_summary(
    phases: list[tuple[str, float]],
    *,
    sum_seconds: float,
    total_seconds: float,
) -> str:
    """Return a formatted string summarising phase timings vs wall-clock total.

    Flags FAILED when sum_seconds exceeds total_seconds.  For a small positive
    gap relative to the total (dynamic tolerance), reports PASSED with a note.
    For a larger gap, injects a Pipeline Overhead row and reports PASSED.
    """
    gap = total_seconds - sum_seconds

    if gap < 0:
        return _format_table(
            list(phases),
            total_seconds,
            "FAILED",
            f"sum {sum_seconds:.3f}s exceeds total {total_seconds:.3f}s",
        )

    within_tolerance = total_seconds >= _DYNAMIC_TOLERANCE_MIN_SECONDS and gap / total_seconds <= _DYNAMIC_TOLERANCE_FRACTION

    if within_tolerance:
        pct = _DYNAMIC_TOLERANCE_FRACTION * 100
        return _format_table(
            list(phases),
            total_seconds,
            "PASSED",
            f"within dynamic tolerance of {pct:.0f}%",
        )

    rows = list(phases) + [("Pipeline Overhead", gap)]
    return _format_table(rows, total_seconds, "PASSED", "")


__all__ = ["format_timing_summary"]
