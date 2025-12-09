import json
from pathlib import Path

import pytest

from src.common.precision_loader import (
    PrecisionConfigError,
    _load_precision_config,
    get_asos_precision,
    get_metar_precision,
    get_temperature_precision,
)


@pytest.fixture(autouse=True)
def clear_precision_cache():
    """Ensure precision config cache does not leak between tests."""
    _load_precision_config.cache_clear()
    yield
    _load_precision_config.cache_clear()


def _write_manifest(manifest_path: Path, stations: dict) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"stations": stations}), encoding="utf-8")


def test_precision_loader_resolves_relative_manifest_path(monkeypatch, tmp_path):
    repo_root = tmp_path
    settings_path = repo_root / "config" / "weather_precision_settings.json"
    manifest_path = repo_root / "config" / "weather_station_precision.json"
    _write_manifest(
        manifest_path,
        {"KJFK": {"metar_precision_c": 0.1, "asos_precision_c": 0.5}},
    )
    settings_path.write_text(
        json.dumps({"WEATHER_PRECISION_CONFIG_PATH": "config/weather_station_precision.json"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "src.common.precision_loader._PRECISION_SETTINGS_PATH",
        settings_path,
    )
    monkeypatch.delenv("WEATHER_PRECISION_CONFIG_PATH", raising=False)

    assert get_metar_precision("KJFK") == pytest.approx(0.1)
    assert get_asos_precision("KJFK") == pytest.approx(0.5)


def test_precision_loader_env_override(monkeypatch, tmp_path):
    manifest_path = tmp_path / "override.json"
    _write_manifest(
        manifest_path,
        {"KBOS": {"metar_precision_c": 0.2, "asos_precision_c": 0.4}},
    )

    monkeypatch.setenv("WEATHER_PRECISION_CONFIG_PATH", str(manifest_path))

    try:
        assert get_temperature_precision("KBOS", "metar") == pytest.approx(0.2)
    finally:
        monkeypatch.delenv("WEATHER_PRECISION_CONFIG_PATH", raising=False)


def test_precision_loader_missing_station(monkeypatch, tmp_path):
    settings_path = tmp_path / "config" / "weather_precision_settings.json"
    manifest_path = tmp_path / "config" / "weather_station_precision.json"
    _write_manifest(
        manifest_path,
        {"KORD": {"metar_precision_c": 0.2, "asos_precision_c": 0.3}},
    )
    settings_path.write_text(
        json.dumps({"WEATHER_PRECISION_CONFIG_PATH": str(manifest_path.relative_to(tmp_path))}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "src.common.precision_loader._PRECISION_SETTINGS_PATH",
        settings_path,
    )

    with pytest.raises(PrecisionConfigError, match="No precision metadata"):
        get_temperature_precision("KSFO", "metar")


def test_precision_loader_invalid_source(monkeypatch, tmp_path):
    settings_path = tmp_path / "config" / "weather_precision_settings.json"
    manifest_path = tmp_path / "config" / "weather_station_precision.json"
    _write_manifest(
        manifest_path,
        {"KLGA": {"metar_precision_c": 0.1, "asos_precision_c": 0.2}},
    )
    settings_path.write_text(
        json.dumps({"WEATHER_PRECISION_CONFIG_PATH": str(manifest_path.relative_to(tmp_path))}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "src.common.precision_loader._PRECISION_SETTINGS_PATH",
        settings_path,
    )

    with pytest.raises(PrecisionConfigError, match="Unsupported precision source"):
        get_temperature_precision("KLGA", "satellite")  # type: ignore[arg-type]


def test_precision_loader_env_override_missing_file(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing.json"
    monkeypatch.setenv("WEATHER_PRECISION_CONFIG_PATH", str(missing_path))

    with pytest.raises(PrecisionConfigError, match="non-existent path"):
        get_metar_precision("KPWM")
