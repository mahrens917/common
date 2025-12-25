# Real Examples from Codebase

Actual silent exception violations found in `/Users/mahrens917/projects/common/src/common/` with recommended fixes.

---

## Example 1: COMPLETELY_SILENT_PASS - logging_config.py:133

**Location:** `/Users/mahrens917/projects/common/src/common/logging_config.py:133`

**Current Code:**
```python
for handler in list(root_logger.handlers):
    try:
        handler.close()
    except OSError:
        pass  # ❌ Completely silent
```

**Problem:** No logging when handler cleanup fails. Could indicate file descriptor leak or permission issue.

**Fixed Code:**
```python
for handler in list(root_logger.handlers):
    try:
        handler.close()
    except OSError as e:
        logger.debug(f"Handler cleanup failed (may already be closed): {e}")
```

**Rationale:** Cleanup failures are often expected (handler already closed), but should be visible at debug level.

---

## Example 2: SILENT_RETURN_None - async_helpers.py:25

**Location:** `/Users/mahrens917/projects/common/src/common/async_helpers.py:25`

**Current Code:**
```python
def safely_schedule_coroutine(coro_or_factory):
    coro = _resolve_coroutine(coro_or_factory)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
        return None  # ❌ Silent return
```

**Problem:** RuntimeError is a programming error (no event loop), but it's silently suppressed.

**Fixed Code (Option 1 - If expected behavior):**
```python
def safely_schedule_coroutine(coro_or_factory):
    coro = _resolve_coroutine(coro_or_factory)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.debug("No running loop, executing coroutine synchronously")
        asyncio.run(coro)
        return None
```

**Fixed Code (Option 2 - If unexpected):**
```python
def safely_schedule_coroutine(coro_or_factory):
    coro = _resolve_coroutine(coro_or_factory)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.exception("No event loop running - this should not happen")
        raise
```

**Rationale:** RuntimeError is usually a programming error. If this is expected fallback behavior, it needs documentation and logging. If unexpected, should re-raise.

---

## Example 3: LOGS_exception_NO_RERAISE - process_monitor_mixins.py:32

**Location:** `/Users/mahrens917/projects/common/src/common/process_monitor_mixins.py:32`

**Current Code:**
```python
try:
    self._monitor_process()
except (RuntimeError, ValueError, OSError):
    logger.exception("Process monitoring failed")
    # ❌ No re-raise - caller continues as if nothing happened
```

**Problem:** Calls `logger.exception()` (which suggests unexpected error) but doesn't re-raise. If it's unexpected, caller should know. If expected, shouldn't use `logger.exception()`.

**Fixed Code (Option 1 - If unexpected):**
```python
try:
    self._monitor_process()
except (RuntimeError, ValueError, OSError):
    logger.exception("Process monitoring failed unexpectedly")
    raise  # Let caller handle this
```

**Fixed Code (Option 2 - If expected but wrong logging):**
```python
try:
    self._monitor_process()
except (RuntimeError, ValueError, OSError) as e:
    logger.warning(f"Process monitoring failed (process may have exited): {e}")
    return None
```

**Rationale:** `logger.exception()` implies "this shouldn't happen". If true, re-raise. If expected, use `logger.warning()`.

---

## Example 4: SILENT_RETURN_empty_collection - orderbook_utils.py:37

**Location:** `/Users/mahrens917/projects/common/src/common/orderbook_utils.py:37`

**Current Code:**
```python
def get_orderbook_data() -> list:
    try:
        return fetch_from_redis()
    except REDIS_ERRORS:
        return []  # ❌ Caller can't tell error from "no data"
```

**Problem:** Returns empty list on error. Caller can't distinguish "Redis failed" from "orderbook is empty".

**Fixed Code:**
```python
def get_orderbook_data() -> list | None:
    try:
        return fetch_from_redis()
    except REDIS_ERRORS as e:
        logger.warning(f"Failed to fetch orderbook from Redis: {e}")
        return None  # Caller checks: if data is None (error) vs if not data (empty)
```

**Rationale:**
- `None` means "error occurred, data unavailable"
- `[]` means "successfully fetched, orderbook is empty"
- Caller must handle both: `if data is None: handle_error()` vs `if not data: handle_empty()`

---

## Example 5: SILENT_CONTINUE - status_reporter.py:115

**Location:** `/Users/mahrens917/projects/common/src/common/status_reporter.py:115`

**Current Code:**
```python
for metric in metrics:
    try:
        process_metric(metric)
    except AttributeError:
        continue  # ❌ Silent skip
```

**Problem:** AttributeError is a programming error (missing attribute). Silently skipping hides bugs.

**Fixed Code (Option 1 - If it's a bug):**
```python
for metric in metrics:
    try:
        process_metric(metric)
    except AttributeError:
        logger.exception(f"Missing attribute in metric {metric} - this is a bug")
        raise  # Fail-fast
```

**Fixed Code (Option 2 - If legitimately optional):**
```python
for metric in metrics:
    try:
        process_metric(metric)
    except AttributeError as e:
        logger.debug(f"Skipping metric {metric} (missing optional field): {e}")
        continue
```

**Rationale:** AttributeError almost always indicates a bug. If truly optional, document why and log.

---

## Example 6: LOGS_error_RETURNS_False - resource_tracker.py:36

**Location:** `/Users/mahrens917/projects/common/src/common/resource_tracker.py:36`

**Current Code:**
```python
def check_redis_health() -> bool:
    try:
        ping_redis()
        return True
    except (RedisError, OSError, RuntimeError, ConnectionError, ValueError):
        logger.error("Redis health check failed")
        return False
```

**Problem:** Logs at ERROR level, but this is expected transient failure. Also catches programming errors (ValueError).

**Fixed Code:**
```python
def check_redis_health() -> bool:
    try:
        ping_redis()
        return True
    except (RedisError, ConnectionError, OSError) as e:
        logger.warning(f"Redis health check failed (transient): {e}")
        return False
    except (RuntimeError, ValueError):
        logger.exception("Redis health check failed with programming error")
        raise  # These indicate bugs
```

**Rationale:**
- Separate transient errors (warning + return False) from programming errors (exception + raise)
- ConnectionError/RedisError are expected transient failures
- ValueError/RuntimeError are bugs

---

## Example 7: SILENT_ASSIGNMENT - dependency_validator.py:120

**Location:** `/Users/mahrens917/projects/common/src/common/dependency_validator.py:120`

**Current Code:**
```python
try:
    from ldm_client import LDMClient
    ldm = LDMClient()
except LDMNotInstalledError:
    ldm = None  # ❌ Silent fallback
```

**Problem:** Silent assignment of fallback without logging. Caller may not realize LDM is unavailable.

**Fixed Code:**
```python
try:
    from ldm_client import LDMClient
    ldm = LDMClient()
except LDMNotInstalledError as e:
    logger.debug(f"LDM client not available (optional dependency): {e}")
    ldm = None
```

**Rationale:** Optional dependencies should be logged at debug level so developers know which features are unavailable.

---

## Example 8: LOGS_warning_NO_RERAISE - redis_connection_manager.py:49

**Location:** `/Users/mahrens917/projects/common/src/common/redis_connection_manager.py:49`

**Current Code:**
```python
try:
    connect_to_redis()
except REDIS_ERRORS:
    logger.warning("Redis connection failed")
    # ❌ Falls through - caller doesn't know connection failed
```

**Problem:** Logs warning but doesn't return error indication or re-raise. Caller continues as if connected.

**Fixed Code:**
```python
try:
    connect_to_redis()
except REDIS_ERRORS as e:
    logger.warning(f"Redis connection failed (will retry): {e}")
    return False  # Indicate failure to caller
```

**Or if method should propagate:**
```python
try:
    connect_to_redis()
except REDIS_ERRORS:
    logger.warning("Redis connection failed, propagating error")
    raise
```

**Rationale:** Handler should either return error indication or re-raise. Silent failure leaves caller in inconsistent state.

---

## Example 9: Mixed Exception Types - chart_components/trade_visualization.py:93

**Location:** `/Users/mahrens917/projects/common/src/common/chart_components/trade_visualization.py:93`

**Current Code:**
```python
try:
    render_chart()
except (OSError, RuntimeError, ValueError):
    logger.exception("Chart rendering failed")
    # ❌ Treats system errors same as programming errors
```

**Problem:** Catches both system errors (OSError) and programming errors (ValueError, RuntimeError) together.

**Fixed Code:**
```python
try:
    render_chart()
except OSError as e:
    logger.warning(f"Chart rendering failed (file system issue): {e}")
    return None
except (RuntimeError, ValueError):
    logger.exception("Chart rendering failed with programming error")
    raise  # These are bugs
```

**Rationale:** Different exception types need different handling. OSError may be expected (disk full), but ValueError is a bug.

---

## Example 10: LOGS_debug_RETURNS_0.0 - simple_system_metrics.py:81

**Location:** `/Users/mahrens917/projects/common/src/common/simple_system_metrics.py:81`

**Current Code:**
```python
def get_cpu_usage() -> float:
    try:
        return psutil.cpu_percent()
    except OSError:
        logger.debug("Failed to get CPU usage")
        return 0.0  # ❌ 0% CPU is indistinguishable from error
```

**Problem:** Returns 0.0 on error. Caller can't tell "CPU is idle" from "failed to read CPU".

**Fixed Code:**
```python
def get_cpu_usage() -> float | None:
    try:
        return psutil.cpu_percent()
    except OSError as e:
        logger.debug(f"Failed to get CPU usage: {e}")
        return None  # Caller checks: if usage is None
```

**Rationale:** Sentinel values (0.0, -1, etc.) are ambiguous. Use None for errors.

---

## Summary of Common Issues in Examples

1. **Completely silent** (Example 1) → Add debug logging minimum
2. **Silent return** (Examples 2, 4, 10) → Add logging + return None
3. **Logs exception but doesn't re-raise** (Example 3) → Re-raise for bugs
4. **Returns empty collection** (Example 4) → Return None instead
5. **Silent control flow** (Example 5) → Add logging before continue
6. **Wrong logging level** (Example 6) → Match severity to expectation
7. **Silent assignment** (Example 7) → Add debug logging
8. **Logs but no error indication** (Example 8) → Return error or re-raise
9. **Mixed exception types** (Example 9) → Split handlers by type
10. **Returns sentinel value** (Example 10) → Use None for errors

---

## Quick Fixes Checklist

For each violation:
- [ ] Is it a programming error? → `logger.exception()` + `raise`
- [ ] Is it expected transient? → `logger.warning()` + `return None`
- [ ] Is it optional/expected? → `logger.debug()` + `return None`
- [ ] Returns hardcoded value? → Change to `None`
- [ ] Update return type hint to include `None`
- [ ] Add test for error path
