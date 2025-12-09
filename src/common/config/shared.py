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
    host = env_str("REDIS_HOST", required=True)
    if host is None:
        raise ConfigurationError("REDIS_HOST is required")

    port_value = env_int("REDIS_PORT", required=True)
    if port_value is None:
        raise ConfigurationError("REDIS_PORT is required")

    db_value = env_int("REDIS_DB", or_value=0)
    if db_value is None:
        db_value = 0
    if db_value != 0:
        raise ConfigurationError(
            f"Only Redis database 0 is supported; received REDIS_DB={db_value}"
        )

    db = 0

    password = env_str("REDIS_PASSWORD", or_value=None, allow_blank=True)
    ssl_flag = env_bool("REDIS_SSL", required=True)
    socket_timeout = env_float("REDIS_SOCKET_TIMEOUT")
    socket_connect_timeout = env_float("REDIS_SOCKET_CONNECT_TIMEOUT")
    retry_on_timeout_flag = env_bool("REDIS_RETRY_ON_TIMEOUT", required=True)
    health_check_interval = env_float("REDIS_HEALTH_CHECK_INTERVAL")

    return RedisSettings(
        host=host,
        port=port_value,
        db=db,
        password=password,
        ssl=bool(ssl_flag),
        socket_timeout=socket_timeout,
        socket_connect_timeout=socket_connect_timeout,
        retry_on_timeout=bool(retry_on_timeout_flag),
        health_check_interval=health_check_interval,
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
