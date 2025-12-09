import json
from pathlib import Path

import pytest

from src.common.config import ConfigurationError, get_data_dir


def _write_runtime_config(tmp_path: Path, payload: dict) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "settings.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    return config_path


def test_get_data_dir_resolves_relative_path(tmp_path):
    config_path = _write_runtime_config(tmp_path, {"data_dir": "artifacts"})
    data_dir = config_path.parent / "artifacts"
    data_dir.mkdir()

    # No environment overrides so helper should derive from config path
    result = get_data_dir(config_path=config_path)
    assert result == str(data_dir.resolve())


def test_get_data_dir_supports_s3_uri(tmp_path):
    config_path = _write_runtime_config(tmp_path, {"data_dir": "s3://zeus-weather-bucket"})

    result = get_data_dir(config_path=config_path)
    assert result == "s3://zeus-weather-bucket"


def test_get_data_dir_missing_directory_raises(tmp_path):
    config_path = _write_runtime_config(tmp_path, {"data_dir": "missing"})

    with pytest.raises(ConfigurationError):
        get_data_dir(config_path=config_path)
