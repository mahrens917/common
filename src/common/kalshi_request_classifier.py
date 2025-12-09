"""
Kalshi API Request Classification - Classifies requests as READ or WRITE operations

Provides logic to classify Kalshi API requests based on HTTP method and endpoint
to determine appropriate rate limiting bucket (READ vs WRITE operations).
"""

import logging
from typing import Set

from .kalshi_rate_limiter import RequestType

logger = logging.getLogger(__name__)

# Kalshi API endpoints classified as READ operations (30/sec limit)
# Based on Kalshi API documentation and issue #73 specifications
READ_ENDPOINTS: Set[str] = {
    "/trade-api/v2/markets",
    "/trade-api/v2/series",
    "/trade-api/v2/events",
    "/portfolio/balance",
    "/portfolio/positions",
    # GET order status is a read operation
    "/portfolio/orders",  # When used with GET method for order status
}

# Kalshi API endpoints classified as WRITE operations (30/sec limit)
# Based on Kalshi API documentation and issue #73 specifications
WRITE_ENDPOINTS: Set[str] = {
    "/portfolio/orders",  # When used with POST method to create orders
    # Order cancellation endpoints follow pattern /portfolio/orders/{order_id}/cancel
    # These are handled by pattern matching in classify_request()
}


# Constants
_CONST_3 = 3


def classify_request(method: str, path: str) -> RequestType:
    """
    Classify Kalshi API request as READ or WRITE operation.

    Classification rules based on Kalshi API documentation:
    1. GET requests are always READ operations
    2. POST/PUT/DELETE/PATCH requests are WRITE operations
    3. Specific endpoint patterns override general rules
    4. Unknown methods default to WRITE (more restrictive) for safety

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH, etc.)
        path: API endpoint path (e.g., '/trade-api/v2/markets')

    Returns:
        RequestType.READ or RequestType.WRITE

    Examples:
        >>> classify_request('GET', '/trade-api/v2/markets')
        RequestType.READ
        >>> classify_request('POST', '/portfolio/orders')
        RequestType.WRITE
        >>> classify_request('GET', '/portfolio/orders/12345')
        RequestType.READ
        >>> classify_request('POST', '/portfolio/orders/12345/cancel')
        RequestType.WRITE
    """
    method_upper = method.upper()

    # GET requests are always reads
    if method_upper == "GET":
        logger.debug(f"[RequestClassifier] Classified GET {path} as READ")
        return RequestType.READ

    # POST/PUT/DELETE/PATCH are writes
    if method_upper in ["POST", "PUT", "DELETE", "PATCH"]:
        logger.debug(f"[RequestClassifier] Classified {method_upper} {path} as WRITE")
        return RequestType.WRITE

    # For unknown methods, default to WRITE for safety (more restrictive limit)
    logger.warning(
        f"[RequestClassifier] Unknown method {method} for path {path}, "
        f"defaulting to WRITE classification for safety"
    )
    return RequestType.WRITE


def is_order_status_request(method: str, path: str) -> bool:
    """
    Check if request is for getting order status (READ operation).

    Order status requests follow the pattern:
    - GET /portfolio/orders/{order_id}

    Args:
        method: HTTP method
        path: API endpoint path

    Returns:
        True if this is an order status request (READ), False otherwise
    """
    if method.upper() != "GET":
        return False

    # Check for order status pattern: /portfolio/orders/{order_id}
    if path.startswith("/portfolio/orders/") and path.count("/") == _CONST_3:
        # Extract order_id part
        order_id_part = path.split("/")[-1]
        # Order IDs should not contain 'cancel' or other action words
        if "cancel" not in order_id_part.lower():
            return True

    return False


def is_order_cancel_request(method: str, path: str) -> bool:
    """
    Check if request is for cancelling an order (write operation).

    Order cancellation requests follow the pattern:
    - POST /portfolio/orders/{order_id}/cancel

    Args:
        method: HTTP method
        path: API endpoint path

    Returns:
        True if this is an order cancellation request (write), False otherwise
    """
    if method.upper() != "POST":
        return False

    # Check for order cancellation pattern: /portfolio/orders/{order_id}/cancel
    return path.startswith("/portfolio/orders/") and path.endswith("/cancel")


def get_endpoint_classification_info(path: str) -> dict:
    """
    Get detailed classification information for an endpoint.

    Useful for debugging and monitoring to understand how requests
    are being classified by the rate limiter.

    Args:
        path: API endpoint path

    Returns:
        Dictionary with classification details
    """
    is_read_endpoint = path in READ_ENDPOINTS
    # Endpoints may appear in both read and write sets when classification depends on method.
    # Only treat it as a known write endpoint if it is exclusive to the write set.
    is_write_endpoint = path in WRITE_ENDPOINTS and path not in READ_ENDPOINTS

    if is_read_endpoint or is_write_endpoint:
        classification_method = "endpoint_list"
    else:
        classification_method = "http_method"

    return {
        "path": path,
        "is_known_read_endpoint": is_read_endpoint,
        "is_known_write_endpoint": is_write_endpoint,
        "classification_method": classification_method,
    }
