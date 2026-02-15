# Common Documentation

Shared Python utilities library used across multiple trading system repositories. Provides Kalshi API clients, Redis utilities, service lifecycle management, weather services, market data parsing, alerting, and connection management.

## Key References

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | Project overview, installation, and development setup |
| [CLAUDE.md](../CLAUDE.md) | Claude Code guide: CI pipeline, code hygiene, external dependencies |
| [src/common/README.md](../src/common/README.md) | Source package overview and module inventory |
| [src/common/CONSOLIDATION_PATTERNS.md](../src/common/CONSOLIDATION_PATTERNS.md) | Canonical code patterns reference |

## Core Modules

| Module | Responsibility |
|--------|---------------|
| `kalshi_api/` | Kalshi REST API client and authentication |
| `kalshi_ws/` | Kalshi WebSocket client (used by peak) |
| `kalshi_trading_client/` | Trade execution and order management |
| `redis_protocol/` | Redis pub/sub, streams, retry client |
| `redis_schema/` | Redis key schema and contracts |
| `weather_services/` | Weather data utilities and rule engine |
| `service_lifecycle/` | Service startup, shutdown, health reporting |
| `monitoring/` | Health checks, dependency monitoring, metrics |
| `alerting/` | Telegram alerts and notification routing |
| `market_data/` | Market data structures and parsing |
| `data_models/` | Shared data models and type definitions |
| `config/` | Configuration loading and validation |
