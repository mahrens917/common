from __future__ import annotations

"""Shared configuration dataclasses consumed across multiple modules."""


from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from . import ConfigurationError, env_bool, env_float, env_int, env_list, env_seconds, env_str

EMPTY_KALSHI_SECRET = ""


@dataclass(frozen=True)
class RedisSettings:
    host: str
    port: int
    db: int
    password: str | None
    ssl: bool
    socket_timeout: float | None
    socket_connect_timeout: float | None
    retry_on_timeout: bool
    health_check_interval: float | None


@lru_cache(maxsize=1)
def get_redis_settings() -> RedisSettings:
    file_settings = _load_redis_settings_from_json()

    host = env_str("REDIS_HOST", or_value=file_settings.host)
    port_value = env_int("REDIS_PORT", or_value=file_settings.port)
    db_value = env_int("REDIS_DB", or_value=file_settings.db)
    if db_value != 0:
        raise ConfigurationError(f"Only Redis database 0 is supported; received REDIS_DB={db_value}")

    password = env_str("REDIS_PASSWORD", or_value=file_settings.password, allow_blank=True)
    ssl_flag = env_bool("REDIS_SSL", or_value=file_settings.ssl)
    socket_timeout = env_float("REDIS_SOCKET_TIMEOUT", or_value=file_settings.socket_timeout)
    socket_connect_timeout = env_float(
        "REDIS_SOCKET_CONNECT_TIMEOUT", or_value=file_settings.socket_connect_timeout
    )
    retry_on_timeout_flag = env_bool("REDIS_RETRY_ON_TIMEOUT", or_value=file_settings.retry_on_timeout)
    health_check_interval = env_float(
        "REDIS_HEALTH_CHECK_INTERVAL", or_value=file_settings.health_check_interval
    )

    return RedisSettings(
        host=host,
        port=int(port_value),
        db=0,
        password=password,
        ssl=bool(ssl_flag),
        socket_timeout=socket_timeout,
        socket_connect_timeout=socket_connect_timeout,
        retry_on_timeout=bool(retry_on_timeout_flag),
        health_check_interval=health_check_interval,
    )


def _load_redis_settings_from_json() -> RedisSettings:
    import json
    from pathlib import Path

    config_path = Path.cwd() / "config" / "redis_config.json"
    if not config_path.exists():
        raise ConfigurationError(
            "Redis configuration is missing. Provide env vars (REDIS_HOST/REDIS_PORT/REDIS_SSL/etc.) "
            f"or create {config_path}."
        )

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Failed to read Redis config at {config_path}: {exc}") from exc

    if not isinstance(payload, dict) or "redis" not in payload:
        raise ConfigurationError(f"Redis config at {config_path} must be a JSON object with key 'redis'")

    raw = payload["redis"]
    if not isinstance(raw, dict):
        raise ConfigurationError(f"Redis config at {config_path}['redis'] must be a JSON object")

    host = raw.get("host")
    port = raw.get("port")
    db = raw.get("db", 0)
    password = raw.get("password", None)
    ssl = raw.get("ssl", False)
    socket_timeout = raw.get("socket_timeout", None)
    socket_connect_timeout = raw.get("socket_connect_timeout", None)
    retry_on_timeout = raw.get("retry_on_timeout", False)
    health_check_interval = raw.get("health_check_interval", None)

    if not isinstance(host, str) or not host:
        raise ConfigurationError(f"Redis config at {config_path}: 'host' must be a non-empty string")
    if not isinstance(port, int):
        raise ConfigurationError(f"Redis config at {config_path}: 'port' must be an integer")
    if not isinstance(db, int):
        raise ConfigurationError(f"Redis config at {config_path}: 'db' must be an integer")
    if db != 0:
        raise ConfigurationError(f"Only Redis database 0 is supported; received db={db}")
    if password is not None and not isinstance(password, str):
        raise ConfigurationError(f"Redis config at {config_path}: 'password' must be a string or null")
    if not isinstance(ssl, bool):
        raise ConfigurationError(f"Redis config at {config_path}: 'ssl' must be a boolean")
    if socket_timeout is not None and not isinstance(socket_timeout, (int, float)):
        raise ConfigurationError(f"Redis config at {config_path}: 'socket_timeout' must be a number or null")
    if socket_connect_timeout is not None and not isinstance(socket_connect_timeout, (int, float)):
        raise ConfigurationError(
            f"Redis config at {config_path}: 'socket_connect_timeout' must be a number or null"
        )
    if not isinstance(retry_on_timeout, bool):
        raise ConfigurationError(f"Redis config at {config_path}: 'retry_on_timeout' must be a boolean")
    if health_check_interval is not None and not isinstance(health_check_interval, (int, float)):
        raise ConfigurationError(
            f"Redis config at {config_path}: 'health_check_interval' must be a number or null"
        )

    password_value = password if password not in ("", None) else None

    return RedisSettings(
        host=host,
        port=port,
        db=0,
        password=password_value,
        ssl=ssl,
        socket_timeout=float(socket_timeout) if socket_timeout is not None else None,
        socket_connect_timeout=float(socket_connect_timeout) if socket_connect_timeout is not None else None,
        retry_on_timeout=retry_on_timeout,
        health_check_interval=float(health_check_interval)
        if health_check_interval is not None
        else None,
    )


@dataclass(frozen=True)
class KalshiCredentials:
    key_id: str
    api_key_secret: str
    rsa_private_key: Optional[str]

    def require_private_key(self) -> str:
        if not self.rsa_private_key:
            raise ConfigurationError("KALSHI_RSA_PRIVATE_KEY is required for this operation")
        return self.rsa_private_key


@lru_cache(maxsize=1)
def get_kalshi_credentials(*, require_secret: bool = True) -> KalshiCredentials:
    key_id = env_str("KALSHI_KEY_ID", required=True)
    if key_id is None:
        raise ConfigurationError("KALSHI_KEY_ID must be set")
    api_key_secret = env_str("KALSHI_API_KEY_SECRET", required=require_secret)
    private_key = env_str("KALSHI_RSA_PRIVATE_KEY", or_value=None, allow_blank=True)

    if require_secret and not api_key_secret:
        raise ConfigurationError("KALSHI_API_KEY_SECRET must be provided")

    secret_value = api_key_secret if api_key_secret is not None else EMPTY_KALSHI_SECRET

    return KalshiCredentials(
        key_id=key_id,
        api_key_secret=secret_value,
        rsa_private_key=private_key,
    )


@dataclass(frozen=True)
class TelegramSettings:
    bot_token: str
    chat_ids: tuple[str, ...]
    timeout_seconds: int

    def __post_init__(self) -> None:
        if not self.bot_token:
            raise ConfigurationError("TELEGRAM_BOT_TOKEN must not be empty")
        if not self.chat_ids:
            raise ConfigurationError("TELEGRAM_AUTHORIZED_USERS must list at least one chat id")
        if self.timeout_seconds <= 0:
            raise ConfigurationError("TELEGRAM timeout must be a positive number of seconds")


@lru_cache(maxsize=1)
def get_telegram_settings(default_timeout: int = 10) -> TelegramSettings:
    bot_token = env_str("TELEGRAM_BOT_TOKEN", required=True, strip=True)
    if bot_token is None:
        raise ConfigurationError("TELEGRAM_BOT_TOKEN must not be empty")
    chat_ids_value = env_list("TELEGRAM_AUTHORIZED_USERS", separator=",", required=True)
    if chat_ids_value is None:
        raise ConfigurationError("TELEGRAM_AUTHORIZED_USERS must list at least one chat id")
    chat_ids = chat_ids_value

    timeout_seconds = env_seconds("TELEGRAM_TIMEOUT_SECONDS")
    if timeout_seconds is None:
        timeout_seconds = default_timeout

    return TelegramSettings(
        bot_token=bot_token,
        chat_ids=chat_ids,
        timeout_seconds=timeout_seconds,
    )


__all__ = [
    "KalshiCredentials",
    "RedisSettings",
    "TelegramSettings",
    "get_kalshi_credentials",
    "get_redis_settings",
    "get_telegram_settings",
]
