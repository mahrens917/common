"""
Optimized data structures for status reporting with __slots__ for memory efficiency.
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class ServiceStatus(Enum):
    """Service status enumeration"""

    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ServiceInfo:
    """Optimized service information with __slots__ for memory efficiency"""

    __slots__ = ("name", "status", "process_id", "memory_mb", "messages_60s")

    def __init__(
        self,
        name: str,
        status: ServiceStatus,
        process_id: Optional[int] = None,
        memory_mb: Optional[float] = None,
        messages_60s: int = 0,
    ):
        self.name = name
        self.status = status
        self.process_id = process_id
        self.memory_mb = memory_mb
        self.messages_60s = messages_60s


class SystemMetrics:
    """Optimized system metrics with __slots__"""

    __slots__ = ("cpu_percent", "memory_percent", "disk_percent", "redis_process_id")

    def __init__(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float,
        redis_process_id: Optional[int] = None,
    ):
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent
        self.disk_percent = disk_percent
        self.redis_process_id = redis_process_id


class RedisMetrics:
    """Optimized Redis metrics with __slots__"""

    __slots__ = ("deribit_keys", "kalshi_keys", "cfb_keys", "weather_keys", "connection_healthy")

    def __init__(
        self,
        deribit_keys: int,
        kalshi_keys: int,
        cfb_keys: int,
        weather_keys: int,
        connection_healthy: bool,
    ):
        self.deribit_keys = deribit_keys
        self.kalshi_keys = kalshi_keys
        self.cfb_keys = cfb_keys
        self.weather_keys = weather_keys
        self.connection_healthy = connection_healthy


class PriceData:
    """Optimized price data with __slots__"""

    __slots__ = ("btc_price", "eth_price")

    def __init__(self, btc_price: Optional[float] = None, eth_price: Optional[float] = None):
        self.btc_price = btc_price
        self.eth_price = eth_price


class WeatherInfo:
    """Optimized weather information with __slots__"""

    __slots__ = ("icao_code", "temp_f", "emoticon")

    def __init__(self, icao_code: str, temp_f: float, emoticon: str = "🌡️"):
        self.icao_code = icao_code
        self.temp_f = temp_f
        self.emoticon = emoticon


class StatusReportData:
    """Complete status report data structure with __slots__"""

    __slots__ = (
        "services",
        "system_metrics",
        "redis_metrics",
        "price_data",
        "weather_data",
        "kalshi_market_status",
        "tracker_status",
    )

    def __init__(
        self,
        services: List[ServiceInfo],
        system_metrics: SystemMetrics,
        redis_metrics: RedisMetrics,
        price_data: PriceData,
        weather_data: List[WeatherInfo],
        kalshi_market_status: Dict[str, Any],
        tracker_status: Dict[str, Any],
    ):
        self.services = services
        self.system_metrics = system_metrics
        self.redis_metrics = redis_metrics
        self.price_data = price_data
        self.weather_data = weather_data
        self.kalshi_market_status = kalshi_market_status
        self.tracker_status = tracker_status
