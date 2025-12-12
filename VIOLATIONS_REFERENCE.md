# Policy Guard Violations Reference

**Total: 430 violations across 100+ files**

## Violations by Type

| Type | Count | Strategy | Examples |
|------|-------|----------|----------|
| Exception handler without re-raise | ~300 | Re-raise or Suppress | `alerter_factory.py:14`, `logging_config.py:59,73,147` |
| Suppresses exception with return | ~60 | Return None or Suppress | `async_helpers.py:25,31`, `dependency_aware_error_filter.py:88` |
| Suppresses exception with continue | ~40 | Collect errors or Suppress | `callback_runner.py:21`, `expiry_utils.py:155,216` |
| Suppresses exception with break | ~20 | Explicit control flow or Suppress | `monitoring_loop.py:57`, `memory_monitor_helpers/monitoring_loop.py:100` |
| Suppresses exception with pass | ~10 | Re-raise or Suppress | `logging_config.py:132,143`, `connection_pool_core.py:205` |

---

## Violations by Severity & Module

### CRITICAL (Tier 1) - Fix First
These affect core system functionality and startup.

#### `logging_config.py` - 7 violations
**Impact:** System initialization
**Issue:** Logging setup errors being suppressed
**Fix Strategy:** Re-raise all - logging failures should crash immediately

```python
# Current (line 59)
except Exception:
    logger = logging.getLogger(__name__)

# Fixed - Re-raise
except Exception as exc:
    raise InitializationError("Failed to configure logging") from exc
```

**Violations:**
- Line 35: suppresses exception with literal return
- Line 59: exception handler without re-raise
- Line 73: exception handler without re-raise
- Line 99: suppresses exception with continue
- Line 132: suppresses exception with pass
- Line 143: suppresses exception with pass
- Line 147: exception handler without re-raise

---

#### `connection_manager.py` - 1 violation
**Impact:** All client connections
**Issue:** Connection setup errors not propagated
**Fix Strategy:** Re-raise - connection failures must be visible

```python
# Line 146
except ConnectionError:
    logger.error("Failed to connect")
    # Add: raise
```

---

#### `redis_protocol/connection_pool_core.py` - 12 violations
**Impact:** Data storage layer
**Issue:** Connection pool errors with silent continues/passes
**Fix Strategy:** Collect errors, raise if all connections fail

```python
# Lines 205, 213, 215, 226, 245, 252, 290, 329
# Pattern: Connection retry logic with silent failures

# Fixed pattern:
failed_connections = []
for attempt in range(MAX_ATTEMPTS):
    try:
        return establish_connection()
    except ConnectionError as exc:
        failed_connections.append(exc)
        continue

if all_attempts_failed:
    raise PoolExhaustedError("All connection attempts failed", failed_connections)
```

---

#### `redis_protocol/kalshi_store/` - 30+ violations
**Impact:** Market data access
**Issue:** Defensive returns in critical data paths
**Fix Strategy:** Mix - return None for queries (data), re-raise for writes (integrity)

```python
# Example 1: Read operation (safe to return None)
# Line 40 (orderbook.py)
except KeyError:
    return None  # OK - data not available yet

# Example 2: Write operation (must re-raise)
# Line 259 (store_methods.py)
except RedisError as exc:
    raise DataIntegrityError("Failed to persist") from exc
```

**Key Lines to Fix:**
- `orderbook.py:40,109,116` - Read operations (OK to suppress)
- `store_methods.py:100,117,134,259,300` - Write operations (re-raise)
- `writer_helpers/orderbook_writer.py:38,41,61,66` - Critical writes
- `connection_helpers/retry_handler.py:105,107` - Retry logic

---

#### `metadata_store_auto_updater.py` - 8 violations
**Impact:** Market metadata updates
**Issue:** Batch update failures causing silent skips
**Fix Strategy:** Collect errors, report, but don't crash

```python
# Pattern: Batch update with partial failures
errors = []
for market_id in markets:
    try:
        update_market(market_id)
    except UpdateError as exc:
        errors.append((market_id, exc))
        continue

if errors:
    logger.warning("Failed to update %d markets", len(errors))
    # Don't raise - partial success is OK for metadata updates
```

**Violations:**
- Line 90: exception handler without re-raise
- Line 97: exception handler without re-raise
- Plus helpers: `batch_processor.py:42,54`, `initialization_manager.py:67,89,97`

---

### HIGH (Tier 2) - Fix Second
These affect significant features or background services.

#### `process_monitor.py` - 5 violations
**Impact:** Process monitoring background service
**Issue:** Monitoring loop errors being suppressed
**Fix Strategy:** Log and continue (monitoring is best-effort)

```python
# Line 144
except ProcessError as exc:
    logger.warning("Process check failed: %s", exc)
    # Current: handler doesn't re-raise, but should document why
    # Fixed: Add comment explaining why we continue
    continue  # Skip this process, check others
```

---

#### `market_lifecycle_monitor_helpers/` - 12 violations
**Impact:** Market state tracking
**Issue:** Multiple handlers with defensive returns
**Fix Strategy:** Return None for queries, re-raise for state changes

**Files:**
- `close_detector.py:54,80,104` - Re-raise (state critical)
- `expiry_checker.py:45,76` - Return None (query only)
- `settlement_fetcher.py:73` - Return None (optional data)
- `market_updater.py:44` - Re-raise (state change)
- `settlement_validator.py:52` - Re-raise (validation critical)

---

#### `emergency_position_manager.py` - 1 violation
**Impact:** Risk management
**Issue:** Position closure failures not propagated
**Fix Strategy:** Re-raise - position management must not fail silently

```python
# Line 105
except OrderError as exc:
    logger.error("Failed to close position")
    raise PositionClosureError("Emergency close failed") from exc
```

---

#### `error_analyzer.py` - 1 violation
**Impact:** Error analysis service
**Issue:** Analysis failures being suppressed
**Fix Strategy:** Log and continue (analysis is secondary)

```python
# Line 127
except AnalysisError as exc:
    logger.warning("Could not analyze error: %s", exc)
    continue  # Analysis failed, try next error
```

---

### MEDIUM (Tier 3) - Fix Third
These are utility/helper functions with defensive patterns.

#### `expiry_utils.py` - 3 violations
**Impact:** Date/time parsing
**Issue:** Parse failures returning None
**Fix Strategy:** Continue pattern (safe - bad dates skipped)

```python
# Lines 155, 216: continue on parse error
# Lines 236: return None on invalid date
# These are acceptable - returning None for optional data
```

Violations:
- Line 155: suppresses exception with continue
- Line 216: suppresses exception with continue
- Line 236: exception handler without re-raise

---

#### `async_helpers.py` - 2 violations
**Impact:** Async utilities
**Issue:** Timeout handling with defensive returns
**Fix Strategy:** Suppress pattern (timeouts are expected)

```python
# Lines 25, 31
# Pattern: Timeout is expected, return default
except asyncio.TimeoutError:
    return None  # OK - operation timed out as expected
```

---

#### `parsing_utils.py` - 2 violations
**Impact:** Data parsing
**Issue:** Parse failures returning None
**Fix Strategy:** Suppress pattern (bad data is expected)

```python
# Parse operations - safe to return None for invalid input
except (ValueError, TypeError):
    return None  # Input not parseable
```

---

#### Helper Modules (Low Impact)
**Pattern:** Defensive utilities with sensible defaults

Files with multiple similar violations (OK to suppress):
- `optimized_status_reporter_helpers/` (20+ return None violations)
  - These are status/reporting helpers - returning None is fine
  - Pattern: Try to get status, return None if unavailable

- `redis_protocol/kalshi_store/reader_helpers/` (25+ violations)
  - Read operations - returning None for missing data is correct

- `memory_monitor_helpers/` (6 violations)
  - Metrics collection - skip on error, continue monitoring

---

## File-by-File Fix Checklist

### Phase 1: Critical (Week 1)
- [ ] `logging_config.py` - Re-raise all (7)
- [ ] `connection_manager.py` - Re-raise (1)
- [ ] `redis_protocol/connection_pool_core.py` - Refactor retry logic (12)

### Phase 2: High Impact (Week 2-3)
- [ ] `redis_protocol/kalshi_store/` - Categorize read vs write (30+)
- [ ] `metadata_store_auto_updater.py` - Collect errors pattern (8)
- [ ] `process_monitor.py` - Add comments + suppress (5)
- [ ] `market_lifecycle_monitor_helpers/` - Mixed strategy (12)
- [ ] `emergency_position_manager.py` - Re-raise (1)

### Phase 3: Medium Impact (Week 4)
- [ ] `expiry_utils.py` - Suppress + document (3)
- [ ] `async_helpers.py` - Suppress + document (2)
- [ ] `parsing_utils.py` - Suppress + document (2)
- [ ] `dependency_aware_error_filter.py` - Mixed (4)
- [ ] `orderbook_utils.py` - Mixed (4)

### Phase 4: Utility Modules (Week 5-6)
- [ ] `optimized_status_reporter_helpers/` - Suppress all (20+)
- [ ] `redis_protocol/kalshi_store/reader_helpers/` - Suppress all (25+)
- [ ] `memory_monitor_helpers/` - Suppress all (6)
- [ ] Remaining helpers - Case by case

---

## Quick Reference: Which Strategy to Use

### For Connection/Init Failures
**Use:** Re-raise
**Reason:** System must not continue without working connections
**Pattern:**
```python
except ConnectionError as exc:
    raise ConnectionFailureError("Init failed") from exc
```

### For Data Read Operations
**Use:** Return None or suppress
**Reason:** Reading missing data is expected
**Pattern:**
```python
except KeyError:
    return None  # Data not available
```

### For Data Write Operations
**Use:** Re-raise
**Reason:** Write failures indicate data integrity risk
**Pattern:**
```python
except IOError as exc:
    raise DataWriteError("Persist failed") from exc
```

### For Batch Processing Loops
**Use:** Collect errors + continue
**Reason:** Process as much as possible, report failures
**Pattern:**
```python
errors = []
for item in items:
    try:
        process(item)
    except ProcessError as exc:
        errors.append(exc)

if errors:
    logger.warning("Processed with %d errors", len(errors))
```

### For Monitoring Loops
**Use:** Suppress + log
**Reason:** Monitoring is best-effort, shouldn't crash main program
**Pattern:**
```python
except MonitorError as exc:
    logger.warning("Monitor check failed: %s", exc)
    continue  # Check next item
```

### For Utility/Helper Functions
**Use:** Suppress if optional, re-raise if core
**Reason:** Context matters
**Pattern for optional:**
```python
except ValueError:
    return None  # Formatting not critical
```

**Pattern for core:**
```python
except ValueError as exc:
    raise ValidationError("Core validation failed") from exc
```

---

## Testing Your Fixes

For each module fixed, run:

```bash
# Unit tests
pytest tests/unit/<module_test> -v --tb=short

# Full module tests
pytest tests/ -k "<module_name>" -v

# Full CI validation
make check
```

**Success criteria:**
- All tests pass (6030/6030)
- Coverage maintained (≥95.22%)
- No new warnings in logs
- No regression in error handling

---

## Documentation Requirements

For each suppressed violation, add a comment:

```python
except SomeError:  # policy_guard: allow-silent-handler
    logger.info("This is expected: reason why suppression is safe")
    return None  # OR continue, OR break, OR pass
```

Examples:

```python
# ✅ Good - explains why suppression is safe
except FileNotFoundError:  # policy_guard: allow-silent-handler
    logger.debug("Optional config file not found, using defaults")
    return DEFAULT_CONFIG

# ✅ Good - safety is obvious from code context
except KeyError:  # policy_guard: allow-silent-handler
    # Data not yet available, return None
    return None

# ❌ Bad - no explanation
except ValueError:  # policy_guard: allow-silent-handler
    return None
```

---

## Quick Stats for Planning

**By Fix Effort:**
- Easy (suppress + comment): 150 violations - 1-2 weeks
- Medium (refactor logic): 150 violations - 2-3 weeks
- Hard (architectural change): 130 violations - 3-4 weeks

**By File Count:**
- 10 files with 10+ violations: 150 violations
- 30 files with 3-9 violations: 150 violations
- 60 files with 1-2 violations: 130 violations

**Recommended Team Approach:**
- 1 engineer, 6 weeks (part-time)
- 2 engineers, 3 weeks (full-time)
- 3 engineers, 2 weeks (coordinated)

---

## Questions to Ask When Fixing

For each violation, ask:

1. **Is this error expected and handled correctly?**
   - Yes → Suppress with comment
   - No → Re-raise or refactor

2. **Can the operation continue without this action?**
   - Yes (reads, optional) → Return None / continue
   - No (writes, critical) → Re-raise

3. **Is failure information important?**
   - Yes → Collect errors and report
   - No → Simple continue/return None

4. **Would losing this data be a problem?**
   - Yes (writes, state) → Re-raise
   - No (reads, status) → Return None / suppress

5. **Should the user know this failed?**
   - Yes → Log warning and re-raise
   - No (internal) → Log debug and suppress
