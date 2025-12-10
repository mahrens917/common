import pytest

from common.config.errors import ConfigurationError


@pytest.mark.parametrize(
    ("factory", "args", "expected"),
    [
        (
            ConfigurationError.import_failed,
            ("module", "Class", ""),
            "Unable to import Class from module.",
        ),
        (
            ConfigurationError.import_failed,
            ("module", "Class", "Check dependencies"),
            "Unable to import Class from module. Check dependencies",
        ),
        (
            ConfigurationError.invalid_format,
            ("param", "value", "expected pattern"),
            "param has invalid format (received 'value'). Expected expected pattern",
        ),
        (
            ConfigurationError.missing_value,
            ("param", "context"),
            "param is missing or empty: context",
        ),
        (
            ConfigurationError.invalid_value,
            ("name", 5, "must be positive"),
            "Invalid value for name: 5. must be positive",
        ),
        (
            ConfigurationError.instantiation_failed,
            ("ClassName", "context"),
            "Failed to instantiate ClassName for context",
        ),
        (
            ConfigurationError.load_failed,
            ("resource", "id"),
            "Failed to load resource for id",
        ),
    ],
)
def test_configuration_error_factories(factory, args, expected):
    exc = factory(*args)
    assert isinstance(exc, ConfigurationError)
    assert str(exc) == expected


def test_specific_configuration_errors():
    assert str(ConfigurationError.empty_windows()) == (
        "HistoricalFeatureAugmenter window lengths does not define any window lengths"
    )
    assert str(ConfigurationError.empty_feature_windows()) == (
        "Feature windows configuration is missing or empty; cannot compute history days"
    )
    assert (
        str(ConfigurationError.non_integer_windows([1, "two"]))
        == "HistoricalFeatureAugmenter returned non-integer window lengths: [1, 'two']"
    )
    assert str(ConfigurationError.station_metadata_load_failed("ABC")) == (
        "Failed to load station metadata for ABC"
    )
    assert str(ConfigurationError.station_timezone_missing("ABC")) == (
        "Station catalog entry for ABC does not define a timezone"
    )
    assert str(ConfigurationError.invalid_timezone("ABC", "Bad/TZ")) == (
        "Invalid timezone 'Bad/TZ' for station ABC"
    )
