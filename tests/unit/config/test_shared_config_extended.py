import pytest

from src.common.config import ConfigurationError, runtime, shared


@pytest.fixture(autouse=True)
def clear_shared_caches():
    shared.get_redis_settings.cache_clear()
    shared.get_kalshi_credentials.cache_clear()
    shared.get_telegram_settings.cache_clear()
    runtime._DEFAULT_VALUES = {}
    yield
    shared.get_redis_settings.cache_clear()
    shared.get_kalshi_credentials.cache_clear()
    shared.get_telegram_settings.cache_clear()
    runtime._DEFAULT_VALUES = {}


def test_get_redis_settings_happy_path(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "cache")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.delenv("REDIS_DB", raising=False)
    monkeypatch.setenv("REDIS_PASSWORD", "")
    monkeypatch.setenv("REDIS_SSL", "true")
    monkeypatch.setenv("REDIS_SOCKET_TIMEOUT", "1.5")
    monkeypatch.setenv("REDIS_SOCKET_CONNECT_TIMEOUT", "2.5")
    monkeypatch.setenv("REDIS_RETRY_ON_TIMEOUT", "false")
    monkeypatch.setenv("REDIS_HEALTH_CHECK_INTERVAL", "0.0")

    settings = shared.get_redis_settings()
    assert settings.host == "cache"
    assert settings.port == 6379
    assert settings.db == 0
    assert settings.password == ""
    assert settings.ssl is True
    assert settings.retry_on_timeout is False
    assert settings.socket_timeout == 1.5
    assert settings.socket_connect_timeout == 2.5
    assert settings.health_check_interval == 0.0


def test_get_redis_settings_validation(monkeypatch):
    monkeypatch.delenv("REDIS_HOST", raising=False)
    with pytest.raises(ConfigurationError):
        shared.get_redis_settings()

    shared.get_redis_settings.cache_clear()
    monkeypatch.setenv("REDIS_HOST", "cache")
    monkeypatch.delenv("REDIS_PORT", raising=False)
    with pytest.raises(ConfigurationError):
        shared.get_redis_settings()

    shared.get_redis_settings.cache_clear()
    monkeypatch.setenv("REDIS_HOST", "cache")
    monkeypatch.setenv("REDIS_PORT", "1234")
    monkeypatch.setenv("REDIS_DB", "2")
    monkeypatch.setenv("REDIS_SSL", "false")
    monkeypatch.setenv("REDIS_RETRY_ON_TIMEOUT", "true")
    with pytest.raises(ConfigurationError):
        shared.get_redis_settings()


def test_get_redis_settings_handles_none_db(monkeypatch):
    def fake_env_int(name, or_value=None, required=False):
        if name == "REDIS_DB":
            return None
        return runtime.env_int(name, or_value=or_value, required=required)

    monkeypatch.setenv("REDIS_HOST", "cache")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_SSL", "false")
    monkeypatch.setenv("REDIS_RETRY_ON_TIMEOUT", "true")
    monkeypatch.setattr(shared, "env_int", fake_env_int)

    settings = shared.get_redis_settings()
    assert settings.db == 0


def test_get_redis_settings_guard_clauses(monkeypatch):
    shared.get_redis_settings.cache_clear()

    def host_none_env_str(name, **kwargs):
        if name == "REDIS_HOST":
            return None
        return runtime.env_str(name, **kwargs)

    monkeypatch.setattr(shared, "env_str", host_none_env_str)
    monkeypatch.setenv("REDIS_PORT", "1")
    monkeypatch.setenv("REDIS_SSL", "false")
    monkeypatch.setenv("REDIS_RETRY_ON_TIMEOUT", "true")
    with pytest.raises(ConfigurationError):
        shared.get_redis_settings()

    shared.get_redis_settings.cache_clear()
    monkeypatch.setattr(shared, "env_str", runtime.env_str)

    def port_none_env_int(name, default=None, required=False):
        if name == "REDIS_PORT":
            return None
        return runtime.env_int(name, default=default, required=required)

    monkeypatch.setattr(shared, "env_int", port_none_env_int)
    monkeypatch.setenv("REDIS_HOST", "cache")
    monkeypatch.setenv("REDIS_SSL", "false")
    monkeypatch.setenv("REDIS_RETRY_ON_TIMEOUT", "true")
    with pytest.raises(ConfigurationError):
        shared.get_redis_settings()


def test_kalshi_credentials_requirements(monkeypatch):
    shared.get_kalshi_credentials.cache_clear()
    monkeypatch.delenv("KALSHI_KEY_ID", raising=False)
    with pytest.raises(ConfigurationError):
        shared.get_kalshi_credentials()

    shared.get_kalshi_credentials.cache_clear()
    monkeypatch.setenv("KALSHI_KEY_ID", "key")
    monkeypatch.delenv("KALSHI_API_KEY_SECRET", raising=False)
    with pytest.raises(ConfigurationError):
        shared.get_kalshi_credentials(require_secret=True)

    credentials = shared.KalshiCredentials("id", "secret", None)
    with pytest.raises(ConfigurationError):
        credentials.require_private_key()

    monkeypatch.setenv("KALSHI_KEY_ID", "key")
    monkeypatch.setenv("KALSHI_API_KEY_SECRET", "secret")
    monkeypatch.setenv("KALSHI_RSA_PRIVATE_KEY", "private")
    shared.get_kalshi_credentials.cache_clear()
    creds = shared.get_kalshi_credentials()
    assert creds.key_id == "key"
    assert creds.api_key_secret == "secret"
    assert creds.rsa_private_key == "private"
    assert shared.KalshiCredentials("id", "secret", "private").require_private_key() == "private"

    monkeypatch.setenv("KALSHI_KEY_ID", "key")
    monkeypatch.delenv("KALSHI_API_KEY_SECRET", raising=False)
    shared.get_kalshi_credentials.cache_clear()
    creds = shared.get_kalshi_credentials(require_secret=False)
    assert creds.api_key_secret == ""

    shared.get_kalshi_credentials.cache_clear()

    def fake_env_str(name, **kwargs):
        if name == "KALSHI_API_KEY_SECRET":
            return ""
        return runtime.env_str(name, **kwargs)

    monkeypatch.setattr(shared, "env_str", fake_env_str)
    with pytest.raises(ConfigurationError):
        shared.get_kalshi_credentials()
    monkeypatch.setattr(shared, "env_str", runtime.env_str)
    monkeypatch.setenv("KALSHI_KEY_ID", "key")
    monkeypatch.delenv("KALSHI_API_KEY_SECRET", raising=False)
    monkeypatch.setattr(shared, "env_str", fake_env_str)
    with pytest.raises(ConfigurationError):
        shared.get_kalshi_credentials(require_secret=True)

    shared.get_kalshi_credentials.cache_clear()

    def key_id_none_env_str(name, **kwargs):
        if name == "KALSHI_KEY_ID":
            return None
        return runtime.env_str(name, **kwargs)

    monkeypatch.setattr(shared, "env_str", key_id_none_env_str)
    with pytest.raises(ConfigurationError):
        shared.get_kalshi_credentials(require_secret=False)


def test_telegram_settings_validations(monkeypatch):
    with pytest.raises(ConfigurationError):
        shared.TelegramSettings(bot_token="", chat_ids=("1",), timeout_seconds=1)
    with pytest.raises(ConfigurationError):
        shared.TelegramSettings(bot_token="token", chat_ids=(), timeout_seconds=1)
    with pytest.raises(ConfigurationError):
        shared.TelegramSettings(bot_token="token", chat_ids=("1",), timeout_seconds=0)

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_AUTHORIZED_USERS", raising=False)
    shared.get_telegram_settings.cache_clear()
    with pytest.raises(ConfigurationError):
        shared.get_telegram_settings()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_AUTHORIZED_USERS", "")
    shared.get_telegram_settings.cache_clear()
    with pytest.raises(ConfigurationError):
        shared.get_telegram_settings()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_AUTHORIZED_USERS", "1,2")
    monkeypatch.delenv("TELEGRAM_TIMEOUT_SECONDS", raising=False)
    shared.get_telegram_settings.cache_clear()
    settings = shared.get_telegram_settings()
    assert settings.bot_token == "token"
    assert settings.chat_ids == ("1", "2")
    assert settings.timeout_seconds == 10

    shared.get_telegram_settings.cache_clear()

    def token_none_env_str(name, **kwargs):
        if name == "TELEGRAM_BOT_TOKEN":
            return None
        return runtime.env_str(name, **kwargs)

    monkeypatch.setattr(shared, "env_str", token_none_env_str)
    monkeypatch.setenv("TELEGRAM_AUTHORIZED_USERS", "1")
    with pytest.raises(ConfigurationError):
        shared.get_telegram_settings()

    shared.get_telegram_settings.cache_clear()
    monkeypatch.setattr(shared, "env_str", runtime.env_str)

    def list_none_env_list(name, **kwargs):
        if name == "TELEGRAM_AUTHORIZED_USERS":
            return None
        return runtime.env_list(name, **kwargs)

    monkeypatch.setattr(shared, "env_list", list_none_env_list)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    with pytest.raises(ConfigurationError):
        shared.get_telegram_settings()
