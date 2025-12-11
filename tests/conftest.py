"""Root pytest configuration and shared fixtures."""

from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set required environment variables for tests
os.environ.setdefault("CONNECTION_TIMEOUT_SECONDS", "30")
os.environ.setdefault("REQUEST_TIMEOUT_SECONDS", "30")
os.environ.setdefault("RECONNECTION_INITIAL_DELAY_SECONDS", "1")
os.environ.setdefault("RECONNECTION_MAX_DELAY_SECONDS", "60")
os.environ.setdefault("RECONNECTION_BACKOFF_MULTIPLIER", "2.0")
os.environ.setdefault("MAX_CONSECUTIVE_FAILURES", "5")
os.environ.setdefault("HEALTH_CHECK_INTERVAL_SECONDS", "10")
os.environ.setdefault("SUBSCRIPTION_TIMEOUT_SECONDS", "5")


class FakeRedis:
    """In-memory Redis mock for testing."""

    def __init__(self):
        self._data: dict[str, Any] = {}
        self._sets: dict[str, set[str]] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._sorted_sets: dict[str, dict[str, float]] = {}
        self.published: list[tuple[str, str]] = []

    async def set(self, key: str, value: str | bytes) -> bool:
        """Set a string value."""
        self._data[key] = value if isinstance(value, str) else value.decode()
        return True

    async def get(self, key: str) -> str | None:
        """Get a string value."""
        return self._data.get(key)

    async def sadd(self, key: str, *members: str) -> int:
        """Add members to a set."""
        if key not in self._sets:
            self._sets[key] = set()
        added = len(set(members) - self._sets[key])
        self._sets[key].update(members)
        return added

    async def smembers(self, key: str) -> set[str]:
        """Get all members of a set."""
        return self._sets.get(key, set()).copy()

    async def scard(self, key: str) -> int:
        """Get cardinality of a set."""
        return len(self._sets.get(key, set()))

    async def srem(self, key: str, *members: str) -> int:
        """Remove members from a set."""
        if key not in self._sets:
            return 0
        removed = sum(1 for m in members if m in self._sets[key])
        for m in members:
            self._sets[key].discard(m)
        return removed

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key."""
        return True

    async def hset(
        self, key: str, mapping: dict[str, str] | str | None = None, field: str | None = None, value: str | None = None, **kwargs: Any
    ) -> int:
        """Set hash fields. Supports both old and new redis-py signatures.

        Old API: hset(key, field, value)
        New API: hset(key, mapping={...}) or hset(key, **kwargs)
        """
        if key not in self._hashes:
            self._hashes[key] = {}

        # Support old signature: hset(key, field, value)
        if isinstance(mapping, str) and isinstance(field, str) and value is None:
            # Called as hset(key, field, value) where mapping is actually the field name
            # In this case: mapping="field", field="value", value is None
            update_map = {mapping: field}
        elif isinstance(mapping, dict):
            # Called with dict: hset(key, {"field": "value"})
            update_map = mapping
        elif mapping is None:
            # Called with kwargs: hset(key, field="value")
            update_map = kwargs
        else:
            # Fallback for other cases
            update_map = mapping or kwargs

        added = sum(1 for k in update_map if k not in self._hashes[key])
        self._hashes[key].update(update_map)
        return added

    async def hget(self, key: str, field: str) -> str | None:
        """Get a hash field."""
        return self._hashes.get(key, {}).get(field)

    async def hgetall(self, key: str) -> dict[str, str]:
        """Get all fields in a hash."""
        return self._hashes.get(key, {}).copy()

    async def hmget(self, key: str, fields: list[str]) -> list[str | None]:
        """Get multiple field values from a hash."""
        if key not in self._hashes:
            return [None] * len(fields)
        return [self._hashes[key].get(field) for field in fields]

    async def hincrby(self, key: str, field: str, increment: int) -> int:
        """Increment a hash field."""
        if key not in self._hashes:
            self._hashes[key] = {}
        current = int(self._hashes[key].get(field, 0))
        new_val = current + increment
        self._hashes[key][field] = str(new_val)
        return new_val

    async def hdel(self, key: str, *fields: str) -> int:
        """Delete hash fields."""
        if key not in self._hashes:
            return 0
        deleted = sum(1 for f in fields if f in self._hashes[key])
        for f in fields:
            self._hashes[key].pop(f, None)
        return deleted

    async def hlen(self, key: str) -> int:
        """Get number of fields in a hash."""
        return len(self._hashes.get(key, {}))

    async def incrby(self, key: str, increment: int = 1) -> str:
        """Increment a counter."""
        current = int(self._data.get(key, 0))
        new_val = current + increment
        self._data[key] = str(new_val)
        return str(new_val)

    async def incrbyfloat(self, key: str, increment: float) -> float:
        """Increment a float counter."""
        current = float(self._data.get(key, 0))
        new_val = current + increment
        self._data[key] = str(new_val)
        return new_val

    async def delete(self, *keys: str) -> int:
        """Delete keys."""
        deleted = 0
        for k in keys:
            if k in self._data:
                del self._data[k]
                deleted += 1
            if k in self._sets:
                del self._sets[k]
                deleted += 1
            if k in self._hashes:
                del self._hashes[k]
                deleted += 1
            if k in self._sorted_sets:
                del self._sorted_sets[k]
                deleted += 1
        return deleted

    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        return sum(1 for k in keys if k in self._data or k in self._sets or k in self._hashes or k in self._sorted_sets)

    async def keys(self, pattern: str) -> list[str]:
        """Get all keys matching pattern."""
        import re

        regex = pattern.replace("*", ".*").replace("?", ".")
        regex = f"^{regex}$"
        all_keys = list(self._data.keys()) + list(self._sets.keys()) + list(self._hashes.keys())
        return [k for k in all_keys if re.match(regex, k)]

    async def scan_iter(self, match: str | None = None, count: int | None = None):
        """Scan keys."""
        import re

        if match:
            regex = match.replace("*", ".*").replace("?", ".")
            regex = f"^{regex}$"
            all_keys = list(self._data.keys()) + list(self._sets.keys()) + list(self._hashes.keys())
            keys = [k for k in all_keys if re.match(regex, k)]
        else:
            keys = list(self._data.keys()) + list(self._sets.keys()) + list(self._hashes.keys())

        for key in keys:
            yield key

    async def zadd(self, key: str, mapping: dict[str, float] | None = None, **kwargs) -> int:
        """Add members to a sorted set."""
        if key not in self._sorted_sets:
            self._sorted_sets[key] = {}

        update_map = mapping or kwargs
        added = sum(1 for k in update_map if k not in self._sorted_sets[key])
        self._sorted_sets[key].update(update_map)
        return added

    async def zrangebyscore(self, key: str, min_score: float | str, max_score: float | str, withscores: bool = False) -> list:
        """Get members of a sorted set by score range."""
        if key not in self._sorted_sets:
            return []

        min_val = float(min_score) if isinstance(min_score, str) else min_score
        max_val = float(max_score) if isinstance(max_score, str) else max_score

        members = self._sorted_sets[key]
        filtered = [(m, s) for m, s in members.items() if min_val <= s <= max_val]
        filtered.sort(key=lambda x: x[1])

        if withscores:
            return filtered
        return [m for m, _ in filtered]

    async def ping(self) -> str:
        """Ping the Redis server."""
        return "PONG"

    async def publish(self, channel: str, message: str) -> int:
        """Publish message to channel."""
        self.published.append((channel, message))
        return 1

    def pipeline(self, transaction: bool = True):
        """Create a pipeline context."""
        return FakeRedisPipeline(self, transaction=transaction)

    def dump_set(self, key: str) -> set[str]:
        """Dump contents of a set (test helper)."""
        return self._sets.get(key, set()).copy()

    def dump_hash(self, key: str) -> dict[str, str]:
        """Dump contents of a hash (test helper)."""
        return self._hashes.get(key, {}).copy()

    def dump_string(self, key: str) -> str | None:
        """Dump contents of a string (test helper)."""
        return self._data.get(key)


class FakeRedisPipeline:
    """Redis pipeline mock."""

    def __init__(self, fake_redis: FakeRedis, transaction: bool = True):
        self.fake_redis = fake_redis
        self.transaction = transaction
        self.commands: list[tuple[str, Any]] = []

    def set(self, key: str, value: str | bytes) -> "FakeRedisPipeline":
        """Pipeline set."""
        self.commands.append(("set", (key, value)))
        return self

    def sadd(self, key: str, *members: str) -> "FakeRedisPipeline":
        """Pipeline sadd."""
        self.commands.append(("sadd", (key, members)))
        return self

    def hset(
        self, key: str, mapping: dict[str, str] | str | None = None, field: str | None = None, value: str | None = None, **kwargs: str
    ) -> "FakeRedisPipeline":
        """Pipeline hset. Supports both old and new redis-py signatures.

        Old API: hset(key, field, value)
        New API: hset(key, mapping={...}) or hset(key, **kwargs)
        """
        if isinstance(mapping, str) and isinstance(field, str) and value is None:
            # Old API: hset(key, field, value) where mapping is actually the field name
            update_map = {mapping: field}
        elif isinstance(mapping, dict):
            # New API with dict: hset(key, {"field": "value"})
            update_map = mapping
        elif mapping is None:
            # New API with kwargs: hset(key, field="value")
            update_map = kwargs
        else:
            # Fallback
            update_map = mapping or kwargs

        self.commands.append(("hset", (key, update_map)))
        return self

    def hget(self, key: str, field: str) -> "FakeRedisPipeline":
        """Pipeline hget."""
        self.commands.append(("hget", (key, field)))
        return self

    def hincrby(self, key: str, field: str, increment: int) -> "FakeRedisPipeline":
        """Pipeline hincrby."""
        self.commands.append(("hincrby", (key, field, increment)))
        return self

    def expire(self, key: str, seconds: int) -> "FakeRedisPipeline":
        """Pipeline expire."""
        self.commands.append(("expire", (key, seconds)))
        return self

    def hdel(self, key: str, *fields: str) -> "FakeRedisPipeline":
        """Pipeline hdel."""
        self.commands.append(("hdel", (key, fields)))
        return self

    def delete(self, *keys: str) -> "FakeRedisPipeline":
        """Pipeline delete."""
        self.commands.append(("delete", keys))
        return self

    def exists(self, *keys: str) -> "FakeRedisPipeline":
        """Pipeline exists."""
        self.commands.append(("exists", keys))
        return self

    def srem(self, key: str, *members: str) -> "FakeRedisPipeline":
        """Pipeline srem."""
        self.commands.append(("srem", (key, members)))
        return self

    def publish(self, channel: str, message: str) -> "FakeRedisPipeline":
        """Pipeline publish (no-op)."""
        self.commands.append(("publish", (channel, message)))
        return self

    async def _execute_command(self, cmd: str, args: tuple) -> Any:
        """Execute a single command. Dispatch based on command type."""
        dispatcher = {
            "set": lambda: self.fake_redis.set(args[0], args[1]),
            "sadd": lambda: self.fake_redis.sadd(args[0], *args[1]),
            "hset": lambda: self.fake_redis.hset(args[0], args[1]),
            "hget": lambda: self.fake_redis.hget(args[0], args[1]),
            "hincrby": lambda: self.fake_redis.hincrby(args[0], args[1], args[2]),
            "expire": lambda: self.fake_redis.expire(args[0], args[1]),
            "hdel": lambda: self.fake_redis.hdel(args[0], *args[1]),
            "delete": lambda: self.fake_redis.delete(*args),
            "exists": lambda: self.fake_redis.exists(*args),
            "srem": lambda: self.fake_redis.srem(args[0], *args[1]),
            "publish": lambda: self.fake_redis.publish(args[0], args[1]),
        }
        handler = dispatcher.get(cmd)
        return await handler() if handler else None

    async def execute(self) -> list[Any]:
        """Execute all commands."""
        results = []
        for cmd, args in self.commands:
            result = await self._execute_command(cmd, args)
            results.append(result)
        self.commands.clear()
        return results

    async def __aenter__(self) -> "FakeRedisPipeline":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args):
        """Async context manager exit."""
        await self.execute()


@pytest.fixture
def fake_redis() -> FakeRedis:
    """Provide a fake Redis instance."""
    return FakeRedis()


@pytest.fixture
def fake_redis_client_factory(monkeypatch):
    """Provide a factory for creating patched fake Redis clients."""

    def factory(module_path: str = "") -> FakeRedis:
        """Create a fake Redis and patch it into the specified module."""
        fake = FakeRedis()

        # Patch redis.asyncio.Redis
        monkeypatch.setattr("redis.asyncio.Redis", lambda *args, **kwargs: fake)

        # Patch the module's get_redis_pool or similar function
        if module_path and "get_redis_pool" in module_path:
            target_module = module_path.rsplit(".", 1)[0]
            monkeypatch.setattr(
                f"{target_module}.get_redis_pool",
                AsyncMock(return_value=fake),
            )

        return fake

    return factory


@pytest.fixture
def stub_schema_config(monkeypatch):
    """Provide a stub schema config."""
    from common.config.redis_schema import RedisSchemaConfig

    stub = RedisSchemaConfig(
        kalshi_market_prefix="markets:kalshi",
        kalshi_weather_prefix="weather:kalshi",
        kalshi_subscriptions_key="subscriptions:kalshi",
        kalshi_subscription_ids_key="subscription_ids:kalshi",
        kalshi_trading_active_key="trading_active:kalshi",
        kalshi_exchange_active_key="exchange_active:kalshi",
        deribit_market_prefix="markets:deribit",
        deribit_spot_prefix="spot:deribit",
        deribit_gp_surface_prefix="surface:deribit",
        deribit_gp_metadata_key="metadata:deribit",
        deribit_subscriptions_key="subscriptions:deribit",
        deribit_instrument_lookup_key="instruments:deribit",
        weather_station_prefix="stations:weather",
        weather_station_history_prefix="history:weather",
        weather_station_mapping_key="mapping:weather",
        weather_forecast_prefix="forecast:weather",
        weather_features_prefix="features:weather",
        weather_rule_4_trigger_suffix="rule4",
        pdf_phase4_filters_key="filters:pdf",
        monitoring_status_prefix="status:monitoring",
        monitoring_history_prefix="history:monitoring",
        monitoring_monitor_jobs_prefix="jobs:monitoring",
        cfb_price_prefix="prices:cfb",
    )

    # Mock the class variable and the load method
    monkeypatch.setattr(RedisSchemaConfig, "_instance", stub)
    monkeypatch.setattr("common.config.redis_schema.get_schema_config", lambda: stub)

    return stub


@pytest.fixture
def schema_config_factory(monkeypatch):
    """Provide a factory for creating custom schema configs."""
    from common.config.redis_schema import RedisSchemaConfig

    def factory(**kwargs) -> RedisSchemaConfig:
        """Create and set a schema config."""
        config = RedisSchemaConfig(
            kalshi_market_prefix=kwargs.get("kalshi_market_prefix", "markets:kalshi"),
            kalshi_weather_prefix=kwargs.get("kalshi_weather_prefix", "weather:kalshi"),
            kalshi_subscriptions_key=kwargs.get("kalshi_subscriptions_key", "subscriptions:kalshi"),
            kalshi_subscription_ids_key=kwargs.get("kalshi_subscription_ids_key", "subscription_ids:kalshi"),
            kalshi_trading_active_key=kwargs.get("kalshi_trading_active_key", "trading_active:kalshi"),
            kalshi_exchange_active_key=kwargs.get("kalshi_exchange_active_key", "exchange_active:kalshi"),
            deribit_market_prefix=kwargs.get("deribit_market_prefix", "markets:deribit"),
            deribit_spot_prefix=kwargs.get("deribit_spot_prefix", "spot:deribit"),
            deribit_gp_surface_prefix=kwargs.get("deribit_gp_surface_prefix", "surface:deribit"),
            deribit_gp_metadata_key=kwargs.get("deribit_gp_metadata_key", "metadata:deribit"),
            deribit_subscriptions_key=kwargs.get("deribit_subscriptions_key", "subscriptions:deribit"),
            deribit_instrument_lookup_key=kwargs.get("deribit_instrument_lookup_key", "instruments:deribit"),
            weather_station_prefix=kwargs.get("weather_station_prefix", "stations:weather"),
            weather_station_history_prefix=kwargs.get("weather_station_history_prefix", "history:weather"),
            weather_station_mapping_key=kwargs.get("weather_station_mapping_key", "mapping:weather"),
            weather_forecast_prefix=kwargs.get("weather_forecast_prefix", "forecast:weather"),
            weather_features_prefix=kwargs.get("weather_features_prefix", "features:weather"),
            weather_rule_4_trigger_suffix=kwargs.get("weather_rule_4_trigger_suffix", "rule4"),
            pdf_phase4_filters_key=kwargs.get("pdf_phase4_filters_key", "filters:pdf"),
            monitoring_status_prefix=kwargs.get("monitoring_status_prefix", "status:monitoring"),
            monitoring_history_prefix=kwargs.get("monitoring_history_prefix", "history:monitoring"),
            monitoring_monitor_jobs_prefix=kwargs.get("monitoring_monitor_jobs_prefix", "jobs:monitoring"),
            cfb_price_prefix=kwargs.get("cfb_price_prefix", "prices:cfb"),
        )
        # Set as the global default
        monkeypatch.setattr(RedisSchemaConfig, "_instance", config)
        monkeypatch.setattr("common.config.redis_schema.get_schema_config", lambda: config)
        return config

    return factory
