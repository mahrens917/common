"""
Kalshi API Rate Limiter - Token bucket implementation for API request rate limiting

Provides centralized rate limiting for all Kalshi API requests to ensure compliance
with API limits and eliminate the need for complex exponential backoff logic.
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Dict

from .kalshi_rate_limiter_helpers import (
    MetricsCollector,
)
from .kalshi_rate_limiter_helpers import RateLimiterWorkerError as _WorkerManagerError
from .kalshi_rate_limiter_helpers import (
    RequestEnqueuer,
    StateAccessorsMixin,
    TokenManager,
    WorkerManager,
)

logger = logging.getLogger(__name__)

# Kalshi API rate limits from official documentation
KALSHI_READ_REQUESTS_PER_SECOND = 30
KALSHI_WRITE_REQUESTS_PER_SECOND = 30

# Queue size limits to prevent memory bloat under high load
READ_QUEUE_MAX_SIZE = 100
WRITE_QUEUE_MAX_SIZE = 50


class RequestType(Enum):
    """Classification of API requests for rate limiting purposes"""

    READ = "READ"
    WRITE = "WRITE"


class QueueFullError(Exception):
    """Raised when request queue is at capacity - indicates system overload"""

    pass


# Alias helper exceptions
RateLimiterBugError = _WorkerManagerError
RateLimiterWorkerError = _WorkerManagerError


class KalshiRateLimiter(StateAccessorsMixin):
    """
    Token bucket rate limiter for Kalshi API requests.

    Maintains separate token buckets for READ and WRITE operations
    with automatic token refill every second. Implements fail-fast
    behavior for queue overflow and rate limit violations.
    """

    def __init__(self):
        """Initialize rate limiter with Kalshi API rate limits."""
        # Request queues with size limits
        self.read_queue = asyncio.Queue(maxsize=READ_QUEUE_MAX_SIZE)
        self.write_queue = asyncio.Queue(maxsize=WRITE_QUEUE_MAX_SIZE)

        # Initialize helpers
        self.token_manager = TokenManager(KALSHI_READ_REQUESTS_PER_SECOND, KALSHI_WRITE_REQUESTS_PER_SECOND)
        self.worker_manager = WorkerManager(self.token_manager, self.read_queue, self.write_queue)
        self.metrics_collector = MetricsCollector(self.read_queue, self.write_queue, self.token_manager)
        # Preserve executor implementation for test patches
        self._executor_impl = self.worker_manager.executor.execute_request

        logger.info(
            f"[KalshiRateLimiter] Initialized with {KALSHI_READ_REQUESTS_PER_SECOND} read/sec, "
            f"{KALSHI_WRITE_REQUESTS_PER_SECOND} write/sec limits"
        )

    async def _execute_request(self, request_data: Dict[str, Any]):
        """Execute a request."""
        return await self._executor_impl(request_data)

    async def _process_requests_worker(self):
        """Process requests worker loop."""
        original_executor = self.worker_manager.executor.execute_request

        async def execute_request_wrapper(request_data: Dict[str, Any]):
            return await self._execute_request(request_data)

        self.worker_manager.executor.execute_request = execute_request_wrapper
        try:
            return await self.worker_manager.process_requests_worker()
        finally:
            self.worker_manager.executor.execute_request = original_executor

    async def start_worker(self):
        """Start the background worker task that processes queued requests."""
        await self.worker_manager.start_worker()

    async def shutdown(self):
        """Shutdown the rate limiter and cleanup resources."""
        await self.worker_manager.shutdown()

    async def enqueue_request(self, request_type: RequestType, request_data: Dict[str, Any]) -> str:
        """
        Queue a request for rate-limited execution.

        Args:
            request_type: RequestType.READ or RequestType.WRITE
            request_data: Request parameters including method, path, params, and callbacks

        Returns:
            request_id: Unique identifier for tracking this request

        Raises:
            QueueFullError: If request queue is at capacity
            ValueError: If request_type is invalid
        """
        return await RequestEnqueuer.enqueue_request(
            request_type,
            request_data,
            self.read_queue,
            self.write_queue,
            READ_QUEUE_MAX_SIZE,
            WRITE_QUEUE_MAX_SIZE,
        )

    def get_queue_metrics(self) -> Dict[str, Any]:
        """Get current queue status for monitoring."""
        return self.metrics_collector.get_queue_metrics()


class RateLimiterMetrics:
    """
    Metrics collection for rate limiter monitoring.

    Provides methods to collect and format rate limiter metrics
    for integration with monitoring systems.
    """

    def __init__(self, rate_limiter: KalshiRateLimiter):
        """Initialize metrics collector."""
        self.rate_limiter = rate_limiter

    def get_queue_metrics(self) -> Dict[str, Any]:
        """Get current queue status for monitoring."""
        return self.rate_limiter.get_queue_metrics()

    def get_health_status(self) -> Dict[str, Any]:
        """Get rate limiter health status."""
        return self.rate_limiter.metrics_collector.get_health_status()
