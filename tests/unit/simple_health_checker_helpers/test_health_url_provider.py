import pytest

from src.common.simple_health_checker_helpers.health_url_provider import HealthUrlProvider


class TestHealthUrlProvider:
    def test_get_health_urls_unknown_service(self):
        provider = HealthUrlProvider()
        urls = provider.get_health_urls("unknown_service")

        expected_base_urls = [
            "http://localhost:8080/unknown_service/health",
            "http://localhost:8080/health",
            "http://localhost:8000/unknown_service/health",
            "http://localhost:8000/health",
        ]

        assert urls == expected_base_urls

    def test_get_health_urls_known_service(self):
        provider = HealthUrlProvider()
        urls = provider.get_health_urls("kalshi")

        expected_base_urls = [
            "http://localhost:8080/kalshi/health",
            "http://localhost:8080/health",
            "http://localhost:8000/kalshi/health",
            "http://localhost:8000/health",
        ]

        expected_service_urls = [
            "http://localhost:8081/health",
            "http://localhost:8081/kalshi/health",
        ]

        expected_urls = expected_base_urls + expected_service_urls

        assert urls == expected_urls
