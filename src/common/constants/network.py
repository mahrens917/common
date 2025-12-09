"""Network and HTTP constants.

These constants define HTTP status codes and network-related values
used throughout the codebase for API interactions.
"""

# HTTP status codes
HTTP_OK = 200
HTTP_INTERNAL_SERVER_ERROR = 500

# WebSocket close codes
WEBSOCKET_ABNORMAL_CLOSURE = 1006

__all__ = [
    "HTTP_OK",
    "HTTP_INTERNAL_SERVER_ERROR",
    "WEBSOCKET_ABNORMAL_CLOSURE",
]
