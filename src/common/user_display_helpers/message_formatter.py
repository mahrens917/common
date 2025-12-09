"""
Message Formatter Module

Handles emoji-enhanced message formatting for user-facing output.
"""


def format_startup_message(currencies: list) -> str:
    """Format startup message with currency list."""
    currency_list = ", ".join(currencies)
    return f"🚀 Starting Kalshi PDF Generator...\n📊 Processing currencies: {currency_list}"


def format_service_ready() -> str:
    """Format service ready message."""
    return "✅ Service initialized successfully"


def format_step_message(step_num: int, description: str, details: str = "") -> str:
    """Format step progress message."""
    base_msg = f"🔄 Step {step_num}: {description}..."
    if details:
        return f"{base_msg}\n   {details}"
    return base_msg


def format_step_complete(step_num: int, description: str, result: str = "") -> str:
    """Format step completion message."""
    if result:
        return f"✅ Step {step_num} complete: {result}"
    return f"✅ Step {step_num} complete"


def format_data_loading(options_count: int, futures_count: int) -> str:
    """Format data loading results message."""
    total_points = options_count + futures_count
    return f"✅ Using {total_points} Deribit data points ({options_count} options + {futures_count} futures)"


def format_kalshi_targets(count: int) -> str:
    """Format Kalshi targets loaded message."""
    return f"✅ Loaded {count} Kalshi target points"


def format_probability_calculation(currency: str, successful: int, total: int) -> str:
    """Format probability calculation results."""
    return f"✅ Calculated {successful}/{total} probabilities for {currency}"


def format_market_updates(successful: int, total: int) -> str:
    """Format market update results."""
    return f"✅ Updated {successful}/{total} Kalshi markets"


def format_completion(currency: str, total_calculations: int, processing_time: float) -> str:
    """Format completion summary."""
    return f"✅ {currency}: {total_calculations} probabilities calculated in {processing_time:.1f}s"


def format_error(message: str) -> str:
    """Format error message."""
    return f"❌ {message}"


def format_warning(message: str) -> str:
    """Format warning message."""
    return f"⚠️  {message}"
