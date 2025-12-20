"""Validate media delivery requests."""

from pathlib import Path
from typing import List, Optional


class DeliveryValidator:
    """Validates media delivery requests."""

    @staticmethod
    def validate_request(
        recipients: List[str],
        source_path: Path,
        spooled_path: Optional[Path],
        backoff_manager,
        telegram_method: str,
    ) -> Path:
        """Validate send request and return payload path."""
        if not recipients:
            raise ValueError("Telegram media delivery requires at least one recipient.")

        payload_path = spooled_path if spooled_path is not None else source_path
        if not payload_path.exists():
            raise FileNotFoundError(f"Telegram media payload missing at {payload_path}")

        if backoff_manager.should_skip_operation(telegram_method):
            raise RuntimeError(f"Telegram network backoff active; refusing to send {telegram_method} payload.")

        return payload_path

    @staticmethod
    def verify_success(success_count: int) -> None:
        """Verify that at least one delivery succeeded."""
        if success_count == 0:
            raise RuntimeError("Telegram media delivery reported zero successes unexpectedly.")
