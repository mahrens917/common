import asyncio
import builtins
import importlib
import sys
import types
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from common import process_killer
from tests.helpers.process_killer_test_helper import create_monitor_mock

REAL_CONSOLE = process_killer._console


class FakeProcess:
    def __init__(self, pid: int, wait_side_effects=None):
        self.pid = pid
        self.wait_side_effects = list(wait_side_effects or [])
        self.wait_calls = []
        self.terminate_called = False
        self.kill_called = False

    def terminate(self):
        self.terminate_called = True

    def wait(self, timeout: float):
        self.wait_calls.append(timeout)
        if self.wait_side_effects:
            effect = self.wait_side_effects.pop(0)
            if isinstance(effect, BaseException):
                raise effect
            return effect
        return None

    def kill(self):
        self.kill_called = True


@pytest.fixture
def psutil_stub(monkeypatch):
    module = types.ModuleType("psutil")

    class TimeoutExpired(Exception):
        pass

    class NoSuchProcess(Exception):
        pass

    class AccessDenied(Exception):
        pass

    module.TimeoutExpired = TimeoutExpired
    module.NoSuchProcess = NoSuchProcess
    module.AccessDenied = AccessDenied

    processes = {}

    def process_factory(pid):
        return processes[pid]

    module.Process = process_factory

    monkeypatch.setitem(sys.modules, "psutil", module)

    return module, processes


@pytest.fixture(autouse=True)
def reset_console(monkeypatch):
    monkeypatch.setattr(process_killer, "_console", lambda message: None)


@pytest.mark.asyncio
async def test_ensure_single_instance_rejects_unknown_service():
    with pytest.raises(ValueError):
        await process_killer.ensure_single_instance("unknown-service")


@pytest.mark.asyncio
async def test_ensure_single_instance_invokes_killer(monkeypatch):
    killer = AsyncMock()
    monkeypatch.setattr(process_killer, "kill_existing_processes", killer)

    await process_killer.ensure_single_instance("kalshi")

    killer.assert_awaited_once_with(process_killer.SERVICE_PROCESS_PATTERNS["kalshi"], "kalshi")


def test_ensure_single_instance_sync_rejects_running_loop(monkeypatch):
    loop = SimpleNamespace(is_running=lambda: True)
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: loop)

    with pytest.raises(RuntimeError):
        process_killer.ensure_single_instance_sync("kalshi")


def test_ensure_single_instance_sync_calls_async(monkeypatch):
    async_call = AsyncMock()
    monkeypatch.setattr(process_killer, "ensure_single_instance", async_call)
    monkeypatch.setattr(asyncio, "get_running_loop", MagicMock(side_effect=RuntimeError()))

    captured: dict[str, Any] = {}

    def fake_run(coro):
        captured["coro"] = coro
        assert asyncio.iscoroutine(coro)
        coro.close()

    monkeypatch.setattr(asyncio, "run", fake_run)

    process_killer.ensure_single_instance_sync("kalshi")

    assert "coro" in captured
    async_call.assert_called_once_with("kalshi")


@pytest.mark.asyncio
async def test_kill_existing_processes_terminates_match(monkeypatch, psutil_stub):
    module, processes = psutil_stub
    process = FakeProcess(
        pid=1000,
        wait_side_effects=[None],
    )
    processes[1000] = process

    monitor = create_monitor_mock(
        {
            1000: SimpleNamespace(
                name="python3",
                cmdline=["python", "-m", "src.kalshi"],
            )
        }
    )

    process_monitor_module = importlib.import_module("common.process_monitor")
    monkeypatch.setattr(
        process_monitor_module,
        "get_global_process_monitor",
        AsyncMock(return_value=monitor),
    )
    monkeypatch.setattr(process_killer.os, "getpid", lambda: 999)
    sleep_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(process_killer.asyncio, "sleep", sleep_mock)

    await process_killer.kill_existing_processes(
        process_killer.SERVICE_PROCESS_PATTERNS["kalshi"],
        service_name="kalshi",
    )

    assert process.terminate_called
    assert not process.kill_called
    assert process.wait_calls == [process_killer.GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS]
    sleep_mock.assert_awaited_once_with(process_killer.POST_KILL_WAIT_SECONDS)


@pytest.mark.asyncio
async def test_kill_existing_processes_force_kill_on_timeout(monkeypatch, psutil_stub):
    module, processes = psutil_stub
    timeout = module.TimeoutExpired()
    process = FakeProcess(
        pid=2000,
        wait_side_effects=[timeout, None],
    )
    processes[2000] = process

    monitor = create_monitor_mock(
        {
            2000: SimpleNamespace(
                name="python3",
                cmdline=["python", "-m", "src.kalshi"],
            )
        }
    )

    process_monitor_module = importlib.import_module("common.process_monitor")
    monkeypatch.setattr(
        process_monitor_module,
        "get_global_process_monitor",
        AsyncMock(return_value=monitor),
    )
    monkeypatch.setattr(process_killer.os, "getpid", lambda: 999)
    sleep_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(process_killer.asyncio, "sleep", sleep_mock)

    await process_killer.kill_existing_processes(
        process_killer.SERVICE_PROCESS_PATTERNS["kalshi"],
        service_name="kalshi",
    )

    assert process.terminate_called
    assert process.kill_called
    assert process.wait_calls == [
        process_killer.GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS,
        process_killer.FORCE_KILL_TIMEOUT_SECONDS,
    ]
    sleep_mock.assert_awaited_once_with(process_killer.POST_KILL_WAIT_SECONDS)


@pytest.mark.asyncio
async def test_kill_existing_processes_skips_when_no_matches(monkeypatch, psutil_stub):
    module, processes = psutil_stub
    module.Process = MagicMock(side_effect=AssertionError("Process lookup should not occur"))

    monitor = create_monitor_mock(
        {
            500: SimpleNamespace(
                name="python3",
                cmdline=["python", "-m", "src.kalshi"],
            )
        }
    )

    process_monitor_module = importlib.import_module("common.process_monitor")
    monkeypatch.setattr(
        process_monitor_module,
        "get_global_process_monitor",
        AsyncMock(return_value=monitor),
    )
    monkeypatch.setattr(process_killer.os, "getpid", lambda: 500)
    sleep_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(process_killer.asyncio, "sleep", sleep_mock)

    await process_killer.kill_existing_processes(
        process_killer.SERVICE_PROCESS_PATTERNS["kalshi"],
        service_name="kalshi",
    )

    module.Process.assert_not_called()
    assert sleep_mock.await_args_list == []


def test_console_respects_suppression(monkeypatch, capsys):
    monkeypatch.setattr(process_killer, "SUPPRESS_CONSOLE_OUTPUT", False)
    REAL_CONSOLE("visible")
    assert "visible" in capsys.readouterr().out

    monkeypatch.setattr(process_killer, "SUPPRESS_CONSOLE_OUTPUT", True)
    REAL_CONSOLE("hidden")
    assert capsys.readouterr().out == ""


@pytest.mark.asyncio
async def test_kill_existing_processes_errors_without_psutil(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "psutil":
            raise ImportError("missing psutil")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError):
        await process_killer.kill_existing_processes(["kalshi"], "kalshi")


@pytest.mark.asyncio
async def test_kill_existing_processes_handles_process_lookup_errors(monkeypatch, psutil_stub):
    module, _ = psutil_stub
    module.Process = MagicMock(side_effect=module.AccessDenied("denied"))

    monitor = create_monitor_mock(
        {501: SimpleNamespace(name="python", cmdline=["python", "-m", "src.kalshi"])}
    )

    process_monitor_module = importlib.import_module("common.process_monitor")
    monkeypatch.setattr(
        process_monitor_module,
        "get_global_process_monitor",
        AsyncMock(return_value=monitor),
    )
    monkeypatch.setattr(process_killer.os, "getpid", lambda: 1)

    await process_killer.kill_existing_processes(
        process_killer.SERVICE_PROCESS_PATTERNS["kalshi"], "kalshi"
    )

    assert module.Process.call_count == 1


@pytest.mark.asyncio
async def test_kill_existing_processes_handles_termination_exception(monkeypatch, psutil_stub):
    module, processes = psutil_stub

    class FailingProcess(FakeProcess):
        def terminate(self):
            raise module.AccessDenied("no terminate")

    failing = FailingProcess(pid=602)
    processes[602] = failing

    monitor = create_monitor_mock(
        {602: SimpleNamespace(name="python", cmdline=["python", "-m", "src.kalshi"])}
    )

    process_monitor_module = importlib.import_module("common.process_monitor")
    monkeypatch.setattr(
        process_monitor_module,
        "get_global_process_monitor",
        AsyncMock(return_value=monitor),
    )
    monkeypatch.setattr(process_killer.os, "getpid", lambda: 0)

    await process_killer.kill_existing_processes(
        process_killer.SERVICE_PROCESS_PATTERNS["kalshi"], "kalshi"
    )

    assert not failing.kill_called


@pytest.mark.asyncio
async def test_kill_all_service_processes_invokes_killers(monkeypatch):
    patterns = {"svc1": ["svc1"], "svc2": ["svc2"]}
    monkeypatch.setattr(process_killer, "SERVICE_PROCESS_PATTERNS", patterns, raising=False)

    killer = AsyncMock()
    monkeypatch.setattr(process_killer, "_kill_processes_without_current_exclusion", killer)

    await process_killer.kill_all_service_processes()

    assert killer.await_args_list == [
        ((patterns["svc1"], "svc1"),),
        ((patterns["svc2"], "svc2"),),
    ]


@pytest.mark.asyncio
async def test_kill_all_service_processes_reports_unknown(monkeypatch):
    patterns = {"svc": ["svc"]}
    monkeypatch.setattr(process_killer, "SERVICE_PROCESS_PATTERNS", patterns, raising=False)
    killer = AsyncMock()
    monkeypatch.setattr(process_killer, "_kill_processes_without_current_exclusion", killer)
    messages: list[str] = []
    monkeypatch.setattr(process_killer, "_console", messages.append, raising=False)

    await process_killer.kill_all_service_processes(["svc", "unknown"])

    assert killer.await_args_list == [((patterns["svc"], "svc"),)]
    assert any("Unknown service" in msg for msg in messages)


@pytest.mark.asyncio
async def test_kill_processes_without_current_exclusion_requires_psutil(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "psutil":
            raise ImportError("missing psutil")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    messages: list[str] = []
    monkeypatch.setattr(process_killer, "_console", messages.append, raising=False)

    await process_killer._kill_processes_without_current_exclusion(["svc"], "svc")

    assert any("psutil not available" in msg for msg in messages)


@pytest.mark.asyncio
async def test_kill_processes_without_current_exclusion_kills(monkeypatch, psutil_stub):
    module, processes = psutil_stub
    process = FakeProcess(
        pid=703,
        wait_side_effects=[module.TimeoutExpired(), None],
    )
    processes[703] = process

    monitor = create_monitor_mock(
        {
            703: SimpleNamespace(
                name="python3",
                cmdline=["python", "-m", "svc"],
            )
        }
    )

    process_monitor_module = importlib.import_module("common.process_monitor")
    monkeypatch.setattr(
        process_monitor_module,
        "get_global_process_monitor",
        AsyncMock(return_value=monitor),
    )

    await process_killer._kill_processes_without_current_exclusion(["svc"], "svc")

    assert process.terminate_called
    assert process.kill_called


@pytest.mark.asyncio
async def test_kill_existing_processes_reports_force_kill_timeout(monkeypatch, psutil_stub):
    module, processes = psutil_stub
    process = FakeProcess(
        pid=800,
        wait_side_effects=[module.TimeoutExpired(), module.TimeoutExpired()],
    )
    processes[800] = process

    monitor = create_monitor_mock(
        {800: SimpleNamespace(name="python3", cmdline=["python", "-m", "src.kalshi"])}
    )

    process_monitor_module = importlib.import_module("common.process_monitor")
    monkeypatch.setattr(
        process_monitor_module,
        "get_global_process_monitor",
        AsyncMock(return_value=monitor),
    )
    messages: list[str] = []
    monkeypatch.setattr(process_killer, "_console", messages.append, raising=False)
    monkeypatch.setattr(process_killer.os, "getpid", lambda: 1)
    sleep_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(process_killer.asyncio, "sleep", sleep_mock)

    await process_killer.kill_existing_processes(
        process_killer.SERVICE_PROCESS_PATTERNS["kalshi"], "kalshi"
    )

    assert any("still alive after force kill timeout" in message for message in messages)
    sleep_mock.assert_awaited_once_with(process_killer.POST_KILL_WAIT_SECONDS)


@pytest.mark.asyncio
async def test_kill_existing_processes_handles_kill_race(monkeypatch, psutil_stub):
    module, processes = psutil_stub

    class KillRaceProcess(FakeProcess):
        def kill(self):
            raise module.NoSuchProcess("gone")

    process = KillRaceProcess(pid=801, wait_side_effects=[module.TimeoutExpired()])
    processes[801] = process
    monitor = create_monitor_mock(
        {801: SimpleNamespace(name="python3", cmdline=["python", "-m", "src.kalshi"])}
    )

    process_monitor_module = importlib.import_module("common.process_monitor")
    monkeypatch.setattr(
        process_monitor_module,
        "get_global_process_monitor",
        AsyncMock(return_value=monitor),
    )
    messages: list[str] = []
    monkeypatch.setattr(process_killer, "_console", messages.append, raising=False)
    monkeypatch.setattr(process_killer.os, "getpid", lambda: 0)
    sleep_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(process_killer.asyncio, "sleep", sleep_mock)

    await process_killer.kill_existing_processes(
        process_killer.SERVICE_PROCESS_PATTERNS["kalshi"], "kalshi"
    )

    assert any("no longer exists" in message for message in messages)
    sleep_mock.assert_awaited_once_with(process_killer.POST_KILL_WAIT_SECONDS)


@pytest.mark.asyncio
async def test_kill_existing_processes_handles_error_without_pid(monkeypatch, psutil_stub):
    module, processes = psutil_stub

    class BrokenProcess:
        @property
        def pid(self):
            raise module.AccessDenied("forbidden")

    processes[900] = BrokenProcess()
    monitor = create_monitor_mock(
        {900: SimpleNamespace(name="python3", cmdline=["python", "-m", "src.kalshi"])}
    )

    process_monitor_module = importlib.import_module("common.process_monitor")
    monkeypatch.setattr(
        process_monitor_module,
        "get_global_process_monitor",
        AsyncMock(return_value=monitor),
    )
    messages: list[str] = []
    monkeypatch.setattr(process_killer, "_console", messages.append, raising=False)
    monkeypatch.setattr(process_killer.os, "getpid", lambda: 0)

    await process_killer.kill_existing_processes(
        process_killer.SERVICE_PROCESS_PATTERNS["kalshi"], "kalshi"
    )

    assert any("Could not kill process:" in message for message in messages)


@pytest.mark.asyncio
async def test_kill_all_service_processes_logs_errors(monkeypatch):
    patterns = {"svc": ["svc"]}
    monkeypatch.setattr(process_killer, "SERVICE_PROCESS_PATTERNS", patterns, raising=False)
    messages: list[str] = []
    monkeypatch.setattr(process_killer, "_console", messages.append, raising=False)
    monkeypatch.setattr(
        process_killer,
        "_kill_processes_without_current_exclusion",
        AsyncMock(side_effect=RuntimeError("boom")),
    )

    await process_killer.kill_all_service_processes(["svc"])

    assert any("Error killing svc processes" in message for message in messages)


@pytest.mark.asyncio
async def test_kill_processes_without_current_exclusion_skips_process_errors(
    monkeypatch, psutil_stub
):
    module, _ = psutil_stub
    module.Process = MagicMock(side_effect=module.AccessDenied("no access"))

    monitor = create_monitor_mock(
        {
            1000: SimpleNamespace(
                name="python3",
                cmdline=["python", "-m", "svc"],
            )
        }
    )

    process_monitor_module = importlib.import_module("common.process_monitor")
    monkeypatch.setattr(
        process_monitor_module,
        "get_global_process_monitor",
        AsyncMock(return_value=monitor),
    )
    messages: list[str] = []
    monkeypatch.setattr(process_killer, "_console", messages.append, raising=False)

    await process_killer._kill_processes_without_current_exclusion(["svc"], "svc")

    assert any("No svc processes found" in message for message in messages)


@pytest.mark.asyncio
async def test_kill_processes_without_current_exclusion_handles_pidless_error(
    monkeypatch, psutil_stub
):
    module, processes = psutil_stub

    class BrokenProcess:
        @property
        def pid(self):
            raise module.AccessDenied("no pid")

    processes[1100] = BrokenProcess()
    monitor = create_monitor_mock(
        {
            1100: SimpleNamespace(
                name="python3",
                cmdline=["python", "-m", "svc"],
            )
        }
    )

    process_monitor_module = importlib.import_module("common.process_monitor")
    monkeypatch.setattr(
        process_monitor_module,
        "get_global_process_monitor",
        AsyncMock(return_value=monitor),
    )
    messages: list[str] = []
    monkeypatch.setattr(process_killer, "_console", messages.append, raising=False)

    await process_killer._kill_processes_without_current_exclusion(["svc"], "svc")

    assert any("Could not kill process:" in message for message in messages)


@pytest.mark.asyncio
async def test_kill_processes_without_current_exclusion_handles_terminate_failure(
    monkeypatch, psutil_stub
):
    module, processes = psutil_stub

    class FailTerminate(FakeProcess):
        def terminate(self):
            raise module.AccessDenied("denied")

    process = FailTerminate(pid=1200)
    processes[1200] = process

    monitor = create_monitor_mock(
        {
            1200: SimpleNamespace(
                name="python3",
                cmdline=["python", "-m", "svc"],
            )
        }
    )

    process_monitor_module = importlib.import_module("common.process_monitor")
    monkeypatch.setattr(
        process_monitor_module,
        "get_global_process_monitor",
        AsyncMock(return_value=monitor),
    )
    messages: list[str] = []
    monkeypatch.setattr(process_killer, "_console", messages.append, raising=False)

    await process_killer._kill_processes_without_current_exclusion(["svc"], "svc")

    assert any("Could not kill process 1200" in message for message in messages)


@pytest.mark.asyncio
async def test_kill_processes_without_current_exclusion_reports_graceful_exit(
    monkeypatch, psutil_stub
):
    module, processes = psutil_stub
    process = FakeProcess(pid=1300, wait_side_effects=[None])
    processes[1300] = process

    monitor = create_monitor_mock(
        {
            1300: SimpleNamespace(
                name="python3",
                cmdline=["python", "-m", "svc"],
            )
        }
    )

    process_monitor_module = importlib.import_module("common.process_monitor")
    monkeypatch.setattr(
        process_monitor_module,
        "get_global_process_monitor",
        AsyncMock(return_value=monitor),
    )
    messages: list[str] = []
    monkeypatch.setattr(process_killer, "_console", messages.append, raising=False)

    await process_killer._kill_processes_without_current_exclusion(["svc"], "svc")

    assert any("terminated gracefully" in message for message in messages)
