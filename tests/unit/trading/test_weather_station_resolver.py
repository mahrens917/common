from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Dict
from unittest.mock import mock_open

import pytest

from common.config.weather import WeatherConfigError
from common.trading.weather_station import (
    WeatherStationResolver,
    load_weather_station_mapping,
)


@pytest.fixture
def base_mapping() -> Dict[str, Dict]:
    return {
        "NY": {"icao": "KNYC", "aliases": ["NYC"]},
        "AUS": {"icao": "KAUS", "aliases": ["HAUS"]},
    }


def test_resolver_resolves_alias(base_mapping: Dict[str, Dict]) -> None:
    resolver = WeatherStationResolver(mapping=base_mapping)
    assert resolver.resolve_ticker("KXHIGHNYC-25AUG15-B80") == "KNYC"
    assert resolver.resolve_ticker("KXHIGHAUS-25AUG15-B80") == "KAUS"


def test_resolver_refresh_updates_lookup(base_mapping: Dict[str, Dict]) -> None:
    resolver = WeatherStationResolver(mapping={})
    resolver.refresh(base_mapping)
    assert resolver.resolve_ticker("KXHIGHNYC-25AUG15-B80") == "KNYC"
    assert "NY" in resolver.alias_map.values()


@pytest.mark.parametrize(
    "ticker, message",
    [
        ("OTHER-25JAN01", "Market ticker must start with KXHIGH"),
        ("KXHIGHLON", "Invalid market ticker format"),
        ("KXHIGHCHI-25JAN01", "Weather station 'CHI' not found"),
    ],
)
def test_resolver_validation_errors(
    ticker: str, message: str, base_mapping: Dict[str, Dict]
) -> None:
    resolver = WeatherStationResolver(mapping=base_mapping)
    with pytest.raises(ValueError) as exc:
        resolver.resolve_ticker(ticker)
    assert message in str(exc.value)


def test_resolver_requires_valid_icao(base_mapping: Dict[str, Dict]) -> None:
    broken = {"NY": {"icao": "NYC"}}
    resolver = WeatherStationResolver(mapping=broken)
    with pytest.raises(ValueError) as exc:
        resolver.resolve_ticker("KXHIGHNY-25JAN01-B80")
    assert "Invalid ICAO code" in str(exc.value)


def test_load_weather_station_mapping_handles_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    path = Path(tempfile.gettempdir()) / "missing.json"

    def fake_open(*_args, **_kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr("builtins.open", fake_open)
    with pytest.raises(WeatherConfigError):
        load_weather_station_mapping(path=path)


def test_load_weather_station_mapping_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"mappings": {"NY": {"icao": "KNYC"}}}
    monkeypatch.setattr("builtins.open", mock_open(read_data=json.dumps(payload)))
    assert load_weather_station_mapping(Path("unused")) == payload["mappings"]


def test_load_weather_station_mapping_uses_config_loader(
    monkeypatch: pytest.MonkeyPatch, base_mapping: Dict[str, Dict]
) -> None:
    monkeypatch.setattr(
        "common.trading.weather_station._load_config_weather_station_mapping",
        lambda: base_mapping,
    )
    assert load_weather_station_mapping() == base_mapping


def test_load_weather_station_mapping_propagates_config_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail():
        raise WeatherConfigError("boom")

    monkeypatch.setattr("common.trading.weather_station._load_config_weather_station_mapping", fail)

    with pytest.raises(WeatherConfigError):
        load_weather_station_mapping()
