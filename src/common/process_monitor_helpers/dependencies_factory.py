from __future__ import annotations

"""Dependency factory for ProcessMonitor."""


import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ..process_monitor_helpers import (
        BackgroundScanWorker,
        CacheOperations,
        LifecycleManager,
        ProcessLookup,
        ProcessScanner,
        ScanCoordinator,
    )
    from ..process_monitor_helpers.public_api import PublicAPI


@dataclass
class ProcessMonitorDependencies:
    """Container for all ProcessMonitor dependencies."""

    scanner: "ProcessScanner"
    cache_ops: "CacheOperations"
    process_lookup: "ProcessLookup"
    scan_coordinator: "ScanCoordinator"
    background_worker: "BackgroundScanWorker"
    lifecycle: "LifecycleManager"
    api: "PublicAPI"


class ProcessMonitorDependenciesFactory:
    """Factory for creating ProcessMonitor dependencies."""

    @staticmethod
    def create(
        cache_ttl_seconds: int,
        scan_interval_seconds: int,
        perform_incremental_scan: Callable,
        shutdown_event: asyncio.Event,
    ) -> ProcessMonitorDependencies:
        """Create all dependencies for ProcessMonitor."""
        from ..process_monitor_helpers import (
            BackgroundScanWorker,
            CacheOperations,
            LifecycleManager,
            ProcessLookup,
            ProcessScanner,
            ScanCoordinator,
        )
        from ..process_monitor_helpers.public_api import PublicAPI
        from ..process_monitor_helpers.service_patterns import get_default_service_patterns

        scanner = ProcessScanner(get_default_service_patterns())
        cache_ops = CacheOperations(cache_ttl_seconds)
        process_lookup = ProcessLookup()

        scan_coordinator = ScanCoordinator(scanner)
        background_worker = BackgroundScanWorker(
            scan_interval_seconds, perform_incremental_scan, shutdown_event
        )
        lifecycle = LifecycleManager(background_worker, shutdown_event)
        api = PublicAPI(cache_ops, process_lookup, cache_ttl_seconds)

        return ProcessMonitorDependencies(
            scanner=scanner,
            cache_ops=cache_ops,
            process_lookup=process_lookup,
            scan_coordinator=scan_coordinator,
            background_worker=background_worker,
            lifecycle=lifecycle,
            api=api,
        )
