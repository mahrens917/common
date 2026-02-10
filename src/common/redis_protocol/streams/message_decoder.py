"""Decode raw XREADGROUP / XAUTOCLAIM responses into typed tuples."""

from __future__ import annotations

from typing import Any, List, Tuple


def decode_stream_response(result: Any) -> List[Tuple[str, dict]]:
    """Convert XREADGROUP raw response to list of (entry_id, fields) tuples.

    XREADGROUP returns:
        [[stream_name, [(entry_id, {field: value}), ...]], ...]

    Each entry_id and field key/value may be bytes or str depending on
    the Redis client's decode_responses setting.
    """
    if not result:
        return []

    entries: List[Tuple[str, dict]] = []
    for _stream_name, stream_entries in result:
        for entry_id, fields in stream_entries:
            decoded_id = _to_str(entry_id)
            decoded_fields = {_to_str(k): _to_str(v) for k, v in fields.items()}
            entries.append((decoded_id, decoded_fields))
    return entries


def _to_str(value: Any) -> str:
    """Convert bytes to str, pass through str values."""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


__all__ = ["decode_stream_response"]
