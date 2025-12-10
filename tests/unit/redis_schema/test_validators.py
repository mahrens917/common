import importlib

import pytest

from common.redis_schema import validators


@pytest.fixture(autouse=True)
def reset_registry():
    importlib.reload(validators)
    yield
    validators._registered_prefixes.clear()


def test_register_namespace_accepts_unique_and_duplicate_descriptions():
    validators.register_namespace("market:", "Market data keys")

    # same description should be a no-op
    validators.register_namespace("market:", "Market data keys")

    assert validators._registered_prefixes["market:"] == "Market data keys"


def test_register_namespace_rejects_conflicting_description():
    validators.register_namespace("market:", "Market data keys")

    with pytest.raises(ValueError):
        validators.register_namespace("market:", "Different description")


def test_validate_registered_key_confirms_known_prefix():
    validators.register_namespace("market:", "Market data keys")

    result = validators.validate_registered_key("market:KX123")
    assert result is None
    assert validators._registered_prefixes == {"market:": "Market data keys"}


def test_validate_registered_key_rejects_unknown_prefix():
    validators.register_namespace("market:", "Market data keys")

    with pytest.raises(ValueError):
        validators.validate_registered_key("analytics:instrument")
