from __future__ import annotations

"""Runtime helpers for working with environment-backed configuration."""


import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence, TypeVar

from .errors import ConfigurationError

T = TypeVar("T")

_TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
_FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}

_DOTENV_CANDIDATES = (Path(".env"), Path.home() / ".env")
_JSON_ENV_CANDIDATES = (Path("config/runtime_env.json"), Path.home() / ".kalshi_env.json")

_DEFAULT_VALUES: dict[str, str] | None = None


def _load_default_values() -> dict[str, str]:
    """Load configuration values from .env-style files or JSON defaults."""
    from .runtime_helpers import DotenvLoader, JsonConfigLoader

    global _DEFAULT_VALUES
    if _DEFAULT_VALUES is not None:
        return _DEFAULT_VALUES

    defaults: dict[str, str] = {}

    def _maybe_set(key: str, value: str) -> None:
        if key not in defaults:
            defaults[key] = value

    # Load standard .env style key/value pairs
    for path in _DOTENV_CANDIDATES:
        dotenv_values = DotenvLoader.load_from_file(path)
        for key, value in dotenv_values.items():
            _maybe_set(key, value)

    # Load JSON config dictionaries
    for path in _JSON_ENV_CANDIDATES:
        json_values = JsonConfigLoader.load_from_file(path)
        for key, value in json_values.items():
            _maybe_set(key, value)

    _DEFAULT_VALUES = defaults
    return defaults


def _default_value(name: str) -> Optional[str]:
    """Return the default value for *name* if declared in config."""

    defaults = _load_default_values()
    return defaults.get(name)


def _normalize(value: str | None, *, strip: bool) -> str | None:
    if value is None:
        return None
    return value.strip() if strip else value


def _coerce(name: str, raw_value: str, *, cast: Callable[[str], T]) -> T:
    try:
        return cast(raw_value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"Failed to cast environment variable {name!r}") from exc


def env_str(
    name: str,
    or_value: str | None = None,
    *,
    required: bool = False,
    strip: bool = True,
    allow_blank: bool = False,
) -> str | None:
    """Fetch an environment variable as a string with validation."""

    value = _normalize(os.getenv(name), strip=strip)

    if value is None or (not allow_blank and value == ""):
        configured_default = _default_value(name)
        if configured_default is not None:
            value = _normalize(configured_default, strip=strip)

    if value is None or (not allow_blank and value == ""):
        if required:
            raise ConfigurationError(f"Required environment variable {name!r} is not set")
        return or_value
    return value


def env_int(name: str, or_value: int | None = None, *, required: bool = False) -> int | None:
    """Fetch an environment variable and coerce it to ``int``."""

    raw = env_str(name, strip=True, allow_blank=False)
    if raw is None:
        if required and or_value is None:
            raise ConfigurationError(f"Required environment variable {name!r} is not set")
        return or_value
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"Environment variable {name!r} must be an integer (got {raw!r})") from exc


def env_float(name: str, or_value: float | None = None, *, required: bool = False) -> float | None:
    """Fetch an environment variable and coerce it to ``float``."""

    raw = env_str(name, strip=True, allow_blank=False)
    if raw is None:
        if required and or_value is None:
            raise ConfigurationError(f"Required environment variable {name!r} is not set")
        return or_value
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"Environment variable {name!r} must be a float (got {raw!r})") from exc


def env_bool(name: str, or_value: bool | None = None, *, required: bool = False) -> bool | None:
    """Fetch an environment variable and coerce it to ``bool``."""

    raw = env_str(name, strip=True, allow_blank=False)
    if raw is None:
        if required and or_value is None:
            raise ConfigurationError(f"Required environment variable {name!r} is not set")
        return or_value

    lowered = raw.lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    raise ConfigurationError(f"Environment variable {name!r} must be a boolean (allowed: {_TRUE_VALUES | _FALSE_VALUES}, got {raw!r})")


def env_list(
    name: str,
    *,
    or_value: Sequence[str] | None = None,
    separator: str = ",",
    strip_items: bool = True,
    unique: bool = True,
    required: bool = False,
) -> tuple[str, ...] | None:
    """Fetch a delimited list from the environment."""
    from .runtime_helpers import ListNormalizer

    raw = env_str(name, strip=True, allow_blank=False)
    if raw is None or raw == "":
        if required and not or_value:
            raise ConfigurationError(f"Required environment variable {name!r} is not set")
        if or_value is None:
            return None
        return tuple(or_value)

    normalized_items = ListNormalizer.split_and_normalize(raw, separator, strip_items)
    normalized = tuple(normalized_items)

    if not normalized and required:
        raise ConfigurationError(f"Environment variable {name!r} must contain at least one value")

    if unique:
        return ListNormalizer.deduplicate_preserving_order(normalized)

    return normalized


def env_seconds(name: str, or_value: int | None = None, *, required: bool = False) -> int | None:
    """Convenience wrapper for fetching durations stored as seconds."""

    value = env_int(name, or_value=or_value, required=required)
    if value is None:
        return None
    if value < 0:
        raise ConfigurationError(f"Environment variable {name!r} must be non-negative (got {value})")
    return value


@dataclass(frozen=True)
class JsonConfig:
    path: Path
    payload: dict[str, object]


def load_json(relative_path: str) -> JsonConfig:
    """Load a JSON resource from the ``config/`` directory."""

    config_path = Path("config") / relative_path
    if not config_path.exists():
        raise ConfigurationError(f"Configuration file {config_path} does not exist")
    try:
        data = json.loads(config_path.read_text())
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Failed to parse JSON config {config_path}") from exc

    if not isinstance(data, dict):
        raise ConfigurationError(f"JSON config {config_path} must contain an object at the top level")

    return JsonConfig(path=config_path, payload=data)


_DATA_CONFIG_ENV = "WEATHER_DATA_CONFIG_PATH"


def _resolve_data_config_path(config_path: Optional[Path]) -> Path:
    """Resolve the runtime configuration file that declares the weather data directory."""

    if config_path is not None:
        return config_path.expanduser()

    env_value = os.getenv(_DATA_CONFIG_ENV)
    if not env_value:
        raise ConfigurationError(
            f"Weather data directory configuration not provided. " f"Set {_DATA_CONFIG_ENV} or pass config_path explicitly."
        )

    return Path(env_value).expanduser()


def get_data_dir(*, config_path: Optional[Path] = None) -> str:
    """Return the weather data directory derived from the runtime config."""

    resolved_config = _resolve_data_config_path(config_path)
    if not resolved_config.exists():
        raise ConfigurationError(f"Weather data configuration file not found: {resolved_config}")

    try:
        payload = json.loads(resolved_config.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Failed to parse weather data configuration {resolved_config}") from exc

    if not isinstance(payload, dict):
        raise ConfigurationError(f"Weather data configuration {resolved_config} must contain an object")

    raw_path = payload.get("data_dir")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConfigurationError(f"'data_dir' must be a non-empty string in {resolved_config}")

    raw_path = raw_path.strip()
    if raw_path.lower().startswith("s3://"):
        return raw_path

    resolved = Path(raw_path).expanduser()
    if not resolved.is_absolute():
        resolved = (resolved_config.parent / resolved).resolve()

    if not resolved.exists():
        raise ConfigurationError(f"Configured data directory does not exist: {resolved}")
    if not resolved.is_dir():
        raise ConfigurationError(f"Configured data directory is not a directory: {resolved}")

    return str(resolved)


__all__ = [
    "ConfigurationError",
    "JsonConfig",
    "env_bool",
    "env_float",
    "env_int",
    "env_list",
    "env_seconds",
    "env_str",
    "load_json",
    "get_data_dir",
]
