# Code Consolidation Patterns

This document describes canonical implementations for common patterns across the codebase.
Use these guidelines to avoid duplicating code.

## Table of Contents
1. [Pricing Calculations](#pricing-calculations)
2. [Orderbook Parsing](#orderbook-parsing)
3. [Time Calculations](#time-calculations)
4. [Numeric Conversions](#numeric-conversions)
5. [Strike Price Extraction](#strike-price-extraction)
6. [Configuration Loading](#configuration-loading)
7. [Redis Client Initialization](#redis-client-initialization)
8. [Temperature Conversion](#temperature-conversion)
9. [Timestamp Formatting](#timestamp-formatting)

---

## Pricing Calculations

### USDC Micro Price Calculation

**Canonical Implementation:** `src/common/utils/pricing.py:calculate_usdc_micro_price()`

```python
from src.common.utils.pricing import calculate_usdc_micro_price

# Calculate volume-weighted micro price
micro_price = calculate_usdc_micro_price(
    bid_price=bid,
    ask_price=ask,
    bid_size=bid_sz,
    ask_size=ask_sz
)
```

**DO NOT duplicate this formula.** All micro price calculations must use this function.

**Wrappers (when needed):**
- `src/pdf/phases/phase_1_helpers/cf_helpers/micro_price_calculator.py` - Extracts from dict, delegates to canonical
- `src/cfb/price_validator_helpers/micro_price_calculator.py` - Returns tuple for error handling

---

## Orderbook Parsing

### Canonical Implementation: `src/common/orderbook_utils.py`

```python
from src.common.orderbook_utils import (
    parse_orderbook_field,
    extract_best_price_from_dict,
    extract_best_price_from_json,
    parse_and_extract_best_price,
)

# Parse orderbook JSON field
orderbook_dict, error = parse_orderbook_field(market_data, "yes_bids", ticker)

# Extract best price from dict
best_price, best_size = extract_best_price_from_dict(orderbook_dict, is_bid=True)

# Parse and extract in one call (handles both dict and JSON string)
best_price, best_size = parse_and_extract_best_price(raw_data, "yes_bids")
```

**Redis-specific wrapper:** `src/common/redis_protocol/kalshi_store/reader_helpers/orderbook_parser.py`

---

## Time Calculations

### Time to Expiry (Years)

**Canonical Implementation:** `src/common/time_helpers/expiry_conversions.py:calculate_time_to_expiry_years()`

```python
from src.common.time_helpers.expiry_conversions import calculate_time_to_expiry_years

# Calculate time to expiry in years
time_to_expiry = calculate_time_to_expiry_years(
    current_time=datetime.now(timezone.utc),
    expiry_time=expiry_datetime
)
```

**Formula:** `(expiry_time - current_time).total_seconds() / (365.25 * 24 * 3600)`

**Wrappers (when needed):**
- `src/pdf/phases/phase_4_helpers/time_calculator.py` - Adds PDF-specific validation (non-negative, timezone-aware)
- `src/common/expiry_utils.py:_compute_time_to_expiry_years()` - Delegates to canonical (reversed param order)

---

## Numeric Conversions

### Float Coercion

**Canonical Implementation:** `src/common/utils/numeric.py`

DO NOT create custom float conversion functions. Use the canonical implementations with appropriate error handling:

```python
from src.common.utils.numeric import (
    coerce_float_strict,
    coerce_float_optional,
    coerce_float_default,
)

# Strict conversion (raises ValueError on failure)
price = coerce_float_strict(raw_value)  # Use when value MUST be valid

# Optional conversion (returns None on failure)
optional_value = coerce_float_optional(raw_value)  # Use when None is acceptable

# Default conversion (returns default on failure)
value = coerce_float_default(raw_value, default=0.0)  # Use when you need a guaranteed float
```

**Integer Coercion:**
```python
from src.common.utils.numeric import (
    coerce_int_strict,
    coerce_int_optional,
    coerce_int_default,
)

# Same pattern as float coercion
count = coerce_int_strict(raw_count)
optional_count = coerce_int_optional(raw_count)
count = coerce_int_default(raw_count, default=0)
```

**When to Use Each:**
- **`coerce_float_strict()`**: Trading calculations, pricing, validation where failure is critical
- **`coerce_float_optional()`**: User input, API responses, optional configuration values
- **`coerce_float_default()`**: Metrics, stats, display values where a substitute makes sense

**Files Consolidated (20 files now delegate to canonical):**
- `src/common/redis_protocol/kalshi_store/utils_coercion.py`
- `src/common/redis_protocol/converters.py`
- `src/common/parsing_utils.py`
- `src/pdf/phases/analysis_helpers/market_converter.py`
- `src/weather/kalshi_market_updater/weather_data.py`
- And 15 more files

---

## Strike Price Extraction

### From Ticker Strings

**Canonical Implementation:** `src/pdf/data_models/enhanced_kalshi_market_helpers/strike_display_extractor.py`

```python
from src.pdf.data_models.enhanced_kalshi_market_helpers.strike_display_extractor import (
    StrikeDisplayExtractor
)

# Extract strike price from ticker
strike_price = StrikeDisplayExtractor.extract_display_strike_price_from_ticker(ticker)
```

### Strike Type Determination

**Canonical Implementation:** `src/pdf/phases/analysis_helpers/strike_parameter_extractor.py:StrikeParameterExtractor`

```python
from src.pdf.phases.analysis_helpers.strike_parameter_extractor import StrikeParameterExtractor

# Extract strike type from ticker
strike_type = StrikeParameterExtractor.extract_strike_type(ticker)  # Returns: 'greater', 'less', 'between'

# Extract full strike parameters
strike_type, floor, cap = StrikeParameterExtractor.extract_strike_parameters(
    result_dict, ticker, strike_price
)
```

---

## Configuration Loading

### Canonical Implementation: `src/common/config_loader.py`

DO NOT create new `ConfigLoader` classes for each module. Instead:

**Option 1: Use the simple function for loading config files**
```python
from src.common.config_loader import load_config

# Load config file from config/ directory
config = load_config("my_config.json")
```

**Option 2: Inherit from BaseConfigLoader for more sophisticated needs**
```python
from pathlib import Path
from src.common.config_loader import BaseConfigLoader

class MyConfigLoader(BaseConfigLoader):
    def __init__(self, config_dir: Path):
        super().__init__(config_dir)

    def load_my_config(self) -> Dict[str, Any]:
        config = self.load_json_file("my_config.json")
        # Add domain-specific validation
        required_sections = ["section1", "section2"]
        for section in required_sections:
            if section not in config:
                raise ConfigurationError(f"Missing section: {section}")
        return config
```

**Option 3: Delegate to BaseConfigLoader methods**
```python
from pathlib import Path
from src.common.config_loader import BaseConfigLoader

def load_my_config() -> Dict[str, Any]:
    """Load module-specific config using BaseConfigLoader."""
    loader = BaseConfigLoader(Path("config"))
    config = loader.load_json_file("my_config.json")

    # Domain-specific processing
    section = loader.get_section(config, "my_section")
    param = loader.get_parameter(config, "my_section", "my_param")

    return config
```

**Key Methods in BaseConfigLoader:**
- `load_json_file(filename)` - Load JSON from config directory
- `get_section(config, section_name)` - Extract and validate section
- `get_parameter(config, section_name, param_name)` - Extract specific parameter

**Examples of Modules to Consolidate:**
- `src/pdf/utils/config_loader.py` - Can inherit from BaseConfigLoader
- `src/monitor/simple_monitor_helpers/config_loader.py` - Can delegate to BaseConfigLoader
- `src/weather/config_loader.py` - Has special logic (runtime overrides), keep separate but document

**Current State:** ~48 similar config loaders exist - most can be consolidated to use BaseConfigLoader.

---

## Redis Client Initialization

### Canonical Implementation: `src/common/redis_protocol/connection_pool_core.py`

DO NOT create service-specific `get_redis_client()` functions. Use centralized connection management:

**Async Redis Client (Recommended)**
```python
from src.common.redis_protocol.connection_pool_core import get_redis_client

# Get async Redis client with unified connection pooling
redis_client = await get_redis_client()

# Use the client
await redis_client.set("key", "value")
value = await redis_client.get("key")

# No need to manually close - connection returned to pool automatically
```

**Key Features:**
- **Unified Connection Pool:** All services share the same pool (120 max connections)
- **Thread-Safe:** Cross-loop safety with event loop detection
- **Health Monitoring:** Built-in metrics for connection reuse tracking
- **Auto-Cleanup:** Pool automatically manages connection lifecycle
- **Decode Responses:** All responses decoded to strings automatically

**Advanced Usage**
```python
from src.common.redis_protocol.connection_pool_core import (
    get_redis_pool,
    get_redis_pool_metrics,
    perform_redis_health_check,
    cleanup_redis_pool,
)

# Get the connection pool directly (for advanced use)
pool = await get_redis_pool()
client = redis.asyncio.Redis(connection_pool=pool)

# Check pool health and metrics
is_healthy = await perform_redis_health_check()
metrics = get_redis_pool_metrics()  # Returns reuse rate, connection count, etc.

# Manually cleanup pool (usually not needed)
await cleanup_redis_pool()
```

**When NOT to Use the Canonical Implementation:**
Only create custom Redis initialization if you have specific needs:

1. **Sync Redis client** (rare - most code should be async)
   ```python
   import redis
   client = redis.Redis(host=..., port=..., decode_responses=True)
   ```

2. **Different Redis database** (default is db=0)
   ```python
   # For testing or separate data stores
   import redis.asyncio
   pool = redis.asyncio.ConnectionPool(host=..., port=..., db=1)
   client = redis.asyncio.Redis(connection_pool=pool)
   ```

3. **Sentinel or cluster configuration** (not standard in our setup)

**Current State:** ~68 `get_redis_client()` implementations exist across modules.

**Migration Path:**
Most of these can be replaced with the canonical implementation. When refactoring:
1. Check if the custom implementation has special config (e.g., different db, password)
2. If standard config, replace with: `await get_redis_client()`
3. If special config needed, document why and keep separate

**Example Consolidation:**
```python
# BEFORE: Custom implementation
async def _get_redis_client(self) -> RedisClient:
    return redis.asyncio.Redis(
        host="localhost",
        port=6379,
        decode_responses=True
    )

# AFTER: Use canonical
from src.common.redis_protocol.connection_pool_core import get_redis_client

async def _get_redis_client(self) -> RedisClient:
    """Get Redis client via unified connection pool."""
    return await get_redis_client()
```

---

## Temperature Conversion

### TWO SEPARATE IMPLEMENTATIONS (Keep Both)

#### For Kalshi Market Settlement

**USE:** `src/weather/temperature_converter.py:cli_temp_f()`

```python
from src.weather.temperature_converter import cli_temp_f

# Convert for Kalshi settlement (double-round ASOS→CLI formula)
fahrenheit = cli_temp_f(celsius_temp, precision=0.1)
```

**Formula:** `round(round(celsius - precision/2) * 9/5 + 32)`

#### For Display/Internal Use

**USE:** `src/weather/collectors/synoptic/parser_utils.py:celsius_to_fahrenheit()`

```python
from src.weather.collectors.synoptic.parser_utils import celsius_to_fahrenheit

# Simple conversion for display
fahrenheit = celsius_to_fahrenheit(celsius_temp)
```

**Formula:** `(celsius * 9/5) + 32`

⚠️ **WARNING:** Do NOT use `celsius_to_fahrenheit()` for trading calculations. The formulas produce different results due to rounding differences that can affect market settlement.

---

## Summary of Consolidation Benefits

1. **Single Source of Truth:** Changes to calculation logic only need to happen in one place
2. **Consistency:** All parts of the codebase use the same formula/logic
3. **Testing:** Only need to test one implementation thoroughly
4. **Maintenance:** Easier to understand code flow and dependencies
5. **Bug Prevention:** Reduces risk of formula inconsistencies affecting trading

---

## Spread Calculations

### Why Spread Functions Are NOT Consolidated

While there are 15+ "spread" functions in the codebase, they are **NOT duplicates** - they serve distinct purposes:

#### 1. Simple Spread Calculation (ask - bid)

**Context-Specific Implementations:**

- **Kalshi Markets:** `src/pdf/data_models/enhanced_kalshi_market_helpers/spread_calculator.py:get_spread()`
  - Validates contract type, raises RuntimeError on invalid spread
  - Returns: `float` (spread value)

- **Option Normalization:** `src/pdf/phases/phase_1_helpers/option_normalizer.py:_option_normalizer_compute_spreads()`
  - Computes both absolute and relative spread
  - Returns: `Optional[Tuple[float, float]]` (absolute, relative)
  - Returns None on invalid data

- **GP Interpolation Results:** `src/pdf/data_models/surface_data.py:_get_spread()`
  - Simple calculation from reconstructed bid/ask
  - Returns: `float`

- **Excessive Spread Check:** `src/pdf/phases/phase_2_helpers/arbitrage_validator.py:_has_excessive_spread()`
  - Checks if spread > 50% of ask price
  - Returns: `bool`

**Why Not Consolidated:** Each has different error handling, return types, and validation logic appropriate for its domain.

#### 2. Spread Validation (bid < ask checks)

**Different Validators for Different Contexts:**

- **Market Data Models:** `src/common/data_models/trading_helpers/market_validator.py:validate_bid_ask_spread()`
  - Validates bid < ask for data model construction
  - Raises: `ValueError` with descriptive message

- **Redis Race Condition Detection:** `src/common/redis_protocol/atomic_redis_operations_helpers/spread_validator.py:validate_bid_ask_spread()`
  - Detects inverted spreads from concurrent writes
  - Raises: `RedisDataValidationError` for retry logic
  - Includes diagnostic logging

- **Micro Price Calculations:** `src/common/data_models/micro_price_helpers/calculation_validator.py:validate_absolute_spread()`
  - Validates spread >= 0 for calculation constraints
  - Raises: `TypeError`

**Why Not Consolidated:** Each validator has different exception types, messages, and context-specific logic (Redis retry vs model validation).

#### 3. Spread Statistics (GP Surface Fitting)

- **Spread Statistics by Expiry:** `src/pdf/phases/phase_5_helpers/spread_statistics.py:SpreadStatisticsCalculator.compute()`
  - Computes median spreads and log-spreads grouped by expiry time
  - Returns: Tuple of dicts mapping expiry → median values
  - Used for GP noise estimation in PDF pipeline

**Why Not Consolidated:** This is statistical analysis of spreads, not simple spread calculation.

#### Summary

The basic formula `ask - bid` is trivial (one line). The value is in the **context-specific logic**:
- Error handling patterns (raise vs return None vs retry)
- Return types (float vs tuple vs bool vs dict)
- Validation rules (bid < ask vs spread > 0 vs spread > threshold)
- Domain-specific operations (statistics, race condition detection, etc.)

**Consolidating these would create a complex generic function with many parameters and branches, reducing code clarity.**

---

## Timestamp Formatting

### Canonical Implementation: `src/common/time_helpers/timezone.py`

DO NOT create custom timestamp formatting functions. Use the canonical utilities:

```python
from src.common.time_helpers.timezone import (
    get_current_utc,
    get_current_est,
    ensure_timezone_aware,
    to_utc,
    format_timestamp,
)

# Get current time in UTC
now_utc = get_current_utc()

# Ensure datetime is timezone-aware (defaults to UTC if naive)
aware_dt = ensure_timezone_aware(datetime_value)

# Convert to UTC
utc_dt = to_utc(datetime_value)

# Format timestamp with timezone
formatted = format_timestamp(datetime_value, tz_name="UTC")
```

**Common Patterns:**
```python
# ISO formatting
iso_string = aware_dt.isoformat()

# UTC timestamp for APIs
utc_string = to_utc(dt).isoformat()

# Display formatting
display_string = format_timestamp(dt, tz_name="EST")
```

**Files Consolidated (6 files now delegate to canonical):**
- `src/deribit/message_handler_helpers/timestamp_helpers.py`
- `src/weather/redis_store_helpers/observation_validator.py`
- `src/deribit/message_handler_helpers/snapshotbuilder_helpers/expiry_calculator.py`
- `src/common/redis_protocol/messages_helpers/timestamp_converter.py`
- `src/monitor/dawn_reset_coordinator_helpers/time_calculator.py`
- `src/kalshi/notifications/trade_notifier_helpers/attempt_formatter.py`

**Domain-Specific Formatters (Kept Separate):**
- `src/monitor/simple_monitor_helpers.py:format_relative_time()` - Relative time display ("2h3m ago")
- `src/pdf/visualization/surface_plotter_helpers/axis_formatters.py:format_time()` - Chart axis labels ("1.5y")

**Why Use Canonical:**
- Consistent timezone handling across codebase
- Centralized UTC conversion logic
- Proper handling of naive datetimes
- Single source of truth for timestamp formatting

---

## When to Create Duplicates

Only duplicate code when:

1. **Different Use Cases:** Like the two temperature converters (settlement vs display)
2. **Performance Critical:** JIT-compiled versions for hot paths
3. **Error Handling Variations:** Different error return patterns (tuple vs exception)
4. **Different Dependencies:** Avoiding circular imports
5. **Trivial Formulas in Different Contexts:** Like spread calculations (ask - bid)

**But Always:** Document the relationship and cross-reference the canonical implementation.
