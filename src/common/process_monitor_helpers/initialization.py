"""Initialization logic for ProcessMonitor."""

import logging

logger = logging.getLogger(__name__)


class Initialization:
    """Handles process monitor initialization."""

    @staticmethod
    async def perform_initial_scan(scan_coordinator, process_cache, service_cache, redis_processes):
        """
        Perform initial scan during monitor initialization.

        Args:
            scan_coordinator: Scan coordinator to use
            process_cache: Process cache to populate
            service_cache: Service cache to populate
            redis_processes: Redis process list to populate

        Returns:
            Tuple of (process_cache, service_cache, redis_processes, timestamp)
        """
        logger.info("Initializing process monitor with initial scan...")
        result = await scan_coordinator.perform_full_scan(
            process_cache, service_cache, redis_processes
        )
        process_cache, service_cache, redis_processes, timestamp = result
        logger.info(f"Process monitor initialized with {len(process_cache)} cached processes")
        return process_cache, service_cache, redis_processes, timestamp
