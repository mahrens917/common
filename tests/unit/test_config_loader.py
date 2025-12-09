import builtins
from datetime import date
from typing import Any, Dict
from unittest.mock import mock_open

import pytest

from src.common import config_loader


def _mock_exists(monkeypatch: pytest.MonkeyPatch, suffix: str, exists: bool) -> None:
    original_exists = config_loader.Path.exists

    def fake_exists(self: Any) -> bool:
        if str(self).endswith(suffix):
            return exists
        return original_exists(self)

    monkeypatch.setattr(config_loader.Path, "exists", fake_exists, raising=False)


def _mock_file(monkeypatch: pytest.MonkeyPatch, data: str) -> None:
    mocked_open = mock_open(read_data=data)
    monkeypatch.setattr(builtins, "open", mocked_open)


def test_load_pnl_config_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_exists(monkeypatch, "pnl_config.json", False)

    with pytest.raises(FileNotFoundError):
        config_loader.load_pnl_config()


def test_load_pnl_config_missing_trade_collection(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_exists(monkeypatch, "pnl_config.json", True)
    _mock_file(monkeypatch, "{}")

    with pytest.raises(RuntimeError) as err:
        config_loader.load_pnl_config()

    assert "trade_collection" in str(err.value)


def test_load_pnl_config_missing_historical_start_date(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_exists(monkeypatch, "pnl_config.json", True)
    _mock_file(monkeypatch, '{"trade_collection": {}}')

    with pytest.raises(RuntimeError) as err:
        config_loader.load_pnl_config()

    assert "historical_start_date" in str(err.value)


def test_load_pnl_config_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_exists(monkeypatch, "pnl_config.json", True)
    _mock_file(monkeypatch, "{ invalid")

    with pytest.raises(RuntimeError) as err:
        config_loader.load_pnl_config()

    assert "Invalid JSON" in str(err.value)


def test_load_pnl_config_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_exists(monkeypatch, "pnl_config.json", True)
    config_payload = """
    {
        "trade_collection": {
            "historical_start_date": "2023-07-15"
        },
        "reporting": {"enabled": true}
    }
    """
    _mock_file(monkeypatch, config_payload)

    config = config_loader.load_pnl_config()

    assert config["trade_collection"]["historical_start_date"] == "2023-07-15"
    assert config["reporting"]["enabled"] is True


def test_get_historical_start_date_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_config: Dict[str, Any] = {"trade_collection": {"historical_start_date": "2024-02-29"}}
    monkeypatch.setattr(config_loader, "load_pnl_config", lambda: fake_config)

    start_date = config_loader.get_historical_start_date()

    assert start_date == date(2024, 2, 29)


def test_get_historical_start_date_invalid_date(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_config = {"trade_collection": {"historical_start_date": "2024-13-01"}}
    monkeypatch.setattr(config_loader, "load_pnl_config", lambda: fake_config)

    with pytest.raises(RuntimeError) as err:
        config_loader.get_historical_start_date()

    assert "Invalid date format" in str(err.value)


def test_get_historical_start_date_load_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_error() -> Dict[str, Any]:
        raise FileNotFoundError("missing config")

    monkeypatch.setattr(config_loader, "load_pnl_config", raise_error)

    with pytest.raises(RuntimeError) as err:
        config_loader.get_historical_start_date()

    assert "Failed to load historical start date" in str(err.value)
    assert "missing config" in str(err.value)


def test_get_reporting_timezone_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_config: Dict[str, Any] = {
        "trade_collection": {"historical_start_date": "2023-01-01"},
        "reporting": {"timezone": "Europe/Berlin"},
    }
    monkeypatch.setattr(config_loader, "load_pnl_config", lambda: fake_config)

    assert config_loader.get_reporting_timezone() == "Europe/Berlin"


def test_get_reporting_timezone_raises_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_missing() -> Dict[str, Any]:
        raise FileNotFoundError("missing config")

    monkeypatch.setattr(config_loader, "load_pnl_config", raise_missing)

    with pytest.raises(RuntimeError) as err:
        config_loader.get_reporting_timezone()
    assert "Failed to load PnL config for timezone lookup" in str(err.value)


def test_load_weather_trading_config_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_exists(monkeypatch, "weather_trading_config.json", False)

    with pytest.raises(FileNotFoundError):
        config_loader.load_weather_trading_config()


def test_load_weather_trading_config_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_exists(monkeypatch, "weather_trading_config.json", True)
    _mock_file(monkeypatch, "{ invalid")

    with pytest.raises(RuntimeError) as err:
        config_loader.load_weather_trading_config()

    assert "Invalid JSON" in str(err.value)


def test_load_weather_trading_config_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_exists(monkeypatch, "weather_trading_config.json", True)
    _mock_file(monkeypatch, '{"trading": {"enabled": true}}')

    config = config_loader.load_weather_trading_config()

    assert config == {"trading": {"enabled": True}}
