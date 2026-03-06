"""Alert logging with severity-based log level routing."""

from __future__ import annotations

import logging

_SEVERITY_LEVELS: dict[str, int] = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
}


def _resolve_alert_level(severity: str | None) -> int:
    """Return the log level for the given severity string."""
    if severity is not None and severity in _SEVERITY_LEVELS:
        return _SEVERITY_LEVELS[severity]
    return logging.INFO


class AlertLogger:
    """Logs alert payloads at the appropriate severity level for each alert."""

    def __init__(self, service_name: str) -> None:
        self._service_name = service_name
        self._logger = logging.getLogger(f"{__name__}.{service_name}")

    def log_alerts(self, data: dict) -> None:
        """Log each alert in the payload at the level matching its severity."""
        alerts = data.get("alerts")
        if not alerts:
            return
        for alert in alerts:
            level = _resolve_alert_level(alert.get("severity"))
            self._logger.log(level, "%s", alert.get("message"))


__all__ = ["AlertLogger"]
