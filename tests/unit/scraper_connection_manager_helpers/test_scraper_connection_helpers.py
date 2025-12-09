import asyncio
from types import SimpleNamespace

import pytest

from src.common.redis_protocol.persistence_manager_helpers.config_orchestrator import (
    ConfigOrchestrator,
)
from src.common.redis_protocol.persistence_manager_helpers.connection_manager import (
    ConnectionManager as PersistenceConnectionManager,
)
from src.common.scraper_connection_manager_helpers.connection_lifecycle import (
    ScraperConnectionLifecycle,
)
from src.common.scraper_connection_manager_helpers.scraping_operations import ScrapingOperations


class _StubHealth:
    def __init__(self, healthy=True):
        self._healthy = healthy
        self.clear_calls = 0

    async def check_health(self):
        return SimpleNamespace(healthy=self._healthy)

    def clear_health_status(self):
        self.clear_calls += 1


class _StubSession:
    def __init__(self):
        self.created = False
        self.closed = False
        self.get_calls = []

    async def create_session(self):
        self.created = True

    async def close_session(self):
        self.closed = True

    def get_session(self):
        return self

    def is_session_valid(self):
        return not self.closed

    @property
    def closed(self):
        return getattr(self, "_closed", False)

    @closed.setter
    def closed(self, val):
        self._closed = val

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))

        async def _text():
            return "ok"

        class _Resp:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def text(self):
                return await _text()

        return _Resp()


def test_scraper_connection_lifecycle_success(monkeypatch):
    session = _StubSession()
    health = _StubHealth(healthy=True)
    lifecycle = ScraperConnectionLifecycle("svc", session, health)
    assert asyncio.run(lifecycle.establish_connection())
    asyncio.run(lifecycle.cleanup_connection())
    assert session.closed and health.clear_calls == 1


@pytest.mark.asyncio
async def test_scraping_operations_handles_session_and_validation(monkeypatch):
    session = _StubSession()

    class StubValidator:
        def __init__(self, valid=True):
            self.valid = valid
            self.calls = []

        def has_validators(self):
            return True

        async def validate_content(self, content, url):
            self.calls.append((content, url))
            return self.valid

    validator = StubValidator(valid=True)
    ops = ScrapingOperations("svc", ["http://example.com"], session, validator)
    session.closed = False
    result = await ops.scrape_all_urls()
    assert result["http://example.com"] == "ok"

    # Invalid content path should log and return None
    validator.valid = False
    result_invalid = await ops.scrape_url("http://example.com")
    assert result_invalid is None


@pytest.mark.asyncio
async def test_persistence_connection_manager(monkeypatch):
    manager = PersistenceConnectionManager()

    class StubRedis:
        def __init__(self):
            self.ping_called = 0

        async def ping(self):
            self.ping_called += 1
            return True

        async def close(self):
            return True

        async def aclose(self):
            await self.close()

    async def fake_pool():
        return "pool"

    monkeypatch.setattr(
        "src.common.redis_protocol.persistence_manager_helpers.connection_manager.get_redis_pool",
        fake_pool,
    )
    monkeypatch.setattr(
        "src.common.redis_protocol.persistence_manager_helpers.connection_manager.Redis",
        lambda connection_pool=None, decode_responses=True: StubRedis(),
    )

    redis = await manager.get_redis()
    assert redis.ping_called >= 1
    await manager.close()
    assert manager.redis is None


@pytest.mark.asyncio
async def test_config_orchestrator_coordinates(monkeypatch):
    class StubCoordinator:
        def __init__(self):
            self.persist_called = False
            self.immutable_logged = False

        async def ensure_data_directory(self):
            return True

        async def apply_runtime_config(self, redis):
            return (1, 0, 0)

        def log_immutable_configs(self):
            self.immutable_logged = True

        async def persist_config_to_disk(self, redis):
            self.persist_called = True

    class StubSnapshot:
        async def configure_save_points(self, redis, save_config):
            return True

        async def force_background_save(self, redis):
            return True

    orchestrator = ConfigOrchestrator(StubCoordinator(), StubSnapshot())
    assert await orchestrator.configure_all(redis="redis")


@pytest.mark.asyncio
async def test_content_validation_handler_metrics_and_failures(monkeypatch):
    from src.common.scraper_connection_manager_helpers.content_validation import (
        ContentValidationHandler,
    )

    calls = []

    def validator_ok(content, url):
        calls.append(("ok", content, url))
        return True

    def validator_fail(content, url):
        calls.append(("fail", content, url))
        return False

    handler = ContentValidationHandler("svc", [validator_ok])
    assert handler.has_validators() is True
    assert handler.get_validator_count() == 1
    assert await handler.validate_content("body", "url") is True
    metrics = handler.get_validation_metrics()
    assert metrics["consecutive_validation_failures"] == 0

    handler.content_validators.append(validator_fail)
    assert await handler.validate_content("body", "url") is False
    metrics = handler.get_validation_metrics()
    assert metrics["consecutive_validation_failures"] == 1
    assert any(call[0] == "fail" for call in calls)


@pytest.mark.asyncio
async def test_scraper_session_manager_lifecycle(monkeypatch):
    from src.common.scraper_connection_manager_helpers import session_manager

    created_sessions = []

    class DummySession:
        def __init__(self, *_, **__):
            self.closed = False
            self._connector = SimpleNamespace(close=lambda: asyncio.sleep(0))

        async def close(self):
            self.closed = True

    class DummyTimeout:
        def __init__(self, *_, **__):
            pass

    class DummyConnector:
        def __init__(self, *_, **__):
            self.closed = False

        async def close(self):
            self.closed = True

    def fake_track_existing_session(_session, name):
        created_sessions.append(name)
        return "session-id"

    def fake_track_session_close(session_id):
        created_sessions.append(f"closed-{session_id}")

    monkeypatch.setattr(
        session_manager,
        "aiohttp",
        SimpleNamespace(
            ClientSession=lambda *args, **kwargs: DummySession(*args, **kwargs),
            ClientTimeout=DummyTimeout,
            TCPConnector=DummyConnector,
        ),
    )
    monkeypatch.setattr(session_manager, "track_existing_session", fake_track_existing_session)
    monkeypatch.setattr(session_manager, "track_session_close", fake_track_session_close)

    mgr = session_manager.ScraperSessionManager("svc", "agent", 1, 2)
    session = await mgr.create_session()
    assert mgr.is_session_valid() is True
    assert mgr.session_id == "session-id"
    await mgr.close_session()
    assert mgr.session is None
    assert created_sessions[-1] == "closed-session-id"
