"""Tests for message decoder."""

from common.redis_protocol.streams.message_decoder import decode_stream_response


class TestDecodeStreamResponse:
    """Tests for decode_stream_response function."""

    def test_decodes_bytes_response(self):
        raw = [
            [
                b"stream:test",
                [
                    (b"1234-0", {b"ticker": b"AAPL", b"price": b"150"}),
                ],
            ]
        ]

        result = decode_stream_response(raw)

        assert len(result) == 1
        assert result[0] == ("1234-0", {"ticker": "AAPL", "price": "150"})

    def test_decodes_string_response(self):
        raw = [
            [
                "stream:test",
                [
                    ("1234-0", {"ticker": "AAPL", "price": "150"}),
                ],
            ]
        ]

        result = decode_stream_response(raw)

        assert len(result) == 1
        assert result[0] == ("1234-0", {"ticker": "AAPL", "price": "150"})

    def test_multiple_entries(self):
        raw = [
            [
                b"stream:test",
                [
                    (b"1234-0", {b"ticker": b"AAPL"}),
                    (b"1234-1", {b"ticker": b"GOOG"}),
                ],
            ]
        ]

        result = decode_stream_response(raw)

        assert len(result) == 2
        assert result[0][1]["ticker"] == "AAPL"
        assert result[1][1]["ticker"] == "GOOG"

    def test_multiple_streams(self):
        raw = [
            [b"stream:a", [(b"1-0", {b"k": b"v1"})]],
            [b"stream:b", [(b"2-0", {b"k": b"v2"})]],
        ]

        result = decode_stream_response(raw)

        assert len(result) == 2

    def test_empty_response(self):
        assert decode_stream_response(None) == []
        assert decode_stream_response([]) == []

    def test_empty_stream_entries(self):
        raw = [[b"stream:test", []]]

        result = decode_stream_response(raw)

        assert result == []
