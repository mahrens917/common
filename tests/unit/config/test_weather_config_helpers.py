from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.config.weather import (
    WeatherConfigError,
    _get_weather_settings_func,
    _import_config_loader,
    _resolve_config_json,
    load_weather_station_mapping,
    load_weather_trading_config,
)


def test_load_weather_station_mapping_from_directory(tmp_path: Path):
    mapping_path = tmp_path / "stations.json"
    mapping_path.write_text(json.dumps({"stations": {"KJFK": {"city_code": "NYC", "icao": "KJFK"}}}))

    result = load_weather_station_mapping(config_dir=tmp_path)
    assert result == {"NYC": {"city_code": "NYC", "icao": "KJFK"}}


def test_load_weather_station_mapping_requires_mappings_key(tmp_path: Path):
    mapping_path = tmp_path / "stations.json"
    mapping_path.write_text(json.dumps({"invalid": {}}))

    with pytest.raises(WeatherConfigError):
        load_weather_station_mapping(config_dir=tmp_path)


def test_load_weather_trading_config_reads_file(tmp_path: Path):
    config_path = tmp_path / "weather_trading_config.json"
    config_path.write_text(json.dumps({"rules": ["rule1"]}))

    config = load_weather_trading_config(config_dir=tmp_path)
    assert config["rules"] == ["rule1"]


def test_load_weather_station_mapping_missing_file(tmp_path: Path):
    with pytest.raises(WeatherConfigError):
        load_weather_station_mapping(config_dir=tmp_path)


def test_load_weather_trading_config_with_package(tmp_path: Path):
    from common.config import weather

    original_projects_base = weather._PROJECTS_BASE
    try:
        weather._PROJECTS_BASE = tmp_path
        package_config_dir = tmp_path / "test_pkg" / "config"
        package_config_dir.mkdir(parents=True)
        config_file = package_config_dir / "weather_trading_config.json"
        config_file.write_text(json.dumps({"enabled": True}))

        result = load_weather_trading_config(package="test_pkg")

        assert result == {"enabled": True}
    finally:
        weather._PROJECTS_BASE = original_projects_base


def test_load_weather_trading_config_package_not_found(tmp_path: Path):
    from common.config import weather

    original_projects_base = weather._PROJECTS_BASE
    try:
        weather._PROJECTS_BASE = tmp_path

        with pytest.raises(WeatherConfigError) as err:
            load_weather_trading_config(package="missing_pkg")

        assert "missing_pkg" in str(err.value)
    finally:
        weather._PROJECTS_BASE = original_projects_base


def test_load_weather_trading_config_invalid_json(tmp_path: Path):
    config_path = tmp_path / "weather_trading_config.json"
    config_path.write_text("{ invalid json")

    with pytest.raises(WeatherConfigError) as err:
        load_weather_trading_config(config_dir=tmp_path)

    assert "Invalid JSON" in str(err.value)


def test_load_weather_trading_config_os_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = tmp_path / "weather_trading_config.json"
    config_path.write_text('{"key": "value"}')

    def fake_open(*args, **kwargs):
        raise OSError("Unable to read file")

    monkeypatch.setattr(Path, "open", fake_open)

    with pytest.raises(WeatherConfigError) as err:
        load_weather_trading_config(config_dir=tmp_path)

    assert "Unable to read" in str(err.value)


def test_resolve_config_json_with_explicit_directory(tmp_path: Path):
    config_file = tmp_path / "test_config.json"
    config_file.write_text(json.dumps({"key": "value"}))

    result = _resolve_config_json("test_config.json", tmp_path)

    assert result == {"key": "value"}


def test_resolve_config_json_from_local_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "test_config.json"
    config_file.write_text(json.dumps({"local": True}))

    result = _resolve_config_json("test_config.json", None)

    assert result == {"local": True}


def test_import_config_loader_raises_when_not_installed(monkeypatch: pytest.MonkeyPatch):
    import importlib
    import sys

    for mod in list(sys.modules.keys()):
        if "weather" in mod and ("config_loader" in mod or "settings" in mod):
            monkeypatch.delitem(sys.modules, mod, raising=False)

    def mock_import_module(name):
        raise ImportError(f"No module named '{name}'")

    monkeypatch.setattr(importlib, "import_module", mock_import_module)

    with pytest.raises(WeatherConfigError, match="weather package is not installed"):
        _import_config_loader()


def test_get_weather_settings_func_returns_fallback(monkeypatch: pytest.MonkeyPatch):
    import importlib
    import sys
    from types import SimpleNamespace

    for mod in list(sys.modules.keys()):
        if "weather" in mod and "settings" in mod:
            monkeypatch.delitem(sys.modules, mod, raising=False)

    def mock_import_module(name):
        raise ImportError(f"No module named '{name}'")

    monkeypatch.setattr(importlib, "import_module", mock_import_module)

    result = _get_weather_settings_func()()

    assert result.sources.asos_source is None
    assert result.sources.metar_source is None


def test_load_weather_station_mapping_uses_load_config(monkeypatch: pytest.MonkeyPatch):
    from common.config import weather as weather_module

    mock_data = {"stations": {"KTEST": {"city_code": "TEST", "icao": "KTEST"}}}
    monkeypatch.setattr(weather_module, "load_config", lambda *args, **kwargs: mock_data)

    result = load_weather_station_mapping()

    assert result == {"TEST": {"city_code": "TEST", "icao": "KTEST"}}


def test_load_weather_trading_config_uses_load_config(monkeypatch: pytest.MonkeyPatch):
    from common.config import weather as weather_module

    mock_data = {"enabled": True, "rules": []}
    monkeypatch.setattr(weather_module, "load_config", lambda *args, **kwargs: mock_data)

    result = load_weather_trading_config()

    assert result == {"enabled": True, "rules": []}
