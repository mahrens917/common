"""Tests for the rate_limiter module."""

import pytest

from common.rate_limiter import (
    BACKOFF_MULTIPLIER,
    INITIAL_BACKOFF_MS,
    MAX_BACKOFF_MS,
    RateLimiter,
    RateLimiterConfig,
)


class TestRateLimiterConfig:
    """Tests for RateLimiterConfig dataclass."""

    def test_default_values(self):
        config = RateLimiterConfig()
        assert config.initial_backoff_ms == INITIAL_BACKOFF_MS
        assert config.max_backoff_ms == MAX_BACKOFF_MS
        assert config.backoff_multiplier == BACKOFF_MULTIPLIER

    def test_custom_values(self):
        config = RateLimiterConfig(
            initial_backoff_ms=500.0,
            max_backoff_ms=10000.0,
            backoff_multiplier=1.5,
        )
        assert config.initial_backoff_ms == 500.0
        assert config.max_backoff_ms == 10000.0
        assert config.backoff_multiplier == 1.5


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_init_with_default_config(self):
        limiter = RateLimiter()
        assert limiter.current_delay_ms == 0.0
        assert limiter._is_backing_off is False

    def test_init_with_custom_config(self):
        config = RateLimiterConfig(initial_backoff_ms=500.0)
        limiter = RateLimiter(config=config)
        assert limiter._config.initial_backoff_ms == 500.0

    def test_stats_initial(self):
        limiter = RateLimiter()
        stats = limiter.stats
        assert stats["total_requests"] == 0
        assert stats["total_rate_limits"] == 0
        assert stats["total_errors"] == 0
        assert stats["current_delay_ms"] == 0.0
        assert stats["is_backing_off"] is False

    @pytest.mark.asyncio
    async def test_wait_increments_requests(self):
        limiter = RateLimiter()
        await limiter.wait()
        assert limiter.stats["total_requests"] == 1

    @pytest.mark.asyncio
    async def test_wait_with_delay(self):
        config = RateLimiterConfig(initial_backoff_ms=10.0)
        limiter = RateLimiter(config=config)
        limiter.record_rate_limit()
        await limiter.wait()
        assert limiter.stats["total_requests"] == 1

    def test_record_success_clears_backoff(self):
        limiter = RateLimiter()
        limiter.record_rate_limit()
        assert limiter._is_backing_off is True
        limiter.record_success()
        assert limiter._is_backing_off is False
        assert limiter.current_delay_ms == 0.0

    def test_record_rate_limit_first_time(self):
        config = RateLimiterConfig(initial_backoff_ms=1000.0)
        limiter = RateLimiter(config=config)
        delay = limiter.record_rate_limit()
        assert delay == 1000.0
        assert limiter._is_backing_off is True
        assert limiter.stats["total_rate_limits"] == 1

    def test_record_rate_limit_consecutive(self):
        config = RateLimiterConfig(
            initial_backoff_ms=1000.0,
            backoff_multiplier=2.0,
            max_backoff_ms=10000.0,
        )
        limiter = RateLimiter(config=config)
        delay1 = limiter.record_rate_limit()
        delay2 = limiter.record_rate_limit()
        assert delay1 == 1000.0
        assert delay2 == 2000.0
        assert limiter.stats["total_rate_limits"] == 2

    def test_record_rate_limit_capped_at_max(self):
        config = RateLimiterConfig(
            initial_backoff_ms=5000.0,
            backoff_multiplier=3.0,
            max_backoff_ms=10000.0,
        )
        limiter = RateLimiter(config=config)
        limiter.record_rate_limit()
        delay = limiter.record_rate_limit()
        assert delay == 10000.0  # Capped at max

    def test_record_rate_limit_with_retry_after(self):
        limiter = RateLimiter()
        delay = limiter.record_rate_limit(retry_after_seconds=5.0)
        assert delay == 5000.0  # 5 seconds in ms
        assert limiter._is_backing_off is True

    def test_handle_429_response_alias(self):
        limiter = RateLimiter()
        delay = limiter.handle_429_response(retry_after_seconds=3.0)
        assert delay == 3000.0

    def test_record_error_increments_counter(self):
        limiter = RateLimiter()
        limiter.record_error()
        assert limiter.stats["total_errors"] == 1

    def test_record_error_does_not_affect_backoff(self):
        limiter = RateLimiter()
        limiter.record_error()
        assert limiter._is_backing_off is False
        assert limiter.current_delay_ms == 0.0

    def test_get_metrics_alias(self):
        limiter = RateLimiter()
        metrics = limiter.get_metrics()
        assert metrics == limiter.stats

    def test_reset_clears_all_state(self):
        limiter = RateLimiter()
        limiter.record_rate_limit()
        limiter.record_error()
        limiter.reset()
        assert limiter.current_delay_ms == 0.0
        assert limiter._is_backing_off is False
        assert limiter.stats["total_requests"] == 0
        assert limiter.stats["total_rate_limits"] == 0
        assert limiter.stats["total_errors"] == 0


class TestRateLimiterConstants:
    """Tests for module-level constants."""

    def test_initial_backoff_ms_value(self):
        assert INITIAL_BACKOFF_MS == 1000.0

    def test_max_backoff_ms_value(self):
        assert MAX_BACKOFF_MS == 30000.0

    def test_backoff_multiplier_value(self):
        assert BACKOFF_MULTIPLIER == 2.0
