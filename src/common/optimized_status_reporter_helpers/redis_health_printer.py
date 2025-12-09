"""
Redis health section printer.

Formats and prints Redis health check information.
"""

from typing import Any, Dict

from .base_printer import StatusLinePrinterBase


class RedisHealthPrinter(StatusLinePrinterBase):
    """Prints Redis health section."""

    def print_redis_health_section(self, status_data: Dict[str, Any]) -> None:
        """Print Redis health check section."""
        self._emit_status_line()
        self._emit_status_line("🔍 Redis Health Check:")
        redis_health = status_data.get("redis_health_check")

        if status_data["redis_connection_healthy"]:
            self._print_healthy_redis(redis_health, status_data)
        else:
            self._print_failed_redis(redis_health)

    def _print_healthy_redis(self, redis_health: Any, status_data: Dict[str, Any]) -> None:
        """Print healthy Redis connection details."""
        if redis_health and hasattr(redis_health, "details") and redis_health.details:
            details = self.data_coercion.coerce_mapping(redis_health.details)
            ping_duration = self.data_coercion.float_or_default(details.get("ping_duration"), 0.0)
            pool_metrics = self.data_coercion.coerce_mapping(details.get("connection_pool_metrics"))

            if redis_health.status.value == "degraded":
                self._emit_status_line(f"  ⚠️ Redis Connection - Slow (ping: {ping_duration:.3f}s)")
            else:
                self._emit_status_line(
                    f"  🟢 Redis Connection - Healthy (ping: {ping_duration:.3f}s)"
                )

            if pool_metrics:
                reuse_rate = (
                    self.data_coercion.float_or_default(
                        pool_metrics.get("connection_reuse_rate"), 0.0
                    )
                    * 100
                )
                connection_errors = self.data_coercion.int_or_default(
                    pool_metrics.get("connection_errors"), 0
                )
                self._emit_status_line(f"  📊 Pool Reuse Rate: {reuse_rate:.1f}%")
                if connection_errors > 0:
                    self._emit_status_line(f"  ⚠️ Connection Errors: {connection_errors}")
        else:
            self._emit_status_line("  🟢 Redis Connection - Healthy")

        # Print key counts
        self._emit_status_line(
            f"  🟢 Deribit Market Data - {status_data['redis_deribit_keys']:,} keys"
        )
        self._emit_status_line(
            f"  🟢 Kalshi Market Data - {status_data['redis_kalshi_keys']:,} keys"
        )
        self._emit_status_line(f"  🟢 CFB Price Data - {status_data['redis_cfb_keys']:,} keys")
        self._emit_status_line(f"  🟢 Weather Data - {status_data['redis_weather_keys']:,} keys")

    def _print_failed_redis(self, redis_health: Any) -> None:
        """Print failed Redis connection details."""
        if redis_health and hasattr(redis_health, "details") and redis_health.details:
            details = self.data_coercion.coerce_mapping(redis_health.details)
            timeout_value = details.get("timeout_duration")
            error_type_raw = details.get("error_type")
            if timeout_value is not None:
                timeout_duration = self.data_coercion.float_or_default(timeout_value, 0.0)
                self._emit_status_line(f"  🔴 Redis Connection - Timeout ({timeout_duration:.2f}s)")
            elif error_type_raw:
                error_type = self.data_coercion.string_or_default(error_type_raw, "unknown")
                self._emit_status_line(f"  🔴 Redis Connection - Failed ({error_type})")
            else:
                self._emit_status_line("  🔴 Redis Connection - Failed")
            self._emit_status_line(f"  ⚠️ Error: {redis_health.message}")
        else:
            self._emit_status_line("  🔴 Redis Connection - Failed")
