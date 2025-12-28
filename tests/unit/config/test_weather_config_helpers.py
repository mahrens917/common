from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.config.weather import (
    WeatherConfigError,
    load_weather_station_mapping,
    load_weather_trading_config,
)


def test_load_weather_station_mapping_from_directory(tmp_path: Path):
    mapping_path = tmp_path / "weather_station_mapping.json"
    mapping_path.write_text(json.dumps({"mappings": {"NYC": {"icao": "KJFK"}}}))

    result = load_weather_station_mapping(config_dir=tmp_path)
    assert result == {"NYC": {"icao": "KJFK"}}


def test_load_weather_station_mapping_requires_mappings_key(tmp_path: Path):
    mapping_path = tmp_path / "weather_station_mapping.json"
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
