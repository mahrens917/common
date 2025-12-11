"""Comprehensive unit tests for dependencies_factory module."""

from dataclasses import dataclass, fields
from unittest.mock import Mock, patch

import pytest


@dataclass
class DependencyFactoryMocks:
    """Container for all dependency factory mocks."""

    error_adapter_class: Mock
    state_manager_class: Mock
    decision_coordinator_class: Mock
    context_builder_class: Mock
    time_window_class: Mock
    evaluator_class: Mock
    tracker_class: Mock
    dependency_init_class: Mock


@pytest.fixture
def factory_mocks():
    """Fixture providing all dependency factory mocks."""
    with (
        patch("common.alert_suppression_manager_helpers.dependencies_factory.DependencyInitializer") as mock_dependency_init_class,
        patch("common.alert_suppression_manager_helpers.dependencies_factory.SuppressionTracker") as mock_tracker_class,
        patch("common.alert_suppression_manager_helpers.dependencies_factory.AlertEvaluator") as mock_evaluator_class,
        patch("common.alert_suppression_manager_helpers.dependencies_factory.TimeWindowManager") as mock_time_window_class,
        patch("common.alert_suppression_manager_helpers.dependencies_factory.ContextBuilder") as mock_context_builder_class,
        patch("common.alert_suppression_manager_helpers.dependencies_factory.DecisionCoordinator") as mock_decision_coordinator_class,
        patch("common.alert_suppression_manager_helpers.dependencies_factory.StateManager") as mock_state_manager_class,
        patch("common.alert_suppression_manager_helpers.dependencies_factory.ErrorClassifierAdapter") as mock_error_adapter_class,
    ):
        yield DependencyFactoryMocks(
            error_adapter_class=mock_error_adapter_class,
            state_manager_class=mock_state_manager_class,
            decision_coordinator_class=mock_decision_coordinator_class,
            context_builder_class=mock_context_builder_class,
            time_window_class=mock_time_window_class,
            evaluator_class=mock_evaluator_class,
            tracker_class=mock_tracker_class,
            dependency_init_class=mock_dependency_init_class,
        )


class TestAlertSuppressionManagerDependencies:
    """Tests for AlertSuppressionManagerDependencies dataclass."""

    def test_dataclass_creation_with_all_fields(self):
        """Test creating AlertSuppressionManagerDependencies with all fields."""
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependencies,
        )

        dependency_init = Mock()
        tracker = Mock()
        evaluator = Mock()
        time_window_manager = Mock()
        context_builder = Mock()
        decision_coordinator = Mock()
        state_manager = Mock()
        error_adapter = Mock()

        deps = AlertSuppressionManagerDependencies(
            dependency_init=dependency_init,
            tracker=tracker,
            evaluator=evaluator,
            time_window_manager=time_window_manager,
            context_builder=context_builder,
            decision_coordinator=decision_coordinator,
            state_manager=state_manager,
            error_adapter=error_adapter,
        )

        assert deps.dependency_init is dependency_init
        assert deps.tracker is tracker
        assert deps.evaluator is evaluator
        assert deps.time_window_manager is time_window_manager
        assert deps.context_builder is context_builder
        assert deps.decision_coordinator is decision_coordinator
        assert deps.state_manager is state_manager
        assert deps.error_adapter is error_adapter

    def test_dataclass_has_correct_fields(self):
        """Test that dataclass has all required fields."""
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependencies,
        )

        field_names = {f.name for f in fields(AlertSuppressionManagerDependencies)}
        expected_fields = {
            "dependency_init",
            "tracker",
            "evaluator",
            "time_window_manager",
            "context_builder",
            "decision_coordinator",
            "state_manager",
            "error_adapter",
        }
        assert field_names == expected_fields

    def test_dataclass_is_mutable(self):
        """Test that dataclass instances are mutable."""
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependencies,
        )

        deps = AlertSuppressionManagerDependencies(
            dependency_init=Mock(),
            tracker=Mock(),
            evaluator=Mock(),
            time_window_manager=Mock(),
            context_builder=Mock(),
            decision_coordinator=Mock(),
            state_manager=Mock(),
            error_adapter=Mock(),
        )

        new_tracker = Mock()
        deps.tracker = new_tracker
        assert deps.tracker is new_tracker


class TestOptionalDependencies:
    """Tests for OptionalDependencies dataclass."""

    def test_dataclass_creation_with_all_none(self):
        """Test creating OptionalDependencies with all fields as None."""
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            OptionalDependencies,
        )

        deps = OptionalDependencies()

        assert deps.dependency_init is None
        assert deps.tracker is None
        assert deps.evaluator is None
        assert deps.time_window_manager is None
        assert deps.context_builder is None
        assert deps.decision_coordinator is None
        assert deps.state_manager is None
        assert deps.error_adapter is None

    def test_dataclass_creation_with_some_fields(self):
        """Test creating OptionalDependencies with some fields set."""
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            OptionalDependencies,
        )

        tracker = Mock()
        evaluator = Mock()

        deps = OptionalDependencies(tracker=tracker, evaluator=evaluator)

        assert deps.tracker is tracker
        assert deps.evaluator is evaluator
        assert deps.dependency_init is None
        assert deps.time_window_manager is None

    def test_dataclass_is_frozen(self):
        """Test that OptionalDependencies is frozen (immutable)."""
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            OptionalDependencies,
        )

        deps = OptionalDependencies()

        with pytest.raises(AttributeError):
            deps.tracker = Mock()

    def test_dataclass_has_correct_fields(self):
        """Test that dataclass has all required optional fields."""
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            OptionalDependencies,
        )

        field_names = {f.name for f in fields(OptionalDependencies)}
        expected_fields = {
            "dependency_init",
            "tracker",
            "evaluator",
            "time_window_manager",
            "context_builder",
            "decision_coordinator",
            "state_manager",
            "error_adapter",
        }
        assert field_names == expected_fields


class TestDependenciesFactoryCreate:
    """Tests for AlertSuppressionManagerDependenciesFactory.create method."""

    def test_create_instantiates_all_dependencies(self, factory_mocks):
        """Test that create method instantiates all dependencies correctly."""
        from common.alert_suppression_manager_helpers.alert_evaluator import (
            SuppressionRule,
        )
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependencies,
            AlertSuppressionManagerDependenciesFactory,
        )

        # Set up mock instances
        mock_dependency_init = Mock()
        mock_tracker = Mock()
        mock_evaluator = Mock()
        mock_time_window = Mock()
        mock_context_builder = Mock()
        mock_decision_coordinator = Mock()
        mock_state_manager = Mock()
        mock_error_adapter = Mock()

        factory_mocks.dependency_init_class.return_value = mock_dependency_init
        factory_mocks.tracker_class.return_value = mock_tracker
        factory_mocks.evaluator_class.return_value = mock_evaluator
        factory_mocks.time_window_class.return_value = mock_time_window
        factory_mocks.context_builder_class.return_value = mock_context_builder
        factory_mocks.decision_coordinator_class.return_value = mock_decision_coordinator
        factory_mocks.state_manager_class.return_value = mock_state_manager
        factory_mocks.error_adapter_class.return_value = mock_error_adapter

        suppression_rule = SuppressionRule()
        result = AlertSuppressionManagerDependenciesFactory.create(suppression_rule)

        # Verify all constructors were called
        factory_mocks.dependency_init_class.assert_called_once_with()
        factory_mocks.tracker_class.assert_called_once_with(max_history_entries=1000)
        factory_mocks.evaluator_class.assert_called_once_with(suppression_rule)
        factory_mocks.time_window_class.assert_called_once_with()
        factory_mocks.context_builder_class.assert_called_once_with(mock_time_window)
        factory_mocks.decision_coordinator_class.assert_called_once_with(
            suppression_rule=suppression_rule,
            tracker=mock_tracker,
            evaluator=mock_evaluator,
            context_builder=mock_context_builder,
        )
        factory_mocks.state_manager_class.assert_called_once_with(mock_tracker)
        # error_adapter is not instantiated, just set to None
        factory_mocks.error_adapter_class.assert_not_called()

        # Verify result is correct type
        assert isinstance(result, AlertSuppressionManagerDependencies)
        assert result.dependency_init is mock_dependency_init
        assert result.tracker is mock_tracker
        assert result.evaluator is mock_evaluator
        assert result.time_window_manager is mock_time_window
        assert result.context_builder is mock_context_builder
        assert result.decision_coordinator is mock_decision_coordinator
        assert result.state_manager is mock_state_manager
        assert result.error_adapter is None

    def test_create_passes_suppression_rule_correctly(self, factory_mocks):
        """Test that suppression_rule is passed to correct constructors."""
        from common.alert_suppression_manager_helpers.alert_evaluator import (
            SuppressionRule,
        )
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependenciesFactory,
        )

        suppression_rule = SuppressionRule(enabled=False, grace_period_seconds=600)
        AlertSuppressionManagerDependenciesFactory.create(suppression_rule)

        # Verify suppression_rule was passed to AlertEvaluator
        factory_mocks.evaluator_class.assert_called_once_with(suppression_rule)

        # Verify suppression_rule was passed to DecisionCoordinator
        call_kwargs = factory_mocks.decision_coordinator_class.call_args[1]
        assert call_kwargs["suppression_rule"] is suppression_rule

    def test_create_uses_fixed_max_history_entries(self, factory_mocks):
        """Test that SuppressionTracker is created with max_history_entries=1000."""
        from common.alert_suppression_manager_helpers.alert_evaluator import (
            SuppressionRule,
        )
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependenciesFactory,
        )

        suppression_rule = SuppressionRule()
        AlertSuppressionManagerDependenciesFactory.create(suppression_rule)

        factory_mocks.tracker_class.assert_called_once_with(max_history_entries=1000)

    def test_create_sets_error_adapter_to_none(self, factory_mocks):
        """Test that error_adapter is set to None (not instantiated)."""
        from common.alert_suppression_manager_helpers.alert_evaluator import (
            SuppressionRule,
        )
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependenciesFactory,
        )

        suppression_rule = SuppressionRule()
        result = AlertSuppressionManagerDependenciesFactory.create(suppression_rule)

        # error_adapter is not instantiated, just set to None
        factory_mocks.error_adapter_class.assert_not_called()
        assert result.error_adapter is None


class TestDependenciesFactoryCreateOrUse:
    """Tests for AlertSuppressionManagerDependenciesFactory.create_or_use method."""

    def test_create_or_use_with_none_optional_deps_calls_create(self):
        """Test that when optional_deps is None, calls create method."""
        from common.alert_suppression_manager_helpers.alert_evaluator import (
            SuppressionRule,
        )
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependenciesFactory,
        )

        suppression_rule = SuppressionRule()

        with patch.object(AlertSuppressionManagerDependenciesFactory, "create") as mock_create:
            mock_create.return_value = Mock()

            result = AlertSuppressionManagerDependenciesFactory.create_or_use(suppression_rule, optional_deps=None)

            mock_create.assert_called_once_with(suppression_rule)
            assert result is mock_create.return_value

    def test_create_or_use_with_all_optional_deps_uses_provided(self, factory_mocks):
        """Test that when all optional deps provided, they are used."""
        from common.alert_suppression_manager_helpers.alert_evaluator import (
            SuppressionRule,
        )
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependencies,
            AlertSuppressionManagerDependenciesFactory,
            OptionalDependencies,
        )

        # Create mock instances for all dependencies
        dependency_init = Mock()
        tracker = Mock()
        evaluator = Mock()
        time_window_manager = Mock()
        context_builder = Mock()
        decision_coordinator = Mock()
        state_manager = Mock()
        error_adapter = Mock()

        optional_deps = OptionalDependencies(
            dependency_init=dependency_init,
            tracker=tracker,
            evaluator=evaluator,
            time_window_manager=time_window_manager,
            context_builder=context_builder,
            decision_coordinator=decision_coordinator,
            state_manager=state_manager,
            error_adapter=error_adapter,
        )

        suppression_rule = SuppressionRule()
        result = AlertSuppressionManagerDependenciesFactory.create_or_use(suppression_rule, optional_deps=optional_deps)

        # Verify no constructors were called
        factory_mocks.dependency_init_class.assert_not_called()
        factory_mocks.tracker_class.assert_not_called()
        factory_mocks.evaluator_class.assert_not_called()

        # Verify result uses provided dependencies
        assert isinstance(result, AlertSuppressionManagerDependencies)
        assert result.dependency_init is dependency_init
        assert result.tracker is tracker
        assert result.evaluator is evaluator
        assert result.time_window_manager is time_window_manager
        assert result.context_builder is context_builder
        assert result.decision_coordinator is decision_coordinator
        assert result.state_manager is state_manager
        assert result.error_adapter is error_adapter

    def test_create_or_use_with_partial_optional_deps_merges(self, factory_mocks):
        """Test that when some optional deps provided, merges with defaults."""
        from common.alert_suppression_manager_helpers.alert_evaluator import (
            SuppressionRule,
        )
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependencies,
            AlertSuppressionManagerDependenciesFactory,
            OptionalDependencies,
        )

        # Provide only some dependencies
        provided_tracker = Mock()
        provided_evaluator = Mock()

        optional_deps = OptionalDependencies(
            tracker=provided_tracker,
            evaluator=provided_evaluator,
        )

        # Set up mock instances for defaults
        mock_dependency_init = Mock()
        mock_time_window = Mock()
        mock_context_builder = Mock()
        mock_decision_coordinator = Mock()
        mock_state_manager = Mock()
        mock_error_adapter = Mock()

        factory_mocks.dependency_init_class.return_value = mock_dependency_init
        factory_mocks.time_window_class.return_value = mock_time_window
        factory_mocks.context_builder_class.return_value = mock_context_builder
        factory_mocks.decision_coordinator_class.return_value = mock_decision_coordinator
        factory_mocks.state_manager_class.return_value = mock_state_manager
        factory_mocks.error_adapter_class.return_value = mock_error_adapter

        suppression_rule = SuppressionRule()
        result = AlertSuppressionManagerDependenciesFactory.create_or_use(suppression_rule, optional_deps=optional_deps)

        # Verify result uses provided dependencies where available
        assert isinstance(result, AlertSuppressionManagerDependencies)
        assert result.tracker is provided_tracker
        assert result.evaluator is provided_evaluator

        # Verify result uses defaults for missing dependencies
        assert result.dependency_init is mock_dependency_init
        assert result.time_window_manager is mock_time_window
        assert result.context_builder is mock_context_builder
        assert result.decision_coordinator is mock_decision_coordinator
        assert result.state_manager is mock_state_manager
        # error_adapter is always None when created through factory
        assert result.error_adapter is None

    def test_create_or_use_with_empty_optional_deps_uses_defaults(self, factory_mocks):
        """Test that when optional deps has all None, uses defaults."""
        from common.alert_suppression_manager_helpers.alert_evaluator import (
            SuppressionRule,
        )
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependencies,
            AlertSuppressionManagerDependenciesFactory,
            OptionalDependencies,
        )

        # Create OptionalDependencies with all None
        optional_deps = OptionalDependencies()

        # Set up mock instances for defaults
        mock_dependency_init = Mock()
        mock_tracker = Mock()
        mock_evaluator = Mock()
        mock_time_window = Mock()
        mock_context_builder = Mock()
        mock_decision_coordinator = Mock()
        mock_state_manager = Mock()
        mock_error_adapter = Mock()

        factory_mocks.dependency_init_class.return_value = mock_dependency_init
        factory_mocks.tracker_class.return_value = mock_tracker
        factory_mocks.evaluator_class.return_value = mock_evaluator
        factory_mocks.time_window_class.return_value = mock_time_window
        factory_mocks.context_builder_class.return_value = mock_context_builder
        factory_mocks.decision_coordinator_class.return_value = mock_decision_coordinator
        factory_mocks.state_manager_class.return_value = mock_state_manager
        factory_mocks.error_adapter_class.return_value = mock_error_adapter

        suppression_rule = SuppressionRule()
        result = AlertSuppressionManagerDependenciesFactory.create_or_use(suppression_rule, optional_deps=optional_deps)

        # Verify result uses all defaults
        assert isinstance(result, AlertSuppressionManagerDependencies)
        assert result.dependency_init is mock_dependency_init
        assert result.tracker is mock_tracker
        assert result.evaluator is mock_evaluator
        assert result.time_window_manager is mock_time_window
        assert result.context_builder is mock_context_builder
        assert result.decision_coordinator is mock_decision_coordinator
        assert result.state_manager is mock_state_manager
        # error_adapter defaults to None
        assert result.error_adapter is None

    def test_create_or_use_merge_preserves_all_provided(self, factory_mocks):
        """Test that merge logic preserves all provided dependencies."""
        from common.alert_suppression_manager_helpers.alert_evaluator import (
            SuppressionRule,
        )
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependenciesFactory,
            OptionalDependencies,
        )

        # Provide specific dependencies
        provided_dependency_init = Mock()
        provided_time_window = Mock()
        provided_state_manager = Mock()

        optional_deps = OptionalDependencies(
            dependency_init=provided_dependency_init,
            time_window_manager=provided_time_window,
            state_manager=provided_state_manager,
        )

        # Set up defaults
        factory_mocks.dependency_init_class.return_value = Mock()
        factory_mocks.tracker_class.return_value = Mock()
        factory_mocks.evaluator_class.return_value = Mock()
        factory_mocks.time_window_class.return_value = Mock()
        factory_mocks.context_builder_class.return_value = Mock()
        factory_mocks.decision_coordinator_class.return_value = Mock()
        factory_mocks.state_manager_class.return_value = Mock()
        factory_mocks.error_adapter_class.return_value = Mock()

        suppression_rule = SuppressionRule()
        result = AlertSuppressionManagerDependenciesFactory.create_or_use(suppression_rule, optional_deps=optional_deps)

        # Verify provided dependencies are in result
        assert result.dependency_init is provided_dependency_init
        assert result.time_window_manager is provided_time_window
        assert result.state_manager is provided_state_manager


class TestModuleIntegration:
    """Integration tests for the module."""

    def test_all_classes_importable(self):
        """Test that all classes are importable."""
        from common.alert_suppression_manager_helpers import dependencies_factory

        assert hasattr(dependencies_factory, "AlertSuppressionManagerDependencies")
        assert hasattr(dependencies_factory, "OptionalDependencies")
        assert hasattr(dependencies_factory, "AlertSuppressionManagerDependenciesFactory")

    def test_field_count_matches_between_dataclasses(self):
        """Test that both dataclasses have the same number of fields."""
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependencies,
            OptionalDependencies,
        )

        main_fields = {f.name for f in fields(AlertSuppressionManagerDependencies)}
        optional_fields = {f.name for f in fields(OptionalDependencies)}

        assert main_fields == optional_fields

    def test_factory_methods_return_correct_type(self, factory_mocks):
        """Test that both factory methods return AlertSuppressionManagerDependencies."""
        from common.alert_suppression_manager_helpers.alert_evaluator import (
            SuppressionRule,
        )
        from common.alert_suppression_manager_helpers.dependencies_factory import (
            AlertSuppressionManagerDependencies,
            AlertSuppressionManagerDependenciesFactory,
        )

        # Set up mocks
        factory_mocks.dependency_init_class.return_value = Mock()
        factory_mocks.tracker_class.return_value = Mock()
        factory_mocks.evaluator_class.return_value = Mock()
        factory_mocks.time_window_class.return_value = Mock()
        factory_mocks.context_builder_class.return_value = Mock()
        factory_mocks.decision_coordinator_class.return_value = Mock()
        factory_mocks.state_manager_class.return_value = Mock()
        factory_mocks.error_adapter_class.return_value = Mock()

        suppression_rule = SuppressionRule()

        result1 = AlertSuppressionManagerDependenciesFactory.create(suppression_rule)
        result2 = AlertSuppressionManagerDependenciesFactory.create_or_use(suppression_rule, None)

        assert isinstance(result1, AlertSuppressionManagerDependencies)
        assert isinstance(result2, AlertSuppressionManagerDependencies)
