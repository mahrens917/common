from __future__ import annotations

"""Operational Redis key helpers (subscriptions, status, metrics)."""


from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .namespaces import KeyBuilder, RedisNamespace, sanitize_segment
from .validators import register_namespace

register_namespace("ops:subscriptions:", "Per-service subscription registries")
register_namespace("ops:status:", "Service lifecycle states")
register_namespace("ops:metrics:", "Operational metrics streams")


class SubscriptionType(str, Enum):
    """Subscription types supported across services."""

    INSTRUMENT = "instrument"
    PRICE_INDEX = "price_index"
    VOLATILITY_INDEX = "volatility_index"


@dataclass(frozen=True)
class SubscriptionKey:
    """Hash key for a service's active subscriptions."""

    service: str

    def key(self) -> str:
        segments = ["subscriptions", sanitize_segment(self.service)]
        builder = KeyBuilder(RedisNamespace.OPERATIONS, tuple(segments))
        return builder.render()

    def field(self, sub_type: SubscriptionType, name: str) -> str:
        return f"{sub_type.value}:{sanitize_segment(name)}"


@dataclass(frozen=True)
class ServiceStatusKey:
    """Hash key tracking a service's lifecycle state."""

    service: str

    def key(self) -> str:
        segments = ["status", sanitize_segment(self.service)]
        builder = KeyBuilder(RedisNamespace.OPERATIONS, tuple(segments))
        return builder.render()


@dataclass(frozen=True)
class MetricStreamKey:
    """Key for operational metrics (hash or sorted set)."""

    service: str
    metric: str
    window: Optional[str] = None

    def key(self) -> str:
        segments = ["metrics", sanitize_segment(self.service), sanitize_segment(self.metric)]
        if self.window:
            segments.append(sanitize_segment(self.window))
        builder = KeyBuilder(RedisNamespace.OPERATIONS, tuple(segments))
        return builder.render()
