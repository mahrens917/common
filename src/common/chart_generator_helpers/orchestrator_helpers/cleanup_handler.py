"""Clean up generated chart files on failure."""

import logging
import sys
from typing import List

logger = logging.getLogger("src.monitor.chart_generator")


def cleanup_chart_files(chart_paths: List[str]) -> None:
    """Clean up generated chart files on failure."""
    import os

    os_module = getattr(sys.modules.get("src.monitor.chart_generator"), "os", os)
    for chart_path in chart_paths:
        try:
            if os_module.path.exists(chart_path):
                os_module.unlink(chart_path)
        except OSError:
            logger.warning("Unable to clean up weather chart %s", chart_path)
