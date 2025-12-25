# Silent Exception Handler Fix Guide

Quick reference for fixing the 519 silent exception violations.

## Decision Tree

```
Is the exception a programming error (ValueError, TypeError, AttributeError, KeyError)?
├─ YES → logger.exception() + raise
└─ NO → Is it expected in normal operation?
   ├─ YES → Is it domain-specific (InsufficientDataError)?
   │  ├─ YES → logger.debug() or logger.warning() + return None
   │  └─ NO → Is it transient (ConnectionError, Redis)?
   │     ├─ YES → logger.warning() + return None or retry
   │     └─ NO → logger.error() + consider re-raising
   └─ NO → logger.exception() + raise (unexpected error)
```

---

## Fix Patterns by Violation Type

### 1. COMPLETELY_SILENT_PASS (16 violations) - CRITICAL

**Before:**
```python
except OSError:
    pass
```

**After (cleanup/expected):**
```python
except OSError as e:
    logger.debug(f"Cleanup failed (expected): {e}")
```

**After (unexpected):**
```python
except OSError as e:
    logger.exception("Unexpected OSError")
    raise
```

---

### 2. LOGS_exception_NO_RERAISE (34 violations) - CRITICAL

**Before:**
```python
except ValueError:
    logger.exception("Parse failed")
    # Falls through
```

**After (if it's a bug):**
```python
except ValueError:
    logger.exception("Parse failed - this is a bug")
    raise
```

**After (if expected but wrong logging):**
```python
except ValueError as e:
    logger.warning(f"Parse failed for invalid input: {e}")
    return None
```

---

### 3. SILENT_RETURN_None (36 violations) - HIGH

**Before:**
```python
except ValueError:
    return None
```

**After:**
```python
except ValueError as e:
    logger.warning(f"Failed to process: {e}")
    return None
```

---

### 4. SILENT_RETURN_empty_collection (18 violations) - HIGH

**Before:**
```python
def get_items() -> list:
    try:
        return fetch()
    except KeyError:
        return []
```

**After:**
```python
def get_items() -> list | None:
    try:
        return fetch()
    except KeyError as e:
        logger.warning(f"Failed to fetch items: {e}")
        return None  # Caller checks: if items is None
```

---

### 5. SILENT_ASSIGNMENT (31 violations) - HIGH

**Before:**
```python
try:
    value = compute()
except ValueError:
    value = fallback
```

**After (if expected):**
```python
try:
    value = compute()
except ValueError as e:
    logger.debug(f"Using fallback value: {e}")
    value = fallback
```

**After (if unexpected - programming error):**
```python
try:
    value = compute()
except ValueError:
    logger.exception("Computation failed - this is a bug")
    raise
```

---

### 6. SILENT_CONTINUE (17 violations) - HIGH

**Before:**
```python
for item in items:
    try:
        process(item)
    except ValueError:
        continue
```

**After:**
```python
for item in items:
    try:
        process(item)
    except ValueError as e:
        logger.warning(f"Skipping invalid item {item}: {e}")
        continue
```

---

### 7. LOGS_error_RETURNS_False (24 violations) - MEDIUM

**Before:**
```python
def validate() -> bool:
    try:
        check()
        return True
    except ValueError:
        logger.error("Validation failed")
        return False
```

**After (if expected validation failure):**
```python
def validate() -> bool:
    try:
        check()
        return True
    except ValueError as e:
        logger.warning(f"Validation failed: {e}")  # Not error, just warning
        return False
```

**After (if unexpected error):**
```python
def validate() -> bool:
    try:
        check()
        return True
    except ValueError:
        logger.exception("Validation failed unexpectedly")
        raise  # Let caller handle this
```

---

### 8. LOGS_warning_NO_RERAISE (42 violations) - REVIEW

**Current:**
```python
except REDIS_ERRORS:
    logger.warning("Redis failed")
    # Falls through
```

**If acceptable (transient error):**
```python
except REDIS_ERRORS as e:
    logger.warning(f"Redis transient failure: {e}")
    return None  # Make it explicit
```

**If should propagate:**
```python
except REDIS_ERRORS:
    logger.warning("Redis failed, propagating")
    raise
```

---

## Fix by Exception Type

### Programming Errors (ValueError, TypeError, AttributeError, KeyError)

**Always:**
```python
except ValueError:
    logger.exception("Description")
    raise
```

**Only exception:** Parsing user input (use validation instead)
```python
except ValueError as e:
    logger.debug(f"Invalid user input: {e}")
    return None
```

---

### Network/Transient (ConnectionError, TimeoutError, REDIS_ERRORS)

**Pattern:**
```python
except REDIS_ERRORS as e:
    logger.warning(f"Redis transient failure: {e}")
    return None
```

---

### Domain Expected (InsufficientDataError, ValidationError)

**Pattern:**
```python
except InsufficientDataError as e:
    logger.debug(f"Expected data unavailable: {e}")
    return None
```

---

### System (OSError, ImportError)

**Cleanup/Optional:**
```python
except OSError as e:
    logger.debug(f"Optional cleanup failed: {e}")
```

**Critical:**
```python
except OSError:
    logger.exception("Critical file operation failed")
    raise
```

**Optional imports:**
```python
except ImportError as e:
    logger.debug(f"Optional dependency not available: {e}")
    fallback = None
```

---

## Common Mistakes to Avoid

### ❌ Don't: Return hardcoded values for errors
```python
except ValueError:
    return []  # Caller can't tell error from empty
```

### ✅ Do: Return None for errors
```python
except ValueError as e:
    logger.warning(f"Error: {e}")
    return None  # Caller checks: if result is None
```

---

### ❌ Don't: Log exception but not re-raise for bugs
```python
except ValueError:
    logger.exception("Parse failed")
    # Falls through - caller continues with bad state
```

### ✅ Do: Re-raise after logging
```python
except ValueError:
    logger.exception("Parse failed")
    raise
```

---

### ❌ Don't: Completely silent
```python
except Exception:
    pass
```

### ✅ Do: At minimum log at debug
```python
except Exception as e:
    logger.debug(f"Suppressing expected exception: {e}")
```

---

### ❌ Don't: Mix exception types without handling differently
```python
except (ValueError, ConnectionError):
    logger.warning("Something failed")
    return None
```

### ✅ Do: Handle each appropriately
```python
except ValueError:
    logger.exception("Programming error")
    raise
except ConnectionError as e:
    logger.warning(f"Transient failure: {e}")
    return None
```

---

## Logging Level Guide

| Level | When to Use | Re-raise? |
|-------|-------------|-----------|
| `logger.debug()` | Expected failures, optional operations | No - return None |
| `logger.warning()` | Transient failures, data issues | Usually no - return None |
| `logger.error()` | Unexpected but recoverable errors | Consider re-raising |
| `logger.exception()` | Programming errors, bugs | **YES - always re-raise** |

---

## Return Value Guide

| Return | When to Use |
|--------|-------------|
| `None` | Error occurred, caller must check |
| `False` | Boolean operation failed (validation, etc.) |
| `raise` | Programming error or caller must handle |
| Empty collection `[]` | **AVOID** - use None instead |
| Computed fallback | Only if truly safe default exists |

---

## File-Specific Notes

### logging_config.py
- OSError during cleanup: `logger.debug()` is OK
- ImportError for optional deps: `logger.debug()` is OK
- FileNotFoundError for optional configs: `logger.debug()` is OK

### process_killer.py
- Many unknown exception types - needs comprehensive review
- Likely mix of expected (process not found) and unexpected errors

### redis_connection_manager.py
- REDIS_ERRORS are transient - `logger.warning()` is appropriate
- Should return None, not empty collections

### chart_generator/*
- InsufficientDataError: `logger.debug()` or `logger.warning()`
- OSError on image operations: `logger.error()` + return None

### alerter_helpers/*
- Telegram errors often transient: `logger.warning()`
- Command parsing errors: `logger.debug()` for invalid input

---

## Testing Strategy

When fixing handlers, add tests for:

1. **Error path is exercised**
```python
def test_handles_invalid_input():
    with pytest.raises(ValueError):  # If we re-raise
        parse_value("invalid")
```

2. **Return value on error**
```python
def test_returns_none_on_error():
    result = fetch_data("invalid")
    assert result is None
```

3. **Logging occurs**
```python
def test_logs_warning_on_transient_error(caplog):
    fetch_data("cause_redis_error")
    assert "Redis transient failure" in caplog.text
```

---

## Priority Order

1. **COMPLETELY_SILENT_PASS** (16) - Add any logging
2. **LOGS_exception but doesn't re-raise** (34) - Re-raise if programming error
3. **SILENT_RETURN_None** (36) - Add logging
4. **SILENT_ASSIGNMENT** (31) - Add logging
5. **SILENT_CONTINUE** (17) - Add logging
6. **Everything else** - Case by case

---

## Checklist for Each Fix

- [ ] Identified exception type (programming vs expected vs transient)
- [ ] Added appropriate logging level
- [ ] Re-raised if programming error
- [ ] Returned None instead of empty collection (if applicable)
- [ ] Updated return type hint to include None
- [ ] Added test for error path
- [ ] Verified caller handles None return

---

## References

- Full analysis: `SILENT_EXCEPTION_ANALYSIS.md`
- Pattern breakdown: `handler_patterns.txt`
- Category breakdown: `violations_by_category.txt`
- Detailed violations: `silent_exceptions_detailed.txt`
