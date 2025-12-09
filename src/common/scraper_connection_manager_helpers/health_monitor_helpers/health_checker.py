"""Health check coordinator."""

import asyncio
from typing import Dict


class HealthChecker:
    """Coordinates health checks across multiple URLs."""

    @staticmethod
    def calculate_threshold(total_urls: int) -> int:
        """Calculate minimum healthy URLs needed (50%)."""
        return max(1, total_urls // 2)

    @staticmethod
    def evaluate_health(healthy_count: int, total_urls: int) -> bool:
        """Determine if system is healthy based on URL results."""
        threshold = HealthChecker.calculate_threshold(total_urls)
        return healthy_count >= threshold

    @staticmethod
    def update_success_metrics(
        health_status: Dict,
        loop: asyncio.AbstractEventLoop,
        healthy_count: int,
        total_urls: int,
        logger,
    ) -> None:
        """Update metrics on successful health check."""
        health_status["last_successful_scrape_time"] = loop.time()
        health_status["consecutive_scrape_failures"] = 0
        logger.debug(f"Health check passed: {healthy_count}/{total_urls} URLs healthy")

    @staticmethod
    def update_failure_metrics(
        health_status: Dict, healthy_count: int, total_urls: int, threshold: int, logger
    ) -> None:
        """Update metrics on failed health check."""
        health_status["consecutive_scrape_failures"] += 1
        logger.warning(
            f"Health check failed: only {healthy_count}/{total_urls} URLs healthy (need {threshold})"
        )
