"""Adapter for error classifier delegation methods."""

from ..reconnection_error_patterns import ReconnectionErrorClassifier


class ErrorClassifierAdapter:
    """Adapts error classifier for alert suppression manager.

    Wraps a ReconnectionErrorClassifier to provide a consistent interface
    for error classification.
    """

    def __init__(self, error_classifier: ReconnectionErrorClassifier):
        """
        Initialize error classifier adapter.

        Args:
            error_classifier: Error classifier instance
        """
        self.error_classifier = error_classifier

    def classify_error_type(self, service_name: str, error_message: str) -> str:
        """
        Classify the type of error for detailed analysis.

        Args:
            service_name: Name of the service
            error_message: Error message to classify

        Returns:
            Error type classification
        """
        return self.error_classifier.classify_error_type(service_name, error_message)

    def is_reconnection_error(self, service_name: str, error_message: str) -> bool:
        """
        Check if an error message indicates a reconnection event.

        Args:
            service_name: Name of the service
            error_message: Error message to check

        Returns:
            True if error indicates reconnection, False otherwise
        """
        return self.error_classifier.is_reconnection_error(service_name, error_message)
