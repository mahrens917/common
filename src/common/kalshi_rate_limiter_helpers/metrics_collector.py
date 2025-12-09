"""Metrics collection for rate limiter"""

import time
from typing import Any, Dict

# Constants
_CONST_50 = 50
_CONST_80 = 80


class MetricsCollector:
    """Collects and formats rate limiter metrics"""

    def __init__(
        self,
        read_queue,
        write_queue,
        token_manager,
    ):
        self.read_queue = read_queue
        self.write_queue = write_queue
        self.token_manager = token_manager

    def get_queue_metrics(self) -> Dict[str, Any]:
        """Get current queue status for monitoring"""
        return {
            "read_queue_depth": self.read_queue.qsize(),
            "write_queue_depth": self.write_queue.qsize(),
            "read_tokens_available": self.token_manager.read_tokens,
            "write_tokens_available": self.token_manager.write_tokens,
            "read_queue_capacity": self.read_queue.maxsize,
            "write_queue_capacity": self.write_queue.maxsize,
            "max_read_tokens": self.token_manager.max_read_tokens,
            "max_write_tokens": self.token_manager.max_write_tokens,
            "timestamp": time.time(),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get rate limiter health status"""
        metrics = self.get_queue_metrics()

        # Calculate queue utilization percentages
        read_utilization = (metrics["read_queue_depth"] / metrics["read_queue_capacity"]) * 100
        write_utilization = (metrics["write_queue_depth"] / metrics["write_queue_capacity"]) * 100

        # Determine health status based on queue utilization
        if read_utilization > _CONST_80 or write_utilization > _CONST_80:
            status = "DEGRADED"
        elif read_utilization > _CONST_50 or write_utilization > _CONST_50:
            status = "WARNING"
        else:
            status = "HEALTHY"

        return {
            "status": status,
            "read_queue_utilization_percent": read_utilization,
            "write_queue_utilization_percent": write_utilization,
            "timestamp": time.time(),
        }
