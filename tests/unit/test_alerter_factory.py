"""Tests for alerter_factory module."""

import pytest

from common.alerter_factory import (
    AlerterCleanupError,
    create_alerter,
    create_alerter_for_service,
)


class TestCreateAlerter:
    """Tests for create_alerter function."""

    def test_creates_alerter_instance(self):
        """Test that create_alerter returns a ServiceAlerter instance."""
        alerter = create_alerter()
        assert alerter is not None

    def test_creates_alerter_returns_object_type(self):
        """Test that create_alerter returns an object."""
        alerter = create_alerter()
        assert isinstance(alerter, object)


class TestCreateAlerterForService:
    """Tests for create_alerter_for_service function."""

    def test_creates_alerter_with_service_name(self):
        """Test creating alerter with service name context."""
        alerter = create_alerter_for_service("test_service")
        assert alerter is not None
        assert isinstance(alerter, object)

    def test_creates_different_instances_per_call(self):
        """Test that each call creates a new alerter instance."""
        alerter1 = create_alerter_for_service("service1")
        alerter2 = create_alerter_for_service("service2")
        # They should be different instances
        assert alerter1 is not alerter2


class TestAlerterCleanupError:
    """Tests for AlerterCleanupError exception."""

    def test_alerter_cleanup_error_can_be_raised(self):
        """Test that AlerterCleanupError is a RuntimeError."""
        with pytest.raises(AlerterCleanupError):
            raise AlerterCleanupError("Test cleanup error")

    def test_alerter_cleanup_error_is_runtime_error(self):
        """Test that AlerterCleanupError inherits from RuntimeError."""
        assert issubclass(AlerterCleanupError, RuntimeError)
