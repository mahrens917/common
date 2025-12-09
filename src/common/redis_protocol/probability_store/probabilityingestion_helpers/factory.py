"""Factory for creating probability ingestion helpers."""

from dataclasses import dataclass
from typing import Awaitable, Callable

from redis.asyncio import Redis

from .compact_store import CompactStore
from .field_iterator import FieldIterator
from .human_readable_store import HumanReadableStore
from .key_collector import KeyCollector
from .record_enqueuer import RecordEnqueuer
from .single_store import SingleStore


@dataclass(frozen=True)
class IngestionHelpers:
    """Container for all probability ingestion helpers."""

    field_iterator: FieldIterator
    key_collector: KeyCollector
    record_enqueuer: RecordEnqueuer
    compact_store: CompactStore
    human_readable_store: HumanReadableStore
    single_store: SingleStore


def create_ingestion_helpers(redis_provider: Callable[[], Awaitable[Redis]]) -> IngestionHelpers:
    """
    Create all probability ingestion helpers with proper dependency wiring.

    Args:
        redis_provider: Async function that returns Redis client

    Returns:
        Container with all wired helpers
    """
    field_iterator = FieldIterator()
    key_collector = KeyCollector()
    record_enqueuer = RecordEnqueuer()

    compact_store = CompactStore(
        redis_provider=redis_provider,
        field_iterator=field_iterator,
    )

    human_readable_store = HumanReadableStore(
        redis_provider=redis_provider,
        key_collector=key_collector,
        record_enqueuer=record_enqueuer,
    )

    single_store = SingleStore(redis_provider=redis_provider)

    return IngestionHelpers(
        field_iterator=field_iterator,
        key_collector=key_collector,
        record_enqueuer=record_enqueuer,
        compact_store=compact_store,
        human_readable_store=human_readable_store,
        single_store=single_store,
    )
