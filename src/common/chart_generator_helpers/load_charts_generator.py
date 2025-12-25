from __future__ import annotations

"""Helper for generating load and system charts"""


import logging
from typing import Dict

from common.redis_protocol.typing import RedisClient

logger = logging.getLogger("src.monitor.chart_generator")


class LoadChartsGenerator:
    """Generates all load and system monitoring charts"""

    def __init__(self, *, load_chart_creator, system_chart_creator):
        self.load_chart_creator = load_chart_creator
        self.system_chart_creator = system_chart_creator

    async def generate_load_charts(self, hours: int, os) -> Dict[str, str]:
        """Generate all load monitoring charts and return file paths"""
        chart_paths = {}
        success = False

        try:
            chart_paths["deribit"] = await self.load_chart_creator.create_load_chart("deribit", hours)
            chart_paths["kalshi"] = await self.load_chart_creator.create_load_chart("kalshi", hours)

            from common.redis_utils import get_redis_connection

            redis_client: RedisClient = await get_redis_connection()
            try:
                chart_paths["cpu"] = await self.system_chart_creator.create_system_chart("cpu", hours, redis_client)
                chart_paths["memory"] = await self.system_chart_creator.create_system_chart("memory", hours, redis_client)
            finally:
                await redis_client.aclose()

            success = True
            return chart_paths

        finally:
            if not success:
                for path in chart_paths.values():
                    try:
                        os.unlink(path)
                    except OSError:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
                        logger.warning("Unable to clean up chart file %s", path)
