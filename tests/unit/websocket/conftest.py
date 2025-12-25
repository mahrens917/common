import sys
import types
from enum import Enum
from types import SimpleNamespace

import pytest


@pytest.fixture
def dummy_alerts(monkeypatch):
    """Provide a lightweight stand-in for the production alerter module."""
    module = types.ModuleType("src.monitor.alerter")
    alerts = []

    class DummyAlertSeverity(Enum):
        INFO = "info"
        WARNING = "warning"
        CRITICAL = "critical"

    class DummyAlerter:
        def __init__(self):
            self.alerts = alerts

        async def send_alert(self, **kwargs):
            alerts.append(kwargs)

    module.Alerter = DummyAlerter
    module.AlertSeverity = DummyAlertSeverity
    module.alerts = alerts

    monkeypatch.setitem(sys.modules, "src.monitor.alerter", module)

    # Also mock common.alerter to use the DummyAlerter
    common_alerter_module = types.ModuleType("common.alerter")
    common_alerter_module.Alerter = DummyAlerter
    common_alerter_module.AlertSeverity = DummyAlertSeverity
    monkeypatch.setitem(sys.modules, "common.alerter", common_alerter_module)

    # Also mock src.monitor.settings to avoid ImportError when Alerter is instantiated
    settings_module = types.ModuleType("src.monitor.settings")

    # Create a flexible settings object with __getattr__ to handle any attribute
    class FlexibleNamespace(SimpleNamespace):
        def __getattr__(self, name):
            # Return an empty FlexibleNamespace for any missing attribute
            return FlexibleNamespace()

    dummy_settings = FlexibleNamespace(
        telegram=FlexibleNamespace(
            bot_token="",
            authorized_users=[],
            timeout_seconds=10,
            chat_ids=[],
        ),
        alerting=FlexibleNamespace(
            telegram_timeout_seconds=10,
        ),
    )

    def dummy_get_monitor_settings():
        return dummy_settings

    class DummyMonitorSettings:
        pass

    settings_module.get_monitor_settings = dummy_get_monitor_settings
    settings_module.MonitorSettings = DummyMonitorSettings
    monkeypatch.setitem(sys.modules, "src.monitor.settings", settings_module)

    return alerts
