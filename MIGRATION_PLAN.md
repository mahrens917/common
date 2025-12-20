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
- [x] kalshi imports updated from `src.kalshi.api` to `common.kalshi_api`
- [x] trade_visualizer moved from monitor to common
- [x] Monitor trade_visualizer files converted to re-export modules

### Not Needed
- [ ] ~~optimized_history_metrics_recorder move~~ - Already uses TYPE_CHECKING guard, no runtime circular dependency

### In Progress
1. **Commit pending changes** - trade_visualizer move and related fixes
2. **Fix remaining CI issues in common repo**

### Pending CI Issues (common repo)

#### Import Fixes Needed
- [ ] `health_snapshot_collector.py` - Fixed `src.common.health_checker` -> `common.service_status`
- [ ] `visualizer_manager.py` - Added `from __future__ import annotations`

#### Cross-Repo Import Warnings (Expected)
These appear when running CI without full PYTHONPATH - not blocking:
- `src.weather.settings` in metrics_section_printer.py
- `src.monitor.pnl_reporter` in chart_manager.py
- `src.pdf.utils.validation_helpers` in crypto_filter_validator.py

#### Pre-existing Issues (Not from migration)
- `redis_protocol/config.py` - Undefined variables in `__all__` (REDIS_DB, REDIS_HOST, etc.)

### Repos Status

| Repo | CI Status | Notes |
|------|-----------|-------|
| common | In Progress | 6303 tests collecting, fixing remaining issues |
| monitor | Pending | Needs CI run after common stabilizes |
| kalshi | Unknown | Needs verification |
| deribit | Unknown | Needs verification |
| weather | Unknown | Needs verification |
| tracker | Unknown | Needs verification |
| pdf | Unknown | Needs verification |
| cfb | Unknown | Needs verification |

## Next Steps
1. Commit changes to common and monitor repos
2. Run full CI on common repo
3. Run full CI on monitor repo
4. Verify all 6 service repos still work
5. Push changes to remote branches
