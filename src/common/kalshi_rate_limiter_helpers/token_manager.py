"""Token bucket management"""

import logging
import time

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages token buckets for rate limiting"""

    def __init__(self, max_read_tokens: int, max_write_tokens: int):
        self.read_tokens = max_read_tokens
        self.write_tokens = max_write_tokens
        self.max_read_tokens = max_read_tokens
        self.max_write_tokens = max_write_tokens
        self.last_refill_time = time.time()

    def refill_tokens_if_needed(self) -> bool:
        """Refill tokens if a second has passed, return True if refilled"""
        current_time = time.time()
        if current_time - self.last_refill_time >= 1.0:
            self.read_tokens = self.max_read_tokens
            self.write_tokens = self.max_write_tokens
            self.last_refill_time = current_time
            logger.debug(
                f"[KalshiRateLimiter] Refilled tokens: read={self.read_tokens}, write={self.write_tokens}"
            )
            return True
        return False

    def consume_read_token(self) -> bool:
        """Try to consume a read token, return True if successful"""
        if self.read_tokens > 0:
            self.read_tokens -= 1
            return True
        return False

    def consume_write_token(self) -> bool:
        """Try to consume a write token, return True if successful"""
        if self.write_tokens > 0:
            self.write_tokens -= 1
            return True
        return False

    def has_read_tokens(self) -> bool:
        """Check if read tokens available"""
        return self.read_tokens > 0

    def has_write_tokens(self) -> bool:
        """Check if write tokens available"""
        return self.write_tokens > 0
