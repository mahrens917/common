from __future__ import annotations

import asyncio
import logging
import weakref

import pytest

from src.common import alerter_factory


class DummyAlerter:
    def __init__(self):
        self.cleaned = False

    async def cleanup(self):
        self.cleaned = True


def test_register_shutdown_hook_registers_once(monkeypatch):
    registry = weakref.WeakSet()
    monkeypatch.setattr(alerter_factory, "_shutdown_registry", registry)

    registered = []

    def fake_register(func):
        registered.append(func)

    monkeypatch.setattr(alerter_factory.atexit, "register", fake_register)

    alerter = DummyAlerter()
    alerter_factory._register_shutdown_hook(alerter)  # type: ignore[attr-defined]
    alerter_factory._register_shutdown_hook(alerter)  # type: ignore[attr-defined]

    assert len(registered) == 1
    assert alerter in registry


def test_register_shutdown_hook_handles_missing_event_loop(monkeypatch):
    registry = weakref.WeakSet()
    monkeypatch.setattr(alerter_factory, "_shutdown_registry", registry)

    registered = []

    def fake_register(func):
        registered.append(func)

    monkeypatch.setattr(alerter_factory.atexit, "register", fake_register)

    dummy = DummyAlerter()

    def fail_run(coro):
        coro.close()
        raise RuntimeError("no loop")

    monkeypatch.setattr(alerter_factory.asyncio, "run", fail_run)

    loops = []
    original_new_loop = asyncio.new_event_loop

    def fake_new_loop():
        loop = original_new_loop()
        loops.append(loop)
        return loop

    monkeypatch.setattr(alerter_factory.asyncio, "new_event_loop", fake_new_loop)

    alerter_factory._register_shutdown_hook(dummy)  # type: ignore[attr-defined]
    cleanup = registered[0]
    cleanup()

    assert dummy.cleaned is True
    assert loops
    for loop in loops:
        assert loop.is_closed()


def test_create_alerter_for_service_logs(monkeypatch, caplog):
    created = DummyAlerter()
    monkeypatch.setattr(alerter_factory, "create_alerter", lambda: created)

    with caplog.at_level(logging.INFO):
        alerter = alerter_factory.create_alerter_for_service("weather")

    assert alerter is created
    assert "Created Alerter instance for service" in caplog.text
