import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.redis_protocol.retry import RedisFatalError, RedisRetryError
from common.redis_protocol.trade_store.store_helpers.connection_manager_helpers.retry_helpers.executor import (
    execute_retry_operation,
)


class TestExecutor:
    @pytest.mark.asyncio
    async def test_execute_retry_operation_success(self):
        operation = AsyncMock()
        policy = Mock()
        context = "test"
        on_retry = Mock()
        logger = Mock(spec=logging.Logger)

        with patch(
            "common.redis_protocol.trade_store.store_helpers.connection_manager_helpers.retry_helpers.executor.execute_with_retry",
            new_callable=AsyncMock,
        ) as mock_execute:
            result = await execute_retry_operation(operation, policy, context, on_retry, logger)

            assert result is True
            mock_execute.assert_called_once_with(
                operation, policy=policy, logger=logger, context=context, on_retry=on_retry
            )

    @pytest.mark.asyncio
    async def test_execute_retry_operation_fatal_error(self):
        operation = AsyncMock()
        policy = Mock()
        context = "test"
        on_retry = Mock()
        logger = Mock(spec=logging.Logger)

        with patch(
            "common.redis_protocol.trade_store.store_helpers.connection_manager_helpers.retry_helpers.executor.execute_with_retry",
            side_effect=RedisFatalError("fatal"),
        ):
            result = await execute_retry_operation(operation, policy, context, on_retry, logger)

            assert result is False

    @pytest.mark.asyncio
    async def test_execute_retry_operation_retry_error(self):
        operation = AsyncMock()
        policy = Mock()
        context = "test"
        on_retry = Mock()
        logger = Mock(spec=logging.Logger)

        with patch(
            "common.redis_protocol.trade_store.store_helpers.connection_manager_helpers.retry_helpers.executor.execute_with_retry",
            side_effect=RedisRetryError("retry failed"),
        ):
            result = await execute_retry_operation(operation, policy, context, on_retry, logger)

            assert result is False
            logger.exception.assert_called_once()
