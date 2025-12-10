import asyncio
import os
import signal
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

from common import service_runner


@pytest.mark.skipif(service_runner.fcntl is None, reason="fcntl not available on this platform")
def test_service_instance_lock_acquire_release(tmp_path, monkeypatch):
    monkeypatch.setenv("SERVICE_RUNTIME_DIR", str(tmp_path))
    lock = service_runner.ServiceInstanceLock("sample_service")
    lock.acquire()
    assert lock.lock_path.exists()
    lock.release()
    assert not lock.lock_path.exists()


def test_single_instance_guard_context_manager(monkeypatch):
    if service_runner.fcntl is None:
        pytest.skip("fcntl required for single_instance_guard test")

    tmp_path = Path(os.getcwd()) / "tmp_runtime_guard"
    tmp_path.mkdir(exist_ok=True)
    monkeypatch.setenv("SERVICE_RUNTIME_DIR", str(tmp_path))

    with service_runner.single_instance_guard("guarded"):
        with pytest.raises(service_runner.SingleInstanceError):
            with service_runner.single_instance_guard("guarded"):
                pass


def test_run_async_service_handles_keyboard_interrupt(monkeypatch, caplog):
    executed = {}

    async def factory():
        executed["ran"] = True
        raise KeyboardInterrupt()

    @contextmanager
    def fake_guard(_):
        yield

    monkeypatch.setattr(service_runner, "single_instance_guard", fake_guard)
    monkeypatch.setattr(service_runner, "setup_logging", lambda name: None)
    monkeypatch.setattr(service_runner, "ensure_single_instance_sync", lambda name: None)

    with caplog.at_level("INFO"):
        service_runner.run_async_service(factory, service_name="test_service")

    assert executed.get("ran") is True
    assert any("interrupted by user" in record.message for record in caplog.records)


def test_run_async_service_propagates_other_exceptions(monkeypatch):
    async def factory():
        raise RuntimeError("boom")

    @contextmanager
    def fake_guard(_):
        yield

    monkeypatch.setattr(service_runner, "single_instance_guard", fake_guard)
    monkeypatch.setattr(service_runner, "setup_logging", lambda name: None)
    monkeypatch.setattr(service_runner, "ensure_single_instance_sync", lambda name: None)

    with pytest.raises(RuntimeError):
        service_runner.run_async_service(factory, service_name="boom_service")


def test_run_async_service_handles_missing_sighup(monkeypatch, caplog):
    async def factory():
        pass

    @contextmanager
    def fake_guard(_):
        yield

    real_signal = signal.signal

    def fake_signal(signum, handler):
        if signum == signal.SIGHUP:
            raise AttributeError("no signal")
        return real_signal(signum, handler)

    monkeypatch.setattr(service_runner, "single_instance_guard", fake_guard)
    monkeypatch.setattr(service_runner, "setup_logging", lambda name: None)
    monkeypatch.setattr(service_runner.signal, "signal", fake_signal)
    monkeypatch.setattr(service_runner, "ensure_single_instance_sync", lambda name: None)

    with caplog.at_level("DEBUG"):
        service_runner.run_async_service(
            factory, service_name="sig_service", ignore_sighup=True, logger_name="test.logger"
        )

    assert any("SIGHUP not available" in record.message for record in caplog.records)
