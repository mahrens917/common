import sys
from types import SimpleNamespace
from typing import Any

import pytest

from common.process_killer_helpers import process_terminator as terminator


@pytest.fixture(autouse=True)
def _restore_psutil():
    """Restore original psutil module after each test."""
    original_psutil = sys.modules.get("psutil")
    yield
    if original_psutil is not None:
        sys.modules["psutil"] = original_psutil
    elif "psutil" in sys.modules:
        del sys.modules["psutil"]


class _DummyPsutilProcess:
    def __init__(self, pid: int):
        self.pid = pid
        self._wait_calls = 0
        self.terminated = False
        self.killed = False

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: float | None = None) -> None:
        self._wait_calls += 1
        if self._wait_calls == 1:
            raise TimeoutError  # will be remapped to TimeoutExpired by stub


class _StubPsutilModule:
    class TimeoutExpired(Exception):
        pass

    class NoSuchProcess(Exception):
        pass

    class AccessDenied(Exception):
        pass

    def __init__(self):
        self.processes: dict[int, _DummyPsutilProcess] = {}

    def Process(self, pid: int) -> _DummyPsutilProcess:  # noqa: N802
        if pid not in self.processes:
            self.processes[pid] = _DummyPsutilProcess(pid)
        return self.processes[pid]


def _install_stub_psutil(stub: Any) -> None:
    sys.modules["psutil"] = stub


def test_validate_process_candidates_success(monkeypatch):
    stub = _StubPsutilModule()
    _install_stub_psutil(stub)

    candidate = SimpleNamespace(pid=5, name="python3", cmdline=["python3", "service.py"])
    result = terminator.validate_process_candidates([candidate], service_name="svc")
    assert len(result) == 1
    assert result[0].pid == 5


def test_validate_process_candidates_access_denied(monkeypatch):
    class DenyProcess:
        def __init__(self, pid):
            self.pid = pid

    class Stub(_StubPsutilModule):
        def Process(self, pid: int):
            raise self.AccessDenied()  # type: ignore[attr-defined]

    stub = Stub()
    _install_stub_psutil(stub)

    candidate = SimpleNamespace(pid=6, name="python", cmdline=["x"])
    with pytest.raises(RuntimeError):
        terminator.validate_process_candidates([candidate], service_name="svc")


@pytest.mark.asyncio
async def test_terminate_matching_processes_force_kill(monkeypatch):
    stub = _StubPsutilModule()

    class TimeoutProc(_DummyPsutilProcess):
        def wait(self, timeout: float | None = None):
            if not hasattr(self, "_wait_calls"):
                self._wait_calls = 0
            self._wait_calls += 1
            if self._wait_calls == 1:
                raise stub.TimeoutExpired()

    proc = TimeoutProc(pid=10)

    _install_stub_psutil(stub)

    messages = []
    proc.kill = lambda: setattr(proc, "killed", True)  # type: ignore[assignment]
    proc.terminate = lambda: setattr(proc, "terminated", True)  # type: ignore[assignment]

    killed = await terminator.terminate_matching_processes(
        [proc],
        service_name="svc",
        graceful_timeout=0.01,
        force_timeout=0.01,
        console_output_func=messages.append,
    )

    assert killed == [10]
    assert proc.terminated is True
    assert proc.killed is True
    assert any("Killing existing" in msg for msg in messages)
