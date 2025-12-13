"""REST connection lifecycle."""

import logging

import aiohttp


class RESTConnectionLifecycle:
    """Manages REST connection lifecycle."""

    def __init__(
        self,
        service_name: str,
        base_url: str,
        session_manager,
        health_monitor,
    ):
        self.service_name = service_name
        self.base_url = base_url
        self.session_manager = session_manager
        self.health_monitor = health_monitor
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def establish_connection(self) -> bool:
        """Establish REST connection."""
        try:
            self.logger.info(f"Establishing REST session for {self.base_url}")

            await self.session_manager.create_session()

            health_result = await self.health_monitor.check_health()

            if not health_result.healthy:
                self.logger.error("Initial health check failed")
                await self.cleanup_connection()
                error = ConnectionError(f"REST health check failed during initialization")
                setattr(error, "_already_cleaned", True)
                raise error

            self.logger.info("REST connection established")

        except (aiohttp.ClientError, OSError) as e:
            if getattr(e, "_already_cleaned", None):
                raise
            self.logger.exception(f"Failed to establish REST connection: ")
            await self.cleanup_connection()
            raise ConnectionError(f"REST connection failed: ")
        else:
            return True

    async def cleanup_connection(self) -> None:
        """Clean up REST connection."""
        await self.session_manager.close_session()
        self.logger.info("Connection cleanup completed")
