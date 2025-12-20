"""Telegram media (photos/documents) sending functionality."""

import asyncio
import logging
from pathlib import Path
from typing import Any, List, Optional

from ..alerting import TelegramClient, TelegramDeliveryResult

logger = logging.getLogger(__name__)


class RecipientValidationMixin:
    def _assert_recipients(self, recipients: List[str]) -> None:
        if not recipients:
            raise ValueError("Telegram media delivery requires at least one recipient.")


class PayloadResolutionMixin:
    def _resolve_payload_path(self, source_path: Path, spooled_path: Optional[Path]) -> Path:
        path = spooled_path if spooled_path is not None else source_path
        if not path.exists():
            raise FileNotFoundError(f"Telegram media payload missing at {path}")
        return path


class BackoffGuardMixin:
    # Declare dynamically-attached attributes for static type checking
    backoff_manager: Any

    def _ensure_backoff_allowance(self, telegram_method: str) -> None:
        if self.backoff_manager.should_skip_operation(telegram_method):
            raise RuntimeError(
                f"Telegram network backoff active; refusing to send {telegram_method} payload."
            )


class DeliveryMixin:
    # Declare dynamically-attached attributes for static type checking
    telegram_client: TelegramClient
    timeout_seconds: float
    backoff_manager: Any

    async def _deliver_to_recipients(
        self,
        recipients: List[str],
        payload_path: Path,
        caption: str,
        is_photo: bool,
        telegram_method: str,
    ) -> int:
        success_count = 0
        for user_id in recipients:
            await self._send_to_single_recipient(
                user_id,
                payload_path,
                caption,
                is_photo,
                telegram_method,
            )
            success_count += 1
        return success_count

    async def _send_to_single_recipient(
        self,
        user_id: str,
        payload_path: Path,
        caption: str,
        is_photo: bool,
        telegram_method: str,
    ) -> None:
        success, error_text = await self._attempt_send(
            user_id,
            payload_path,
            caption,
            is_photo,
            telegram_method,
        )
        if not success:
            failure_message = error_text if error_text else "unknown error"
            self.backoff_manager.record_failure(RuntimeError(failure_message))
            raise RuntimeError(
                f"Telegram media send returned failure for user {user_id}: {failure_message}"
            )
        self.backoff_manager.clear_backoff()
        logger.debug("Telegram media %s delivered to user %s", payload_path.name, user_id)

    async def _attempt_send(
        self,
        user_id: str,
        payload_path: Path,
        caption: str,
        is_photo: bool,
        telegram_method: str,
    ) -> tuple[bool, Optional[str]]:
        try:
            return await self.telegram_client.send_media(
                user_id,
                payload_path,
                caption=caption,
                is_photo=is_photo,
                method=telegram_method,
            )
        except asyncio.TimeoutError as exc:
            self.backoff_manager.record_failure(exc)
            raise RuntimeError(
                f"Telegram media timeout after {self.timeout_seconds}s for user {user_id}"
            ) from exc
        except Exception as exc:
            self.backoff_manager.record_failure(exc)
            raise RuntimeError(
                f"Telegram media send failed for user {user_id} with payload {payload_path}"
            ) from exc


class TelegramMediaSender(
    RecipientValidationMixin,
    PayloadResolutionMixin,
    BackoffGuardMixin,
    DeliveryMixin,
):
    """Sends media files (photos/documents) to Telegram recipients."""

    def __init__(
        self,
        telegram_client: TelegramClient,
        timeout_seconds: int,
        backoff_manager,
    ):
        self.telegram_client = telegram_client
        self.timeout_seconds = timeout_seconds
        self.backoff_manager = backoff_manager

    async def send_media(
        self,
        source_path: Path,
        caption: str,
        recipients: List[str],
        is_photo: bool,
        telegram_method: str,
        spooled_path: Optional[Path] = None,
    ) -> TelegramDeliveryResult:
        self._assert_recipients(recipients)
        payload_path = self._resolve_payload_path(source_path, spooled_path)
        if self.backoff_manager.should_skip_operation(telegram_method):
            logger.warning("Skipping Telegram %s due to active network backoff", telegram_method)
            return TelegramDeliveryResult(
                success=False, failed_recipients=list(recipients), queued_recipients=[]
            )
        success_count = await self._deliver_to_recipients(
            recipients,
            payload_path,
            caption,
            is_photo,
            telegram_method,
        )

        if success_count == 0:
            raise RuntimeError("Telegram media delivery reported zero successes unexpectedly.")

        return TelegramDeliveryResult(success=True, failed_recipients=[], queued_recipients=[])
