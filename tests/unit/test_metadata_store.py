"""Unit tests for the MetadataStore helper."""

from unittest.mock import AsyncMock

import pytest

from src.common import metadata_store as metadata_module
from src.common.metadata_store import MetadataStore


class DummyConnectionManager:
    def __init__(self):
        self.initialize = AsyncMock()
        self.cleanup = AsyncMock()
        self.get_client = AsyncMock(return_value="redis_client")


class DummyOperationsFacade:
    def __init__(self, prefix, stats_key):
        self.prefix = prefix
        self.stats_key = stats_key

    async def get_service_metadata(self, client, service_name):
        return {"service": service_name, "client": client}

    async def get_all_services(self, client):
        return {"client": client, "services": {"svc"}}

    async def get_total_message_count(self, client):
        return 42

    async def increment_service_count(self, client, service_name, count):
        return {"updated": service_name, "count": count, "client": client}

    async def update_time_window_counts(self, client, service_name, hour, minute):
        return {"client": client, "hour": hour, "minute": minute}

    async def update_weather_time_window_counts(self, client, service_name, hour, minute, window):
        return {"client": client, "window": window, "service": service_name}

    async def initialize_service_count(self, client, service_name, initial_count):
        return {"service": service_name, "initial": initial_count, "client": client}

    async def get_service_history(self, client, service_name, hours):
        return [{"service": service_name, "hours": hours, "client": client}]


@pytest.mark.asyncio
async def test_metadata_store_methods_delegate(monkeypatch):
    monkeypatch.setattr(metadata_module, "ConnectionManager", DummyConnectionManager)
    monkeypatch.setattr(metadata_module, "OperationsFacade", DummyOperationsFacade)

    store = MetadataStore()

    await store.initialize()
    store._connection.initialize.assert_awaited_once()

    result = await store.get_service_metadata("svc")
    assert result["service"] == "svc"
    all_services = await store.get_all_services()
    assert all_services["client"] == "redis_client"
    assert await store.get_total_message_count() == 42
    incremented = await store.increment_service_count("svc", 5)
    assert incremented["count"] == 5
    time_window = await store.update_time_window_counts("svc", 10, 1)
    assert time_window["hour"] == 10
    weather_window = await store.update_weather_time_window_counts("svc", 20, 2, 65)
    assert weather_window["window"] == 65
    initialized = await store.initialize_service_count("svc", 7)
    assert initialized["initial"] == 7
    history = await store.get_service_history("svc", 24)
    assert history[0]["hours"] == 24

    await store.cleanup()
    store._connection.cleanup.assert_awaited_once()
