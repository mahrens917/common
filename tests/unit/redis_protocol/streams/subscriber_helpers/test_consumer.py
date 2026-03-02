"""Tests for subscriber_helpers.consumer module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.streams.subscriber import StreamConfig
from common.redis_protocol.streams.subscriber_helpers.consumer import (
    MAX_STREAM_RETRIES,
    consume_stream_queue,
    extract_payload,
    handle_consumer_retry,
    is_json_object_string,
)


class TestIsJsonObjectString:
    """Tests for is_json_object_string."""

    def test_valid_json_string(self):
        assert is_json_object_string('{"key": "value"}') is True

    def test_non_object_string(self):
        assert is_json_object_string("plain text") is False

    def test_bytes_input(self):
        assert is_json_object_string(b'{"key": "value"}') is True

    def test_bytearray_input(self):
        assert is_json_object_string(bytearray(b'{"key": "val"}')) is True

    def test_non_string_type(self):
        assert is_json_object_string(12345) is False

    def test_none(self):
        assert is_json_object_string(None) is False


class TestExtractPayload:
    """Tests for extract_payload."""

    def test_extracts_json_payload_field(self):
        fields = {"ticker": "AAPL", "payload": '{"ticker": "AAPL", "price": 150}'}
        result = extract_payload(fields)
        assert result == {"ticker": "AAPL", "price": 150}

    def test_returns_fields_when_no_payload(self):
        fields = {"ticker": "AAPL", "price": "150"}
        result = extract_payload(fields)
        assert result == fields

    def test_returns_fields_on_invalid_json(self):
        fields = {"ticker": "AAPL", "payload": "not-json"}
        result = extract_payload(fields)
        assert result == fields

    def test_payload_is_json_array(self):
        fields = {"payload": "[1, 2, 3]"}
        assert extract_payload(fields) == fields

    def test_payload_is_bytes_json(self):
        fields = {"payload": b'{"ticker": "AAPL"}'}
        result = extract_payload(fields)
        assert result == {"ticker": "AAPL"}

    def test_malformed_json_object_string(self):
        fields = {"payload": "{malformed json}"}
        result = extract_payload(fields)
        assert result == fields


class TestHandleConsumerRetry:
    """Tests for handle_consumer_retry."""

    @pytest.mark.asyncio
    async def test_requeues_on_first_failure(self):
        queue: asyncio.Queue = asyncio.Queue()
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")
        retry_counts: dict[str, int] = {}

        await handle_consumer_retry("e-1", "TICK", {"data": "1"}, queue, redis_client, config, retry_counts)

        assert retry_counts["e-1"] == 1
        assert not queue.empty()
        redis_client.xack.assert_not_called()

    @pytest.mark.asyncio
    async def test_drops_after_max_retries(self):
        queue: asyncio.Queue = asyncio.Queue()
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")
        retry_counts: dict[str, int] = {"e-1": MAX_STREAM_RETRIES - 1}

        await handle_consumer_retry("e-1", "TICK", {"data": "1"}, queue, redis_client, config, retry_counts)

        assert "e-1" not in retry_counts
        assert queue.empty()
        redis_client.xack.assert_called_once_with("s", "g", "e-1")


class TestConsumeStreamQueue:
    """Tests for consume_stream_queue."""

    @pytest.mark.asyncio
    async def test_acks_on_success(self):
        queue: asyncio.Queue = asyncio.Queue()
        queue.put_nowait(("entry-1", "TICKER", {"ticker": "TICKER"}))
        queue.put_nowait(None)
        handler = AsyncMock()
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")
        retry_counts: dict[str, int] = {}

        await consume_stream_queue(queue, handler, redis_client, config, "test", retry_counts)

        handler.assert_called_once_with("TICKER", {"ticker": "TICKER"})
        redis_client.xack.assert_called_once_with("s", "g", "entry-1")

    @pytest.mark.asyncio
    async def test_handles_handler_error(self):
        queue: asyncio.Queue = asyncio.Queue()
        queue.put_nowait(("entry-1", "TICKER", {"ticker": "TICKER"}))
        queue.put_nowait(None)
        handler = AsyncMock(side_effect=RuntimeError("handler failed"))
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")
        retry_counts: dict[str, int] = {}

        await consume_stream_queue(queue, handler, redis_client, config, "test", retry_counts)

        redis_client.xack.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_malformed_item(self):
        queue: asyncio.Queue = asyncio.Queue()
        queue.put_nowait(("only_two_elements",))
        queue.put_nowait(None)
        handler = AsyncMock()
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")

        await consume_stream_queue(queue, handler, redis_client, config, "test", {})

        handler.assert_not_called()
