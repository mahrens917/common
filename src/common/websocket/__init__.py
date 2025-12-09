"""
Common WebSocket infrastructure for unified subscription management and health monitoring.

This module provides shared components for both Deribit and Kalshi WebSocket services:
- Unified subscription management via Redis pub/sub
- Common message statistics collection
- Fail-fast connection health monitoring
- Sequence validation utilities

Following fail-fast principles, all components raise exceptions on critical failures
rather than silently continuing with degraded functionality.
"""

from .connection_health_monitor import ConnectionHealthMonitor
from .message_stats_collector import MessageStatsCollector
from .sequence_validator import SequenceValidator
from .subscription_manager import UnifiedSubscriptionManager

__all__ = [
    "MessageStatsCollector",
    "ConnectionHealthMonitor",
    "UnifiedSubscriptionManager",
    "SequenceValidator",
]
