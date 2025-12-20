"""Dotenv file loading utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from ..errors import ConfigurationError


class DotenvLoader:
    """Loads configuration from .env-style files."""

    @staticmethod
    def load_from_file(path: Path) -> Dict[str, str]:
        """
        Load key-value pairs from a .env file.

        Args:
            path: Path to .env file

        Returns:
            Dictionary of environment variables

        Raises:
            ConfigurationError: If file cannot be read
        """
        if not path.exists():
            return {}

        values: Dict[str, str] = {}
        try:
            for line in path.read_text().splitlines():
                stripped = line.strip()
                if DotenvLoader._should_skip_line(stripped):
                    continue

                key, value = DotenvLoader._parse_env_line(stripped)
                if key:
                    values[key] = value

        except OSError as exc:  # policy_guard: allow-silent-handler
            raise ConfigurationError(f"Failed to load configuration from {path}") from exc

        return values

    @staticmethod
    def _should_skip_line(line: str) -> bool:
        """Check if line should be skipped."""
        return not line or line.startswith("#") or "=" not in line

    @staticmethod
    def _parse_env_line(line: str) -> tuple[str, str]:
        """
        Parse a single env line into key and value.

        Args:
            line: Line from .env file

        Returns:
            Tuple of (key, value)
        """
        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = raw_value.strip().strip("'").strip('"')
        return key, value
