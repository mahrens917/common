"""Connection lifecycle management for scraper connection manager."""

import asyncio
import logging

import aiohttp


class ScraperConnectionLifecycle:
    """Manages connection lifecycle for scraper service."""

    def __init__(
        self,
        service_name: str,
        session_manager,
        health_monitor,
    ):
        """
        Initialize connection lifecycle manager.

        Args:
            service_name: Service identifier
            session_manager: Session management handler
            health_monitor: Health monitoring handler
        """
        self.service_name = service_name
        self.session_manager = session_manager
        self.health_monitor = health_monitor
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def establish_connection(self) -> bool:
        """
        Establish scraper connection.

        Returns:
            True if connection established successfully

        Raises:
            ConnectionError: For connection failures
            TimeoutError: For timeout
        """
        try:
            self.logger.info(f"Establishing scraper session for {self.service_name}")

            await self.session_manager.create_session()

            health_result = await self.health_monitor.check_health()

            if not health_result.healthy:
                self.logger.error(f"Initial health check failed for {self.service_name}")
                await self.cleanup_connection()
                error = ConnectionError(f"Scraper health check failed for {self.service_name} during initialization")
                setattr(error, "_already_cleaned", True)
                raise error

            self.logger.info(f"Scraper connection established for {self.service_name}")

        except asyncio.TimeoutError as exc:
            self.logger.exception(f"Timeout establishing scraper connection: ")
            await self.cleanup_connection()
            raise TimeoutError(f"Scraper connection establishment timed out for {self.service_name}") from exc

        except aiohttp.ClientError as exc:
            self.logger.exception(f"Client error establishing scraper connection: ")
            await self.cleanup_connection()
            raise ConnectionError(f"Scraper session creation failed for {self.service_name}") from exc

        except (OSError, RuntimeError, ValueError) as exc:
            if getattr(exc, "_already_cleaned", False):
                raise
            self.logger.exception(f"Failed to establish scraper connection: ")
            await self.cleanup_connection()
            raise ConnectionError(f"Scraper connection establishment failed for {self.service_name}") from exc
        else:
            return True

    async def cleanup_connection(self) -> None:
        """Clean up connection resources."""
        await self.session_manager.close_session()
        self.health_monitor.clear_health_status()
        self.logger.info(f"Connection cleanup completed for {self.service_name}")
