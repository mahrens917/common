import asyncio
import logging
from typing import Callable, List, Optional, Tuple

from redis.asyncio import Redis

from .redis_protocol.connection import get_redis_pool
from .resource_tracker_helpers import CpuTracker, MonitoringLoop, RamTracker
from .resource_tracker_helpers.delegation import history, monitoring_control, recording

logger = logging.getLogger(__name__)


class ResourceTracker:
    def __init__(self, redis: Optional[Redis] = None):
        self._redis = redis
        self._cpu_tracker: Optional[CpuTracker] = None
        self._ram_tracker: Optional[RamTracker] = None
        self._monitoring_loop: Optional[MonitoringLoop | Callable] = None
        self._stop_monitoring = asyncio.Event()

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            pool = await get_redis_pool()
            self._redis = Redis(connection_pool=pool)
        return self._redis

    async def _ensure_trackers(self) -> bool:
        cpu_tracker: Optional[CpuTracker] = self._cpu_tracker
        ram_tracker: Optional[RamTracker] = self._ram_tracker
        if not (cpu_tracker and ram_tracker):
            try:
                from redis.exceptions import RedisError

                redis = await self._get_redis()
            except (RedisError, OSError, RuntimeError, Exception) as exc:
                logger.error("Failed to initialize resource trackers: %s", exc, exc_info=True)
                return False
            self._cpu_tracker = CpuTracker(redis)
            self._ram_tracker = RamTracker(redis)
            cpu_tracker = self._cpu_tracker
            ram_tracker = self._ram_tracker
        if not (cpu_tracker and ram_tracker):
            return False
        if self._monitoring_loop is None:
            self._monitoring_loop = MonitoringLoop(
                cpu_tracker,
                ram_tracker,
                stop_event=self._stop_monitoring,
            )
        return True

    async def record_cpu_usage(self, total_cpu_percent: float) -> bool:
        if not await self._ensure_trackers():
            return False
        cpu_tracker = self._cpu_tracker
        assert cpu_tracker is not None
        return await recording.record_cpu_usage(cpu_tracker, total_cpu_percent)

    async def record_ram_usage(self, total_ram_mb: float) -> bool:
        if not await self._ensure_trackers():
            return False
        ram_tracker = self._ram_tracker
        assert ram_tracker is not None
        return await recording.record_ram_usage(ram_tracker, total_ram_mb)

    async def get_cpu_history(self, hours: int = 24) -> List[Tuple[int, float]]:
        if not await self._ensure_trackers():
            return []
        cpu_tracker = self._cpu_tracker
        assert cpu_tracker is not None
        return await history.get_cpu_history(cpu_tracker, hours)

    async def get_ram_history(self, hours: int = 24) -> List[Tuple[int, float]]:
        if not await self._ensure_trackers():
            return []
        ram_tracker = self._ram_tracker
        assert ram_tracker is not None
        return await history.get_ram_history(ram_tracker, hours)

    async def start_per_second_monitoring(self, get_cpu_ram_func):
        if not await self._ensure_trackers():
            logger.debug("Per-second monitoring unavailable; tracker init failed")
            return
        await monitoring_control.start_per_second_monitoring(
            self._monitoring_loop, get_cpu_ram_func
        )

    async def stop_per_second_monitoring(self):
        await monitoring_control.stop_per_second_monitoring(self._monitoring_loop)

    def get_max_cpu_last_minute(self) -> Optional[float]:
        return monitoring_control.get_max_cpu_last_minute(self._monitoring_loop)

    def get_max_ram_last_minute(self) -> Optional[float]:
        return monitoring_control.get_max_ram_last_minute(self._monitoring_loop)

    async def update_current_usage(self, cpu_percent: float, ram_mb: float) -> bool:
        cpu_success = await self.record_cpu_usage(cpu_percent)
        ram_success = await self.record_ram_usage(ram_mb)
        return cpu_success and ram_success
