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
- [x] Added `common.network_errors` module (commit 0df5f99)
- [x] Added `common.time_helpers.time_parsing` module (commit 0df5f99)
- [x] Fixed `src.kalshi.api` imports -> `common.kalshi_api` (commit 4e20b30a)
- [x] Fixed `src.kalshi.api_helpers` imports -> `common.kalshi_api` (commit 4e20b30a)

### CI Status

| Repo | Tests Collected | Errors | Status |
|------|-----------------|--------|--------|
| common | 6303 | 4 | ✅ (cross-repo imports expected) |
| monitor | 9906 | 0 | ✅ |

### Pre-existing Issues (Not from migration)
These exist but are separate from the migration work:
- `redis_protocol/config.py` - Undefined variables in `__all__`
- `tracker_pricing.py` - Imports from `.errors` which doesn't exist
- `daily_max_state.py` - `cli_temp_f` undefined in `__all__`

### Cross-Repo Import Warnings (Expected)
These appear when running CI on common repo without full PYTHONPATH:
- `src.weather.settings` in metrics_section_printer.py
- `src.weather.temperature_converter` in daily_max_state.py
- `src.weather.config_loader` in config/weather.py
- `src.monitor.pnl_reporter` in chart_manager.py
- `src.monitor.settings` in alerter.py
- `src.pdf.utils.validation_helpers` in crypto_filter_validator.py
- `src.pdf.utils.gp_surface_store` in price_path_calculator.py

## Commits Summary

### common repo
1. `524b73c` - Move trade_visualizer from monitor to common
2. `0df5f99` - Add missing common modules for monitor migration

### monitor repo
1. `afbd344a` - Convert trade_visualizer to re-export from common
2. `4e20b30a` - Fix kalshi API imports and update to common modules

## Next Steps
1. Push changes to remote branches
2. Verify all 6 service repos work with the new common modules
3. Run full CI pipeline in GitHub Actions
