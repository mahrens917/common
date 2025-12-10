import json
from pathlib import Path

import pytest

from common.config import ConfigurationError, runtime
from common.config.runtime_helpers import JsonConfigLoader, ListNormalizer


@pytest.fixture(autouse=True)
def reset_runtime_state():
    runtime._DEFAULT_VALUES = None
    yield
    runtime._DEFAULT_VALUES = None


def test_load_default_values_prefers_first_source(monkeypatch, tmp_path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("FIRST=from_env\nSHARED=env\n")

    json_path = tmp_path / "runtime_env.json"
    json_path.write_text(json.dumps({"SHARED": "json", "OTHER": 3}))

    monkeypatch.setattr(runtime, "_DOTENV_CANDIDATES", (dotenv_path,))
    monkeypatch.setattr(runtime, "_JSON_ENV_CANDIDATES", (json_path,))

    defaults = runtime._load_default_values()
    assert defaults == {"FIRST": "from_env", "SHARED": "env", "OTHER": "3"}
    # Cached value is reused without re-reading files
    assert runtime._load_default_values() is defaults


def test_env_str_uses_defaults_and_handles_blanks(monkeypatch):
    runtime._DEFAULT_VALUES = {"FALLBACK": " spaced "}
    monkeypatch.delenv("FALLBACK", raising=False)
    assert runtime.env_str("FALLBACK") == "spaced"

    monkeypatch.setenv("ALLOW_BLANK", "")
    assert runtime.env_str("ALLOW_BLANK", allow_blank=True) == ""

    monkeypatch.setenv("NO_STRIP", " padded ")
    assert runtime.env_str("NO_STRIP", strip=False) == " padded "

    runtime._DEFAULT_VALUES = {}
    with pytest.raises(ConfigurationError):
        runtime.env_str("MISSING_REQUIRED", required=True)


def test_env_int_and_float_validation(monkeypatch):
    monkeypatch.setenv("INT_VALUE", "7")
    assert runtime.env_int("INT_VALUE") == 7

    monkeypatch.delenv("INT_REQUIRED", raising=False)
    with pytest.raises(ConfigurationError):
        runtime.env_int("INT_REQUIRED", required=True)

    monkeypatch.setenv("INT_INVALID", "abc")
    with pytest.raises(ConfigurationError):
        runtime.env_int("INT_INVALID")

    monkeypatch.setenv("FLOAT_VALUE", "2.5")
    assert runtime.env_float("FLOAT_VALUE") == 2.5

    monkeypatch.setenv("FLOAT_INVALID", "five")
    with pytest.raises(ConfigurationError):
        runtime.env_float("FLOAT_INVALID")

    monkeypatch.delenv("FLOAT_DEFAULT", raising=False)
    assert runtime.env_float("FLOAT_DEFAULT", or_value=1.5, required=True) == 1.5

    monkeypatch.delenv("FLOAT_REQUIRED", raising=False)
    with pytest.raises(ConfigurationError):
        runtime.env_float("FLOAT_REQUIRED", required=True)


def test_env_bool_accepts_truthy_and_falsy(monkeypatch):
    monkeypatch.setenv("BOOL_TRUE", "YeS")
    assert runtime.env_bool("BOOL_TRUE") is True

    monkeypatch.setenv("BOOL_FALSE", "0")
    assert runtime.env_bool("BOOL_FALSE") is False

    monkeypatch.delenv("BOOL_REQUIRED", raising=False)
    with pytest.raises(ConfigurationError):
        runtime.env_bool("BOOL_REQUIRED", required=True)

    monkeypatch.setenv("BOOL_INVALID", "perhaps")
    with pytest.raises(ConfigurationError):
        runtime.env_bool("BOOL_INVALID")


def test_env_list_handles_defaults_and_uniqueness(monkeypatch):
    monkeypatch.delenv("LIST_NONE", raising=False)
    assert runtime.env_list("LIST_NONE") is None

    with pytest.raises(ConfigurationError):
        runtime.env_list("LIST_REQUIRED", required=True)

    assert runtime.env_list("LIST_DEFAULT", or_value=("a", "b"), required=True) == ("a", "b")

    monkeypatch.setenv("LIST_VALUES", "a, b ,a")
    assert runtime.env_list("LIST_VALUES") == ("a", "b")
    assert runtime.env_list("LIST_VALUES", unique=False) == ("a", "b", "a")

    monkeypatch.setenv("LIST_EMPTY_AFTER_NORMALIZE", " , ")
    with pytest.raises(ConfigurationError):
        runtime.env_list("LIST_EMPTY_AFTER_NORMALIZE", required=True)


def test_env_seconds_and_coerce(monkeypatch):
    monkeypatch.delenv("SECONDS_NONE", raising=False)
    assert runtime.env_seconds("SECONDS_NONE") is None

    monkeypatch.setenv("SECONDS_NEGATIVE", "-2")
    with pytest.raises(ConfigurationError):
        runtime.env_seconds("SECONDS_NEGATIVE")

    monkeypatch.delenv("SECONDS_DEFAULT", raising=False)
    assert runtime.env_seconds("SECONDS_DEFAULT", or_value=3, required=True) == 3

    monkeypatch.setenv("SECONDS_POSITIVE", "9")
    assert runtime.env_seconds("SECONDS_POSITIVE") == 9

    assert runtime._coerce("INT_CAST", "4", cast=int) == 4


def test_load_json_variants(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    missing = "missing.json"
    with pytest.raises(ConfigurationError):
        runtime.load_json(missing)

    valid_config = config_dir / "valid.json"
    valid_config.write_text(json.dumps({"key": "value"}))
    loaded = runtime.load_json("valid.json")
    assert loaded.path == Path("config") / "valid.json"
    assert loaded.payload == {"key": "value"}

    invalid_config = config_dir / "invalid.json"
    invalid_config.write_text(json.dumps([1, 2, 3]))
    with pytest.raises(ConfigurationError):
        runtime.load_json("invalid.json")


def test_resolve_data_config_path(monkeypatch, tmp_path):
    explicit = Path("~/config.json")
    assert runtime._resolve_data_config_path(explicit) == explicit.expanduser()

    monkeypatch.delenv(runtime._DATA_CONFIG_ENV, raising=False)
    with pytest.raises(ConfigurationError):
        runtime._resolve_data_config_path(None)

    env_path = tmp_path / "runtime.json"
    monkeypatch.setenv(runtime._DATA_CONFIG_ENV, str(env_path))
    assert runtime._resolve_data_config_path(None) == env_path


def test_get_data_dir_paths(monkeypatch, tmp_path):
    config_file = tmp_path / "data_config.json"

    with pytest.raises(ConfigurationError):
        runtime.get_data_dir(config_path=config_file)

    config_file.write_text("{not-json")
    with pytest.raises(ConfigurationError):
        runtime.get_data_dir(config_path=config_file)

    config_file.write_text(json.dumps(["unexpected"]))
    with pytest.raises(ConfigurationError):
        runtime.get_data_dir(config_path=config_file)

    config_file.write_text(json.dumps({"data_dir": ""}))
    with pytest.raises(ConfigurationError):
        runtime.get_data_dir(config_path=config_file)

    config_file.write_text(json.dumps({"data_dir": "s3://bucket/path"}))
    assert runtime.get_data_dir(config_path=config_file) == "s3://bucket/path"

    data_dir = tmp_path / "nested"
    data_dir.mkdir()
    config_file.write_text(json.dumps({"data_dir": "nested"}))
    assert runtime.get_data_dir(config_path=config_file) == str(data_dir.resolve())

    missing_dir_config = tmp_path / "missing_config.json"
    missing_dir_config.write_text(json.dumps({"data_dir": "missing_dir"}))
    with pytest.raises(ConfigurationError):
        runtime.get_data_dir(config_path=missing_dir_config)

    file_target = tmp_path / "file_target.txt"
    file_target.write_text("content")
    config_file.write_text(json.dumps({"data_dir": str(file_target)}))
    with pytest.raises(ConfigurationError):
        runtime.get_data_dir(config_path=config_file)


def test_json_config_loader_behaviour(monkeypatch, tmp_path):
    import importlib

    JsonConfigLoader()

    missing_path = tmp_path / "does_not_exist.json"
    assert JsonConfigLoader.load_from_file(missing_path) == {}

    existing_path = tmp_path / "present.json"
    existing_path.write_text("{}")

    module = importlib.import_module("common.config.runtime_helpers.json_config_loader")

    class DummyLoader:
        def __init__(self, payload):
            self.payload = payload

        def load_json_file(self, _):
            if isinstance(self.payload, Exception):
                raise self.payload
            return self.payload

    monkeypatch.setattr(module, "BaseConfigLoader", lambda path: DummyLoader(FileNotFoundError()))
    assert JsonConfigLoader.load_from_file(existing_path) == {}

    monkeypatch.setattr(
        module, "BaseConfigLoader", lambda path: DummyLoader(ConfigurationError("boom"))
    )
    with pytest.raises(ConfigurationError):
        JsonConfigLoader.load_from_file(existing_path)

    monkeypatch.setattr(
        module,
        "BaseConfigLoader",
        lambda path: DummyLoader({"alpha": 1, "none": None}),
    )
    normalized = JsonConfigLoader.load_from_file(existing_path)
    assert normalized == {"alpha": "1", "none": ""}

    with pytest.raises(ConfigurationError):
        JsonConfigLoader._normalize_values({"nested": {}}, existing_path)


def test_list_normalizer_covers_all_branches():
    assert ListNormalizer.split_and_normalize("a,,b", separator=",", strip_items=True) == ["a", "b"]
    assert ListNormalizer.split_and_normalize(" spaced ", separator="", strip_items=False) == [
        " spaced "
    ]
    assert ListNormalizer.deduplicate_preserving_order(("x", "x", "y")) == ("x", "y")
    assert ListNormalizer._normalize_items(["", " keep "], strip_items=False) == ["", " keep "]
