from __future__ import annotations

import asyncio

import pytest

from common.kalshi_client_mixin import KalshiClientMixin


@pytest.mark.asyncio
async def test_kalshi_client_mixin_caches_instance(monkeypatch):
    class DummyClient:
        pass

    monkeypatch.setattr("common.kalshi_client_mixin.KalshiClient", DummyClient)

    class Dummy(KalshiClientMixin):
        def __init__(self):
            self._kalshi_client = None
            self._kalshi_client_lock = asyncio.Lock()

    obj = Dummy()
    first = await obj._get_kalshi_client()
    second = await obj._get_kalshi_client()

    assert first is second
