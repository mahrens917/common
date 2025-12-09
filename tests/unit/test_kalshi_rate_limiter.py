import asyncio
import time
from typing import Any, Dict, List, Optional

import pytest

from src.common.kalshi_rate_limiter import (
    KALSHI_READ_REQUESTS_PER_SECOND,
    KalshiRateLimiter,
    QueueFullError,
    RateLimiterMetrics,
    RateLimiterWorkerError,
    RequestType,
)

_VAL_5_0 = 5.0
DEFAULT_RATE_LIMITER_QUEUE_SIZE = 10


class StubHttpClient:
    def __init__(self, response: Any = None, error: Optional[Exception] = None):
        self.calls: List[tuple[str, str, Any]] = []
        self.response = response
        self.error = error

    async def make_http_request(self, method: str, path: str, params: Any) -> Any:
        self.calls.append((method, path, params))
        if self.error is not None:
            raise self.error
        return self.response


def _build_request(
    http_client: StubHttpClient,
    success_callback,
    error_callback,
    method: str = "GET",
    path: str = "/test",
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "http_client": http_client,
        "method": method,
        "path": path,
        "params": params,
        "success_callback": success_callback,
        "error_callback": error_callback,
    }


@pytest.mark.asyncio
async def test_enqueue_request_adds_to_queue() -> None:
    limiter = KalshiRateLimiter()
    client = StubHttpClient()

    try:
        req_id = await limiter.enqueue_request(
            RequestType.READ,
            _build_request(client, lambda _: None, lambda _: None),
        )

        assert isinstance(req_id, str)
        assert limiter.read_queue.qsize() == 1
    finally:
        await limiter.shutdown()


@pytest.mark.asyncio
async def test_enqueue_request_queue_full_raises() -> None:
    limiter = KalshiRateLimiter()
    client = StubHttpClient()

    try:
        for _ in range(limiter.read_queue.maxsize):
            limiter.read_queue.put_nowait({})

        with pytest.raises(QueueFullError):
            await limiter.enqueue_request(
                RequestType.READ,
                _build_request(client, lambda _: None, lambda _: None),
            )
    finally:
        await limiter.shutdown()


@pytest.mark.asyncio
async def test_enqueue_request_handles_spurious_queuefull(monkeypatch) -> None:
    limiter = KalshiRateLimiter()

    class FlakyQueue:
        maxsize = DEFAULT_RATE_LIMITER_QUEUE_SIZE

        def full(self) -> bool:
            return False

        def put_nowait(self, _request) -> None:
            raise asyncio.QueueFull

    limiter.read_queue = FlakyQueue()  # type: ignore[assignment]

    with pytest.raises(QueueFullError):
        await limiter.enqueue_request(
            RequestType.READ,
            _build_request(StubHttpClient(), lambda _: None, lambda _: None),
        )


@pytest.mark.asyncio
async def test_enqueue_request_write_queue_full_raises() -> None:
    limiter = KalshiRateLimiter()
    client = StubHttpClient()

    try:
        for _ in range(limiter.write_queue.maxsize):
            limiter.write_queue.put_nowait({})

        with pytest.raises(QueueFullError):
            await limiter.enqueue_request(
                RequestType.WRITE,
                _build_request(client, lambda _: None, lambda _: None),
            )
    finally:
        await limiter.shutdown()


@pytest.mark.asyncio
async def test_enqueue_request_invalid_type() -> None:
    limiter = KalshiRateLimiter()
    client = StubHttpClient()

    try:
        with pytest.raises(ValueError):
            await limiter.enqueue_request(
                "INVALID",  # type: ignore[arg-type]
                _build_request(client, lambda _: None, lambda _: None),
            )
    finally:
        await limiter.shutdown()


@pytest.mark.asyncio
async def test_execute_request_success_path() -> None:
    limiter = KalshiRateLimiter()
    client = StubHttpClient(response={"ok": True})
    successes: List[Any] = []
    errors: List[Exception] = []

    request = _build_request(
        client,
        lambda resp: successes.append(resp),
        lambda exc: errors.append(exc),
    )
    request["request_id"] = "req-1"
    request["enqueue_time"] = time.time()

    await limiter._execute_request(request)

    assert client.calls == [("GET", "/test", None)]
    assert successes == [{"ok": True}]
    assert errors == []


@pytest.mark.asyncio
async def test_execute_request_error_path() -> None:
    limiter = KalshiRateLimiter()
    failure = RuntimeError("boom")
    client = StubHttpClient(error=failure)
    successes: List[Any] = []
    errors: List[Exception] = []

    request = _build_request(
        client,
        lambda resp: successes.append(resp),
        lambda exc: errors.append(exc),
    )
    request["request_id"] = "req-2"
    request["enqueue_time"] = time.time()

    await limiter._execute_request(request)

    assert successes == []
    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)


@pytest.mark.asyncio
async def test_execute_request_skips_when_shutdown_flag_set() -> None:
    limiter = KalshiRateLimiter()
    client = StubHttpClient(response={"ok": True})
    successes: List[Any] = []
    errors: List[Exception] = []

    request = _build_request(
        client,
        lambda resp: successes.append(resp),
        lambda exc: errors.append(exc),
    )
    request["request_id"] = "req-3"
    request["enqueue_time"] = time.time()

    limiter._shutdown_event.set()

    await limiter._execute_request(request)

    assert client.calls == []
    assert successes == []
    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)


@pytest.mark.asyncio
async def test_start_worker_is_idempotent() -> None:
    limiter = KalshiRateLimiter()

    try:
        await limiter.start_worker()
        first_task = limiter._worker_task

        await limiter.start_worker()
        assert limiter._worker_task is first_task
    finally:
        await limiter.shutdown()


@pytest.mark.asyncio
async def test_shutdown_without_worker_is_noop() -> None:
    limiter = KalshiRateLimiter()
    await limiter.shutdown()
    assert limiter._worker_task is None  # type: ignore[attr-defined]
    assert limiter.read_queue.qsize() == 0  # type: ignore[attr-defined]
    assert limiter.write_queue.qsize() == 0  # type: ignore[attr-defined]
    assert limiter._shutdown_event.is_set() is False  # type: ignore[attr-defined]


def test_get_queue_metrics_structure() -> None:
    limiter = KalshiRateLimiter()
    metrics = limiter.get_queue_metrics()

    expected_keys = {
        "read_queue_depth",
        "write_queue_depth",
        "read_tokens_available",
        "write_tokens_available",
        "read_queue_capacity",
        "write_queue_capacity",
        "max_read_tokens",
        "max_write_tokens",
        "timestamp",
    }

    assert expected_keys <= metrics.keys()


def test_rate_limiter_metrics_health_status_thresholds() -> None:
    limiter = KalshiRateLimiter()
    metrics = RateLimiterMetrics(limiter)

    healthy = metrics.get_health_status()
    assert healthy["status"] == "HEALTHY"

    for _ in range(int(0.6 * limiter.read_queue.maxsize)):
        limiter.read_queue.put_nowait({})

    warning = metrics.get_health_status()
    assert warning["status"] == "WARNING"

    while not limiter.read_queue.empty():
        limiter.read_queue.get_nowait()

    for _ in range(int(0.9 * limiter.write_queue.maxsize)):
        limiter.write_queue.put_nowait({})

    degraded = metrics.get_health_status()
    assert degraded["status"] == "DEGRADED"


@pytest.mark.asyncio
async def test_shutdown_cancels_inflight_requests_gracefully() -> None:
    limiter = KalshiRateLimiter()
    client = StubHttpClient()
    skipped: List[str] = []

    try:
        await limiter.start_worker()

        await limiter.enqueue_request(
            RequestType.READ,
            _build_request(
                client,
                lambda _: None,
                lambda exc: skipped.append(str(exc)),
            ),
        )

        limiter._shutdown_event.set()
    finally:
        await limiter.shutdown()

    assert limiter._worker_task is None


@pytest.mark.asyncio
async def test_worker_processes_read_and_write_requests() -> None:
    limiter = KalshiRateLimiter()
    limiter.read_tokens = limiter.max_read_tokens = 1
    limiter.write_tokens = limiter.max_write_tokens = 1

    read_calls: List[str] = []
    write_calls: List[str] = []
    read_client = StubHttpClient(response={"read": True})
    write_client = StubHttpClient(response={"write": True})

    try:
        await limiter.start_worker()

        await limiter.enqueue_request(
            RequestType.READ,
            _build_request(
                read_client,
                lambda resp: read_calls.append("success"),
                lambda _: None,
            ),
        )

        await limiter.enqueue_request(
            RequestType.WRITE,
            _build_request(
                write_client,
                lambda resp: write_calls.append("success"),
                lambda _: None,
            ),
        )

        await asyncio.sleep(0)
    finally:
        await limiter.shutdown()

    assert read_calls == ["success"]
    assert write_calls == ["success"]


@pytest.mark.asyncio
async def test_worker_raises_error_on_unexpected_failure(monkeypatch) -> None:
    limiter = KalshiRateLimiter()
    limiter.read_tokens = 1
    limiter.read_queue.put_nowait({"request_id": "req", "enqueue_time": time.time()})

    async def boom(_request) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(limiter, "_execute_request", boom)

    with pytest.raises(RateLimiterWorkerError):
        await limiter._process_requests_worker()

    assert limiter._shutdown_event.is_set()


@pytest.mark.asyncio
async def test_worker_stops_cleanly_on_shutdown_errors(monkeypatch) -> None:
    limiter = KalshiRateLimiter()
    limiter.read_tokens = 1
    limiter.read_queue.put_nowait({"request_id": "req", "enqueue_time": time.time()})

    async def shutdown_then_fail(_request) -> None:
        limiter._shutdown_event.set()
        raise RuntimeError("Session closed by server")

    monkeypatch.setattr(limiter, "_execute_request", shutdown_then_fail)

    await limiter._process_requests_worker()

    assert limiter._shutdown_event.is_set()
    assert limiter.read_queue.qsize() == 0


@pytest.mark.asyncio
async def test_shutdown_cancels_worker_on_timeout(monkeypatch) -> None:
    limiter = KalshiRateLimiter()
    lingering_task = asyncio.Future()
    limiter._worker_task = lingering_task

    async def fake_wait_for(awaitable, timeout):
        assert awaitable is lingering_task
        assert timeout == _VAL_5_0
        raise asyncio.TimeoutError

    monkeypatch.setattr(asyncio, "wait_for", fake_wait_for)

    with pytest.raises(RuntimeError, match="worker cancelled"):
        await limiter.shutdown()

    assert lingering_task.cancelled()
