# Monolith Breakup Migration Plan

## Overview
Breaking up the kalshi monolith into 6 service repos (cfb, deribit, kalshi, pdf, tracker, weather), a monitor repo, and a common repo for shared utilities.

## Current State (2024-12-20)

### Completed
- [x] PYTHONPATH fixes for namespace packages
- [x] Namespace package setup with `pkgutil.extend_path`
- [x] Config files setup across repos
- [x] `from __future__ import annotations` added to 135+ files for Python 3.8/3.9 compatibility
- [x] zoneinfo backports for Python 3.8 (`backports.zoneinfo`)
- [x] trade_visualizer moved from monitor to common (commit 524b73c)
- [x] Monitor trade_visualizer files converted to re-export modules (commit afbd344a)
- [x] Fixed `health_snapshot_collector.py` import
- [x] Added `from __future__ import annotations` to `visualizer_manager.py`

### In Progress
1. **Fix remaining `src.kalshi.api` imports** - 45 files in monitor still use old import path
2. **Fix missing common modules** - Several modules referenced but don't exist

### Remaining Import Fixes (monitor repo)

#### src.kalshi.api -> common.kalshi_api (45 files)
Files still using `src.kalshi.api.client.KalshiClient` need updating to `common.kalshi_api.client.KalshiClient`:
- `src/kalshi/subscription_helpers/market_manager.py`
- `src/kalshi/subscription_helpers/initialization.py`
- `src/kalshi/notifications/notifier_helpers/notification_sender.py`
- `src/kalshi/notifications/trade_notifier_helpers/fills_data_processor.py`
- `src/pdf/utils/kalshi_metadata_primer.py`
- ... and 40 more files

#### Missing Common Modules (need to be created or imports fixed)
- `common.network_errors` - 29 imports, module doesn't exist
- `common.time_helpers.time_parsing` - 56 imports, module doesn't exist

### CI Status

| Repo | Tests Collected | Errors | Notes |
|------|-----------------|--------|-------|
| common | 6303 | 4 | Cross-repo imports (expected) |
| monitor | 7711 | 190 | Missing modules, old kalshi imports |

### Error Breakdown (monitor)
- 103 errors: `src.kalshi.api` - needs import update
- 56 errors: `common.time_helpers.time_parsing` - module missing
- 29 errors: `common.network_errors` - module missing
- 1 error: `src.kalshi.api_helpers` - needs import update

### Pre-existing Issues (Not from migration)
- `redis_protocol/config.py` - Undefined variables in `__all__`
- `tracker_pricing.py` - Imports from `.errors` which doesn't exist
- `daily_max_state.py` - `cli_temp_f` undefined in `__all__`

## Next Steps
1. **Fix src.kalshi.api imports** - Update 45 files to use common.kalshi_api
2. **Create missing modules or fix imports**:
   - `common.network_errors`
   - `common.time_helpers.time_parsing`
3. Run full CI on both repos
4. Push changes to remote branches
