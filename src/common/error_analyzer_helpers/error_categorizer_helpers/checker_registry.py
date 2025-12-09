"""Registry for error category checkers."""

from ..data_classes import ErrorCategory


class CheckerRegistry:
    """Maintains ordered list of category checkers by specificity."""

    # Category checkers ordered by specificity (most specific first)
    CATEGORY_CHECKERS = [
        (ErrorCategory.WEBSOCKET, "_is_websocket_error"),
        (ErrorCategory.API, "_is_api_error"),
        (ErrorCategory.DEPENDENCY, "_is_dependency_error"),
        (ErrorCategory.NETWORK, "_is_network_error"),
        (ErrorCategory.AUTHENTICATION, "_is_authentication_error"),
        (ErrorCategory.DATA, "_is_data_error"),
        (ErrorCategory.CONFIGURATION, "_is_configuration_error"),
        (ErrorCategory.RESOURCE, "_is_resource_error"),
    ]
