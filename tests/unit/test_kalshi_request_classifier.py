import logging

import pytest

from src.common import kalshi_request_classifier as classifier
from src.common.kalshi_rate_limiter import RequestType


@pytest.mark.parametrize(
    "method,path,expected",
    [
        ("GET", "/trade-api/v2/markets", RequestType.READ),
        ("GET", "/portfolio/orders", RequestType.READ),
        ("POST", "/portfolio/orders", RequestType.WRITE),
        ("PUT", "/portfolio/orders", RequestType.WRITE),
        ("DELETE", "/portfolio/orders/123/cancel", RequestType.WRITE),
    ],
)
def test_classify_request_http_methods(method: str, path: str, expected: RequestType) -> None:
    assert classifier.classify_request(method, path) is expected


def test_classify_request_unknown_method_defaults_to_write(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        result = classifier.classify_request("HEAD", "/trade-api/v2/markets")

    assert result is RequestType.WRITE
    assert "Unknown method" in caplog.messages[0]


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/portfolio/orders/12345", True),
        ("/portfolio/orders/12345/cancel", False),
        ("/portfolio/orders/123/extra/path", False),
        ("/portfolio/orders", False),
    ],
)
def test_is_order_status_request(path: str, expected: bool) -> None:
    assert classifier.is_order_status_request("GET", path) is expected


@pytest.mark.parametrize(
    "method,path,expected",
    [
        ("POST", "/portfolio/orders/12345/cancel", True),
        ("POST", "/portfolio/orders/12345", False),
        ("GET", "/portfolio/orders/12345/cancel", False),
    ],
)
def test_is_order_cancel_request(method: str, path: str, expected: bool) -> None:
    assert classifier.is_order_cancel_request(method, path) is expected


def test_get_endpoint_classification_info_known_endpoint() -> None:
    path = next(iter(classifier.READ_ENDPOINTS))
    info = classifier.get_endpoint_classification_info(path)

    assert info["path"] == path
    assert info["is_known_read_endpoint"] is True
    assert info["is_known_write_endpoint"] is False
    assert info["classification_method"] == "endpoint_list"


def test_get_endpoint_classification_info_unknown_endpoint() -> None:
    path = "/custom/endpoint"
    info = classifier.get_endpoint_classification_info(path)

    assert info["path"] == path
    assert info["is_known_read_endpoint"] is False
    assert info["is_known_write_endpoint"] is False
    assert info["classification_method"] == "http_method"
