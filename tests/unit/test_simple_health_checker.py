'"""Tests for the lightweight health checker."""'

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common import simple_health_checker as module
from src.common.simple_health_checker import SimpleHealthChecker


class DummyDelegator:
    def __init__(self, **_kwargs):
        self.check_service_health = AsyncMock(return_value={"status": "ok"})
        self.check_multiple_services = AsyncMock(return_value={"svc": {"status": "ok"}})
        self.is_service_healthy = MagicMock(return_value=True)
        self.get_detailed_service_status = AsyncMock(return_value={"status": "detailed"})


@pytest.fixture(autouse=True)
def stub_delegator(monkeypatch):
    monkeypatch.setattr(module, "SimpleHealthDelegator", DummyDelegator)
    yield


@pytest.mark.asyncio
async def test_checks_delegate_to_delegator():
    checker = SimpleHealthChecker(logs_directory="./logs")

    assert await checker.check_service_health("svc") == {"status": "ok"}
    assert await checker.check_multiple_services(["svc"]) == {"svc": {"status": "ok"}}
    assert checker.is_service_healthy({"status": "ok"})
    assert await checker.get_detailed_service_status("svc") == {"status": "detailed"}
