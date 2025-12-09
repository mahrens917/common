import json
from pathlib import Path

import pytest

from src.common.config.weather import (
    WeatherConfigError,
    _load_from_directory,
    _resolve_config_json,
    load_weather_station_mapping,
    load_weather_trading_config,
)
from src.weather.config_loader import WeatherConfigLoadError


def test_load_from_directory_errors(monkeypatch, tmp_path):
    with pytest.raises(WeatherConfigError):
        _load_from_directory("missing.json", tmp_path)

    bad_path = tmp_path / "bad.json"
    bad_path.write_text("{not-json")
    with pytest.raises(WeatherConfigError):
        _load_from_directory(bad_path.name, tmp_path)

    good_path = tmp_path / "good.json"
    good_path.write_text(json.dumps({"ok": True}))

    monkeypatch.setattr(
        Path, "open", lambda self, *args, **kwargs: (_ for _ in ()).throw(OSError("fail"))
    )
    with pytest.raises(WeatherConfigError):
        _load_from_directory(good_path.name, tmp_path)


def test_resolve_config_json_branches(monkeypatch, tmp_path):
    file_path = tmp_path / "config.json"
    file_path.write_text(json.dumps({"value": 1}))
    assert _resolve_config_json(file_path.name, tmp_path) == {"value": 1}

    monkeypatch.setattr(
        "src.common.config.weather.load_config_json",
        lambda name: (_ for _ in ()).throw(WeatherConfigLoadError("missing", ["config_dir"])),
    )
    with pytest.raises(WeatherConfigError):
        _resolve_config_json("anything.json", None)


def test_load_weather_station_mapping_validation(tmp_path):
    mapping_file = tmp_path / "weather_station_mapping.json"
    mapping_file.write_text(json.dumps({"mappings": {"ABC": {"city": "Somewhere"}}}))
    result = load_weather_station_mapping(config_dir=tmp_path)
    assert result["ABC"]["city"] == "Somewhere"

    mapping_file.write_text(json.dumps({"wrong": {}}))
    with pytest.raises(WeatherConfigError):
        load_weather_station_mapping(config_dir=tmp_path)


def test_load_weather_trading_config(tmp_path):
    trading_file = tmp_path / "weather_trading_config.json"
    trading_file.write_text(json.dumps({"key": "value"}))
    assert load_weather_trading_config(config_dir=tmp_path) == {"key": "value"}
