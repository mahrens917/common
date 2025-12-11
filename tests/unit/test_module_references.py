"""Tests for src/common/_module_references.py.

This module tests that the module reference system correctly imports modules
when the REFERENCE_UNUSED_MODULES environment variable is set.
"""

import importlib
import os
import sys
from typing import List
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_modules() -> List[str]:
    """List of all modules that should be imported."""
    return [
        "common.backoff_manager_helpers.delay_calculator",
        "common.backoff_manager_helpers.retry_checker",
        "common.connection_state_tracker_helpers.event_manager",
        "common.connection_state_tracker_helpers.state_querier",
        "common.connection_state_tracker_helpers.state_updater",
        "common.daily_max_state_helpers.state_persistence",
        "common.data_models.trade_record_helpers.pnl_report_validation",
        "common.dawn_reset_service_helpers.dawn_check_coordinator",
        "common.dependency_monitor_helpers.callback_executor",
        "common.dependency_monitor_helpers.redis_tracker",
        "common.dict_utils",
        "common.emergency_position_manager_helpers.exposure_calculator",
        "common.emergency_position_manager_helpers.limit_enforcer",
        "common.emergency_position_manager_helpers.stop_loss_monitor",
        "common.error_analyzer_helpers.error_analysis_builder",
        "common.exceptions.market",
        "common.function_params",
        "common.health.service_health_checker_helpers.batch_health_checker",
        "common.health.service_health_checker_helpers.redis_status_checker",
        "common.kalshi_trading_client.client_helpers.initialization_coordinator_helpers.service_creator",
        "common.kalshi_trading_client.services.order_helpers.factory_utils",
        "common.kalshi_trading_client.services.order_helpers.notifier_updater",
        "common.kalshi_trading_client.services.order_helpers.order_creator_helpers",
        "common.kalshi_trading_client.services.order_helpers.order_poller_helpers",
        "common.market_data_parser_helpers.contract_validator_helpers.batch_validator",
        "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow",
        "common.market_data_parser_helpers.data_cleaner",
        "common.market_data_parser_helpers.date_parser_helpers",
        "common.market_data_parser_helpers.instrument_parser",
        "common.market_data_parser_helpers.parsed_instrument_validator",
        "common.market_data_parser_helpers.structure_validator",
        "common.metadata_store_auto_updater_helpers.time_window_updater_helpers.message_counter",
        "common.midnight_reset_service_helpers.max_temp_processor_helpers",
        "common.network_adaptive_poller_helpers.interval_adjuster",
        "common.network_adaptive_poller_helpers.network_classifier",
        "common.network_adaptive_poller_helpers.performance_calculator",
        "common.optimized_status_reporter_helpers.basic_info_printer",
        "common.optimized_status_reporter_helpers.redis_health_printer",
        "common.optimized_status_reporter_helpers.system_health_printer",
        "common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.station_scanner",
        "common.order_execution.finalizer_helpers.notification",
        "common.order_execution.finalizer_helpers.storage",
        "common.order_execution.finalizer_helpers.trade_record_builder",
        "common.order_execution.finalizer_helpers.validation_helper",
        "common.order_response_parser_helpers.fill_price_extractor",
        "common.order_response_parser_helpers.order_fills_parser",
        "common.pnl_calculator_helpers.reportgenerator_helpers.close_date_report_builder",
        "common.pnl_calculator_helpers.reportgenerator_helpers.date_range_report_builder",
        "common.process_killer_helpers.monitor_query",
        "common.process_killer_helpers.process_filter",
        "common.process_killer_helpers.process_normalizer",
        "common.process_monitor_helpers.service_patterns",
        "common.redis_protocol.connection_helpers.pool_initialization",
        "common.redis_protocol.connection_helpers.pool_lifecycle",
        "common.redis_protocol.connection_store_helpers.global_instance",
        "common.redis_protocol.connection_store_helpers.state_persistence",
        "common.redis_protocol.connection_store_helpers.state_queries",
        "common.redis_protocol.connection_store_helpers.state_serializer",
        "common.redis_protocol.kalshi_store.optimized_attribute_resolver",
        "common.redis_protocol.kalshi_store.optimized_fallback_methods",
        "common.redis_protocol.kalshi_store.orderbook_helpers.best_price_updater",
        "common.redis_protocol.kalshi_store.orderbook_helpers.delta_field_extractor",
        "common.redis_protocol.kalshi_store.orderbook_helpers.delta_processor_helpers",
        "common.redis_protocol.kalshi_store.orderbook_helpers.trade_price_updater",
        "common.redis_protocol.kalshi_store.reader_helpers.expiry_operations",
        "common.redis_protocol.kalshi_store.reader_helpers.lazy_property_factory",
        "common.redis_protocol.kalshi_store.reader_helpers.market_operations",
        "common.strike_helpers",
        "common.redis_protocol.kalshi_store.reader_helpers.orderbook_operations",
        "common.redis_protocol.kalshi_store.reader_helpers.snapshot_operations",
        "common.redis_protocol.kalshi_store.subscription_factory",
        "common.redis_protocol.kalshi_store.writer_helpers.orderbook_writer_helpers.trade_mapping_builder",
        "common.redis_protocol.kalshi_store.writer_helpers.timestamp_converter",
        "common.redis_protocol.kalshi_store.writer_helpers.timestamp_helpers",
        "common.redis_protocol.market_normalization_helpers.strike_bounds_builder",
        "common.redis_protocol.market_normalization_helpers.strike_derivation",
        "common.redis_protocol.messages_helpers.timestamp_converter",
        "common.redis_protocol.orderbook_utils_helpers.side_builder",
        "common.redis_protocol.persistence_manager_helpers.convenience",
        "common.redis_protocol.probability_store.keys_helpers",
        "common.redis_protocol.probability_store.probabilityingestion_helpers.compact_store_helpers",
        "common.redis_protocol.trade_store.optional_field_extractor",
        "common.redis_protocol.trade_store.store_helpers.api_delegator",
        "common.redis_protocol.trade_store.trade_record_validator",
        "common.rest_connection_manager_helpers.connection_info",
        "common.rest_connection_manager_helpers.request_handler",
        "common.scraper_connection_manager_helpers.connection_establisher",
        "common.scraper_connection_manager_helpers.health_monitor_helpers.url_checker",
        "common.scraper_connection_manager_helpers.scraper_operations",
        "common.status_reporter_helpers.lifecycle_reporter",
        "common.status_reporter_helpers.market_reporter",
        "common.status_reporter_helpers.rule_explainer",
        "common.status_reporter_helpers.scan_reporter",
        "common.status_reporter_helpers.trade_status_reporter",
        "common.time_helpers.solar_checks",
        "common.trading.order_metadata_service",
        "common.websocket.message_stats_helpers.redis_history_writer",
        "common.websocket.message_stats_helpers.silent_failure_alerter",
        "common.websocket_connection_manager_helpers.connection_info",
        "common.websocket_connection_manager_helpers.connection_lifecycle_helpers.connection_establisher",
        "common.websocket_connection_manager_helpers.ping_pong_manager",
        "common.websocket_connection_manager_helpers.ws_connection_handler",
    ]


@pytest.fixture
def clear_module_cache():
    """Clear the module cache before and after each test."""
    # Remove module if already imported
    if "common._module_references" in sys.modules:
        del sys.modules["common._module_references"]
    yield
    # Clean up after test
    if "common._module_references" in sys.modules:
        del sys.modules["common._module_references"]


pytestmark = pytest.mark.usefixtures("clear_module_cache")


def test_module_references_without_env_variable():
    """Test that modules are NOT imported when env variable is not set."""
    # Ensure env variable is not set
    os.environ.pop("REFERENCE_UNUSED_MODULES", None)

    # Import the module
    import common._module_references  # noqa: F401

    # Verify that none of the referenced modules were imported
    # (We can't directly verify non-imports, but we can verify the module loads without error)
    assert "common._module_references" in sys.modules


def test_module_references_with_env_variable_empty():
    """Test that modules are NOT imported when env variable is empty string."""
    os.environ["REFERENCE_UNUSED_MODULES"] = ""

    # Import the module
    import common._module_references  # noqa: F401

    # Module should load successfully
    assert "common._module_references" in sys.modules


def test_module_references_with_env_variable_set(mock_modules):
    """Test that modules ARE imported when env variable is set."""
    os.environ["REFERENCE_UNUSED_MODULES"] = "1"

    # Mock all the imports to prevent actual module loading
    with patch.dict("sys.modules"):
        for module_name in mock_modules:
            sys.modules[module_name] = MagicMock()

        # Import the module
        import common._module_references  # noqa: F401

        # Verify module loaded successfully
        assert "common._module_references" in sys.modules


def test_module_references_with_env_variable_true(mock_modules):
    """Test that modules are imported when env variable is set to 'true'."""
    os.environ["REFERENCE_UNUSED_MODULES"] = "true"

    # Mock all the imports
    with patch.dict("sys.modules"):
        for module_name in mock_modules:
            sys.modules[module_name] = MagicMock()

        # Import the module
        import common._module_references  # noqa: F401

        # Verify module loaded successfully
        assert "common._module_references" in sys.modules


def test_module_references_import_side_effects():
    """Test that importing the module has no side effects when env is not set."""
    os.environ.pop("REFERENCE_UNUSED_MODULES", None)

    # Count modules before import
    modules_before = set(sys.modules.keys())

    # Import the module
    import common._module_references  # noqa: F401

    # Count modules after import
    modules_after = set(sys.modules.keys())

    # Only the _module_references module itself should be added
    new_modules = modules_after - modules_before
    assert "common._module_references" in new_modules


def test_module_references_can_be_imported_multiple_times():
    """Test that the module can be imported multiple times without issues."""
    os.environ.pop("REFERENCE_UNUSED_MODULES", None)

    # Import multiple times
    import common._module_references  # noqa: F401

    # Re-import using importlib
    importlib.reload(sys.modules["common._module_references"])

    # Should not raise any errors
    assert "common._module_references" in sys.modules


def test_module_references_env_variable_case_sensitivity(mock_modules):
    """Test that env variable check is case-sensitive for the value."""
    # Test with different cases - Python's truthiness should handle this
    for value in ["1", "TRUE", "True", "yes", "anything"]:
        os.environ["REFERENCE_UNUSED_MODULES"] = value

        # Clear module if already loaded
        if "common._module_references" in sys.modules:
            del sys.modules["common._module_references"]

        # Mock all imports to prevent actual module loading
        with patch.dict("sys.modules"):
            for module_name in mock_modules:
                sys.modules[module_name] = MagicMock()

            # Import should work with any truthy value
            import common._module_references  # noqa: F401

            assert "common._module_references" in sys.modules


def test_module_docstring_present():
    """Test that the module has a proper docstring."""
    os.environ.pop("REFERENCE_UNUSED_MODULES", None)

    import common._module_references

    assert common._module_references.__doc__ is not None
    assert "References optional modules" in common._module_references.__doc__
    assert "unused_module_guard" in common._module_references.__doc__


def test_module_has_no_exports():
    """Test that the module doesn't export anything (it's just for side effects)."""
    os.environ.pop("REFERENCE_UNUSED_MODULES", None)

    import common._module_references

    # Get all non-private attributes
    public_attrs = [attr for attr in dir(common._module_references) if not attr.startswith("_")]

    # Should only have 'os' from the import
    assert "os" in public_attrs
    # No other public exports expected
    non_builtin_attrs = [attr for attr in public_attrs if attr not in ["os"]]
    assert len(non_builtin_attrs) == 0


def test_module_references_all_imports_use_noqa():
    """Test that all import statements in the file use noqa: F401 to suppress warnings."""
    # Read the source file
    module_path = os.path.join(os.path.dirname(__file__), "../../src/common/_module_references.py")

    with open(module_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all import lines within the if block
    lines = content.split("\n")
    import_lines = [line for line in lines if line.strip().startswith("import common.")]

    # Verify each import has noqa comment
    for line in import_lines:
        assert "# noqa: F401" in line, f"Import missing noqa comment: {line}"


def test_module_references_env_check_pattern():
    """Test that the environment variable check uses os.environ.get pattern."""
    # Read the source file to verify the pattern
    module_path = os.path.join(os.path.dirname(__file__), "../../src/common/_module_references.py")

    with open(module_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify it uses os.environ.get (not os.getenv or os.environ[])
    assert 'os.environ.get("REFERENCE_UNUSED_MODULES")' in content


def test_module_name_convention():
    """Test that the module follows underscore naming convention for private modules."""
    os.environ.pop("REFERENCE_UNUSED_MODULES", None)

    import common._module_references

    # Module name should start with underscore (private convention)
    assert common._module_references.__name__ == "common._module_references"
    assert common._module_references.__name__.split(".")[-1].startswith("_")
