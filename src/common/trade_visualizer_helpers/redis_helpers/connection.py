"""Redis connection helpers for trade visualizer."""


def get_redis_connection():
    """Get Redis connection (used by tests)."""
    from common.redis_utils import get_redis_connection as _get_redis_connection

    return _get_redis_connection()


def get_schema_config():
    """Expose schema config accessor for tests."""
    from common.config.redis_schema import get_schema_config as _get_schema_config

    return _get_schema_config()
