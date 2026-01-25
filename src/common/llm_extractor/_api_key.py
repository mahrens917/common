"""API key loading utility for LLM extractor."""

from __future__ import annotations

from pathlib import Path

_ENV_FILE_PATH = Path.home() / ".env"


def load_api_key_from_env_file(key_name: str) -> str | None:
    """Load an API key from ~/.env file.

    Args:
        key_name: The environment variable name (e.g., 'LLM_PROVIDER_KEY').

    Returns:
        The API key value, or None if not found.
    """
    if not _ENV_FILE_PATH.exists():
        return None
    for line in _ENV_FILE_PATH.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{key_name}="):
            value = line.split("=", 1)[1].strip()
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            return value
    return None


__all__ = ["load_api_key_from_env_file"]
