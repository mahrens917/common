# Monolith Breakup Migration Plan

## Overview
Breaking up the kalshi monolith into 6 service repos (cfb, deribit, kalshi, pdf, tracker, weather), a monitor repo, and a common repo for shared utilities.

## Current State (2024-12-20) - COMPLETE

### All Migration Work Completed ✅

#### Core Migration
- [x] PYTHONPATH fixes for namespace packages
- [x] Namespace package setup with `pkgutil.extend_path`
- [x] Config files setup across repos
- [x] `from __future__ import annotations` added to 135+ files for Python 3.8/3.9 compatibility
- [x] zoneinfo backports for Python 3.8 (`backports.zoneinfo`)
- [x] trade_visualizer moved from monitor to common
- [x] Monitor trade_visualizer files converted to re-export modules
- [x] Fixed `src.kalshi.api` imports -> `common.kalshi_api`
- [x] Fixed `src.kalshi.api_helpers` imports -> `common.kalshi_api`

#### Missing Modules Added
- [x] `common.network_errors` - `is_network_unreachable_error` function
- [x] `common.time_helpers.time_parsing` - `parse_time_utc` function
- [x] `common.errors` - `PricingValidationError` class

#### Cross-Repo Tests Moved & Fixed
- [x] `test_daily_max_state.py` → weather repo (depends on `src.weather`)
- [x] `test_weather_config_extended.py` → weather repo (fixed monkeypatch target)
- [x] `test_alert_sender.py` → monitor repo (fixed AlertSeverity import)
- [x] `test_silent_failure_alerter.py` → monitor repo (fixed Alerter patch target)

### CI Status - All Passing ✅

| Repo | Tests Collected | Errors | Status |
|------|-----------------|--------|--------|
| common | 6284 | 0 | ✅ |
| monitor | 9906 | 0 | ✅ |

### Service Repos Verified ✅
All 6 service repos tested with common imports:
- [x] kalshi - `common.kalshi_api`
- [x] weather - `common.network_errors`, `common.time_helpers.time_parsing`
- [x] deribit - `common.redis_utils`
- [x] cfb - `common.network_errors`
- [x] pdf - `common.config.redis_schema`
- [x] tracker - `common.redis_protocol.converters`

### Pylint False Positives (Not Bugs)
These are working code using `__getattr__` for lazy loading:
- `redis_protocol/config.py` - Lazy-loaded REDIS_* variables in `__all__`
- `daily_max_state.py` - Lazy-loaded `cli_temp_f` in `__all__`

## Commits Summary

### common repo
1. `524b73c` - Move trade_visualizer from monitor to common
2. `0df5f99` - Add missing common modules (network_errors, time_parsing)
3. `0786cc5` - Update MIGRATION_PLAN.md
4. `01c553d` - Add common/errors.py with PricingValidationError
5. `253c00a` - Move cross-repo dependent tests to their respective repos
6. `41f09b9` - Update MIGRATION_PLAN.md with test move details
7. `948e0f0` - Disable library-level websocket ping/pong

### monitor repo
1. `afbd344a` - Convert trade_visualizer to re-export from common
2. `4e20b30a` - Fix kalshi API imports and update to common modules
3. `0174f86f` - Add websocket tests from common repo
4. `c005ea1b` - Fix websocket test imports and patch targets

### weather repo
1. `fa7de83` - Add cross-repo tests from common repo
2. `5df8356` - Fix test_weather_config_extended.py monkeypatch target

## Migration Complete
All migration work has been completed and pushed to remote repositories.
