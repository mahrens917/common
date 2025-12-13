"""
System dependency validator for fail-fast startup validation.

This module validates that all required system dependencies are available
before starting services, providing clear error messages with installation
instructions when dependencies are missing.

Follows fail-fast principles: detect problems early, fail immediately with
clear instructions, no silent failures or long timeouts.
"""

import logging
import shutil
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULT_WEATHER_SOURCE = "ldm"

from src.weather.settings import get_weather_settings


class DependencyError(Exception):
    """Base exception for dependency validation errors"""

    pass


class LDMNotInstalledError(DependencyError):
    """Raised when LDM system is not properly installed"""

    pass


class DependencyValidator:
    """Validates system dependencies before service startup"""

    @staticmethod
    def validate_ldm_dependencies():
        """
        Validate LDM system is installed and pqstream utility is available.

        Raises:
            LDMNotInstalledError: If pqstream utility is not found in PATH
        """
        if not shutil.which("pqstream"):
            raise LDMNotInstalledError(
                "Weather service requires LDM (Local Data Manager)\n"
                "Missing: pqstream utility\n"
                "Install:\n"
                "  macOS: brew install ldm\n"
                "  Ubuntu: sudo apt-get install ldm\n"
                "  CentOS: yum install ldm\n"
                "  Source: https://www.unidata.ucar.edu/software/ldm/\n"
                "Verify: which pqstream\n"
                "Documentation: https://www.unidata.ucar.edu/software/ldm/ldm-current/basics/installation.html"
            )

        logger.info("✅ LDM dependency validated: pqstream utility found")

    @staticmethod
    def validate_service_dependencies(config: Any):
        """
        Validate all enabled services have required dependencies.

        Args:
            config: Monitor configuration object with services definitions

        Raises:
            DependencyError: If any required dependency is missing
        """
        logger.info("Validating system dependencies for enabled services...")

        # Check weather service dependencies
        if hasattr(config, "services") and "weather" in config.services:
            weather_config = config.services["weather"]
            if "enabled" in weather_config:
                enabled = bool(weather_config["enabled"])
            else:
                enabled = False
            if enabled:
                DependencyValidator._validate_weather_service_dependencies()

        logger.info("✅ All system dependencies validated successfully")

    @staticmethod
    def _validate_weather_service_dependencies():
        """Validate weather service specific dependencies"""
        weather_settings = get_weather_settings()
        metar_source = weather_settings.sources.metar_source
        if metar_source is None or metar_source == "":
            metar_source = DEFAULT_WEATHER_SOURCE

        asos_source = weather_settings.sources.asos_source
        if asos_source is None or asos_source == "":
            asos_source = DEFAULT_WEATHER_SOURCE

        logger.info(f"Weather service configuration: METAR={metar_source}, ASOS={asos_source}")

        if "ldm" in (metar_source, asos_source):
            logger.info("Weather service configured to use LDM, validating LDM dependencies...")
            DependencyValidator.validate_ldm_dependencies()
        else:
            logger.info("Weather service not using LDM, skipping LDM validation")

    @staticmethod
    def get_dependency_status() -> Dict[str, bool]:
        """
        Get status of all system dependencies.

        Returns:
            Dictionary mapping dependency names to their availability status
        """
        status = {}

        # Check LDM
        try:
            DependencyValidator.validate_ldm_dependencies()
            status["ldm"] = True
        except LDMNotInstalledError:  # policy_guard: allow-silent-handler
            status["ldm"] = False

        return status
