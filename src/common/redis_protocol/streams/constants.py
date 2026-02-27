"""Redis Streams constants for persistent message delivery."""

from common.config_loader import load_config

_streams_config = load_config("streams_config.json", package="common")

# Stream names
ALGO_SIGNAL_STREAM = "stream:algo_signal"
CLOSE_POSITIONS_STREAM = "stream:close_positions"
MARKET_EVENT_STREAM = "stream:market_event_updates"
SERVICE_EVENTS_STREAM = "stream:service_events"

# Consumer groups
TRACKER_CONSUMER_GROUP = "tracker"
MONITOR_CONSUMER_GROUP = "monitor"

# Stream trimming — approximate maxlen to keep streams bounded
STREAM_DEFAULT_MAXLEN: int = _streams_config["default_maxlen"]

# Pending entry recovery — claim entries idle longer than this
PENDING_CLAIM_IDLE_MS: int = _streams_config["pending_claim_idle_ms"]

# XAUTOCLAIM returns (next_start_id, entries, deleted_ids) — need at least 2 elements
XAUTOCLAIM_MIN_RESULT_LENGTH = 2

__all__ = [
    "ALGO_SIGNAL_STREAM",
    "CLOSE_POSITIONS_STREAM",
    "MARKET_EVENT_STREAM",
    "MONITOR_CONSUMER_GROUP",
    "PENDING_CLAIM_IDLE_MS",
    "SERVICE_EVENTS_STREAM",
    "STREAM_DEFAULT_MAXLEN",
    "TRACKER_CONSUMER_GROUP",
    "XAUTOCLAIM_MIN_RESULT_LENGTH",
]
