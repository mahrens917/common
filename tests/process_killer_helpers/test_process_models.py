from types import SimpleNamespace

from src.common.process_killer_helpers.process_models import (
    NormalizedProcessCandidate,
    ProcessCandidate,
)


def test_normalized_process_candidate_fields():
    candidate = NormalizedProcessCandidate(pid=123, name="python", cmdline=["python", "app.py"])
    assert candidate.pid == 123
    assert candidate.name == "python"
    assert list(candidate.cmdline) == ["python", "app.py"]

    def accepts_protocol(proc: ProcessCandidate) -> int:
        return proc.pid

    assert accepts_protocol(candidate) == 123
