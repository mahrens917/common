"""Progress callback emission utilities."""

import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def emit_progress(callback: Optional[Callable], total_steps: int, current_step: int) -> None:
    """Emit progress callback at appropriate intervals."""
    if not callback or total_steps <= 0:
        return
    interval = max(1, total_steps // 10)
    if current_step % interval == 0 or current_step == total_steps:
        try:
            callback(current_step, total_steps)
        except (TypeError, ValueError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            logger.debug("Progress callback failed; ignoring error: %s", exc, exc_info=True)
