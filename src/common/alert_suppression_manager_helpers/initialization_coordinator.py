"""Initialization coordinator for AlertSuppressionManager."""

import logging
from typing import Dict

from .config_loader import build_suppression_rule_from_config, load_suppression_config

logger = logging.getLogger(__name__)


class InitializationCoordinator:
    """Coordinates AlertSuppressionManager initialization."""

    @staticmethod
    def initialize_from_config(config_path: str, suppression_rule=None) -> tuple:
        """
        Initialize suppression rule and service type mapping from config.

        Returns:
            Tuple of (suppression_rule, service_type_mapping)
        """
        if suppression_rule is None:
            config = load_suppression_config(config_path)
            suppression_rule = build_suppression_rule_from_config(config)
            service_type_mapping: Dict[str, str] = config["suppression_rules"]["service_type_mapping"]
        else:
            service_type_mapping = {}

        logger.debug(
            f"Alert suppression manager initialized (enabled: {suppression_rule.enabled}, "
            f"grace_period: {suppression_rule.grace_period_seconds}s, "
            f"suppressed_types: {[t.value for t in suppression_rule.suppressed_alert_types]})"
        )

        return suppression_rule, service_type_mapping

    @staticmethod
    def create_dependencies_if_needed(suppression_rule, provided_dependencies):
        """Create dependencies using factory if not all provided."""
        if not all(provided_dependencies):
            from .dependencies_factory import AlertSuppressionManagerDependenciesFactory  # gitleaks:allow

            # Factory invocation annotated to prevent gitleaks false positive
            return AlertSuppressionManagerDependenciesFactory.create(suppression_rule)  # gitleaks:allow
        return None
