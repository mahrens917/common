import builtins
from datetime import date
from typing import Any, Dict
from unittest.mock import mock_open

import pytest

from common import config_loader


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
    monkeypatch.setattr(config_loader, "load_pnl_config", lambda package=None: fake_config)

    start_date = config_loader.get_historical_start_date()

    assert start_date == date(2024, 2, 29)


def test_get_historical_start_date_invalid_date(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_config = {"trade_collection": {"historical_start_date": "2024-13-01"}}
    monkeypatch.setattr(config_loader, "load_pnl_config", lambda package=None: fake_config)

    with pytest.raises(RuntimeError) as err:
        config_loader.get_historical_start_date()

    assert "Invalid date format" in str(err.value)


def test_get_historical_start_date_load_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_error(package: Any = None) -> Dict[str, Any]:
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
    monkeypatch.setattr(config_loader, "load_pnl_config", lambda package=None: fake_config)

    assert config_loader.get_reporting_timezone() == "Europe/Berlin"


def test_get_reporting_timezone_raises_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_missing(package: Any = None) -> Dict[str, Any]:
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


def test_resolve_package_config_dir_not_found(tmp_path: pytest.MonkeyPatch) -> None:
    import common.config_loader as loader

    original_projects_base = loader._PROJECTS_BASE
    try:
        loader._PROJECTS_BASE = tmp_path

        with pytest.raises(FileNotFoundError) as err:
            loader._resolve_package_config_dir("nonexistent_package")

        assert "nonexistent_package" in str(err.value)
    finally:
        loader._PROJECTS_BASE = original_projects_base


def test_resolve_package_config_dir_success(tmp_path: pytest.TempPathFactory) -> None:
    import common.config_loader as loader

    original_projects_base = loader._PROJECTS_BASE
    try:
        loader._PROJECTS_BASE = tmp_path
        package_config_dir = tmp_path / "my_package" / "config"
        package_config_dir.mkdir(parents=True)

        result = loader._resolve_package_config_dir("my_package")

        assert result == package_config_dir
    finally:
        loader._PROJECTS_BASE = original_projects_base


def test_load_config_with_package(tmp_path: pytest.TempPathFactory) -> None:
    import common.config_loader as loader

    original_projects_base = loader._PROJECTS_BASE
    try:
        loader._PROJECTS_BASE = tmp_path
        package_config_dir = tmp_path / "test_pkg" / "config"
        package_config_dir.mkdir(parents=True)
        config_file = package_config_dir / "test_config.json"
        config_file.write_text('{"key": "value"}')

        result = loader.load_config("test_config.json", package="test_pkg")

        assert result == {"key": "value"}
    finally:
        loader._PROJECTS_BASE = original_projects_base


def test_load_config_with_package_not_found(tmp_path: pytest.TempPathFactory) -> None:
    import common.config_loader as loader

    original_projects_base = loader._PROJECTS_BASE
    try:
        loader._PROJECTS_BASE = tmp_path

        with pytest.raises(FileNotFoundError):
            loader.load_config("test_config.json", package="missing_pkg")
    finally:
        loader._PROJECTS_BASE = original_projects_base


def test_get_reporting_timezone_missing_reporting_section(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_config: Dict[str, Any] = {
        "trade_collection": {"historical_start_date": "2023-01-01"},
    }
    monkeypatch.setattr(config_loader, "load_pnl_config", lambda package=None: fake_config)

    with pytest.raises(TypeError) as err:
        config_loader.get_reporting_timezone()
    assert "reporting" in str(err.value)


def test_get_reporting_timezone_invalid_timezone_type(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_config: Dict[str, Any] = {
        "trade_collection": {"historical_start_date": "2023-01-01"},
        "reporting": {"timezone": 123},
    }
    monkeypatch.setattr(config_loader, "load_pnl_config", lambda package=None: fake_config)

    with pytest.raises(TypeError):
        config_loader.get_reporting_timezone()


def test_get_reporting_timezone_empty_string(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_config: Dict[str, Any] = {
        "trade_collection": {"historical_start_date": "2023-01-01"},
        "reporting": {"timezone": "   "},
    }
    monkeypatch.setattr(config_loader, "load_pnl_config", lambda package=None: fake_config)

    with pytest.raises(RuntimeError) as err:
        config_loader.get_reporting_timezone()
    assert "non-empty" in str(err.value)
