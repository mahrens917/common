import sys
import types
from enum import Enum

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
    return alerts
