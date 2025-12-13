"""Pattern compilation for reconnection error detection."""

import re
from typing import Dict, List

from .service_type_manager import ServiceType

# Reconnection error patterns by service type
RECONNECTION_ERROR_PATTERNS: Dict[ServiceType, List[str]] = {
    ServiceType.WEBSOCKET: [
        r"no close frame received or sent",
        r"connection lost",
        r"websocket.*disconnect.*",
        r"connection.*reset.*by.*peer",
        r"websocket.*connection.*closed",
        r"connection.*unexpectedly.*closed",
        r"websocket.*error.*1006",
        r"connection.*timeout",
        r"ping.*timeout",
        r"pong.*timeout",
        r"heartbeat.*failed",
        r"keep.*alive.*failed",
    ],
    ServiceType.REST: [
        r"connection.*timeout",
        r"http.*connection.*failed",
        r"request.*timeout",
        r"connection.*reset.*by.*peer",
        r"connection.*refused",
        r"network.*unreachable",
        r"temporary.*failure.*in.*name.*resolution",
        r"ssl.*handshake.*failed",
        r"certificate.*verify.*failed",
        r"read.*timeout",
        r"connect.*timeout",
        r"connection.*pool.*exhausted",
        r"timeout.*fetching.*data",
        r"timeout.*error",
        r"asyncio\.timeouterror",
    ],
    ServiceType.DATABASE: [
        r"connection.*lost",
        r"database.*disconnect",
        r"connection.*timeout",
        r"server.*has.*gone.*away",
        r"connection.*reset",
        r"database.*connection.*failed",
        r"connection.*pool.*exhausted",
        r"connection.*refused",
        r"authentication.*failed",
        r"ssl.*connection.*error",
    ],
    ServiceType.SCRAPER: [
        r"connection.*timeout",
        r"http.*connection.*failed",
        r"request.*timeout",
        r"connection.*reset.*by.*peer",
        r"connection.*refused",
        r"network.*unreachable",
        r"temporary.*failure.*in.*name.*resolution",
        r"ssl.*handshake.*failed",
        r"certificate.*verify.*failed",
        r"read.*timeout",
        r"connect.*timeout",
        r"rate.*limit.*exceeded",
        r"too.*many.*requests",
        r"service.*unavailable",
        r"bad.*gateway",
        r"gateway.*timeout",
        r"timeout.*fetching.*data",
        r"timeout.*error",
        r"asyncio\.timeouterror",
    ],
}


class PatternCompiler:
    """Compiles and manages regex patterns for error matching."""

    def __init__(self):
        """Initialize pattern compiler with compiled regex patterns."""
        self.compiled_patterns: Dict[ServiceType, List[re.Pattern]] = {}
        self._compile_all_patterns()

    def _compile_all_patterns(self) -> None:
        """Compile all regex patterns for performance."""
        for service_type, patterns in RECONNECTION_ERROR_PATTERNS.items():
            self.compiled_patterns[service_type] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    def get_compiled_patterns(self, service_type: ServiceType) -> List[re.Pattern]:
        """
        Get compiled patterns for a service type.

        Args:
            service_type: Type of service

        Returns:
            List of compiled regex patterns
        """
        patterns = self.compiled_patterns.get(service_type)
        if patterns is None:
            return list()
        return patterns

    def get_raw_patterns(self, service_type: ServiceType) -> List[str]:
        """
        Get raw pattern strings for a service type.

        Args:
            service_type: Type of service

        Returns:
            List of regex pattern strings
        """
        patterns = RECONNECTION_ERROR_PATTERNS.get(service_type)
        if patterns is None:
            return list()
        return patterns

    def recompile_patterns(self, service_type: ServiceType) -> None:
        """
        Recompile patterns for a service type.

        Args:
            service_type: Type of service to recompile
        """
        patterns = RECONNECTION_ERROR_PATTERNS.get(service_type)
        if patterns is None:
            patterns = []
        self.compiled_patterns[service_type] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
