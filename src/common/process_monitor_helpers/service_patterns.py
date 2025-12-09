"""Default process keyword patterns used by the process monitor."""

from __future__ import annotations

from typing import Dict, List

_DEFAULT_PATTERNS: Dict[str, List[str]] = {
    "kalshi": ["src.kalshi"],
    "deribit": ["src.deribit"],
    "monitor": ["src.monitor", "simple_monitor"],
    "cfb": ["src.cfb"],
    "weather": ["src.weather"],
    "tracker": ["src.tracker"],
    "price_alert": ["src.price_alert"],
    "pdf": ["src.pdf"],
}


def get_default_service_patterns() -> Dict[str, List[str]]:
    """Return service keyword patterns used to classify processes."""
    return _DEFAULT_PATTERNS.copy()
