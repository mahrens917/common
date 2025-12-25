"""Minimal alerter with maximal delegation to helpers."""

from __future__ import annotations

import asyncio
import logging
import sys
import time
import types
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, cast

import aiohttp

from .alerter_helpers.alert_sender import AlertSender
from .alerter_helpers.chart_manager import ChartManager
from .alerter_helpers.command_coordinator import CommandCoordinator
from .alerter_helpers.telegram_rate_limit_handler import TelegramRateLimitHandler
from .alerting import AlertSeverity, AlertThrottle
from .alerting.models import (
    Alert,
    AlerterError,
    PendingTelegramMedia,
    PendingTelegramMessage,
    QueuedCommand,
    TelegramDeliveryResult,
)

if TYPE_CHECKING:
    from src.monitor.settings import MonitorSettings

logger = logging.getLogger(__name__)

# Error types that can occur during alert delivery
ALERT_FAILURE_ERRORS = (
    aiohttp.ClientError,
    asyncio.TimeoutError,
    OSError,
    RuntimeError,
)

__all__ = [
    "Alerter",
    "Alert",
    "AlertSeverity",
    "AlerterError",
    "ALERT_FAILURE_ERRORS",
    "PendingTelegramMedia",
    "PendingTelegramMessage",
    "QueuedCommand",
    "TelegramDeliveryResult",
]

# Provide a module alias for monkeypatch-friendly Path.exists
_path_module_name = __name__ + ".Path"
_path_module = types.ModuleType(_path_module_name)
_path_module.__name__ = _path_module_name
setattr(_path_module, "exists", Path.exists)
sys.modules[_path_module_name] = _path_module


class AlertDispatchMixin:
    telegram_enabled: bool
    delivery_manager: Any
    authorized_user_ids: Optional[list[str]]
    alert_throttle: AlertThrottle | None
    command_processor: Any

    async def send_alert(
        self,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        alert_type: str = "general",
        details: Optional[Dict[str, Any]] = None,
        target_user_id: Optional[str] = None,
    ) -> bool:
        return await _send_alert(
            self,
            message,
            severity,
            alert_type,
            details,
            target_user_id,
        )

    async def send_chart_image(self, image_path: str, caption: str = "", target_user_id: str | None = None) -> bool:
        if not self.telegram_enabled:
            return False
        assert self.delivery_manager is not None
        authorized_user_ids = self.authorized_user_ids
        assert authorized_user_ids is not None
        if target_user_id is not None:
            recipients = [target_user_id]
        else:
            recipients = list(authorized_user_ids)
        if not recipients:
            return False
        return await self.delivery_manager.send_chart(image_path, caption, recipients)

    async def send_chart(self, image_path: str, caption: str = "", target_user_id: str | None = None) -> bool:
        return await self.send_chart_image(image_path, caption, target_user_id)

    def _ensure_proc(self) -> None:
        if self.telegram_enabled:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:  # Expected runtime failure in operation  # policy_guard: allow-silent-handler
                logger.debug("No running event loop, skipping command processor start")
            else:
                asyncio.create_task(self.command_processor.start())

    async def _flush(self) -> None:
        return None


class CommandHandlersMixin:
    command_registry: Any
    command_coordinator: Any
    polling_coordinator: Any
    command_processor: Any
    telegram_enabled: bool

    def _register_cmds(self) -> None:
        from .telegram_surface_handler import TelegramSurfaceHandler

        self.command_registry.register_command_handler("help", self.command_coordinator.handle_help)
        self.command_registry.register_command_handler("load", self.command_coordinator.handle_load)
        self.command_registry.register_command_handler("price", self.command_coordinator.handle_price)
        self.command_registry.register_command_handler("temp", self.command_coordinator.handle_temp)
        self.command_registry.register_command_handler("pnl", self.command_coordinator.handle_pnl)
        TelegramSurfaceHandler(self).register_surface_command()

    def register_command_handler(self, command: str, handler: Callable) -> None:
        if self.telegram_enabled:
            assert self.command_registry is not None
            self.command_registry.register_command_handler(command, handler)

    async def poll_telegram_updates(self) -> None:
        if self.telegram_enabled:
            assert self.polling_coordinator is not None
            await self.polling_coordinator.poll_updates()

    @property
    def command_queue(self):
        if not self.telegram_enabled:
            return None
        assert self.command_processor is not None
        return self.command_processor.command_queue

    @property
    def last_update_id(self):
        if not self.telegram_enabled:
            return None
        assert self.polling_coordinator is not None
        return self.polling_coordinator.update_processor.last_update_id

    @property
    def queue_processor_task(self):
        if not self.telegram_enabled:
            return None
        assert self.command_processor is not None
        return self.command_processor.processor_task


class RateLimitMixin:
    telegram_enabled: bool
    rate_limit_handler: Any

    @property
    def _last_429_time(self):
        if not self.telegram_enabled:
            return None
        handler = self.rate_limit_handler
        if handler is None:
            return None
        return handler._last_429_time

    @property
    def _last_429_backoff_seconds(self):
        if not self.telegram_enabled:
            return None
        handler = self.rate_limit_handler
        if handler is None:
            return None
        return handler._last_429_backoff_seconds

    @property
    def _429_count(self) -> int | None:
        if not self.telegram_enabled:
            return None
        handler = self.rate_limit_handler
        if handler is None:
            return None
        return handler._429_count


class PriceValidationMixin:
    chart_manager: Any
    price_tracker: Any

    def set_metrics_recorder(self, recorder) -> None:
        self.chart_manager.set_metrics_recorder(recorder)

    def should_send_price_validation_alert(self, currency: str, details: Dict[str, Any]) -> bool:
        return self.price_tracker.should_send_alert(currency, details)

    def clear_price_validation_alert(self, currency: str) -> bool:
        return self.price_tracker.clear_alert(currency)

    def is_price_validation_alert_active(self, currency: str) -> bool:
        return self.price_tracker.is_alert_active(currency)


class Alerter(
    AlertDispatchMixin,
    CommandHandlersMixin,
    RateLimitMixin,
    PriceValidationMixin,
):
    """Minimal alerter - all logic delegated to helpers."""

    def __init__(self, settings: MonitorSettings | None = None):
        from .alerter_helpers.alerter_components_builder import AlerterComponentsBuilder

        if settings is None:
            try:
                from src.monitor.settings import get_monitor_settings

                settings = get_monitor_settings()
            except (ModuleNotFoundError, ImportError):  # pragma: no cover
                # Monitor module not available; raise with helpful message
                logger.debug("Monitor settings not available, Alerter requires monitor repo")
                raise RuntimeError("Alerter requires monitor repository to be installed") from None
        self.settings = settings
        self.rate_limit_handler: TelegramRateLimitHandler | None = None
        self.delivery_manager: Any | None = None
        self.command_registry: Any | None = None
        self.command_processor: Any | None = None
        self.polling_coordinator: Any | None = None
        self.alert_sender: AlertSender | None = None
        c = AlerterComponentsBuilder(self.settings).build(self.send_alert, self._flush, self._ensure_proc)
        self.telegram_enabled, self.authorized_user_ids = (
            c["telegram_enabled"],
            c["authorized_user_ids"],
        )
        self.alert_throttle = c["alert_throttle"]
        self.price_tracker = c["price_validation_tracker"]
        if self.telegram_enabled:
            self.delivery_manager, self.command_registry, self.command_processor = (
                c["delivery_manager"],
                c["command_registry"],
                c["command_processor"],
            )
            self.polling_coordinator, self.rate_limit_handler = (
                c["polling_coordinator"],
                c["rate_limit_handler"],
            )
            self.alert_sender = AlertSender(
                c["suppression_manager"],
                c["alert_throttle"],
                True,
                self.authorized_user_ids,
                self.delivery_manager,
                self._ensure_proc,
            )
        self.chart_manager = ChartManager(self.telegram_enabled)
        self.command_coordinator = CommandCoordinator(self.chart_manager, self.send_alert, self.send_chart_image)
        if self.telegram_enabled:
            self._register_cmds()

    async def cleanup(self) -> None:
        """Stop the command processor when telemetry is enabled."""
        if self.telegram_enabled:
            assert self.command_processor is not None
            await self.command_processor.stop()


async def _send_alert(
    self: Any,
    message: str,
    severity: AlertSeverity = AlertSeverity.INFO,
    alert_type: str = "general",
    details: Optional[Dict[str, Any]] = None,
    target_user_id: Optional[str] = None,
) -> bool:
    alerter = cast("Alerter", self)
    if alerter.telegram_enabled:
        assert alerter.alert_sender is not None
        return await alerter.alert_sender.send_alert(message, severity, alert_type, details, target_user_id)
    alert = Alert(
        message=message,
        severity=severity,
        timestamp=time.time(),
        alert_type=alert_type,
        details=details,
    )
    assert alerter.alert_throttle is not None
    if not alerter.alert_throttle.record(alert):
        return False
    logger.info("Alert (no channels): [%s] %s", severity.value, message)
    return True
