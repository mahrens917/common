import io

import pytest

import common.simple_system_metrics as metrics

DEFAULT_STATVFS_FR_SIZE = 1024


def _patch_subprocess_popen(
    monkeypatch,
    *,
    stdout: str = "",
    returncode: int = 0,
    popen_side_effect: Exception | None = None,
    communicate_side_effect: Exception | None = None,
) -> None:
    import subprocess

    class FakePopen:
        def __init__(self) -> None:
            self.returncode = returncode

        def communicate(self, timeout: float | None = None) -> tuple[str, str]:
            _ = timeout
            if communicate_side_effect is not None:
                raise communicate_side_effect
            return stdout, ""

    def fake_popen(*args, **kwargs):
        _ = args, kwargs
        if popen_side_effect is not None:
            raise popen_side_effect
        return FakePopen()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)


def test_get_disk_percent_calculates_usage(monkeypatch):
    class FakeStat:
        f_blocks = 200
        f_frsize = DEFAULT_STATVFS_FR_SIZE
        f_bavail = 50

    monkeypatch.setattr(metrics.os, "statvfs", lambda path: FakeStat())

    usage = metrics.get_disk_percent("/any")

    expected_used_bytes = (FakeStat.f_blocks - FakeStat.f_bavail) * FakeStat.f_frsize
    expected_total_bytes = FakeStat.f_blocks * FakeStat.f_frsize
    assert usage == pytest.approx((expected_used_bytes / expected_total_bytes) * 100.0)


def test_get_disk_percent_returns_zero_on_error(monkeypatch):
    def _raise(_):
        raise OSError("boom")

    monkeypatch.setattr(metrics.os, "statvfs", _raise)

    assert metrics.get_disk_percent("/any") == 0.0


def test_get_memory_percent_linux_reads_proc(monkeypatch):
    fake_meminfo = io.StringIO("MemTotal:       1000 kB\nMemFree:        100 kB\nMemAvailable:   250 kB\n")

    def fake_open(path, mode="r", *args, **kwargs):
        if path == "/proc/meminfo":
            fake_meminfo.seek(0)
            return fake_meminfo
        raise AssertionError("Unexpected file access")

    monkeypatch.setattr(metrics, "open", fake_open, raising=False)

    usage = metrics._get_memory_percent_linux()

    # MemTotal=1000kB, MemAvailable=250kB => used=750 => 75%
    assert usage == pytest.approx(75.0)


def test_get_cpu_percent_linux_reads_proc(monkeypatch):
    fake_stat = io.StringIO("cpu 100 50 50 200 25 0 0 0\n")

    def fake_open(path, mode="r", *args, **kwargs):
        if path == "/proc/stat":
            fake_stat.seek(0)
            return fake_stat
        raise AssertionError("Unexpected file access")

    monkeypatch.setattr(metrics, "open", fake_open, raising=False)

    usage = metrics._get_cpu_percent_linux()

    # total = 100 + 50 + 50 + 200 + 25 = 425, idle = 200 + 25 = 225 => active = 200 => ~47.0588235%
    assert usage == pytest.approx((425 - 225) / 425 * 100.0)


def test_get_memory_percent_raises_on_non_linux(monkeypatch):
    monkeypatch.setattr(metrics.platform, "system", lambda: "Windows")
    with pytest.raises(RuntimeError):
        metrics.get_memory_percent()


def test_get_memory_percent_macos_reads_vm_stat(monkeypatch):
    monkeypatch.setattr(metrics.platform, "system", lambda: "Darwin")

    monkeypatch.setattr(metrics, "_get_memory_percent_macos", lambda: 50.0)

    usage = metrics.get_memory_percent()
    assert usage == 50.0


def test_get_cpu_percent_raises_on_non_linux(monkeypatch):
    monkeypatch.setattr(metrics.platform, "system", lambda: "Windows")
    with pytest.raises(RuntimeError):
        metrics.get_cpu_percent()


def test_cpu_percent_linux_returns_zero_for_malformed_stat(monkeypatch):
    fake_stat = io.StringIO("cpu 1 2\n")

    def fake_open(path, mode="r", *args, **kwargs):
        if path == "/proc/stat":
            fake_stat.seek(0)
            return fake_stat
        raise AssertionError("Unexpected file access")

    monkeypatch.setattr(metrics, "open", fake_open, raising=False)

    assert metrics._get_cpu_percent_linux() == 0.0


def test_cpu_percent_linux_handles_read_errors(monkeypatch):
    def fake_open(*args, **kwargs):
        raise OSError("no stat")

    monkeypatch.setattr(metrics, "open", fake_open, raising=False)

    assert metrics._get_cpu_percent_linux() == 0.0


def test_get_disk_percent_returns_zero_when_total_zero(monkeypatch):
    class FakeStat:
        f_blocks = 0
        f_frsize = DEFAULT_STATVFS_FR_SIZE
        f_bavail = 0

    monkeypatch.setattr(metrics.os, "statvfs", lambda path: FakeStat())

    assert metrics.get_disk_percent("/any") == 0.0


def test_memory_percent_linux_returns_zero_when_total_zero(monkeypatch):
    fake_meminfo = io.StringIO("MemTotal:       0 kB\nMemAvailable:   0 kB\n")

    def fake_open(path, mode="r", *args, **kwargs):
        if path == "/proc/meminfo":
            fake_meminfo.seek(0)
            return fake_meminfo
        raise AssertionError("Unexpected file access")

    monkeypatch.setattr(metrics, "open", fake_open, raising=False)

    assert metrics._get_memory_percent_linux() == 0.0


def test_memory_percent_linux_handles_value_error(monkeypatch):
    fake_meminfo = io.StringIO("MemTotal:       abc kB\nMemAvailable:   250 kB\n")

    def fake_open(path, mode="r", *args, **kwargs):
        if path == "/proc/meminfo":
            fake_meminfo.seek(0)
            return fake_meminfo
        raise AssertionError("Unexpected file access")

    monkeypatch.setattr(metrics, "open", fake_open, raising=False)

    assert metrics._get_memory_percent_linux() == 0.0


def test_memory_percent_linux_handles_missing_fields(monkeypatch):
    fake_meminfo = io.StringIO("SomeOtherField: 100 kB\n")

    def fake_open(path, mode="r", *args, **kwargs):
        if path == "/proc/meminfo":
            fake_meminfo.seek(0)
            return fake_meminfo
        raise AssertionError("Unexpected file access")

    monkeypatch.setattr(metrics, "open", fake_open, raising=False)

    assert metrics._get_memory_percent_linux() == 0.0


def test_cpu_percent_linux_returns_zero_when_total_zero(monkeypatch):
    fake_stat = io.StringIO("cpu 0 0 0 0 0 0 0 0\n")

    def fake_open(path, mode="r", *args, **kwargs):
        if path == "/proc/stat":
            fake_stat.seek(0)
            return fake_stat
        raise AssertionError("Unexpected file access")

    monkeypatch.setattr(metrics, "open", fake_open, raising=False)

    assert metrics._get_cpu_percent_linux() == 0.0


def test_cpu_percent_linux_includes_iowait(monkeypatch):
    fake_stat = io.StringIO("cpu 100 50 50 200 25 10 5 3\n")

    def fake_open(path, mode="r", *args, **kwargs):
        if path == "/proc/stat":
            fake_stat.seek(0)
            return fake_stat
        raise AssertionError("Unexpected file access")

    monkeypatch.setattr(metrics, "open", fake_open, raising=False)

    usage = metrics._get_cpu_percent_linux()

    # total = 100+50+50+200+25+10+5+3 = 443, idle = 200+25 = 225, active = 218
    expected_usage = (443 - 225) / 443 * 100.0
    assert usage == pytest.approx(expected_usage)


def test_cpu_percent_linux_handles_value_error(monkeypatch):
    fake_stat = io.StringIO("cpu abc def ghi jkl\n")

    def fake_open(path, mode="r", *args, **kwargs):
        if path == "/proc/stat":
            fake_stat.seek(0)
            return fake_stat
        raise AssertionError("Unexpected file access")

    monkeypatch.setattr(metrics, "open", fake_open, raising=False)

    assert metrics._get_cpu_percent_linux() == 0.0


def test_get_cpu_percent_macos_reads_iostat(monkeypatch):
    monkeypatch.setattr(metrics.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(metrics, "_get_cpu_percent_macos", lambda: 35.5)

    usage = metrics.get_cpu_percent()
    assert usage == 35.5


def test_get_memory_percent_macos_parses_vm_stat(monkeypatch):
    import subprocess

    vm_stat_output = """Mach Virtual Memory Statistics: (page size of 4096 bytes)
Pages free:                               100000.
Pages active:                             200000.
Pages inactive:                           50000.
Pages wired down:                         150000."""

    _patch_subprocess_popen(monkeypatch, stdout=vm_stat_output, returncode=0)

    usage = metrics._get_memory_percent_macos()

    # total = 100000 + 200000 + 50000 + 150000 = 500000
    # used = 200000 + 150000 = 350000
    expected = (350000 / 500000) * 100.0
    assert usage == pytest.approx(expected)


def test_get_memory_percent_macos_returns_zero_on_error(monkeypatch):
    _patch_subprocess_popen(monkeypatch, stdout="", returncode=1)

    assert metrics._get_memory_percent_macos() == 0.0


def test_get_memory_percent_macos_handles_timeout(monkeypatch):
    import subprocess

    _patch_subprocess_popen(
        monkeypatch,
        communicate_side_effect=subprocess.TimeoutExpired(cmd="vm_stat", timeout=1),
    )

    assert metrics._get_memory_percent_macos() == 0.0


def test_get_memory_percent_macos_handles_subprocess_error(monkeypatch):
    import subprocess

    _patch_subprocess_popen(monkeypatch, communicate_side_effect=subprocess.SubprocessError("error"))

    assert metrics._get_memory_percent_macos() == 0.0


def test_get_memory_percent_macos_handles_value_error(monkeypatch):
    vm_stat_output = """Mach Virtual Memory Statistics: (page size of 4096 bytes)
Pages free:                               abc.
Pages active:                             200000."""

    _patch_subprocess_popen(monkeypatch, stdout=vm_stat_output, returncode=0)

    assert metrics._get_memory_percent_macos() == 0.0


def test_get_memory_percent_macos_returns_zero_when_total_zero(monkeypatch):
    vm_stat_output = """Mach Virtual Memory Statistics: (page size of 4096 bytes)
Pages free:                               0.
Pages active:                             0.
Pages inactive:                           0.
Pages wired down:                         0."""

    _patch_subprocess_popen(monkeypatch, stdout=vm_stat_output, returncode=0)

    assert metrics._get_memory_percent_macos() == 0.0


def test_get_cpu_percent_macos_parses_iostat(monkeypatch):
    iostat_output = """      disk0       cpu    load average
    KB/t  tps  MB/s  us sy id   1m   5m   15m
   16.00   10  0.16  25 15 60  1.5  1.8  2.0
   12.00    8  0.10  30 10 60  1.5  1.8  2.0"""

    _patch_subprocess_popen(monkeypatch, stdout=iostat_output, returncode=0)

    usage = metrics._get_cpu_percent_macos()

    # Last line: us=30, sy=10, id=60 => (30+10)/(30+10+60)*100 = 40%
    expected = (30 + 10) / (30 + 10 + 60) * 100.0
    assert usage == pytest.approx(expected)


def test_get_cpu_percent_macos_returns_zero_on_error(monkeypatch):
    _patch_subprocess_popen(monkeypatch, stdout="", returncode=1)

    assert metrics._get_cpu_percent_macos() == 0.0


def test_get_cpu_percent_macos_handles_timeout(monkeypatch):
    import subprocess

    _patch_subprocess_popen(
        monkeypatch,
        communicate_side_effect=subprocess.TimeoutExpired(cmd="iostat", timeout=3),
    )

    assert metrics._get_cpu_percent_macos() == 0.0


def test_get_cpu_percent_macos_handles_subprocess_error(monkeypatch):
    import subprocess

    _patch_subprocess_popen(monkeypatch, communicate_side_effect=subprocess.SubprocessError("error"))

    assert metrics._get_cpu_percent_macos() == 0.0


def test_get_cpu_percent_macos_handles_value_error(monkeypatch):
    iostat_output = """      disk0       cpu    load average
    KB/t  tps  MB/s  us sy id   1m   5m   15m
   16.00   10  0.16  abc def ghi  1.5  1.8  2.0"""

    _patch_subprocess_popen(monkeypatch, stdout=iostat_output, returncode=0)

    assert metrics._get_cpu_percent_macos() == 0.0


def test_find_cpu_column_index_finds_us_column():
    lines = [
        "      disk0       cpu    load average",
        "    KB/t  tps  MB/s  us sy id   1m   5m   15m",
        "   16.00   10  0.16  25 15 60  1.5  1.8  2.0",
    ]

    idx = metrics._find_cpu_column_index(lines)
    assert idx == 3  # 'us' is at index 3 in the header


def test_find_cpu_column_index_returns_negative_when_not_found():
    lines = ["some random output", "without cpu headers"]

    idx = metrics._find_cpu_column_index(lines)
    assert idx == -1


def test_parse_cpu_from_iostat_output_parses_last_line():
    lines = [
        "      disk0       cpu    load average",
        "    KB/t  tps  MB/s  us sy id   1m   5m   15m",
        "   16.00   10  0.16  20 10 70  1.5  1.8  2.0",
        "   12.00    8  0.10  30 15 55  1.5  1.8  2.0",
    ]
    us_col_idx = 3

    usage = metrics._parse_cpu_from_iostat_output(lines, us_col_idx)

    # Last line: us=30, sy=15, id=55
    expected = (30 + 15) / (30 + 15 + 55) * 100.0
    assert usage == pytest.approx(expected)


def test_parse_cpu_from_iostat_output_skips_invalid_lines():
    lines = [
        "      disk0       cpu    load average",
        "    KB/t  tps  MB/s  us sy id   1m   5m   15m",
        "   16.00   10",  # Invalid line
        "   12.00    8  0.10  25 10 65  1.5  1.8  2.0",  # Valid line
    ]
    us_col_idx = 3

    usage = metrics._parse_cpu_from_iostat_output(lines, us_col_idx)

    # Should parse the valid line: us=25, sy=10, id=65
    expected = (25 + 10) / (25 + 10 + 65) * 100.0
    assert usage == pytest.approx(expected)


def test_parse_cpu_from_iostat_output_returns_zero_when_no_valid_lines():
    lines = ["header", "invalid", "lines"]
    us_col_idx = 3

    usage = metrics._parse_cpu_from_iostat_output(lines, us_col_idx)
    assert usage == 0.0


def test_calculate_cpu_percentage_calculates_correctly():
    usage = metrics._calculate_cpu_percentage(user=30.0, system=10.0, idle=60.0)
    expected = (30 + 10) / (30 + 10 + 60) * 100.0
    assert usage == pytest.approx(expected)


def test_calculate_cpu_percentage_returns_zero_when_total_zero():
    usage = metrics._calculate_cpu_percentage(user=0.0, system=0.0, idle=0.0)
    assert usage == 0.0


def test_get_cpu_percent_macos_handles_missing_column(monkeypatch):
    iostat_output = """some output
without proper headers"""

    _patch_subprocess_popen(monkeypatch, stdout=iostat_output, returncode=0)
    assert metrics._get_cpu_percent_macos() == 0.0


def test_get_cpu_percent_macos_handles_os_error(monkeypatch):
    _patch_subprocess_popen(monkeypatch, popen_side_effect=OSError("error"))

    assert metrics._get_cpu_percent_macos() == 0.0


def test_get_memory_percent_macos_handles_os_error(monkeypatch):
    _patch_subprocess_popen(monkeypatch, popen_side_effect=OSError("error"))

    assert metrics._get_memory_percent_macos() == 0.0


def test_parse_cpu_from_iostat_output_handles_index_error():
    lines = [
        "      disk0       cpu    load average",
        "    KB/t  tps  MB/s  us sy id   1m   5m   15m",
        "   12.00    8  0.10  25",  # Not enough columns
    ]
    us_col_idx = 3

    usage = metrics._parse_cpu_from_iostat_output(lines, us_col_idx)
    assert usage == 0.0


def test_find_cpu_column_index_partial_match():
    lines = [
        "      disk0       cpu    load average",
        "    KB/t  tps  MB/s  us sy   1m   5m   15m",  # Missing 'id'
    ]

    idx = metrics._find_cpu_column_index(lines)
    assert idx == -1


def test_get_memory_percent_macos_with_custom_page_size(monkeypatch):
    vm_stat_output = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                               10000.
Pages active:                             20000.
Pages inactive:                           5000.
Pages wired down:                         15000."""

    _patch_subprocess_popen(monkeypatch, stdout=vm_stat_output, returncode=0)

    usage = metrics._get_memory_percent_macos()

    # total = 10000 + 20000 + 5000 + 15000 = 50000
    # used = 20000 + 15000 = 35000
    expected = (35000 / 50000) * 100.0
    assert usage == pytest.approx(expected)
