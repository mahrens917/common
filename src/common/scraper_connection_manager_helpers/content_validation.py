"""Content validation for scraper connection manager."""

import asyncio
import logging
from typing import Callable, List, Optional

VALIDATION_EXCEPTIONS = (
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
    AssertionError,
)


class ContentValidationHandler:
    """Handles content validation for scraped data."""

    def __init__(self, service_name: str, content_validators: Optional[List[Callable]] = None):
        """
        Initialize content validator.

        Args:
            service_name: Service identifier
            content_validators: List of validation functions
        """
        self.service_name = service_name
        self.content_validators = list() if content_validators is None else content_validators
        self.last_content_validation_time = 0.0
        self.consecutive_validation_failures = 0
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def validate_content(self, content: str, url: str) -> bool:
        """
        Validate scraped content using configured validators.

        Args:
            content: Scraped content to validate
            url: URL the content was scraped from

        Returns:
            True if all validators pass, False if any validator fails
        """
        try:
            for validator in self.content_validators:
                if asyncio.iscoroutinefunction(validator):
                    is_valid = await validator(content, url)
                else:
                    is_valid = validator(content, url)

                if not is_valid:
                    self.consecutive_validation_failures += 1
                    self.logger.warning(f"Content validation failed: {url}")
                    return False

            loop = asyncio.get_running_loop()
            self.last_content_validation_time = loop.time()
            self.consecutive_validation_failures = 0

        except VALIDATION_EXCEPTIONS:  # policy_guard: allow-silent-handler
            self.consecutive_validation_failures += 1
            self.logger.exception(f"Content validation error: ")
            return False
        else:
            return True

    def has_validators(self) -> bool:
        """
        Check if any validators are configured.

        Returns:
            True if validators exist
        """
        return len(self.content_validators) > 0

    def get_validator_count(self) -> int:
        """
        Get number of configured validators.

        Returns:
            Number of validators
        """
        return len(self.content_validators)

    def get_validation_metrics(self) -> dict:
        """
        Get validation metrics.

        Returns:
            Dictionary with validation metrics
        """
        return {
            "last_content_validation_time": self.last_content_validation_time,
            "consecutive_validation_failures": self.consecutive_validation_failures,
            "validator_count": len(self.content_validators),
        }
