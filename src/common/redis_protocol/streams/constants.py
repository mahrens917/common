"""Redis Streams constants for persistent message delivery."""

from common.config_loader import load_config
from common.constants import VALID_ALGO_NAMES

_streams_config = load_config("streams_config.json", package="common")

# Stream names — split topology
EXCHANGE_EVENT_STREAM = "stream:exchange_events"
ALGO_EVENT_STREAM_PREFIX = "stream:algo_event"
CLOSE_POSITIONS_STREAM = "stream:close_positions"
DERIBIT_MARKET_STREAM = "stream:deribit_market_updates"
SERVICE_EVENTS_STREAM = "stream:service_events"
POLY_MARKET_STREAM = "stream:poly_market_updates"
TRADE_EVENTS_STREAM = "stream:trade_events"


def algo_event_stream(algo: str) -> str:
    """Return the per-algo event stream name, e.g. ``stream:algo_event:peak``."""
    return f"{ALGO_EVENT_STREAM_PREFIX}:{algo}"


ALL_ALGO_EVENT_STREAMS: tuple[str, ...] = tuple(algo_event_stream(a) for a in sorted(VALID_ALGO_NAMES))

# Consumer groups
TRACKER_CONSUMER_GROUP = "tracker"
MONITOR_CONSUMER_GROUP = "monitor"
MONITOR_MARKET_CONSUMER_GROUP = "monitor-market"
MONITOR_DERIBIT_CONSUMER_GROUP = "monitor-deribit"
MONITOR_PRICE_ALERT_DERIBIT_CONSUMER_GROUP = "monitor-price-alert-deribit"
SIGNALS_CLAUDE_CONSUMER_GROUP = "signals-claude"
SIGNALS_PEAK_CONSUMER_GROUP = "signals-peak"
SIGNALS_EDGE_CONSUMER_GROUP = "signals-edge"
SIGNALS_STRUCTURE_CONSUMER_GROUP = "signals-structure"
CROSSARB_CONSUMER_GROUP = "crossarb"
PDF_CONSUMER_GROUP = "pdf"

# Stream trimming — approximate maxlen to keep streams bounded
STREAM_DEFAULT_MAXLEN: int = _streams_config["default_maxlen"]

# Pending entry recovery — claim entries idle longer than this
PENDING_CLAIM_IDLE_MS: int = _streams_config["pending_claim_idle_ms"]

# XAUTOCLAIM returns (next_start_id, entries, deleted_ids) — need at least 2 elements
XAUTOCLAIM_MIN_RESULT_LENGTH = 2

__all__ = [
    "ALGO_EVENT_STREAM_PREFIX",
    "ALL_ALGO_EVENT_STREAMS",
    "CLOSE_POSITIONS_STREAM",
    "CROSSARB_CONSUMER_GROUP",
    "DERIBIT_MARKET_STREAM",
    "EXCHANGE_EVENT_STREAM",
    "PDF_CONSUMER_GROUP",
    "MONITOR_CONSUMER_GROUP",
    "MONITOR_DERIBIT_CONSUMER_GROUP",
    "MONITOR_MARKET_CONSUMER_GROUP",
    "MONITOR_PRICE_ALERT_DERIBIT_CONSUMER_GROUP",
    "PENDING_CLAIM_IDLE_MS",
    "POLY_MARKET_STREAM",
    "SERVICE_EVENTS_STREAM",
    "SIGNALS_CLAUDE_CONSUMER_GROUP",
    "SIGNALS_EDGE_CONSUMER_GROUP",
    "SIGNALS_PEAK_CONSUMER_GROUP",
    "SIGNALS_STRUCTURE_CONSUMER_GROUP",
    "STREAM_DEFAULT_MAXLEN",
    "TRACKER_CONSUMER_GROUP",
    "TRADE_EVENTS_STREAM",
    "XAUTOCLAIM_MIN_RESULT_LENGTH",
    "algo_event_stream",
]
