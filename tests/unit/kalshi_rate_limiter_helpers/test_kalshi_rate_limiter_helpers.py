import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import aiohttp
import pytest

from src.common.kalshi_rate_limiter_helpers.metrics_collector import MetricsCollector
from src.common.kalshi_rate_limiter_helpers.request_executor import (
    RequestExecutor,
    _is_shutdown_error,
)
from src.common.kalshi_rate_limiter_helpers.token_manager import TokenManager
from src.common.kalshi_rate_limiter_helpers.worker_manager import WorkerManager
from src.common.kalshi_rate_limiter_helpers.worker_manager_helpers.error_classifier import (
    ErrorClassifier,
)
from src.common.kalshi_rate_limiter_helpers.worker_manager_helpers.request_processor import (
    RequestProcessor,
)

pytestmark = pytest.mark.unit


class DummyQueue:
    def __init__(self, depth: int, maxsize: int):
        self._depth = depth
        self.maxsize = maxsize

    def qsize(self) -> int:
        return self._depth

    def empty(self) -> bool:
        return self._depth == 0

    def get_nowait(self):
        if self.empty():
            raise asyncio.QueueEmpty
        self._depth -= 1
        return {"request_id": f"req-{self._depth}", "enqueue_time": time.time()}


def test_token_manager_refill_and_consume(monkeypatch):
    token_manager = TokenManager(2, 1)
    token_manager.last_refill_time = 0.0
    monkeypatch.setattr(
        "src.common.kalshi_rate_limiter_helpers.token_manager.time.time", lambda: 2.0
    )

    assert token_manager.refill_tokens_if_needed() is True
    assert token_manager.read_tokens == 2
    assert token_manager.write_tokens == 1

    assert token_manager.consume_read_token() is True
    assert token_manager.consume_write_token() is True
    assert token_manager.has_read_tokens() is True
    assert token_manager.has_write_tokens() is False


def test_metrics_collector_reports_status():
    token_manager = SimpleNamespace(
        read_tokens=3, write_tokens=4, max_read_tokens=5, max_write_tokens=6
    )
    collector = MetricsCollector(DummyQueue(9, 10), DummyQueue(2, 10), token_manager)

    metrics = collector.get_queue_metrics()
    assert metrics["read_queue_depth"] == 9
    assert metrics["write_queue_capacity"] == 10

    health = collector.get_health_status()
    assert health["status"] == "DEGRADED"
    assert health["read_queue_utilization_percent"] > 80

    collector = MetricsCollector(DummyQueue(1, 10), DummyQueue(1, 10), token_manager)
    assert collector.get_health_status()["status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_request_executor_success_and_error(monkeypatch):
    shutdown_event = asyncio.Event()
    executor = RequestExecutor(shutdown_event)
    success_calls = []
    error_calls = []

    async def fake_http_request(data):
        return {"ok": True, "path": data["path"]}

    monkeypatch.setattr(
        "src.common.kalshi_rate_limiter_helpers.request_executor._perform_http_request",
        fake_http_request,
    )

    request_data = {
        "request_id": "1",
        "enqueue_time": time.time(),
        "method": "GET",
        "path": "/ping",
        "http_client": SimpleNamespace(),
        "success_callback": lambda resp: success_calls.append(resp),
    }
    await executor.execute_request(request_data)
    assert success_calls == [{"ok": True, "path": "/ping"}]

    async def failing_http_request(_):
        raise aiohttp.ClientError("boom")

    monkeypatch.setattr(
        "src.common.kalshi_rate_limiter_helpers.request_executor._perform_http_request",
        failing_http_request,
    )
    request_data["error_callback"] = lambda exc: error_calls.append(str(exc))
    await executor.execute_request(request_data)
    assert error_calls and "boom" in error_calls[0]


@pytest.mark.asyncio
async def test_request_executor_skips_when_shutdown(monkeypatch):
    shutdown_event = asyncio.Event()
    shutdown_event.set()
    executor = RequestExecutor(shutdown_event)
    errors = []

    monkeypatch.setattr(
        "src.common.kalshi_rate_limiter_helpers.request_executor._perform_http_request",
        AsyncMock(),
    )

    request_data = {
        "request_id": "skip-me",
        "enqueue_time": time.time(),
        "method": "GET",
        "path": "/ignored",
        "http_client": SimpleNamespace(),
        "error_callback": lambda exc: errors.append(exc),
    }

    await executor.execute_request(request_data)
    assert errors and isinstance(errors[0], RuntimeError)


def test_is_shutdown_error_respects_event_state():
    assert _is_shutdown_error(RuntimeError("Session closed abruptly")) is True
    assert _is_shutdown_error(RuntimeError("Random error")) is False


@pytest.mark.asyncio
async def test_request_processor_handles_tokens_and_queue(monkeypatch):
    executor = AsyncMock()
    token_manager = SimpleNamespace(read_tokens=1, write_tokens=1)

    def has_read_tokens():
        return token_manager.read_tokens > 0

    def consume_read_token():
        token_manager.read_tokens -= 1

    def has_write_tokens():
        return token_manager.write_tokens > 0

    def consume_write_token():
        token_manager.write_tokens -= 1

    token_manager.has_read_tokens = has_read_tokens
    token_manager.consume_read_token = consume_read_token
    token_manager.has_write_tokens = has_write_tokens
    token_manager.consume_write_token = consume_write_token

    processor = RequestProcessor(token_manager, executor)
    read_queue: asyncio.Queue = asyncio.Queue()
    write_queue: asyncio.Queue = asyncio.Queue()
    request = {"request_id": "r1", "enqueue_time": time.time()}
    await read_queue.put(request)
    await write_queue.put(request)

    assert await processor.process_read_request(read_queue) is True
    executor.execute_request.assert_awaited_with(request)

    executor.execute_request.reset_mock()
    assert await processor.process_write_request(write_queue) is True
    executor.execute_request.assert_awaited_with(request)

    token_manager.read_tokens = 0
    assert await processor.process_read_request(asyncio.Queue()) is False


def test_error_classifier_requires_shutdown_flag():
    event = asyncio.Event()
    assert ErrorClassifier.is_shutdown_error(RuntimeError("session closed"), event) is False
    event.set()
    assert ErrorClassifier.is_shutdown_error(RuntimeError("session closed"), event) is True


@pytest.mark.asyncio
async def test_worker_manager_starts_and_shuts_down(monkeypatch):
    token_manager = SimpleNamespace(refill_tokens_if_needed=lambda: None)
    read_queue: asyncio.Queue = asyncio.Queue()
    write_queue: asyncio.Queue = asyncio.Queue()

    shutdown_event_holder = {}

    class DummyProcessor:
        def __init__(self, _token_manager, _executor):
            shutdown_event_holder["event"] = manager.shutdown_event

        async def process_read_request(self, _queue):
            return True

        async def process_write_request(self, _queue):
            manager.shutdown_event.set()
            return True

    monkeypatch.setattr(
        "src.common.kalshi_rate_limiter_helpers.worker_manager_helpers.RequestProcessor",
        DummyProcessor,
    )

    manager = WorkerManager(token_manager, read_queue, write_queue)
    await manager.start_worker()
    await asyncio.sleep(0.02)
    assert manager.worker_task is not None
    await manager.shutdown()
    assert manager.worker_task is None
    assert shutdown_event_holder["event"].is_set()

    # Second shutdown should no-op when worker_task already cleared
    await manager.shutdown()


@pytest.mark.asyncio
async def test_worker_manager_warns_on_double_start(monkeypatch):
    token_manager = SimpleNamespace(refill_tokens_if_needed=lambda: None)
    manager = WorkerManager(token_manager, asyncio.Queue(), asyncio.Queue())

    async def fast_worker():
        manager.shutdown_event.set()

    monkeypatch.setattr(
        manager, "_process_requests_worker", lambda: fast_worker()  # type: ignore[attr-defined]
    )

    await manager.start_worker()
    first_task = manager.worker_task
    await manager.start_worker()
    assert manager.worker_task is first_task
    await manager.shutdown()
