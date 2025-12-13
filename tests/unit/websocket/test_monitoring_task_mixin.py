from __future__ import annotations

import asyncio

import pytest

from common.websocket.monitoring_task_mixin import MonitoringTaskMixin


@pytest.mark.asyncio
async def test_stop_monitoring_cancels_task():
    class Dummy(MonitoringTaskMixin):
        def __init__(self):
            self.service_name = "svc"
            self._monitoring_label = "monitoring"
            self._monitoring_task = None

    async def worker():
        await asyncio.sleep(60)

    obj = Dummy()
    obj._monitoring_task = asyncio.create_task(worker())
    await obj.stop_monitoring()

    assert obj._monitoring_task is None
