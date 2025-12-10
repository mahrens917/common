"""Tests for dawn reset service dependencies factory."""

from unittest.mock import MagicMock

from common.dawn_reset_service_helpers.dependencies_factory import (
    CreateOrUseConfig,
    DawnResetServiceDependencies,
    DawnResetServiceDependenciesFactory,
)


class TestDawnResetServiceDependencies:
    """Tests for DawnResetServiceDependencies dataclass."""

    def test_dependencies_stores_all_fields(self) -> None:
        """DawnResetServiceDependencies stores all provided dependencies."""
        mock_calc = MagicMock()
        mock_cache = MagicMock()
        mock_resolver = MagicMock()
        mock_field_reset = MagicMock()
        mock_alert = MagicMock()
        mock_logger = MagicMock()

        deps = DawnResetServiceDependencies(
            dawn_calculator=mock_calc,
            cache_manager=mock_cache,
            timestamp_resolver=mock_resolver,
            field_reset_manager=mock_field_reset,
            alert_manager=mock_alert,
            logger=mock_logger,
        )

        assert deps.dawn_calculator is mock_calc
        assert deps.cache_manager is mock_cache
        assert deps.timestamp_resolver is mock_resolver
        assert deps.field_reset_manager is mock_field_reset
        assert deps.alert_manager is mock_alert
        assert deps.logger is mock_logger


class TestCreateOrUseConfig:
    """Tests for CreateOrUseConfig dataclass."""

    def test_config_defaults_to_none(self) -> None:
        """CreateOrUseConfig defaults all fields to None."""
        config = CreateOrUseConfig()

        assert config.telegram_handler is None
        assert config.dawn_calculator is None
        assert config.cache_manager is None
        assert config.timestamp_resolver is None
        assert config.field_reset_manager is None
        assert config.alert_manager is None
        assert config.logger is None
        assert config.calculate_dawn_fn is None

    def test_config_accepts_values(self) -> None:
        """CreateOrUseConfig accepts provided values."""
        mock_handler = MagicMock()
        mock_calc = MagicMock()

        config = CreateOrUseConfig(
            telegram_handler=mock_handler,
            dawn_calculator=mock_calc,
        )

        assert config.telegram_handler is mock_handler
        assert config.dawn_calculator is mock_calc


class TestDawnResetServiceDependenciesFactoryCreate:
    """Tests for DawnResetServiceDependenciesFactory.create."""

    def test_create_returns_dependencies(self) -> None:
        """Factory.create returns DawnResetServiceDependencies."""
        deps = DawnResetServiceDependenciesFactory.create()

        assert isinstance(deps, DawnResetServiceDependencies)
        assert deps.dawn_calculator is not None
        assert deps.cache_manager is not None
        assert deps.timestamp_resolver is not None
        assert deps.field_reset_manager is not None
        assert deps.alert_manager is not None
        assert deps.logger is not None

    def test_create_with_telegram_handler(self) -> None:
        """Factory.create accepts telegram_handler."""
        mock_handler = MagicMock()
        deps = DawnResetServiceDependenciesFactory.create(telegram_handler=mock_handler)

        assert deps.alert_manager is not None

    def test_create_with_custom_dawn_fn(self) -> None:
        """Factory.create accepts custom dawn calculation function."""
        mock_fn = MagicMock()
        deps = DawnResetServiceDependenciesFactory.create(calculate_dawn_fn=mock_fn)

        assert deps.dawn_calculator._calculate_dawn_utc is mock_fn


class TestDawnResetServiceDependenciesFactoryCreateOrUse:
    """Tests for DawnResetServiceDependenciesFactory.create_or_use."""

    def test_create_or_use_returns_provided_when_all_given(self) -> None:
        """When all dependencies provided, returns them directly."""
        mock_calc = MagicMock()
        mock_cache = MagicMock()
        mock_resolver = MagicMock()
        mock_field_reset = MagicMock()
        mock_alert = MagicMock()
        mock_logger = MagicMock()

        config = CreateOrUseConfig(
            dawn_calculator=mock_calc,
            cache_manager=mock_cache,
            timestamp_resolver=mock_resolver,
            field_reset_manager=mock_field_reset,
            alert_manager=mock_alert,
            logger=mock_logger,
        )

        deps = DawnResetServiceDependenciesFactory.create_or_use(config)

        assert deps.dawn_calculator is mock_calc
        assert deps.cache_manager is mock_cache
        assert deps.timestamp_resolver is mock_resolver
        assert deps.field_reset_manager is mock_field_reset
        assert deps.alert_manager is mock_alert
        assert deps.logger is mock_logger

    def test_create_or_use_creates_missing_dependencies(self) -> None:
        """When some dependencies missing, creates new ones."""
        mock_calc = MagicMock()
        config = CreateOrUseConfig(dawn_calculator=mock_calc)

        deps = DawnResetServiceDependenciesFactory.create_or_use(config)

        assert deps.dawn_calculator is mock_calc
        assert deps.cache_manager is not None
        assert deps.timestamp_resolver is not None
        assert deps.field_reset_manager is not None
        assert deps.alert_manager is not None
        assert deps.logger is not None

    def test_create_or_use_creates_all_when_none_provided(self) -> None:
        """When no dependencies provided, creates all new."""
        config = CreateOrUseConfig()

        deps = DawnResetServiceDependenciesFactory.create_or_use(config)

        assert deps.dawn_calculator is not None
        assert deps.cache_manager is not None
        assert deps.timestamp_resolver is not None
        assert deps.field_reset_manager is not None
        assert deps.alert_manager is not None
        assert deps.logger is not None
