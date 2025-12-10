from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

import pytest

from common.telegram_utils import BaseTelegramCommandHandler


class _DummyAlerter:
    def __init__(self):
        self.alerts: list[Dict[str, Any]] = []
        self.registered: dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}

    async def send_alert(self, message: str, *, alert_type: str) -> None:
        self.alerts.append({"message": message, "alert_type": alert_type})

    def register_command_handler(
        self, command: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        self.registered[command] = handler


class _BasicAlerter:
    def __init__(self):
        self.alerts: list[str] = []

    async def send_alert(self, message: str, *, alert_type: str) -> None:
        self.alerts.append(f"{alert_type}:{message}")


@pytest.mark.asyncio
async def test_send_uses_alerter():
    alerter = _DummyAlerter()
    handler = BaseTelegramCommandHandler(alerter, alert_type="weather")

    await handler._send("hello")

    assert alerter.alerts == [{"message": "hello", "alert_type": "weather"}]


def test_register_command_noop_when_unsupported():
    alerter = _BasicAlerter()
    handler = BaseTelegramCommandHandler(alerter, alert_type="alert")

    handler.register_command("/ping", lambda _: None)  # type: ignore[arg-type]

    assert not hasattr(alerter, "registered")


@pytest.mark.asyncio
async def test_register_command_delegates_when_supported():
    alerter = _DummyAlerter()
    handler = BaseTelegramCommandHandler(alerter, alert_type="weather")

    async def command(update: Dict[str, Any]) -> None:
        alerter.alerts.append({"message": update["text"]})

    handler.register_command("/status", command)
    assert "/status" in alerter.registered

    await alerter.registered["/status"]({"text": "ok"})
    assert alerter.alerts[-1] == {"message": "ok"}


@pytest.mark.asyncio
async def test_create_handler_wrapper_executes_inner(monkeypatch):
    alerter = _BasicAlerter()
    handler = BaseTelegramCommandHandler(alerter, alert_type="alert")

    calls: list[Dict[str, Any]] = []

    async def inner(update: Dict[str, Any]) -> None:
        calls.append(update)

    wrapper = handler.create_handler_wrapper(inner)
    await wrapper({"text": "wrapped"})

    assert calls == [{"text": "wrapped"}]
