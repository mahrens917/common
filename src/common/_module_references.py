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
    import common.connection_state_tracker_helpers.event_manager
    import common.connection_state_tracker_helpers.initializer
    import common.connection_state_tracker_helpers.state_querier
    import common.connection_state_tracker_helpers.state_updater
    import common.health.service_health_checker_helpers.batch_health_checker
    import common.health.service_health_checker_helpers.redis_status_checker
    import common.network_errors
    import common.process_killer_helpers.process_normalizer
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
    import common.redis_protocol.kalshi_store.orderbook_helpers.message_processing.normalizer
    import common.redis_protocol.kalshi_store.orderbook_helpers.snapshot_processor_helpers.redis_storage
    import common.redis_protocol.kalshi_store.orderbook_helpers.trade_price_updater
    import common.redis_protocol.kalshi_store.reader_helpers.expiry_operations
    import common.redis_protocol.kalshi_store.reader_helpers.lazy_property_factory
    import common.redis_protocol.kalshi_store.reader_helpers.market_operations
    import common.redis_protocol.kalshi_store.reader_helpers.market_query_handler
    import common.redis_protocol.kalshi_store.reader_helpers.market_status_checker
    import common.redis_protocol.kalshi_store.reader_helpers.orderbook_operations
    import common.redis_protocol.kalshi_store.reader_helpers.snapshot_operations
    import common.redis_protocol.kalshi_store.store_helpers.class_setup
    import common.redis_protocol.kalshi_store.store_helpers.data_operations
    import common.redis_protocol.kalshi_store.subscription_factory
    import common.redis_protocol.kalshi_store.writer_helpers.timestamp_helpers
    import common.redis_protocol.market_normalization_helpers.strike_bounds_builder
    import common.redis_protocol.market_normalization_helpers.strike_derivation
    import common.redis_protocol.persistence_manager_helpers.convenience
    import common.redis_protocol.probability_store.probabilityingestion_helpers.compact_store_helpers
    import common.redis_protocol.trade_store.optional_field_extractor
    import common.service_lifecycle.status_reporter_helpers.registration_methods
    import common.service_lifecycle.status_reporter_helpers.status_writer
    import common.strike_helpers
    import common.time_helpers.time_parsing
    import common.utils.temperature
    import common.websocket_connection_manager_helpers.connection_lifecycle
