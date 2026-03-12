# Common

**Shared Python library for a multi-repo quantitative trading system targeting cryptocurrency options arbitrage and weather-based prediction market trading.**

## Overview

Common provides the foundational utilities, data models, Redis protocol layer, and service infrastructure used by every repository in the trading system. All inter-service communication flows through Redis, and this library defines the canonical schemas, connection pools, retry logic, and stream primitives that make that possible.

## Quick Start

### Prerequisites

- Python 3.12+
- Redis 7.0+
- `ci_shared` repository cloned to `~/projects/ci_shared`

### Installation

```bash
# Editable install (recommended for development)
pip install -e ~/projects/common

# Or add to PYTHONPATH
export PYTHONPATH="$HOME/projects/common/src:$PYTHONPATH"
```

### Running CI

```bash
# Full CI pipeline
make check

# Individual steps
make format    # ruff --fix
make type      # pyright --warnings
make lint      # pylint
make test      # pytest with 80% coverage threshold

# CI automation loop
python -m ci_tools.ci --model claude-sonnet-4-6
```

### Running Tests

```bash
pytest tests/ --cov=src --cov-fail-under=80 --strict-markers --cov-report=term -W error
```

## Architecture

### Package Structure

| Package | Description |
|---------|-------------|
| `redis_protocol/` | Core Redis data layer: connection pools, retry clients, market stores, streams, persistence, trade storage |
| `redis_protocol/kalshi_store/` | Kalshi market data in Redis: reader/writer, event-market index, orderbook, subscriptions, cleanup |
| `redis_protocol/streams/` | Redis Streams infrastructure: publisher (`stream_publish`), subscriber (`RedisStreamSubscriber`), consumer groups, message decoding |
| `redis_protocol/probability_store/` | PDF probability data storage: ingestion, retrieval, codec, pipeline, verification |
| `redis_protocol/trade_store/` | Trade record storage: PnL computation, aggregations, codec, metadata |
| `redis_protocol/optimized_market_store_helpers/` | Deribit instrument fetching, spot prices, market data retrieval |
| `redis_schema/` | Canonical Redis key schemas: `kalshi`, `deribit`, `markets`, `weather`, `analytics`, `trades`, `operations` namespaces |
| `kalshi_api/` | Kalshi REST API client: authentication, session management, order/portfolio operations, request building |
| `kalshi_trading_client/` | High-level Kalshi trading client with API mixin bindings |
| `connection_manager.py` | Base WebSocket connection manager with reconnection, health monitoring, backoff |
| `base_connection_manager_helpers/` | Connection lifecycle, retry logic, metrics tracking, status reporting for WebSocket managers |
| `websocket/` | WebSocket utilities: connection health monitor, subscription manager, sequence validation, message stats |
| `websocket_connection_manager_helpers/` | WebSocket-specific connection lifecycle and health monitoring |
| `scraper_connection_manager.py` | HTTP scraper connection manager with session management and content validation |
| `monitoring/` | Process lifecycle types: `ProcessStatus` enum, `ProcessInfo` dataclass |
| `health/` | Health check infrastructure: aggregator, log activity monitor, process health monitor, service health checker |
| `service_lifecycle/` | `StatusReporterMixin` -- standardized service status reporting to Redis (adopted by all services) |
| `service_events/` | Service event publishing to Redis streams |
| `data_models/` | Shared domain models: `Instrument`, `MarketData`, `TradeRecord`, `TradingSignal`, `ModelState` |
| `data_conversion/` | Price data conversion utilities (micro-price converter) |
| `alerter.py` / `alerter_helpers/` | Alert dispatching with suppression management and price validation tracking |
| `alerting/` | Alert models and types |
| `config/` | Runtime configuration, Redis schema config, weather config, shared settings, error definitions |
| `config_loader.py` | JSON configuration file loader |
| `constants.py` | Trading constants: price bounds, algo names, precision thresholds, HTTP codes, timeouts |
| `llm_extractor/` | Anthropic LLM client: prompt management, response parsing, cost tracking |
| `market_filters/` | Market filtering rules for Kalshi and Deribit instruments |
| `order_execution/` | Order execution workflow: polling, finalization |
| `order_response_parser.py` | Kalshi order response parsing and exception handling |
| `trading/` | Trading utilities: order metadata, order payloads, polling workflow, trade store management, weather station logic |
| `validation/` | Data integrity validation, Kalshi price validation, required field checks |
| `weather_services/` | Weather market repository and trading rule engine |
| `weather_history_tracker_helpers/` | Weather observation recording and statistics retrieval |
| `time_helpers/` | Expiry parsing/matching/conversion, timezone handling, timestamp parsing, location-aware time |
| `time_utils/` | Solar/twilight calculations, local time utilities |
| `utils/` | General utilities: dict helpers, distributed locking, formatting, HTTP helpers, numeric/pricing/temperature conversions |
| `session_tracker.py` / `session_tracker_helpers/` | WebSocket session lifecycle tracking, cleanup, GC handling |
| `backoff_manager/` | Exponential backoff state management for retry logic |
| `rate_limiter.py` | Rate limiting with exponential backoff (used by Kalshi API clients) |
| `error_analyzer.py` / `error_analyzer_helpers/` | Error classification, analysis, notification, and recovery reporting |
| `process_killer.py` / `process_killer_helpers/` | Process discovery, normalization, and termination |
| `history_tracker.py` | Generic history tracking for time-series data |
| `strike_helpers.py` | Strike price mapping and derivation utilities |
| `pdf_configuration.py` | Canonical PDF pipeline configuration (imported by pdf and cfb repos) |
| `persistence.py` | Data persistence utilities |
| `network_errors.py` | Network error classification |
| `connection_config.py` / `connectionconfig_helpers/` | Service connection configuration loading and building |
| `connection_state_tracker.py` / `connection_state_tracker_helpers/` | Connection state management, event handling, state queries |

### Key Abstractions

#### StatusReporterMixin

Standardized mixin adopted by all services (poly, pdf, signals, weather, web) for reporting service status to Redis. Provides heartbeat publishing, uptime tracking, and status key management via `ops:status:<service>`.

```python
from common.service_lifecycle import StatusReporterMixin

class MyService(StatusReporterMixin):
    def __init__(self, redis_client):
        StatusReporterMixin.__init__(self, "my_service", redis_client)
```

#### RetryRedisClient

Redis client wrapper with automatic operation-level retry and exponential backoff. Includes mixins for hash, sorted set, collection, and stream operations. Wraps both regular commands and pipelines.

```python
from common.redis_protocol.retry_client import RetryRedisClient

client = RetryRedisClient(redis_client, policy=RedisRetryPolicy())
```

#### Redis Connection Pools

Unified connection pool management with async/sync support, exponential backoff on connection drops, and configurable pool sizes. Configuration loaded from `config/redis_config.json`.

```python
from common.redis_protocol.connection import get_redis_connection, get_sync_redis_client
```

#### Redis Streams

Persistent message delivery infrastructure replacing pub/sub for critical data flows.

| Stream | Purpose |
|--------|---------|
| `stream:algo_signal` | Signal algorithm outputs |
| `stream:market_event_updates` | Market data change notifications |
| `stream:close_positions` | Position close commands |
| `stream:service_events` | Service lifecycle events |
| `stream:trade_events` | Trade execution events |
| `stream:deribit_market` | Deribit market updates |
| `stream:poly_market` | Polymarket data updates |

```python
from common.redis_protocol.streams import stream_publish, RedisStreamSubscriber, ensure_consumer_group
```

#### Redis Key Schema

All Redis keys follow structured namespaces defined in `redis_schema/`:

- `markets:kalshi:<category>:<ticker>` -- Live Kalshi market quotes
- `markets:deribit:<type>:<currency>[:<expiry>:<strike>:<kind>]` -- Deribit instruments
- `analytics:pdf:<currency>:surface:*` -- Theoretical option prices
- `weather:station:<ICAO>` -- Latest METAR observations
- `trades:record:<date>:<order_id>` -- Trade execution records
- `ops:status:<service>` -- Service health status

## Configuration

Configuration files in `config/`:

| File | Purpose |
|------|---------|
| `redis_config.json` | Redis connection settings (host, port, pool sizes, timeouts) |
| `redis_schema.json` | Redis key namespace definitions |
| `streams_config.json` | Stream names, consumer groups, maxlen settings |
| `kalshi_constants.json` | Kalshi API endpoints, rate limits, fee schedules |
| `common_constants.json` | Shared trading constants |
| `stations.json` | Weather station ICAO codes and metadata |
| `metar_data_sources.json` | METAR/ASOS data source configuration |
| `weather_precision_settings.json` | Weather measurement precision thresholds |
| `weather_station_precision.json` | Per-station precision overrides |
| `pdf_parameters.json` | PDF pipeline hyperparameters |
| `pdf_parameters.optimized.BTC.json` | Optimized BTC-specific PDF parameters |
| `pnl_config.json` | PnL calculation settings |
| `monitor_config.json` | Service definitions for process management |
| `process_management_config.json` | Process lifecycle configuration |
| `trade_analyzer_config.json` | Trade analysis settings |
| `validation_constants.json` | Data validation thresholds |
| `websocket_config.json` | WebSocket connection parameters |
| `test_config.json` / `test_constants.json` | Test environment configuration |
| `exception_messages.json` | Standardized error message templates |

## Dependent Repositories

Every repository in the trading system depends on common:

| Repo | Key Imports |
|------|-------------|
| **monitor** | `redis_protocol`, `health`, `monitoring`, `service_events`, `config_loader`, `constants`, `kalshi_api`, `market_filters`, `strike_helpers` |
| **kalshi** | `kalshi_api`, `connection_manager`, `redis_protocol/kalshi_store`, `session_tracker`, `websocket` |
| **deribit** | `connection_manager`, `redis_protocol/optimized_market_store`, `websocket`, `data_models` |
| **poly** | `redis_protocol`, `service_lifecycle`, `kalshi_api`, `market_filters` |
| **signals** | `redis_protocol/streams`, `data_models`, `service_lifecycle`, `strike_helpers` |
| **weather** | `weather_services`, `config_loader`, `connection_config`, `history_tracker`, `service_lifecycle`, `network_errors` |
| **pdf** | `pdf_configuration`, `redis_protocol/probability_store`, `service_lifecycle`, `data_models`, `orderbook_utils` |
| **tracker** | `redis_protocol/streams`, `redis_protocol/trade_store`, `trading`, `constants`, `order_execution`, `kalshi_api` |
| **cfb** | `pdf_configuration`, `scraper_connection_manager`, `network_errors`, `service_lifecycle` |
| **api** | `redis_protocol`, `kalshi_api`, `data_models`, `trade_hash` |

## CI Pipeline

Runs via `make check` (delegates to `scripts/ci.sh`):

`codespell` -> `vulture` -> `deptry` -> `gitleaks` -> `bandit_wrapper` -> `safety scan` -> `ruff --fix` -> `pyright --warnings` -> `pylint` -> `pytest` -> `coverage_guard` -> `compileall`

Structural limits: classes <=150 lines, functions <=80, modules <=600, cyclomatic <=10, cognitive <=15, inheritance depth <=2.

PYTHONPATH must include `~/projects/ci_shared`.

## License

Private -- All rights reserved.
