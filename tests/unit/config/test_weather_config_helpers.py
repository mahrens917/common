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
