"""Builder for Alerter components to reduce __init__ complexity."""

import logging
from typing import Any, Dict

from ..alerting import AlertThrottle
from .alert_formatter import AlertFormatter
from .alert_suppression_manager import AlertSuppressionManager
from .components_builder_helpers import TelegramBuilder
from .price_validation_tracker import PriceValidationTracker

logger = logging.getLogger(__name__)


class AlerterComponentsBuilder:
    """Builds all components needed for Alerter initialization."""

    def __init__(self, settings):
        """Initialize with monitor settings."""
        self.settings = settings
        self.result: Dict[str, Any] = {}

    def build(
        self, send_alert_callback, flush_callback, ensure_processor_callback
    ) -> Dict[str, Any]:
        """Build and return all alerter components."""
        self.result.update(TelegramBuilder.build_telegram_config(self.settings))
        self._build_core_helpers()
        self._build_throttle()

        if self.result["telegram_enabled"]:
            self.result.update(
                TelegramBuilder.build_basic_and_command_components(self.result, send_alert_callback)
            )
            self.result.update(
                TelegramBuilder.build_polling_components(
                    self.result, send_alert_callback, flush_callback, ensure_processor_callback
                )
            )

        return self.result

    def _build_core_helpers(self) -> None:
        """Build core helper components."""
        self.result.update(
            {
                "alert_formatter": AlertFormatter(),
                "suppression_manager": AlertSuppressionManager(),
                "price_validation_tracker": PriceValidationTracker(),
            }
        )

    def _build_throttle(self) -> None:
        """Build throttle configuration."""
        self.result["alert_throttle"] = AlertThrottle(
            self.settings.alerting.throttle_window_seconds,
            self.settings.alerting.max_alerts_per_window,
        )
