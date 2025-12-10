"""Comprehensive tests for initialization_coordinator.py"""

from unittest.mock import Mock, call, patch

import pytest

from common.kalshi_trading_client.client_helpers.initialization_coordinator import (
    InitializationCoordinator,
    _build_initialization_result,
    _create_service_stack,
    _InitializationResultComponents,
    _initialize_core_clients,
    _wire_order_dependencies,
)


class TestInitializationCoordinator:
    """Test InitializationCoordinator class."""

    def test_initialize_all_components_returns_dict(self):
        """Should return dictionary with all components."""
        mock_kalshi = Mock()
        mock_backoff = Mock()
        mock_network_health = Mock()
        mock_trade_store = Mock()
        mock_telegram = Mock()
        mock_weather = Mock()

        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._initialize_core_clients"
            ) as mock_core,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._create_service_stack"
            ) as mock_stack,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._wire_order_dependencies"
            ) as mock_wire,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._build_initialization_result"
            ) as mock_build,
        ):

            mock_core.return_value = (mock_kalshi, mock_backoff, Mock(), Mock())
            mock_initializer.extract_config_values.return_value = {"test": "config"}
            mock_initializer.load_config.return_value = {}
            mock_initializer.initialize_weather_resolver.return_value = mock_weather
            mock_portfolio = Mock()
            mock_orders = Mock()
            mock_collection = Mock()
            mock_stack.return_value = (mock_portfolio, mock_orders, mock_collection)
            mock_build.return_value = {"result": "value"}

            result = InitializationCoordinator.initialize_all_components(
                mock_kalshi,
                mock_backoff,
                mock_network_health,
                mock_trade_store,
                mock_telegram,
                mock_weather,
            )

            assert result == {"result": "value"}
            mock_core.assert_called_once()
            mock_wire.assert_called_once()
            mock_build.assert_called_once()

    def test_initializes_core_clients_first(self):
        """Should initialize core clients before other components."""
        mock_kalshi = Mock()
        mock_backoff = Mock()
        mock_network_health = Mock()
        mock_trade_store = Mock()
        mock_telegram = Mock()
        mock_weather = Mock()

        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._initialize_core_clients"
            ) as mock_core,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._create_service_stack"
            ) as mock_stack,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._wire_order_dependencies"
            ),
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._build_initialization_result"
            ),
        ):

            mock_core.return_value = (Mock(), Mock(), Mock(), Mock())
            mock_initializer.extract_config_values.return_value = {}
            mock_initializer.load_config.return_value = {}
            mock_initializer.initialize_weather_resolver.return_value = Mock()
            mock_stack.return_value = (Mock(), Mock(), Mock())

            InitializationCoordinator.initialize_all_components(
                mock_kalshi,
                mock_backoff,
                mock_network_health,
                mock_trade_store,
                mock_telegram,
                mock_weather,
            )

            mock_core.assert_called_once_with(
                mock_kalshi, mock_trade_store, mock_backoff, mock_network_health
            )

    def test_extracts_config_values(self):
        """Should extract config values using ClientInitializer."""
        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._initialize_core_clients"
            ) as mock_core,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._create_service_stack"
            ) as mock_stack,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._wire_order_dependencies"
            ),
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._build_initialization_result"
            ),
        ):

            mock_core.return_value = (Mock(), Mock(), Mock(), Mock())
            mock_config = {"key": "value"}
            mock_initializer.load_config.return_value = mock_config
            mock_initializer.extract_config_values.return_value = {"extracted": "config"}
            mock_initializer.initialize_weather_resolver.return_value = Mock()
            mock_stack.return_value = (Mock(), Mock(), Mock())

            InitializationCoordinator.initialize_all_components(
                None, None, None, Mock(), None, None
            )

            mock_initializer.load_config.assert_called_once()
            mock_initializer.extract_config_values.assert_called_once_with(mock_config)

    def test_initializes_weather_resolver(self):
        """Should initialize weather resolver."""
        mock_weather = Mock()

        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._initialize_core_clients"
            ) as mock_core,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._create_service_stack"
            ) as mock_stack,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._wire_order_dependencies"
            ),
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._build_initialization_result"
            ),
        ):

            mock_core.return_value = (Mock(), Mock(), Mock(), Mock())
            mock_initializer.extract_config_values.return_value = {}
            mock_initializer.load_config.return_value = {}
            mock_initialized_weather = Mock()
            mock_initializer.initialize_weather_resolver.return_value = mock_initialized_weather
            mock_stack.return_value = (Mock(), Mock(), Mock())

            InitializationCoordinator.initialize_all_components(
                None, None, None, Mock(), None, mock_weather
            )

            mock_initializer.initialize_weather_resolver.assert_called_once_with(mock_weather)

    def test_creates_service_stack(self):
        """Should create service stack with all dependencies."""
        mock_kalshi = Mock()
        mock_trade_store_manager = Mock()
        mock_notifier = Mock()
        mock_weather = Mock()
        mock_telegram = Mock()

        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._initialize_core_clients"
            ) as mock_core,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._create_service_stack"
            ) as mock_stack,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._wire_order_dependencies"
            ),
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._build_initialization_result"
            ),
        ):

            mock_core.return_value = (
                mock_kalshi,
                Mock(),
                mock_trade_store_manager,
                mock_notifier,
            )
            mock_initializer.extract_config_values.return_value = {}
            mock_initializer.load_config.return_value = {}
            mock_initializer.initialize_weather_resolver.return_value = mock_weather
            mock_stack.return_value = (Mock(), Mock(), Mock())

            InitializationCoordinator.initialize_all_components(
                None, None, None, Mock(), mock_telegram, None
            )

            # Verify service stack was called with correct arguments
            args = mock_stack.call_args[0]
            assert args[0] == mock_kalshi
            assert args[1] == mock_trade_store_manager
            assert args[2] == mock_notifier
            assert args[3] == mock_weather
            assert args[5] == mock_telegram

    def test_wires_order_dependencies(self):
        """Should wire order service dependencies."""
        mock_orders = Mock()
        mock_notifier = Mock()
        mock_telegram = Mock()

        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._initialize_core_clients"
            ) as mock_core,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._create_service_stack"
            ) as mock_stack,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._wire_order_dependencies"
            ) as mock_wire,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._build_initialization_result"
            ),
        ):

            mock_core.return_value = (Mock(), Mock(), Mock(), mock_notifier)
            mock_initializer.extract_config_values.return_value = {}
            mock_initializer.load_config.return_value = {}
            mock_initializer.initialize_weather_resolver.return_value = Mock()
            mock_stack.return_value = (Mock(), mock_orders, Mock())

            InitializationCoordinator.initialize_all_components(
                None, None, None, Mock(), mock_telegram, None
            )

            mock_wire.assert_called_once_with(mock_orders, mock_notifier, mock_telegram)

    def test_logs_completion_message(self, caplog):
        """Should log completion message."""
        import logging

        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._initialize_core_clients"
            ) as mock_core,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._create_service_stack"
            ) as mock_stack,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._wire_order_dependencies"
            ),
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator._build_initialization_result"
            ),
        ):

            mock_core.return_value = (Mock(), Mock(), Mock(), Mock())
            mock_initializer.extract_config_values.return_value = {}
            mock_initializer.load_config.return_value = {}
            mock_initializer.initialize_weather_resolver.return_value = Mock()
            mock_stack.return_value = (Mock(), Mock(), Mock())

            with caplog.at_level(logging.INFO):
                InitializationCoordinator.initialize_all_components(
                    None, None, None, Mock(), None, None
                )

            assert any(
                "Initialized unified trading client with trade collection" in message
                for message in caplog.messages
            )


class TestInitializeCoreClients:
    """Test _initialize_core_clients function."""

    def test_initializes_kalshi_client(self):
        """Should initialize Kalshi client."""
        mock_kalshi = Mock()
        mock_trade_store = Mock()
        mock_initialized_kalshi = Mock()

        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.TradeStoreManager"
            ),
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.TradeNotifierAdapter"
            ),
        ):

            mock_initializer.initialize_kalshi_client.return_value = mock_initialized_kalshi
            mock_initializer.initialize_backoff_manager.return_value = Mock()

            result = _initialize_core_clients(mock_kalshi, mock_trade_store, None, None)

            assert result[0] == mock_initialized_kalshi
            mock_initializer.initialize_kalshi_client.assert_called_once_with(
                mock_kalshi, mock_trade_store
            )

    def test_initializes_backoff_manager(self):
        """Should initialize backoff manager."""
        mock_backoff = Mock()
        mock_network_health = Mock()
        mock_initialized_backoff = Mock()

        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.TradeStoreManager"
            ),
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.TradeNotifierAdapter"
            ),
        ):

            mock_initializer.initialize_kalshi_client.return_value = Mock()
            mock_initializer.initialize_backoff_manager.return_value = mock_initialized_backoff

            result = _initialize_core_clients(None, Mock(), mock_backoff, mock_network_health)

            assert result[1] == mock_initialized_backoff
            mock_initializer.initialize_backoff_manager.assert_called_once_with(
                mock_backoff, mock_network_health
            )

    def test_creates_trade_store_manager(self):
        """Should create TradeStoreManager with correct dependencies."""
        mock_kalshi = Mock()
        mock_trade_store = Mock()

        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.TradeStoreManager"
            ) as mock_tsm_class,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.TradeNotifierAdapter"
            ),
        ):

            mock_initializer.initialize_kalshi_client.return_value = mock_kalshi
            mock_initializer.initialize_backoff_manager.return_value = Mock()
            mock_tsm_instance = Mock()
            mock_tsm_class.return_value = mock_tsm_instance

            result = _initialize_core_clients(None, mock_trade_store, None, None)

            assert result[2] == mock_tsm_instance
            mock_tsm_class.assert_called_once()
            call_kwargs = mock_tsm_class.call_args[1]
            assert call_kwargs["kalshi_client"] == mock_kalshi
            # Verify store_supplier is callable
            assert callable(call_kwargs["store_supplier"])
            assert call_kwargs["store_supplier"]() == mock_trade_store

    def test_creates_notifier(self):
        """Should create TradeNotifierAdapter."""
        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.TradeStoreManager"
            ),
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.TradeNotifierAdapter"
            ) as mock_notifier_class,
        ):

            mock_initializer.initialize_kalshi_client.return_value = Mock()
            mock_initializer.initialize_backoff_manager.return_value = Mock()
            mock_notifier_instance = Mock()
            mock_notifier_class.return_value = mock_notifier_instance

            result = _initialize_core_clients(None, Mock(), None, None)

            assert result[3] == mock_notifier_instance
            mock_notifier_class.assert_called_once()

    def test_returns_all_four_components(self):
        """Should return tuple of four components."""
        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.TradeStoreManager"
            ),
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.TradeNotifierAdapter"
            ),
        ):

            mock_initializer.initialize_kalshi_client.return_value = Mock()
            mock_initializer.initialize_backoff_manager.return_value = Mock()

            result = _initialize_core_clients(None, Mock(), None, None)

            assert len(result) == 4
            assert all(r is not None for r in result)


class TestCreateServiceStack:
    """Test _create_service_stack function."""

    def test_creates_service_providers(self):
        """Should create service providers."""
        mock_trade_store_manager = Mock()
        services_holder = {}

        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.create_service_providers"
            ) as mock_create_providers,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
        ):

            mock_create_providers.return_value = {
                "get_trade_store": Mock(),
                "get_order_poller": Mock(),
                "get_trade_finalizer": Mock(),
            }
            mock_initializer.create_services.return_value = (Mock(), Mock(), Mock())

            _create_service_stack(
                Mock(), mock_trade_store_manager, Mock(), Mock(), services_holder, Mock()
            )

            mock_create_providers.assert_called_once_with(mock_trade_store_manager, services_holder)

    def test_calls_create_services_with_providers(self):
        """Should call ClientInitializer.create_services with service providers."""
        mock_kalshi = Mock()
        mock_notifier = Mock()
        mock_weather = Mock()
        mock_telegram = Mock()
        mock_get_trade_store = Mock()
        mock_get_order_poller = Mock()
        mock_get_trade_finalizer = Mock()

        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.create_service_providers"
            ) as mock_create_providers,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
        ):

            mock_create_providers.return_value = {
                "get_trade_store": mock_get_trade_store,
                "get_order_poller": mock_get_order_poller,
                "get_trade_finalizer": mock_get_trade_finalizer,
            }
            mock_initializer.create_services.return_value = (Mock(), Mock(), Mock())

            _create_service_stack(
                mock_kalshi, Mock(), mock_notifier, mock_weather, {}, mock_telegram
            )

            mock_initializer.create_services.assert_called_once_with(
                mock_kalshi,
                mock_get_trade_store,
                mock_notifier,
                mock_weather,
                mock_get_order_poller,
                mock_get_trade_finalizer,
                mock_telegram,
            )

    def test_returns_three_services(self):
        """Should return portfolio, orders, and trade_collection."""
        mock_portfolio = Mock()
        mock_orders = Mock()
        mock_collection = Mock()

        with (
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.create_service_providers"
            ) as mock_create_providers,
            patch(
                "common.kalshi_trading_client.client_helpers.initialization_coordinator.ClientInitializer"
            ) as mock_initializer,
        ):

            mock_create_providers.return_value = {
                "get_trade_store": Mock(),
                "get_order_poller": Mock(),
                "get_trade_finalizer": Mock(),
            }
            mock_initializer.create_services.return_value = (
                mock_portfolio,
                mock_orders,
                mock_collection,
            )

            result = _create_service_stack(Mock(), Mock(), Mock(), Mock(), {}, Mock())

            assert result == (mock_portfolio, mock_orders, mock_collection)


class TestWireOrderDependencies:
    """Test _wire_order_dependencies function."""

    def test_updates_notifier_on_orders(self):
        """Should call update_notifier on orders service."""
        mock_orders = Mock()
        mock_notifier = Mock()
        mock_telegram = Mock()

        _wire_order_dependencies(mock_orders, mock_notifier, mock_telegram)

        mock_orders.update_notifier.assert_called_once_with(mock_notifier)

    def test_updates_telegram_handler_on_orders(self):
        """Should call update_telegram_handler on orders service."""
        mock_orders = Mock()
        mock_notifier = Mock()
        mock_telegram = Mock()

        _wire_order_dependencies(mock_orders, mock_notifier, mock_telegram)

        mock_orders.update_telegram_handler.assert_called_once_with(mock_telegram)

    def test_does_not_return_value(self):
        """Should return None."""
        result = _wire_order_dependencies(Mock(), Mock(), Mock())

        assert result is None


class TestBuildInitializationResult:
    """Test _build_initialization_result function."""

    def test_builds_complete_result_dict(self):
        """Should build dictionary with all components."""
        mock_kalshi = Mock()
        mock_backoff = Mock()
        mock_trade_store = Mock()
        mock_tsm = Mock()
        mock_telegram = Mock()
        mock_notifier = Mock()
        mock_config = {"test": "config"}
        mock_weather = Mock()
        mock_portfolio = Mock()
        mock_orders = Mock()
        mock_collection = Mock()
        services_holder = {"test": "holder"}

        components = _InitializationResultComponents(
            initialized_kalshi=mock_kalshi,
            initialized_backoff=mock_backoff,
            trade_store=mock_trade_store,
            trade_store_manager=mock_tsm,
            telegram_handler=mock_telegram,
            notifier=mock_notifier,
            config_vals=mock_config,
            initialized_weather=mock_weather,
            portfolio=mock_portfolio,
            orders=mock_orders,
            trade_collection=mock_collection,
            services_holder=services_holder,
        )

        result = _build_initialization_result(components)

        assert result["kalshi_client"] == mock_kalshi
        assert result["backoff_manager"] == mock_backoff
        assert result["trade_store"] == mock_trade_store
        assert result["trade_store_manager"] == mock_tsm
        assert result["telegram_handler"] == mock_telegram
        assert result["service_name"] == "kalshi_trading"
        assert result["notifier"] == mock_notifier
        assert result["config_vals"] == mock_config
        assert result["weather_station_resolver"] == mock_weather
        assert result["portfolio"] == mock_portfolio
        assert result["orders"] == mock_orders
        assert result["trade_collection"] == mock_collection
        assert result["is_running"] is False
        assert result["services_holder"] == services_holder

    def test_sets_is_running_to_false(self):
        """Should set is_running to False."""
        components = _InitializationResultComponents(
            initialized_kalshi=Mock(),
            initialized_backoff=Mock(),
            trade_store=Mock(),
            trade_store_manager=Mock(),
            telegram_handler=Mock(),
            notifier=Mock(),
            config_vals={},
            initialized_weather=Mock(),
            portfolio=Mock(),
            orders=Mock(),
            trade_collection=Mock(),
            services_holder={},
        )

        result = _build_initialization_result(components)

        assert result["is_running"] is False

    def test_sets_service_name(self):
        """Should set service_name to kalshi_trading."""
        components = _InitializationResultComponents(
            initialized_kalshi=Mock(),
            initialized_backoff=Mock(),
            trade_store=Mock(),
            trade_store_manager=Mock(),
            telegram_handler=Mock(),
            notifier=Mock(),
            config_vals={},
            initialized_weather=Mock(),
            portfolio=Mock(),
            orders=Mock(),
            trade_collection=Mock(),
            services_holder={},
        )

        result = _build_initialization_result(components)

        assert result["service_name"] == "kalshi_trading"

    def test_includes_all_component_fields(self):
        """Should include all fields from components."""
        components = _InitializationResultComponents(
            initialized_kalshi=Mock(),
            initialized_backoff=Mock(),
            trade_store=Mock(),
            trade_store_manager=Mock(),
            telegram_handler=Mock(),
            notifier=Mock(),
            config_vals={},
            initialized_weather=Mock(),
            portfolio=Mock(),
            orders=Mock(),
            trade_collection=Mock(),
            services_holder={},
        )

        result = _build_initialization_result(components)

        expected_keys = {
            "kalshi_client",
            "backoff_manager",
            "trade_store",
            "trade_store_manager",
            "telegram_handler",
            "service_name",
            "notifier",
            "config_vals",
            "weather_station_resolver",
            "portfolio",
            "orders",
            "trade_collection",
            "is_running",
            "services_holder",
        }

        assert set(result.keys()) == expected_keys


class TestInitializationResultComponents:
    """Test _InitializationResultComponents dataclass."""

    def test_is_frozen(self):
        """Should be immutable (frozen)."""
        components = _InitializationResultComponents(
            initialized_kalshi=Mock(),
            initialized_backoff=Mock(),
            trade_store=Mock(),
            trade_store_manager=Mock(),
            telegram_handler=Mock(),
            notifier=Mock(),
            config_vals={},
            initialized_weather=Mock(),
            portfolio=Mock(),
            orders=Mock(),
            trade_collection=Mock(),
            services_holder={},
        )

        with pytest.raises(Exception):
            components.initialized_kalshi = Mock()

    def test_stores_all_components(self):
        """Should store all provided components."""
        mock_kalshi = Mock()
        mock_backoff = Mock()
        mock_trade_store = Mock()
        mock_tsm = Mock()
        mock_telegram = Mock()
        mock_notifier = Mock()
        mock_config = {}
        mock_weather = Mock()
        mock_portfolio = Mock()
        mock_orders = Mock()
        mock_collection = Mock()
        services_holder = {}

        components = _InitializationResultComponents(
            initialized_kalshi=mock_kalshi,
            initialized_backoff=mock_backoff,
            trade_store=mock_trade_store,
            trade_store_manager=mock_tsm,
            telegram_handler=mock_telegram,
            notifier=mock_notifier,
            config_vals=mock_config,
            initialized_weather=mock_weather,
            portfolio=mock_portfolio,
            orders=mock_orders,
            trade_collection=mock_collection,
            services_holder=services_holder,
        )

        assert components.initialized_kalshi == mock_kalshi
        assert components.initialized_backoff == mock_backoff
        assert components.trade_store == mock_trade_store
        assert components.trade_store_manager == mock_tsm
        assert components.telegram_handler == mock_telegram
        assert components.notifier == mock_notifier
        assert components.config_vals == mock_config
        assert components.initialized_weather == mock_weather
        assert components.portfolio == mock_portfolio
        assert components.orders == mock_orders
        assert components.trade_collection == mock_collection
        assert components.services_holder == services_holder
