"""Parameter dataclass for media send operations."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class MediaSendParameters:
    """Parameters for sending media files via Telegram."""

    source_path: Path
    caption: str
    recipients: List[str]
    is_photo: bool
    telegram_method: str
    spooled_path: Optional[Path] = None
