"""Tests for root cause identifier module."""

from src.common.error_analyzer_helpers.data_classes import ErrorCategory
from src.common.error_analyzer_helpers.root_cause_identifier import RootCauseIdentifier


class TestRootCauseIdentifierIdentifyRootCause:
    """Tests for RootCauseIdentifier.identify_root_cause."""

    def test_identifies_unknown_category(self) -> None:
        """Returns unknown error message for unhandled category."""
        identifier = RootCauseIdentifier()
        error = Exception("test error")

        # Using a category that's not in the handlers
        result = identifier.identify_root_cause(error, "test message", ErrorCategory.UNKNOWN, None)

        assert "Unknown error" in result


class TestRootCauseIdentifierNetworkCause:
    """Tests for network error cause identification."""

    def test_identifies_timeout(self) -> None:
        """Identifies timeout errors."""
        identifier = RootCauseIdentifier()
        error = Exception("Connection timeout")

        result = identifier.identify_root_cause(
            error, "Connection timeout", ErrorCategory.NETWORK, None
        )

        assert "timeout" in result.lower()

    def test_identifies_connection_refused(self) -> None:
        """Identifies connection refused errors."""
        identifier = RootCauseIdentifier()
        error = Exception("Connection refused")

        result = identifier.identify_root_cause(
            error, "Connection refused", ErrorCategory.NETWORK, None
        )

        assert "Connection refused" in result

    def test_identifies_dns_error(self) -> None:
        """Identifies DNS errors."""
        identifier = RootCauseIdentifier()
        error = Exception("DNS lookup failed")

        result = identifier.identify_root_cause(
            error, "DNS lookup failed", ErrorCategory.NETWORK, None
        )

        assert "DNS" in result

    def test_identifies_name_resolution_error(self) -> None:
        """Identifies name resolution errors."""
        identifier = RootCauseIdentifier()
        error = Exception("Name resolution failed")

        result = identifier.identify_root_cause(
            error, "Name resolution failed", ErrorCategory.NETWORK, None
        )

        assert "DNS" in result

    def test_returns_generic_network_error(self) -> None:
        """Returns generic network error for unknown patterns."""
        identifier = RootCauseIdentifier()
        error = Exception("Network error")

        result = identifier.identify_root_cause(
            error, "Something went wrong", ErrorCategory.NETWORK, None
        )

        assert "Network connectivity" in result


class TestRootCauseIdentifierWebSocketCause:
    """Tests for WebSocket error cause identification."""

    def test_identifies_code_1006_from_message(self) -> None:
        """Identifies code 1006 from message."""
        identifier = RootCauseIdentifier()
        error = Exception("code 1006 abnormal closure")

        result = identifier.identify_root_cause(
            error, "code 1006 abnormal closure", ErrorCategory.WEBSOCKET, None
        )

        assert "1006" in result

    def test_identifies_code_1006_from_context(self) -> None:
        """Identifies code 1006 from context."""
        identifier = RootCauseIdentifier()
        error = Exception("connection closed")
        context = {"close_code": 1006}

        result = identifier.identify_root_cause(
            error, "connection closed", ErrorCategory.WEBSOCKET, context
        )

        assert "1006" in result

    def test_identifies_code_1000(self) -> None:
        """Identifies code 1000 normal closure."""
        identifier = RootCauseIdentifier()
        error = Exception("code 1000")

        result = identifier.identify_root_cause(error, "code 1000", ErrorCategory.WEBSOCKET, None)

        assert "1000" in result
        assert "normal" in result.lower()

    def test_identifies_code_1001(self) -> None:
        """Identifies code 1001 going away."""
        identifier = RootCauseIdentifier()
        error = Exception("code 1001")

        result = identifier.identify_root_cause(error, "code 1001", ErrorCategory.WEBSOCKET, None)

        assert "1001" in result
        assert "going away" in result.lower()

    def test_returns_generic_websocket_error(self) -> None:
        """Returns generic WebSocket error for unknown patterns."""
        identifier = RootCauseIdentifier()
        error = Exception("WebSocket error")

        result = identifier.identify_root_cause(
            error, "connection issue", ErrorCategory.WEBSOCKET, None
        )

        assert "WebSocket connection issue" in result


class TestRootCauseIdentifierAuthCause:
    """Tests for authentication error cause identification."""

    def test_identifies_401_error(self) -> None:
        """Identifies 401 unauthorized errors."""
        identifier = RootCauseIdentifier()
        error = Exception("401 Unauthorized")

        result = identifier.identify_root_cause(
            error, "401 Unauthorized", ErrorCategory.AUTHENTICATION, None
        )

        assert "Authentication failed" in result

    def test_identifies_unauthorized(self) -> None:
        """Identifies unauthorized errors."""
        identifier = RootCauseIdentifier()
        error = Exception("Unauthorized access")

        result = identifier.identify_root_cause(
            error, "Unauthorized access", ErrorCategory.AUTHENTICATION, None
        )

        assert "Authentication failed" in result

    def test_identifies_403_error(self) -> None:
        """Identifies 403 forbidden errors."""
        identifier = RootCauseIdentifier()
        error = Exception("403 Forbidden")

        result = identifier.identify_root_cause(
            error, "403 Forbidden", ErrorCategory.AUTHENTICATION, None
        )

        assert "Authorization failed" in result

    def test_identifies_forbidden(self) -> None:
        """Identifies forbidden errors."""
        identifier = RootCauseIdentifier()
        error = Exception("Access forbidden")

        result = identifier.identify_root_cause(
            error, "Access forbidden", ErrorCategory.AUTHENTICATION, None
        )

        assert "Authorization failed" in result

    def test_returns_generic_auth_error(self) -> None:
        """Returns generic auth error for unknown patterns."""
        identifier = RootCauseIdentifier()
        error = Exception("Auth error")

        result = identifier.identify_root_cause(
            error, "auth issue", ErrorCategory.AUTHENTICATION, None
        )

        assert "Authentication/authorization issue" in result


class TestRootCauseIdentifierAPICause:
    """Tests for API error cause identification."""

    def test_identifies_404_error(self) -> None:
        """Identifies 404 not found errors."""
        identifier = RootCauseIdentifier()
        error = Exception("404 Not Found")

        result = identifier.identify_root_cause(error, "404 Not Found", ErrorCategory.API, None)

        assert "not found" in result.lower()

    def test_identifies_500_error(self) -> None:
        """Identifies 500 internal server errors."""
        identifier = RootCauseIdentifier()
        error = Exception("500 Internal Server Error")

        result = identifier.identify_root_cause(
            error, "500 Internal Server Error", ErrorCategory.API, None
        )

        assert "internal error" in result.lower()

    def test_identifies_429_error(self) -> None:
        """Identifies 429 rate limit errors."""
        identifier = RootCauseIdentifier()
        error = Exception("429 Too Many Requests")

        result = identifier.identify_root_cause(
            error, "429 Too Many Requests", ErrorCategory.API, None
        )

        assert "Rate limit" in result

    def test_returns_generic_api_error(self) -> None:
        """Returns generic API error for unknown patterns."""
        identifier = RootCauseIdentifier()
        error = Exception("API error")

        result = identifier.identify_root_cause(error, "API issue", ErrorCategory.API, None)

        assert "API communication issue" in result


class TestRootCauseIdentifierDataCause:
    """Tests for data error cause identification."""

    def test_identifies_json_error(self) -> None:
        """Identifies JSON parsing errors."""
        identifier = RootCauseIdentifier()
        error = Exception("Invalid JSON")

        result = identifier.identify_root_cause(error, "Invalid JSON", ErrorCategory.DATA, None)

        assert "JSON parsing" in result

    def test_identifies_format_error(self) -> None:
        """Identifies data format errors."""
        identifier = RootCauseIdentifier()
        error = Exception("Invalid format")

        result = identifier.identify_root_cause(error, "Invalid format", ErrorCategory.DATA, None)

        assert "Data format" in result

    def test_returns_generic_data_error(self) -> None:
        """Returns generic data error for unknown patterns."""
        identifier = RootCauseIdentifier()
        error = Exception("Data error")

        result = identifier.identify_root_cause(error, "processing issue", ErrorCategory.DATA, None)

        assert "Data processing error" in result


class TestRootCauseIdentifierDependencyCause:
    """Tests for dependency error cause identification."""

    def test_identifies_redis_error(self) -> None:
        """Identifies Redis errors."""
        identifier = RootCauseIdentifier()
        error = Exception("Redis connection failed")

        result = identifier.identify_root_cause(
            error, "Redis connection failed", ErrorCategory.DEPENDENCY, None
        )

        assert "Redis" in result

    def test_identifies_database_error(self) -> None:
        """Identifies database errors."""
        identifier = RootCauseIdentifier()
        error = Exception("Database connection failed")

        result = identifier.identify_root_cause(
            error, "Database connection failed", ErrorCategory.DEPENDENCY, None
        )

        assert "Database" in result

    def test_returns_generic_dependency_error(self) -> None:
        """Returns generic dependency error for unknown patterns."""
        identifier = RootCauseIdentifier()
        error = Exception("Service error")

        result = identifier.identify_root_cause(
            error, "service issue", ErrorCategory.DEPENDENCY, None
        )

        assert "Service dependency unavailable" in result


class TestRootCauseIdentifierConfigCause:
    """Tests for configuration error cause identification."""

    def test_returns_config_error(self) -> None:
        """Returns configuration error message."""
        identifier = RootCauseIdentifier()
        error = Exception("Config error")

        result = identifier.identify_root_cause(
            error, "config issue", ErrorCategory.CONFIGURATION, None
        )

        assert "Configuration error" in result


class TestRootCauseIdentifierResourceCause:
    """Tests for resource error cause identification."""

    def test_returns_resource_error(self) -> None:
        """Returns resource constraint error message."""
        identifier = RootCauseIdentifier()
        error = Exception("Resource error")

        result = identifier.identify_root_cause(
            error, "resource issue", ErrorCategory.RESOURCE, None
        )

        assert "Resource constraint" in result
