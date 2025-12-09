"""Validation logic for Redis persistence configuration."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)


class ValidationManager:
    """Manages validation of Redis persistence configuration."""

    def validate_status(self, status: Dict[str, Any]) -> Tuple[bool, str]:
        if "error" in status:
            return False, f"Error checking persistence: {status['error']}"

        issues = []
        if not status["aof_enabled"]:
            issues.append("AOF persistence is disabled")
        if not status["rdb_enabled"]:
            issues.append("RDB persistence is disabled")

        data_dir_valid, data_dir_message = self._validate_data_directory(status["data_directory"])
        if not data_dir_valid:
            issues.append(data_dir_message)

        if issues:
            return False, f"Persistence validation failed: {'; '.join(issues)}"
        return True, "Redis persistence is properly configured for trades data protection"

    def _validate_data_directory(self, data_directory: str) -> Tuple[bool, str]:
        data_dir = Path(data_directory)
        if not data_dir.exists():
            return False, f"Data directory does not exist: {data_dir}"
        if not data_dir.is_dir():
            return False, f"Data directory is not a directory: {data_dir}"

        if not os.access(data_dir, os.W_OK):
            if str(data_dir).startswith(("/var/", "/usr/", "/opt/")):
                logger.warning(
                    "Data directory %s not writable by current user, but Redis process may have access",
                    data_dir,
                )
                return True, "Directory exists (system directory)"
            return False, f"Data directory is not writable: {data_dir}"
        return True, "Directory valid"

    @staticmethod
    def check_aof_enabled(status: Dict[str, Any]) -> bool:
        """Check if AOF persistence is enabled."""
        return bool(status.get("aof_enabled"))

    @staticmethod
    def check_rdb_enabled(status: Dict[str, Any]) -> bool:
        """Check if RDB persistence is enabled."""
        return bool(status.get("rdb_enabled"))

    @staticmethod
    def is_properly_configured(status: Dict[str, Any]) -> bool:
        """Check if persistence is properly configured."""
        return bool(status.get("persistence_properly_configured"))


def check_aof_enabled(status: Dict[str, Any]) -> bool:
    """Expose ValidationManager.check_aof_enabled as module helper."""
    return ValidationManager.check_aof_enabled(status)


def check_rdb_enabled(status: Dict[str, Any]) -> bool:
    """Expose ValidationManager.check_rdb_enabled as module helper."""
    return ValidationManager.check_rdb_enabled(status)


def is_properly_configured(status: Dict[str, Any]) -> bool:
    """Expose ValidationManager.is_properly_configured as module helper."""
    return ValidationManager.is_properly_configured(status)
