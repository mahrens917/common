"""Persistence lifecycle coordination for Redis."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ..error_types import REDIS_ERRORS
from ..typing import ensure_awaitable

if TYPE_CHECKING:
    from ..typing import RedisClient

logger = logging.getLogger(__name__)


class PersistenceCoordinator:
    """Coordinates persistence lifecycle operations."""

    RUNTIME_PERSISTENCE_CONFIG = {
        "appendonly": "yes",
        "appendfsync": "everysec",
        "no-appendfsync-on-rewrite": "no",
        "auto-aof-rewrite-percentage": "100",
        "auto-aof-rewrite-min-size": "64mb",
        "stop-writes-on-bgsave-error": "yes",
        "rdbcompression": "yes",
    }

    IMMUTABLE_CONFIGS = {
        "appendfilename": "trades_appendonly.aof",
        "rdbchecksum": "yes",
        "dbfilename": "trades_dump.rdb",
        "dir": "./redis_data",
    }

    async def ensure_data_directory(self) -> bool:
        try:
            data_dir = Path(self.IMMUTABLE_CONFIGS["dir"])
            data_dir.mkdir(exist_ok=True)
            logger.info("Ensured data directory exists: %s", data_dir.absolute())
        except OSError:  # policy_guard: allow-silent-handler
            logger.exception("Failed to create data directory")
            return False
        else:
            return True

    async def apply_runtime_config(self, redis: "RedisClient") -> tuple[int, int, int]:
        config_applied = 0
        config_failed = 0
        immutable_skipped = 0

        for key, value in self.RUNTIME_PERSISTENCE_CONFIG.items():
            try:
                await ensure_awaitable(redis.config_set(key, value))
                config_applied += 1
                logger.debug("Applied Redis config: %s = %s", key, value)
            except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
                config_failed += 1
                error_msg = str(exc)
                if "immutable" in error_msg or "protected" in error_msg:
                    logger.info("Skipped immutable Redis config %s = %s (requires redis.conf)", key, value)
                    immutable_skipped += 1
                    config_failed -= 1
                else:
                    logger.warning("Failed to apply Redis config %s = %s", key, value)
                    if "NOPERM" in error_msg or "permission" in error_msg.lower():
                        logger.warning("Redis user lacks CONFIG permission for %s", key)

        return config_applied, config_failed, immutable_skipped

    async def persist_config_to_disk(self, redis: "RedisClient") -> bool:
        try:
            await ensure_awaitable(redis.config_rewrite())
            logger.info("Redis configuration rewritten to disk")
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.warning("Failed to rewrite Redis config to disk: %s", exc)
            return False
        else:
            return True

    def log_immutable_configs(self) -> None:
        if self.IMMUTABLE_CONFIGS:
            logger.info("The following configs must be set in redis.conf or at Redis startup:")
            for key, value in self.IMMUTABLE_CONFIGS.items():
                logger.info("  %s %s", key, value)
