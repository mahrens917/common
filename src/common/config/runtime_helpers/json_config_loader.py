"""JSON configuration file loading utilities.

Delegates to BaseConfigLoader for JSON loading, adds environment variable normalization.
"""

from pathlib import Path
from typing import Any, Dict

from common.config_loader import BaseConfigLoader

from ..errors import ConfigurationError


class JsonConfigLoader:
    """Loads configuration from JSON files.

    Delegates to BaseConfigLoader for JSON loading while providing
    environment variable-specific normalization logic.
    """

    def __init__(self) -> None:
        """Initialize with a shared base loader."""
        # BaseConfigLoader will be instantiated per-directory as needed
        pass

    @staticmethod
    def load_from_file(path: Path) -> Dict[str, str]:
        """
        Load configuration from JSON file.

        Delegates to BaseConfigLoader for JSON loading, then normalizes values
        to strings for environment variable usage.

        Args:
            path: Path to JSON file

        Returns:
            Dictionary of environment variables (all values as strings)

        Raises:
            ConfigurationError: If file cannot be read or parsed
        """
        if not path.exists():
            return {}

        # Use BaseConfigLoader for consistent JSON loading
        loader = BaseConfigLoader(path.parent)
        try:
            payload = loader.load_json_file(path.name)
        except FileNotFoundError:
            return {}
        except ConfigurationError:
            raise
        except OSError as exc:  # pragma: no cover - filesystem access failure
            raise ConfigurationError(f"Failed to read {path}") from exc

        return JsonConfigLoader._normalize_values(payload, path)

    @staticmethod
    def _normalize_values(payload: Dict[str, Any], path: Path) -> Dict[str, str]:
        """
        Normalize JSON values to strings for environment variables.

        Args:
            payload: Parsed JSON object
            path: Path to config file (for error messages)

        Returns:
            Dictionary with string values

        Raises:
            ConfigurationError: If values are nested structures
        """
        normalized: Dict[str, str] = {}

        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                raise ConfigurationError(f"JSON config {path} must map environment names to scalar values (problematic key: {key})")

            if value is None:
                normalized[str(key)] = ""
            else:
                normalized[str(key)] = str(value)

        return normalized
