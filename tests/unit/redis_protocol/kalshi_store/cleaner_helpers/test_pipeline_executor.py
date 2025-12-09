import pytest
from redis.exceptions import RedisError

from src.common.redis_protocol.error_types import REDIS_ERRORS
from src.common.redis_protocol.kalshi_store.cleaner_helpers.pipeline_executor import (
    PipelineExecutor,
)


class _DummyPipe:
    def __init__(self, fail=False):
        self.fail = fail

    async def execute(self):
        if self.fail:
            raise REDIS_ERRORS[0]("boom")
        return True


@pytest.mark.asyncio
async def test_execute_pipeline_success():
    result = await PipelineExecutor.execute_pipeline(_DummyPipe(), "op")
    assert result is True


@pytest.mark.asyncio
async def test_execute_pipeline_handles_failure():
    result = await PipelineExecutor.execute_pipeline(_DummyPipe(fail=True), "op")
    assert result is False
