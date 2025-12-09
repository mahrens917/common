"""
Dependency-aware error filtering for log monitoring.

This module provides filtering logic to suppress expected error messages
when service dependencies are known to be unavailable. This prevents
noise in error alerts when services are in expected degraded mode.

Key Features:
- Dependency status tracking via Redis
- Configurable error pattern matching
- Service-specific dependency mapping
- Fail-fast on unexpected errors
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from .dependency_aware_error_filter_helpers.pattern_matcher import PatternCompilationError
from .redis_utils import RedisOperationError, get_redis_connection

logger = logging.getLogger(__name__)


REDIS_ERRORS = (
    RedisError,
    RedisOperationError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)

if TYPE_CHECKING:
    from .dependency_aware_error_filter_helpers import DependencyErrorPattern


@dataclass
class ErrorSuppressionConfig:
    """Configuration for error suppression system"""

    enabled: bool = True
    dependency_error_patterns: Dict[str, List[str]] = field(default_factory=dict)
    redis_key_prefix: str = "dependency_status"


class _DependencyFilterContext(Protocol):
    config: ErrorSuppressionConfig
    redis: Optional[Redis]
    dependency_patterns: Dict[str, "DependencyErrorPattern"]

    async def get_service_dependencies(self, service_name: str) -> List[str]: ...


class DependencyAwareErrorFilterMixin:
    """Helper methods shared by the dependency-aware error filter."""

    async def should_suppress_error(
        self: _DependencyFilterContext, process_name: str, error_message: str
    ) -> bool:
        from .dependency_aware_error_filter_helpers import DependencyChecker, PatternMatcher

        if not self.config.enabled or self.redis is None:
            return False

        try:
            dependencies = await DependencyChecker.get_service_dependencies(
                self.redis, process_name
            )
            if not dependencies:
                return False

            for dependency_name in dependencies:
                unavailable = await DependencyChecker.is_dependency_unavailable(
                    self.redis, process_name, dependency_name, self.config.redis_key_prefix
                )
                if not unavailable:
                    continue
                if PatternMatcher.is_dependency_related_error(
                    error_message, dependency_name, self.dependency_patterns
                ):
                    logger.debug(
                        "Suppressing error for %s: dependency %s unavailable",
                        process_name,
                        dependency_name,
                    )
                    return True

            else:
                return False
        except REDIS_ERRORS:
            logger.exception("Error checking dependency status for %s", process_name)
            return False

    async def update_service_dependencies(
        self: _DependencyFilterContext, service_name: str, dependencies: List[str]
    ) -> None:
        from .dependency_aware_error_filter_helpers import StatusUpdater

        if not self.redis:
            logger.warning("No Redis connection available for updating dependencies")
            return
        await StatusUpdater.update_service_dependencies(self.redis, service_name, dependencies)

    async def update_dependency_status(
        self: _DependencyFilterContext, service_name: str, dependency_name: str, status: str
    ) -> None:
        from .dependency_aware_error_filter_helpers import StatusUpdater

        if not self.redis:
            logger.warning("No Redis connection available for updating dependency status")
            return
        await StatusUpdater.update_dependency_status(
            self.redis, service_name, dependency_name, status, self.config.redis_key_prefix
        )

    def get_dependency_patterns(self: _DependencyFilterContext) -> Dict[str, List[str]]:
        return {
            dep_name: pattern_config.error_patterns
            for dep_name, pattern_config in self.dependency_patterns.items()
        }

    async def get_service_dependencies(
        self: _DependencyFilterContext, service_name: str
    ) -> List[str]:
        from .dependency_aware_error_filter_helpers.dependency_checker import DependencyChecker

        if not self.redis:
            logger.warning("No Redis connection available for dependency lookup")
            return []
        return await DependencyChecker.get_service_dependencies(self.redis, service_name)

    async def _get_service_dependencies(
        self: _DependencyFilterContext, service_name: str
    ) -> List[str]:
        return await self.get_service_dependencies(service_name)

    async def _is_dependency_unavailable(
        self: _DependencyFilterContext, service_name: str, dependency_name: str
    ) -> bool:
        from .dependency_aware_error_filter_helpers.dependency_checker import DependencyChecker

        if not self.redis:
            logger.warning("No Redis connection available for dependency status check")
            return False
        return await DependencyChecker.is_dependency_unavailable(
            self.redis, service_name, dependency_name, self.config.redis_key_prefix
        )

    def _is_dependency_related_error(
        self: _DependencyFilterContext, error_message: str, dependency_name: str
    ) -> bool:
        from .dependency_aware_error_filter_helpers.pattern_matcher import PatternMatcher

        return PatternMatcher.is_dependency_related_error(
            error_message, dependency_name, self.dependency_patterns
        )


class DependencyAwareErrorFilter(DependencyAwareErrorFilterMixin):
    """Filters error log entries based on known dependency failures."""

    def __init__(self, config: object):
        from .dependency_aware_error_filter_helpers import DependencyErrorPattern

        if not isinstance(config, ErrorSuppressionConfig):
            raise TypeError("config must be ErrorSuppressionConfig instance")

        self.config: ErrorSuppressionConfig = config
        self.redis: Optional[Redis] = None
        self.dependency_patterns: Dict[str, DependencyErrorPattern] = {}
        for dep_name, patterns in config.dependency_error_patterns.items():
            if not patterns:
                continue
            try:
                pattern_config = DependencyErrorPattern(
                    dependency_name=dep_name, error_patterns=patterns
                )
            except PatternCompilationError as exc:
                logger.warning(str(exc))
                pattern_config = DependencyErrorPattern(
                    dependency_name=dep_name, error_patterns=[], compiled_patterns=[]
                )
            self.dependency_patterns[dep_name] = pattern_config
        logger.info(
            "Initialized dependency error filter with %s dependency patterns",
            len(self.dependency_patterns),
        )

    async def __aenter__(self):
        self.redis = await get_redis_connection()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.redis:
            await self.redis.aclose()
        if exc_type:
            logger.debug(
                "DependencyAwareErrorFilter closing due to %s: %s",
                exc_type.__name__,
                exc_val,
                exc_info=(exc_type, exc_val, exc_tb),
            )
