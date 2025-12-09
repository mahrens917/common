from __future__ import annotations

import pytest

from src.common.redis_protocol.probability_store.probabilityretrieval_helpers import (
    grouped_retrieval,
)


@pytest.mark.asyncio
async def test_grouped_retrieval_invokes_event_type_helpers(monkeypatch):
    recorded = {"types": [], "events": []}

    async def _get_all(redis, currency):
        recorded["types"].append((redis, currency))
        return ["event-a", "event-b"]

    async def _get_by_type(redis, currency, event_type):
        recorded["events"].append((redis, currency, event_type))
        return {event_type: {"payload": 1}}

    monkeypatch.setattr(grouped_retrieval, "get_all_event_types", _get_all)
    monkeypatch.setattr(grouped_retrieval, "get_probabilities_by_event_type", _get_by_type)

    result = await grouped_retrieval.get_probabilities_grouped_by_event_type("redis", "btc")

    assert set(result.keys()) == {"event-a", "event-b"}
    assert recorded["events"][0][2] == "event-a"
