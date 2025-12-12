"""Background worker management"""

import asyncio
import logging
from typing import Optional

from .request_executor import WORKER_FAILURE_ERRORS, RequestExecutor
from .token_manager import TokenManager

logger = logging.getLogger(__name__)


class RateLimiterWorkerError(RuntimeError):
    """Raised when the background worker encounters an unexpected failure."""


class WorkerManager:
    """Manages background worker task"""

    def __init__(self, token_manager: TokenManager, read_queue: asyncio.Queue, write_queue: asyncio.Queue):
        self.token_manager = token_manager
        self.read_queue = read_queue
        self.write_queue = write_queue
        self.shutdown_event = asyncio.Event()
        self.worker_task: Optional[asyncio.Task] = None
        self.executor = RequestExecutor(self.shutdown_event)

    async def start_worker(self):
        """Start the background worker task"""
        if self.worker_task is not None:
            logger.warning("[KalshiRateLimiter] Worker already running")
            return
        self.worker_task = asyncio.create_task(self._process_requests_worker())
        logger.info("[KalshiRateLimiter] Started request processing worker")

    async def shutdown(self):
        """Shutdown the worker and cleanup resources"""
        if self.worker_task is None:
            return
        self.shutdown_event.set()
        try:
            await asyncio.wait_for(self.worker_task, timeout=5.0)
        except asyncio.TimeoutError as exc:  # policy_guard: allow-silent-handler
            logger.warning("[KalshiRateLimiter] Worker shutdown timed out, cancelling")
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError as cancel_exc:  # policy_guard: allow-silent-handler
                logger.debug("[KalshiRateLimiter] Worker cancelled after timeout", exc_info=cancel_exc)
                self.worker_task = None
                raise RuntimeError("KalshiRateLimiter worker cancelled during shutdown") from cancel_exc
            self.worker_task = None
            raise RuntimeError("KalshiRateLimiter worker shutdown timed out") from exc
        self.worker_task = None
        logger.info("[KalshiRateLimiter] Shutdown complete")

    async def _process_requests_worker(self):
        """Main worker loop that processes queued requests"""
        from .worker_manager_helpers import ErrorClassifier, RequestProcessor

        logger.info("[KalshiRateLimiter] Request processing worker started")

        processor = RequestProcessor(self.token_manager, self.executor)

        while not self.shutdown_event.is_set():
            try:
                self.token_manager.refill_tokens_if_needed()

                # Process read requests if tokens available
                await processor.process_read_request(self.read_queue)

                # Process write requests if tokens available
                await processor.process_write_request(self.write_queue)

                await asyncio.sleep(0.01)

            except asyncio.CancelledError:  # policy_guard: allow-silent-handler
                logger.info("[KalshiRateLimiter] Worker cancelled")
                raise

            except WORKER_FAILURE_ERRORS as exc:
                if ErrorClassifier.is_shutdown_error(exc, self.shutdown_event):
                    logger.info("[KalshiRateLimiter] Worker stopping cleanly: %s", exc, exc_info=True)
                    break

                self.shutdown_event.set()
                logger.error("[KalshiRateLimiter] Worker failed unexpectedly: %s", exc, exc_info=True)
                raise RateLimiterWorkerError("KalshiRateLimiter worker aborted") from exc

        logger.info("[KalshiRateLimiter] Request processing worker stopped")

    async def process_requests_worker(self):
        """
        Public entry point for running the worker loop when tests or adapters need direct control.
        """
        return await self._process_requests_worker()
