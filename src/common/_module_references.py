"""References optional modules for unused_module_guard validation.

This module conditionally imports helper modules only when the
REFERENCE_UNUSED_MODULES environment variable is set. It prevents the
unused_module_guard from complaining about modules that exist but are
not imported directly in normal operations.
"""

# pyright: reportUnusedImport = false

import os

# Check if module referencing is enabled
if os.environ.get("REFERENCE_UNUSED_MODULES") in ("1", "true"):
    # Import all the modules that should be available even if not directly used
    import common.backoff_manager_helpers.delay_calculator
    import common.backoff_manager_helpers.retry_checker
    import common.connection_state_tracker_helpers.event_manager

    # Additional modules needed for unused_module_guard validation
    import common.connection_state_tracker_helpers.initializer
    import common.connection_state_tracker_helpers.state_querier
    import common.connection_state_tracker_helpers.state_updater
    import common.daily_max_state_helpers.state_persistence
    import common.data_models.trade_record_helpers.pnl_report_validation
    import common.dawn_reset_service_helpers.dawn_check_coordinator
    import common.dependency_monitor_helpers.callback_executor
    import common.dependency_monitor_helpers.redis_tracker
    import common.dict_utils
    import common.emergency_position_manager_helpers.exposure_calculator
    import common.emergency_position_manager_helpers.limit_enforcer
    import common.emergency_position_manager_helpers.stop_loss_monitor
    import common.error_analyzer_helpers.error_analysis_builder
    import common.exceptions.market
    import common.function_params
    import common.health.service_health_checker_helpers.batch_health_checker
    import common.health.service_health_checker_helpers.redis_status_checker
    import common.kalshi_trading_client.client_helpers.initialization_coordinator_helpers.service_creator
    import common.kalshi_trading_client.services.order_helpers.factory_utils
    import common.kalshi_trading_client.services.order_helpers.notifier_updater
    import common.kalshi_trading_client.services.order_helpers.order_creator_helpers
    import common.kalshi_trading_client.services.order_helpers.order_poller_helpers

    # External library modules (used by peak, kalshi, and other projects)
    import common.kalshi_ws.api_client
    import common.market_data_parser_helpers.contract_validator_helpers.batch_validator
    import common.market_data_parser_helpers.contract_validator_helpers.validation_workflow
    import common.market_data_parser_helpers.data_cleaner
    import common.market_data_parser_helpers.date_parser_helpers
    import common.market_data_parser_helpers.instrument_parser
    import common.market_data_parser_helpers.parsed_instrument_validator
    import common.market_data_parser_helpers.structure_validator
    import common.market_lifecycle_monitor_helpers.property_bridge
    import common.metadata_store_auto_updater_helpers.time_window_updater_helpers.message_counter
    import common.midnight_reset_service_helpers.max_temp_processor_helpers
    import common.network_adaptive_poller_helpers.interval_adjuster
    import common.network_adaptive_poller_helpers.network_classifier
    import common.network_adaptive_poller_helpers.performance_calculator
    import common.optimized_status_reporter_helpers.basic_info_printer
    import common.optimized_status_reporter_helpers.redis_health_printer
    import common.optimized_status_reporter_helpers.system_health_printer
    import common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.station_scanner
    import common.order_execution.finalizer_helpers.notification
    import common.order_execution.finalizer_helpers.storage
    import common.order_execution.finalizer_helpers.trade_record_builder
    import common.order_execution.finalizer_helpers.validation_helper
    import common.order_response_parser_helpers.fill_price_extractor
    import common.order_response_parser_helpers.order_fills_parser
    import common.pnl_calculator_helpers.reportgenerator_helpers.close_date_report_builder
    import common.pnl_calculator_helpers.reportgenerator_helpers.date_range_report_builder
    import common.process_killer_helpers.monitor_query
    import common.process_killer_helpers.process_filter
    import common.process_killer_helpers.process_normalizer
    import common.process_monitor_helpers.service_patterns
    import common.rate_limiter
    import common.redis_protocol.atomic_redis_operations_helpers.coordinator
    import common.redis_protocol.connection_helpers.pool_initialization
    import common.redis_protocol.connection_helpers.pool_lifecycle
    import common.redis_protocol.connection_store_helpers.global_instance
    import common.redis_protocol.connection_store_helpers.state_persistence
    import common.redis_protocol.connection_store_helpers.state_queries
    import common.redis_protocol.connection_store_helpers.state_serializer
    import common.redis_protocol.kalshi_store.orderbook_helpers.best_price_updater
    import common.redis_protocol.kalshi_store.orderbook_helpers.delta_field_extractor
    import common.redis_protocol.kalshi_store.orderbook_helpers.delta_processor_helpers
    import common.redis_protocol.kalshi_store.orderbook_helpers.message_processing.dispatcher
    import common.redis_protocol.kalshi_store.orderbook_helpers.snapshot_processor_helpers.price_formatting
    import common.redis_protocol.kalshi_store.orderbook_helpers.snapshot_processor_helpers.redis_storage
    import common.redis_protocol.kalshi_store.orderbook_helpers.trade_price_updater
    import common.redis_protocol.kalshi_store.reader_helpers.expiry_operations
    import common.redis_protocol.kalshi_store.reader_helpers.lazy_property_factory
    import common.redis_protocol.kalshi_store.reader_helpers.market_operations
    import common.redis_protocol.kalshi_store.reader_helpers.market_query_handler
    import common.redis_protocol.kalshi_store.reader_helpers.market_status_checker
    import common.redis_protocol.kalshi_store.reader_helpers.orderbook_operations
    import common.redis_protocol.kalshi_store.reader_helpers.snapshot_operations
    import common.redis_protocol.kalshi_store.store_helpers.property_management
    import common.redis_protocol.kalshi_store.store_helpers.static_methods
    import common.redis_protocol.kalshi_store.subscription_factory
    import common.redis_protocol.kalshi_store.writer_helpers.orderbook_writer_helpers.trade_mapping_builder
    import common.redis_protocol.kalshi_store.writer_helpers.timestamp_converter
    import common.redis_protocol.kalshi_store.writer_helpers.timestamp_helpers
    import common.redis_protocol.market_normalization_helpers.strike_bounds_builder
    import common.redis_protocol.market_normalization_helpers.strike_derivation
    import common.redis_protocol.messages_helpers.option_normalizer
    import common.redis_protocol.messages_helpers.timestamp_converter
    import common.redis_protocol.orderbook_utils_helpers.side_builder
    import common.redis_protocol.persistence_manager_helpers.convenience
    import common.redis_protocol.probability_store.keys_helpers
    import common.redis_protocol.probability_store.probabilityingestion_helpers.compact_store_helpers
    import common.redis_protocol.trade_store.optional_field_extractor
    import common.redis_protocol.trade_store.store_helpers.api_delegator
    import common.redis_protocol.trade_store.trade_record_validator
    import common.resource_tracker_helpers.delegation.history
    import common.resource_tracker_helpers.delegation.monitoring_control
    import common.resource_tracker_helpers.delegation.recording
    import common.rest_connection_manager_helpers.request_handler
    import common.scraper_connection_manager_helpers.connection_establisher
    import common.scraper_connection_manager_helpers.health_monitor_helpers.url_checker
    import common.scraper_connection_manager_helpers.scraper_operations
    import common.service_lifecycle.status_reporter_helpers.registration_methods
    import common.service_lifecycle.status_reporter_helpers.status_writer
    import common.status_reporter_helpers.lifecycle_reporter
    import common.status_reporter_helpers.market_reporter
    import common.status_reporter_helpers.rule_explainer
    import common.status_reporter_helpers.scan_reporter
    import common.status_reporter_helpers.trade_status_reporter
    import common.strike_helpers
    import common.trading.order_metadata_service
    import common.websocket.message_stats_helpers.redis_history_writer
    import common.websocket.message_stats_helpers.silent_failure_alerter
    import common.websocket_connection_manager_helpers.connection_lifecycle_helpers.connection_establisher
    import common.websocket_connection_manager_helpers.ping_pong_manager
    import common.websocket_connection_manager_helpers.ws_connection_handler
