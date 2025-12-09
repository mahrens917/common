"""Provider for health check URLs."""

from typing import Dict, List


class HealthUrlProvider:
    """Provides health check URLs for services."""

    def __init__(self):
        """Initialize health URL provider with service port mappings."""
        self.service_ports: Dict[str, List[int]] = {
            "kalshi": [8081],
            "deribit": [8082],
            "weather": [8083],
            "tracker": [8084],
            "monitor": [8085],
        }

    def get_health_urls(self, service_name: str) -> List[str]:
        """
        Get potential health check URLs for a service.

        Args:
            service_name: Name of the service

        Returns:
            List of URLs to try for health checks
        """
        # Standard health endpoint patterns
        base_urls = [
            f"http://localhost:8080/{service_name}/health",
            f"http://localhost:8080/health",
            f"http://localhost:8000/{service_name}/health",
            f"http://localhost:8000/health",
        ]

        # Service-specific ports (if known)
        if service_name in self.service_ports:
            for port in self.service_ports[service_name]:
                base_urls.extend(
                    [
                        f"http://localhost:{port}/health",
                        f"http://localhost:{port}/{service_name}/health",
                    ]
                )

        return base_urls
