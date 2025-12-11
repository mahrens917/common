"""Tests for alert_suppression_manager module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.alert_suppression_manager import (
    AlertSuppressionManager,
    _build_components,
    _load_rule_and_mapping,
    _log_configuration,
    _SuppressionComponents,
    get_alert_suppression_manager,
)
from common.alert_suppression_manager_helpers.alert_evaluator import SuppressionRule
from common.alert_suppression_manager_helpers.suppression_tracker import (
    AlertType,
    SuppressionDecision,
)

DEFAULT_SUPPRESSION_DURATION_SECONDS = 300


class TestLoadRuleAndMapping:
    """Tests for _load_rule_and_mapping function."""

    def test_returns_rule_and_empty_mapping_when_rule_provided(self) -> None:
        """Returns provided rule and empty mapping."""
        rule = MagicMock(spec=SuppressionRule)

        result_rule, mapping = _load_rule_and_mapping(rule, "config/test.json")

        assert result_rule is rule
        assert mapping == {}

    def test_loads_config_when_no_rule_provided(self) -> None:
        """Loads config from path when no rule provided."""
        mock_config = {
            "suppression_rules": {
                "service_type_mapping": {"service1": "type1"},
            }
        }
        mock_rule = MagicMock(spec=SuppressionRule)

        with patch(
            "common.alert_suppression_manager.load_suppression_config",
            return_value=mock_config,
        ) as mock_load:
            with patch(
                "common.alert_suppression_manager.build_suppression_rule_from_config",
                return_value=mock_rule,
            ):
                result_rule, mapping = _load_rule_and_mapping(None, "config/test.json")

        mock_load.assert_called_once_with("config/test.json")
        assert result_rule is mock_rule
        assert mapping == {"service1": "type1"}


class TestBuildComponents:
    """Tests for _build_components function."""

    def test_builds_all_components(self) -> None:
        """Builds all required components."""
        rule = MagicMock(spec=SuppressionRule)

        components = _build_components(rule)

        assert isinstance(components, _SuppressionComponents)
        assert components.dependency_init is not None
        assert components.tracker is not None
        assert components.evaluator is not None
        assert components.time_window_manager is not None
        assert components.context_builder is not None
        assert components.decision_coordinator is not None
        assert components.state_manager is not None
        assert components.error_adapter is not None

    def test_creates_tracker_with_max_history(self) -> None:
        """Creates tracker with max_history_entries=1000."""
        rule = MagicMock(spec=SuppressionRule)

        components = _build_components(rule)

        assert components.tracker.max_history_entries == 1000


class TestLogConfiguration:
    """Tests for _log_configuration function."""

    def test_logs_debug_message(self) -> None:
        """Logs debug message with configuration details."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = [AlertType.ERROR_LOG, AlertType.HEALTH_CHECK]

        with patch("common.alert_suppression_manager.logger") as mock_logger:
            _log_configuration(rule)

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert "enabled: %s" in call_args[0][0]
        assert call_args[0][1] is True
        assert call_args[0][2] == 30


class TestAlertSuppressionManager:
    """Tests for AlertSuppressionManager class."""

    def test_init_with_provided_rule(self) -> None:
        """Initializes with provided suppression rule."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = []

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        assert manager.suppression_rule is rule
        assert manager.service_type_mapping == {}

    def test_init_loads_config_when_no_rule(self) -> None:
        """Loads config from path when no rule provided."""
        mock_config = {
            "suppression_rules": {
                "service_type_mapping": {"kalshi": "exchange"},
            }
        }
        mock_rule = MagicMock(spec=SuppressionRule)
        mock_rule.enabled = False
        mock_rule.grace_period_seconds = 60
        mock_rule.suppressed_alert_types = []

        with patch(
            "common.alert_suppression_manager.load_suppression_config",
            return_value=mock_config,
        ):
            with patch(
                "common.alert_suppression_manager.build_suppression_rule_from_config",
                return_value=mock_rule,
            ):
                with patch("common.alert_suppression_manager.logger"):
                    manager = AlertSuppressionManager(config_path="config/test.json")

        assert manager.suppression_rule is mock_rule
        assert manager.service_type_mapping == {"kalshi": "exchange"}

    def test_init_sets_all_component_attributes(self) -> None:
        """Sets all component attributes on instance."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = []

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        assert hasattr(manager, "dependency_init")
        assert hasattr(manager, "tracker")
        assert hasattr(manager, "evaluator")
        assert hasattr(manager, "time_window_manager")
        assert hasattr(manager, "context_builder")
        assert hasattr(manager, "decision_coordinator")
        assert hasattr(manager, "state_manager")
        assert hasattr(manager, "error_adapter")


class TestAlertSuppressionManagerInitialize:
    """Tests for AlertSuppressionManager.initialize method."""

    @pytest.mark.asyncio
    async def test_initialize_calls_dependency_init(self) -> None:
        """Calls dependency_init.initialize."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = []

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        manager.dependency_init = AsyncMock()
        manager.dependency_init.initialize = AsyncMock()
        manager.dependency_init.error_classifier = None

        await manager.initialize()

        manager.dependency_init.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_updates_error_adapter_when_classifier_available(self) -> None:
        """Updates error_adapter when error_classifier is available."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = []

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        mock_classifier = MagicMock()
        manager.dependency_init = AsyncMock()
        manager.dependency_init.initialize = AsyncMock()
        manager.dependency_init.error_classifier = mock_classifier

        with patch("common.alert_suppression_manager_helpers.error_classifier_adapter.ErrorClassifierAdapter"):
            await manager.initialize()

        assert manager.error_adapter is not None


class TestAlertSuppressionManagerResolveServiceType:
    """Tests for AlertSuppressionManager._resolve_service_type method."""

    def test_returns_mapped_type(self) -> None:
        """Returns mapped service type."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = []

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        manager.service_type_mapping = {"kalshi": "exchange", "weather": "data_source"}

        result = manager._resolve_service_type("kalshi")

        assert result == "exchange"

    def test_raises_key_error_for_unknown_service(self) -> None:
        """Raises KeyError for unknown service name."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = []

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        manager.service_type_mapping = {"kalshi": "exchange"}

        with pytest.raises(KeyError) as exc_info:
            manager._resolve_service_type("unknown_service")

        assert "unknown_service" in str(exc_info.value)
        assert "monitor_config.json" in str(exc_info.value)


class TestAlertSuppressionManagerShouldSuppressAlert:
    """Tests for AlertSuppressionManager.should_suppress_alert method."""

    @pytest.mark.asyncio
    async def test_should_suppress_alert_returns_decision(self) -> None:
        """Returns suppression decision from coordinator."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = []

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        manager.service_type_mapping = {"kalshi": "exchange"}

        mock_decision = MagicMock(spec=SuppressionDecision)
        manager.dependency_init = MagicMock()
        manager.dependency_init.require_dependencies = MagicMock(return_value=(MagicMock(), MagicMock()))
        manager.decision_coordinator = AsyncMock()
        manager.decision_coordinator.make_decision = AsyncMock(return_value=mock_decision)
        manager.initialize = AsyncMock()

        result = await manager.should_suppress_alert("kalshi", AlertType.ERROR_LOG)

        assert result is mock_decision


class TestAlertSuppressionManagerGetSuppressionReason:
    """Tests for AlertSuppressionManager.get_suppression_reason method."""

    @pytest.mark.asyncio
    async def test_returns_reason_when_suppressed(self) -> None:
        """Returns reason when alert is suppressed."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = []

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        mock_decision = MagicMock()
        mock_decision.should_suppress = True
        mock_decision.reason = "Test suppression reason"
        manager.should_suppress_alert = AsyncMock(return_value=mock_decision)

        result = await manager.get_suppression_reason("kalshi", AlertType.ERROR_LOG)

        assert result == "Test suppression reason"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_suppressed(self) -> None:
        """Returns None when alert is not suppressed."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = []

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        mock_decision = MagicMock()
        mock_decision.should_suppress = False
        mock_decision.reason = "Some reason"
        manager.should_suppress_alert = AsyncMock(return_value=mock_decision)

        result = await manager.get_suppression_reason("kalshi", AlertType.ERROR_LOG)

        assert result is None


class TestAlertSuppressionManagerClassifyErrorType:
    """Tests for AlertSuppressionManager.classify_error_type method."""

    def test_delegates_to_error_adapter(self) -> None:
        """Delegates classification to error_adapter."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = []

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        manager.error_adapter = MagicMock()
        manager.error_adapter.classify_error_type = MagicMock(return_value="connection_error")

        result = manager.classify_error_type("kalshi", "Connection refused")

        manager.error_adapter.classify_error_type.assert_called_once_with("kalshi", "Connection refused")
        assert result == "connection_error"


class TestAlertSuppressionManagerIsReconnectionError:
    """Tests for AlertSuppressionManager.is_reconnection_error method."""

    def test_delegates_to_error_adapter(self) -> None:
        """Delegates to error_adapter.is_reconnection_error."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = []

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        manager.error_adapter = MagicMock()
        manager.error_adapter.is_reconnection_error = MagicMock(return_value=True)

        result = manager.is_reconnection_error("kalshi", "Reconnecting...")

        manager.error_adapter.is_reconnection_error.assert_called_once_with("kalshi", "Reconnecting...")
        assert result is True


class TestSuppressionStats:
    """Tests for AlertSuppressionManager.get_suppression_statistics method."""

    def test_returns_statistics_from_state_manager(self) -> None:
        """Returns statistics from state_manager."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.max_suppression_duration_seconds = DEFAULT_SUPPRESSION_DURATION_SECONDS
        rule.suppressed_alert_types = [AlertType.ERROR_LOG]

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        expected_stats = {
            "enabled": True,
            "suppressed_count": 10,
            "total_count": 50,
        }
        manager.state_manager = MagicMock()
        manager.state_manager.get_suppression_statistics = MagicMock(return_value=expected_stats)

        result = manager.get_suppression_statistics()

        assert result == expected_stats
        manager.state_manager.get_suppression_statistics.assert_called_once_with(
            enabled=True,
            grace_period_seconds=30,
            max_suppression_duration_seconds=DEFAULT_SUPPRESSION_DURATION_SECONDS,
            suppressed_alert_types=["error_log"],
        )


class TestAlertSuppressionManagerGetRecentDecisions:
    """Tests for AlertSuppressionManager.get_recent_decisions method."""

    def test_returns_recent_decisions_from_tracker(self) -> None:
        """Returns recent decisions from tracker."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = []

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        mock_decisions = [MagicMock(), MagicMock()]
        manager.tracker = MagicMock()
        manager.tracker.get_recent_decisions = MagicMock(return_value=mock_decisions)

        result = manager.get_recent_decisions(limit=25)

        manager.tracker.get_recent_decisions.assert_called_once_with(25)
        assert result == mock_decisions

    def test_uses_default_limit(self) -> None:
        """Uses default limit of 50."""
        rule = MagicMock(spec=SuppressionRule)
        rule.enabled = True
        rule.grace_period_seconds = 30
        rule.suppressed_alert_types = []

        with patch("common.alert_suppression_manager.logger"):
            manager = AlertSuppressionManager(suppression_rule=rule)

        manager.tracker = MagicMock()
        manager.tracker.get_recent_decisions = MagicMock(return_value=[])

        manager.get_recent_decisions()

        manager.tracker.get_recent_decisions.assert_called_once_with(50)


class TestGetAlertSuppressionManager:
    """Tests for get_alert_suppression_manager function."""

    @pytest.mark.asyncio
    async def test_creates_new_instance_when_none_exists(self) -> None:
        """Creates new instance when global is None."""
        import common.alert_suppression_manager as module

        module._alert_suppression_manager = None

        mock_config = {
            "suppression_rules": {
                "service_type_mapping": {},
            }
        }
        mock_rule = MagicMock(spec=SuppressionRule)
        mock_rule.enabled = False
        mock_rule.grace_period_seconds = 60
        mock_rule.suppressed_alert_types = []

        with patch.object(module, "load_suppression_config", return_value=mock_config):
            with patch.object(module, "build_suppression_rule_from_config", return_value=mock_rule):
                with patch.object(module, "logger"):
                    with patch.object(AlertSuppressionManager, "initialize", new_callable=AsyncMock):
                        manager = await get_alert_suppression_manager()

        assert manager is not None
        assert module._alert_suppression_manager is manager

        # Clean up global state
        module._alert_suppression_manager = None

    @pytest.mark.asyncio
    async def test_returns_existing_instance(self) -> None:
        """Returns existing instance when already created."""
        import common.alert_suppression_manager as module

        mock_manager = MagicMock()
        module._alert_suppression_manager = mock_manager

        result = await get_alert_suppression_manager()

        assert result is mock_manager

        # Clean up global state
        module._alert_suppression_manager = None
