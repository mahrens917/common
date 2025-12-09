from __future__ import annotations

"""Exception types for configuration handling."""


class ConfigurationError(RuntimeError):
    """Raised when configuration values are missing or malformed."""

    @classmethod
    def import_failed(
        cls, module_name: str, class_name: str, context: str = ""
    ) -> "ConfigurationError":
        """Create error for import failure."""
        msg = f"Unable to import {class_name} from {module_name}."
        if context:
            msg += f" {context}"
        return cls(msg)

    @classmethod
    def invalid_format(
        cls, param_name: str, received_value: str, expected_format: str = ""
    ) -> "ConfigurationError":
        """Create error for invalid format."""
        msg = f"{param_name} has invalid format (received {received_value!r})"
        if expected_format:
            msg += f". Expected {expected_format}"
        return cls(msg)

    @classmethod
    def missing_value(cls, param_name: str, context: str = "") -> "ConfigurationError":
        """Create error for missing value."""
        msg = f"{param_name} is missing or empty"
        if context:
            msg += f": {context}"
        return cls(msg)

    @classmethod
    def empty_windows(cls) -> "ConfigurationError":
        """Create error for empty window configuration."""
        return cls("HistoricalFeatureAugmenter window lengths does not define any window lengths")

    @classmethod
    def empty_feature_windows(cls) -> "ConfigurationError":
        """Create error for empty feature windows configuration."""
        return cls("Feature windows configuration is missing or empty; cannot compute history days")

    @classmethod
    def instantiation_failed(cls, class_name: str, context: str = "") -> "ConfigurationError":
        """Create error for failed instantiation."""
        msg = f"Failed to instantiate {class_name}"
        if context:
            msg += f" for {context}"
        return cls(msg)

    @classmethod
    def invalid_value(cls, param_name: str, value, reason: str = "") -> "ConfigurationError":
        """Create error for invalid value."""
        msg = f"Invalid value for {param_name}: {value!r}"
        if reason:
            msg += f". {reason}"
        return cls(msg)

    @classmethod
    def non_integer_windows(cls, windows) -> "ConfigurationError":
        """Create error for non-integer window lengths."""
        return cls(f"HistoricalFeatureAugmenter returned non-integer window lengths: {windows!r}")

    @classmethod
    def station_metadata_load_failed(cls, station_code: str) -> "ConfigurationError":
        """Create error for station metadata load failure."""
        return cls(f"Failed to load station metadata for {station_code}")

    @classmethod
    def station_timezone_missing(cls, station_code: str) -> "ConfigurationError":
        """Create error for missing station timezone."""
        return cls(f"Station catalog entry for {station_code} does not define a timezone")

    @classmethod
    def invalid_timezone(cls, station_code: str, tz_name: str) -> "ConfigurationError":
        """Create error for invalid timezone."""
        return cls(f"Invalid timezone '{tz_name}' for station {station_code}")

    @classmethod
    def load_failed(cls, resource: str, identifier: str = "") -> "ConfigurationError":
        """Create error for failed resource load."""
        msg = f"Failed to load {resource}"
        if identifier:
            msg += f" for {identifier}"
        return cls(msg)


__all__ = ["ConfigurationError"]
