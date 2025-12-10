"""
Metric Display Module

Handles display of quality metrics, timing summaries, and statistical data.
"""

from typing import Iterable, Optional, Tuple

from common.exceptions import DataError

# Constants
_BASE_GAP_TOLERANCE_MS = 5.0
_RELATIVE_GAP_TOLERANCE = 0.003  # 0.3%
_PIPELINE_OVERHEAD_LABEL = "Pipeline Overhead"
_MAX_RELATIVE_GAP_FOR_PASS = 0.3  # Allow up to 30% untracked overhead before failing


def format_surface_quality(r_squared_values: list, expiry_labels: list) -> str:
    """Format surface quality metrics for display."""
    if not (r_squared_values and expiry_labels):
        raise DataError("Surface quality metrics require non-empty data inputs")

    lines = ["📊 Surface quality metrics:"]
    for label, r_sq in zip(expiry_labels, r_squared_values):
        lines.append(f"   R²={r_sq:.2f} ({label})")

    overall_r_squared = sum(r_squared_values) / len(r_squared_values)
    lines.append(f"   Overall surface R²={overall_r_squared:.2f}")

    return "\n".join(lines)


def format_error_confidence_summary(
    avg_error: Optional[float], avg_confidence: Optional[float]
) -> str:
    """Format error and confidence summary."""
    lines = []

    if avg_error is not None:
        lines.append(f"📊 Overall Average Error: {avg_error:.1f}%")
    else:
        lines.append("📊 Overall Average Error: N/A")

    if avg_confidence is not None:
        lines.append(f"📊 Overall Average Confidence: {avg_confidence:.1f}%")
    else:
        lines.append("📊 Overall Average Confidence: N/A")

    return "\n".join(lines)


def format_timing_summary(
    phase_timings: Iterable[Tuple[str, float]], sum_seconds: float, total_seconds: float
) -> str:
    """Render a structured execution timing summary with millisecond precision."""
    phase_timings = list(phase_timings)
    if not phase_timings:
        return ""

    header_line = "=" * 70
    divider_line = "-" * 70

    name_width = (
        max(
            max(len(name) for name, _ in phase_timings),
            len(_PIPELINE_OVERHEAD_LABEL),
        )
        + 2
    )

    lines = [header_line, "📊 EXECUTION TIMING SUMMARY", header_line]

    for name, duration_seconds in phase_timings:
        duration_ms = duration_seconds * 1000.0
        lines.append(f"⏱️  {name:<{name_width}} : {duration_ms:9.2f}ms")

    sum_ms = sum_seconds * 1000.0
    total_ms = total_seconds * 1000.0
    dynamic_tolerance = max(_BASE_GAP_TOLERANCE_MS, total_ms * _RELATIVE_GAP_TOLERANCE)

    residual_ms = total_ms - sum_ms
    raw_gap_ms = abs(residual_ms)

    if residual_ms > dynamic_tolerance:
        lines.append(f"⏱️  {_PIPELINE_OVERHEAD_LABEL:<{name_width}} : {residual_ms:9.2f}ms")
        sum_ms += residual_ms
        residual_ms = total_ms - sum_ms

    gap_ms = raw_gap_ms

    lines.append(divider_line)
    lines.append(f"📈 Sum of all phases:                    {sum_ms:9.2f}ms")
    lines.append(f"🎯 Total end-to-end time:                {total_ms:9.2f}ms")

    relative_gap = (gap_ms / total_ms) if total_ms else 0.0
    should_fail = gap_ms > dynamic_tolerance and relative_gap > _MAX_RELATIVE_GAP_FOR_PASS

    if not should_fail:
        status = "PASSED"
        status_icon = "✅"
    else:
        status = "FAILED"
        status_icon = "⚠️"
    lines.append(
        f"{status_icon} Timing verification:                  {status} (gap: {gap_ms:.2f}ms "
        f"tolerance: {dynamic_tolerance:.2f}ms)"
    )
    lines.append(header_line)

    return "\n".join(lines)
