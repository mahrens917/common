"""Pipeline execution utilities for market removal operations."""

import logging

from ...error_types import REDIS_ERRORS

logger = logging.getLogger(__name__)


class PipelineExecutor:
    """Executes Redis pipeline operations with error handling."""

    @staticmethod
    async def execute_pipeline(pipe, operation_name: str) -> bool:
        """Execute a Redis pipeline with error handling.

        Args:
            pipe: Redis pipeline to execute
            operation_name: Description of operation for logging

        Returns:
            True if successful, False otherwise
        """
        try:
            await pipe.execute()
        except REDIS_ERRORS as exc:
            logger.error(
                "Error executing pipeline for %s: %s",
                operation_name,
                exc,
                exc_info=True,
            )
            return False
        else:
            return True
