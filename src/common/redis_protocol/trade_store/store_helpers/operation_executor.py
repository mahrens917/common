"""Operation execution with error handling for TradeStore."""

import logging
from typing import Awaitable, Callable, TypeVar

from ...error_types import REDIS_ERRORS
from ..errors import OrderMetadataError, TradeStoreError

T = TypeVar("T")


class OperationExecutor:
    """Execute TradeStore operations with consistent error handling."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def run_with_redis_guard(
        self,
        context: str,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        """
        Execute operation with Redis error handling.

        Args:
            context: Operation name for logging
            operation: Async operation to execute

        Returns:
            Operation result

        Raises:
            OrderMetadataError: For metadata-specific errors
            TradeStoreError: For general trade store errors
        """
        try:
            return await operation()
        except OrderMetadataError:  # policy_guard: allow-silent-handler
            raise
        except TradeStoreError:  # policy_guard: allow-silent-handler
            raise
        except RuntimeError as exc:
            self.logger.error("%s: runtime failure %s", context, exc, exc_info=True)
            raise TradeStoreError(f"{context} failed") from exc
        except (ValueError, TypeError) as exc:
            self.logger.error("%s: payload validation failed: %s", context, exc, exc_info=True)
            raise TradeStoreError(f"{context} failed") from exc
        except REDIS_ERRORS as exc:
            self.logger.error("%s: Redis error %s", context, exc, exc_info=True)
            raise TradeStoreError(f"{context} failed") from exc
