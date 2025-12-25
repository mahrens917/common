"""Shared helpers for managing background monitoring tasks."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MonitoringTaskMixin:
    service_name: str
    _monitoring_task: Optional[asyncio.Task]
    _monitoring_label: str

    async def stop_monitoring(self) -> None:
        if self._monitoring_task is not None:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:  # Expected during task cancellation  # policy_guard: allow-silent-handler
                logger.debug("Expected during task cancellation")
                pass
            self._monitoring_task = None
            logger.info("Stopped %s %s", self.service_name, self._monitoring_label)


__all__ = ["MonitoringTaskMixin"]
