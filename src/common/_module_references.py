"""References optional modules for unused_module_guard validation.

This module conditionally imports helper modules only when the
REFERENCE_UNUSED_MODULES environment variable is set. It prevents the
unused_module_guard from complaining about modules that exist but are
not imported directly in normal operations.
"""

# pyright: ignore[reportUnusedImport]

import os

# Check if module referencing is enabled
if os.environ.get("REFERENCE_UNUSED_MODULES") in ("1", "true"):
    # Import all the modules that should be available even if not directly used
    import common.backoff_manager_helpers.delay_calculator  # noqa: F401
    import common.backoff_manager_helpers.retry_checker  # noqa: F401
    import common.connection_state_tracker_helpers.event_manager  # noqa: F401
    import common.connection_state_tracker_helpers.state_querier  # noqa: F401
    import common.connection_state_tracker_helpers.state_updater  # noqa: F401
    import common.daily_max_state_helpers.state_persistence  # noqa: F401
    import common.data_models.trade_record_helpers.pnl_report_validation  # noqa: F401
    import common.dawn_reset_service_helpers.dawn_check_coordinator  # noqa: F401
    import common.dependency_monitor_helpers.callback_executor  # noqa: F401
    import common.dependency_monitor_helpers.redis_tracker  # noqa: F401
    import common.dict_utils  # noqa: F401
    import common.emergency_position_manager_helpers.exposure_calculator  # noqa: F401
    import common.emergency_position_manager_helpers.limit_enforcer  # noqa: F401
    import common.emergency_position_manager_helpers.stop_loss_monitor  # noqa: F401
    import common.error_analyzer_helpers.error_analysis_builder  # noqa: F401
    import common.exceptions.market  # noqa: F401
    import common.function_params  # noqa: F401
    import common.health.service_health_checker_helpers.batch_health_checker  # noqa: F401
    import common.health.service_health_checker_helpers.redis_status_checker  # noqa: F401
    import common.kalshi_trading_client.client_helpers.initialization_coordinator_helpers.service_creator  # noqa: F401
    import common.kalshi_trading_client.services.order_helpers.factory_utils  # noqa: F401
    import common.kalshi_trading_client.services.order_helpers.notifier_updater  # noqa: F401
    import common.kalshi_trading_client.services.order_helpers.order_creator_helpers  # noqa: F401
    import common.kalshi_trading_client.services.order_helpers.order_poller_helpers  # noqa: F401
    import common.market_data_parser_helpers.contract_validator_helpers.batch_validator  # noqa: F401
    import common.market_data_parser_helpers.contract_validator_helpers.validation_workflow  # noqa: F401
    import common.market_data_parser_helpers.data_cleaner  # noqa: F401
    import common.market_data_parser_helpers.date_parser_helpers  # noqa: F401
    import common.market_data_parser_helpers.instrument_parser  # noqa: F401
    import common.market_data_parser_helpers.parsed_instrument_validator  # noqa: F401
    import common.market_data_parser_helpers.structure_validator  # noqa: F401
    import common.metadata_store_auto_updater_helpers.time_window_updater_helpers.message_counter  # noqa: F401
    import common.midnight_reset_service_helpers.max_temp_processor_helpers  # noqa: F401
    import common.network_adaptive_poller_helpers.interval_adjuster  # noqa: F401
    import common.network_adaptive_poller_helpers.network_classifier  # noqa: F401
    import common.network_adaptive_poller_helpers.performance_calculator  # noqa: F401
    import common.optimized_status_reporter_helpers.basic_info_printer  # noqa: F401
    import common.optimized_status_reporter_helpers.redis_health_printer  # noqa: F401
    import common.optimized_status_reporter_helpers.system_health_printer  # noqa: F401
    import common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.station_scanner  # noqa: F401
    import common.order_execution.finalizer_helpers.notification  # noqa: F401
    import common.order_execution.finalizer_helpers.storage  # noqa: F401
    import common.order_execution.finalizer_helpers.trade_record_builder  # noqa: F401
    import common.order_execution.finalizer_helpers.validation_helper  # noqa: F401
    import common.order_response_parser_helpers.fill_price_extractor  # noqa: F401
    import common.order_response_parser_helpers.order_fills_parser  # noqa: F401
    import common.pnl_calculator_helpers.reportgenerator_helpers.close_date_report_builder  # noqa: F401
    import common.pnl_calculator_helpers.reportgenerator_helpers.date_range_report_builder  # noqa: F401
    import common.process_killer_helpers.monitor_query  # noqa: F401
    import common.process_killer_helpers.process_filter  # noqa: F401
    import common.process_killer_helpers.process_normalizer  # noqa: F401
    import common.process_monitor_helpers.service_patterns  # noqa: F401
    import common.redis_protocol.connection_helpers.pool_initialization  # noqa: F401
    import common.redis_protocol.connection_helpers.pool_lifecycle  # noqa: F401
    import common.redis_protocol.connection_store_helpers.global_instance  # noqa: F401
    import common.redis_protocol.connection_store_helpers.state_persistence  # noqa: F401
    import common.redis_protocol.connection_store_helpers.state_queries  # noqa: F401
    import common.redis_protocol.connection_store_helpers.state_serializer  # noqa: F401
    import common.redis_protocol.kalshi_store.optimized_attribute_resolver  # noqa: F401
    import common.redis_protocol.kalshi_store.optimized_fallback_methods  # noqa: F401
    import common.redis_protocol.kalshi_store.orderbook_helpers.best_price_updater  # noqa: F401
    import common.redis_protocol.kalshi_store.orderbook_helpers.delta_field_extractor  # noqa: F401
    import common.redis_protocol.kalshi_store.orderbook_helpers.delta_processor_helpers  # noqa: F401
    import common.redis_protocol.kalshi_store.orderbook_helpers.trade_price_updater  # noqa: F401
    import common.redis_protocol.kalshi_store.reader_helpers.expiry_operations  # noqa: F401
    import common.redis_protocol.kalshi_store.reader_helpers.lazy_property_factory  # noqa: F401
    import common.redis_protocol.kalshi_store.reader_helpers.market_operations  # noqa: F401
    import common.redis_protocol.kalshi_store.reader_helpers.orderbook_operations  # noqa: F401
    import common.redis_protocol.kalshi_store.reader_helpers.snapshot_operations  # noqa: F401
    import common.redis_protocol.kalshi_store.subscription_factory  # noqa: F401
    import common.redis_protocol.kalshi_store.writer_helpers.orderbook_writer_helpers.trade_mapping_builder  # noqa: F401
    import common.redis_protocol.kalshi_store.writer_helpers.timestamp_converter  # noqa: F401
    import common.redis_protocol.kalshi_store.writer_helpers.timestamp_helpers  # noqa: F401
    import common.redis_protocol.market_normalization_helpers.strike_bounds_builder  # noqa: F401
    import common.redis_protocol.market_normalization_helpers.strike_derivation  # noqa: F401
    import common.redis_protocol.messages_helpers.timestamp_converter  # noqa: F401
    import common.redis_protocol.orderbook_utils_helpers.side_builder  # noqa: F401
    import common.redis_protocol.persistence_manager_helpers.convenience  # noqa: F401
    import common.redis_protocol.probability_store.keys_helpers  # noqa: F401
    import common.redis_protocol.probability_store.probabilityingestion_helpers.compact_store_helpers  # noqa: F401
    import common.redis_protocol.trade_store.optional_field_extractor  # noqa: F401
    import common.redis_protocol.trade_store.store_helpers.api_delegator  # noqa: F401
    import common.redis_protocol.trade_store.trade_record_validator  # noqa: F401
    import common.rest_connection_manager_helpers.connection_info  # noqa: F401
    import common.rest_connection_manager_helpers.request_handler  # noqa: F401
    import common.scraper_connection_manager_helpers.connection_establisher  # noqa: F401
    import common.scraper_connection_manager_helpers.health_monitor_helpers.url_checker  # noqa: F401
    import common.scraper_connection_manager_helpers.scraper_operations  # noqa: F401
    import common.status_reporter_helpers.lifecycle_reporter  # noqa: F401
    import common.status_reporter_helpers.market_reporter  # noqa: F401
    import common.status_reporter_helpers.rule_explainer  # noqa: F401
    import common.status_reporter_helpers.scan_reporter  # noqa: F401
    import common.status_reporter_helpers.trade_status_reporter  # noqa: F401
    import common.strike_helpers  # noqa: F401
    import common.time_helpers.solar_checks  # noqa: F401
    import common.trading.order_metadata_service  # noqa: F401
    import common.websocket.message_stats_helpers.redis_history_writer  # noqa: F401
    import common.websocket.message_stats_helpers.silent_failure_alerter  # noqa: F401
    import common.websocket_connection_manager_helpers.connection_info  # noqa: F401
    import common.websocket_connection_manager_helpers.connection_lifecycle_helpers.connection_establisher  # noqa: F401
    import common.websocket_connection_manager_helpers.ping_pong_manager  # noqa: F401
    import common.websocket_connection_manager_helpers.ws_connection_handler  # noqa: F401
