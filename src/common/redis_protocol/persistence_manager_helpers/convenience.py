"""Convenience functions for Redis persistence management."""

import logging

logger = logging.getLogger(__name__)


async def ensure_redis_persistence() -> bool:
    """
    Ensure Redis persistence is properly configured.

    Returns:
        bool: True if persistence is configured, False otherwise
    """
    from ..persistence_manager import RedisPersistenceManager

    manager = RedisPersistenceManager()
    try:
        await manager.initialize()

        # Check if already configured
        is_valid, message = await manager.validate_persistence()
        if is_valid:
            logger.info("Redis persistence already properly configured")
            return True

        # Configure persistence
        logger.info("Configuring Redis persistence...")
        success = await manager.configure_persistence()

        if success:
            # Validate configuration
            is_valid, message = await manager.validate_persistence()
            if is_valid:
                logger.info("Redis persistence successfully configured and validated")
                return True
            else:
                logger.error(f"Redis persistence configuration validation failed: {message}")
                return False
        else:
            logger.error("Failed to configure Redis persistence")
            return False

    finally:
        await manager.close()


async def get_redis_persistence_status() -> str:
    """
    Get Redis persistence status information.

    Returns:
        Formatted string with persistence status
    """
    from ..persistence_manager import RedisPersistenceManager

    manager = RedisPersistenceManager()
    try:
        await manager.initialize()
        return await manager.get_persistence_info()
    finally:
        await manager.close()
