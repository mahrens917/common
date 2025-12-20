from __future__ import annotations

"""Minimal Telegram API adapter used by monitor alerting."""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import aiohttp

# HTTP status code
_HTTP_OK = 200


class TelegramClient:
    """Convenience wrapper around Telegram Bot HTTP endpoints."""

    def __init__(self, token: str, *, timeout_seconds: float) -> None:
        self._base_url = f"https://api.telegram.org/bot{token}"
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def timeout(self) -> aiohttp.ClientTimeout:
        return self._timeout

    async def send_message(self, chat_id: str, message: str) -> Tuple[bool, Optional[str]]:
        """Send a text message to a single chat id."""

        payload = {"chat_id": chat_id, "text": message}
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.post(f"{self._base_url}/sendMessage", json=payload) as response:
                if response.status == _HTTP_OK:
                    return True, None
                return False, await response.text()

    async def send_media(
        self,
        chat_id: str,
        payload_path: Path,
        *,
        caption: str,
        is_photo: bool,
        method: str,
    ) -> Tuple[bool, Optional[str]]:
        """Send a media payload (photo/document/video) to a single chat id."""

        if not payload_path.exists():
            return False, f"Payload missing: {payload_path}"

        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            with payload_path.open("rb") as file_handle:
                form_data = aiohttp.FormData()
                form_data.add_field("chat_id", chat_id)
                if caption:
                    form_data.add_field("caption", caption)
                field_name = "photo" if is_photo else "document"
                form_data.add_field(field_name, file_handle, filename=payload_path.name)
                async with session.post(f"{self._base_url}/{method}", data=form_data) as response:
                    if response.status == _HTTP_OK:
                        return True, None
                    return False, await response.text()

    async def get_updates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch updates for registered commands."""

        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.get(f"{self._base_url}/getUpdates", params=params) as response:
                response.raise_for_status()
                return await response.json()
