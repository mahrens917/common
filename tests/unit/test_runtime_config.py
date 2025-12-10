import json
from pathlib import Path

import pytest

from common.config.errors import ConfigurationError
from common.config.runtime import (
    env_bool,
    env_float,
    env_int,
    env_list,
    env_seconds,
    get_data_dir,
    load_json,
)

_CONST_15 = 15
_CONST_42 = 42


def test_env_helpers(monkeypatch):
    monkeypatch.setenv("TEST_INT", "42")
    monkeypatch.setenv("TEST_FLOAT", "3.14")
    monkeypatch.setenv("TEST_BOOL_TRUE", "Yes")
    monkeypatch.setenv("TEST_LIST", "a, b, a ,c")
    monkeypatch.setenv("TEST_SECONDS", "15")

    assert env_int("TEST_INT") == _CONST_42
    assert env_float("TEST_FLOAT") == pytest.approx(3.14)
    assert env_bool("TEST_BOOL_TRUE") is True
    assert env_list("TEST_LIST") == ("a", "b", "c")
    assert env_seconds("TEST_SECONDS") == _CONST_15


def test_env_helpers_errors(monkeypatch):
    monkeypatch.delenv("MISSING_INT", raising=False)
    with pytest.raises(ConfigurationError):
        env_int("MISSING_INT", required=True)

    monkeypatch.setenv("BAD_FLOAT", "not-a-float")
    with pytest.raises(ConfigurationError, match="must be a float"):
        env_float("BAD_FLOAT")

    monkeypatch.setenv("BAD_BOOL", "maybe")
    with pytest.raises(ConfigurationError, match="must be a boolean"):
        env_bool("BAD_BOOL")

    monkeypatch.setenv("NEG_SECONDS", "-5")
    with pytest.raises(ConfigurationError, match="must be non-negative"):
        env_seconds("NEG_SECONDS")


def test_load_json_success():
    config = load_json("test_config.json")
    assert config.path.name == "test_config.json"
    assert config.payload["pipeline_data"]["mode"] == "synthetic"


def test_load_json_missing():
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_json("missing_config.json")


def test_get_data_dir_resolves_relative_path(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    data_dir = config_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "settings.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"data_dir": "data"}), encoding="utf-8")

    monkeypatch.setenv("WEATHER_DATA_CONFIG_PATH", str(config_path))

    try:
        resolved = get_data_dir()
    finally:
        monkeypatch.delenv("WEATHER_DATA_CONFIG_PATH", raising=False)

    assert Path(resolved) == data_dir.resolve()


def test_get_data_dir_s3_normalization(monkeypatch, tmp_path):
    config_path = tmp_path / "settings.json"
    config_path.write_text(json.dumps({"data_dir": "s3://bucket/path"}), encoding="utf-8")
    monkeypatch.setenv("WEATHER_DATA_CONFIG_PATH", str(config_path))

    try:
        resolved = get_data_dir()
    finally:
        monkeypatch.delenv("WEATHER_DATA_CONFIG_PATH", raising=False)

    assert resolved == "s3://bucket/path"
