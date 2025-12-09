from unittest.mock import Mock

import pytest

from src.common.status_reporter_helpers.output_writer import OutputWriter


class TestOutputWriter:
    def test_init_default(self):
        writer = OutputWriter()
        import sys

        assert writer.output_stream == sys.stdout

    def test_init_custom_stream(self):
        stream = Mock()
        writer = OutputWriter(stream)
        assert writer.output_stream == stream

    def test_write_success(self):
        stream = Mock()
        writer = OutputWriter(stream)
        writer.write("Test message")
        # print calls write on the stream
        # Actually print usually calls write multiple times (message + newline)
        # We can mock the stream and assert write was called
        assert stream.write.called

    def test_write_broken_pipe(self):
        stream = Mock()
        stream.write.side_effect = BrokenPipeError("Pipe broken")
        writer = OutputWriter(stream)
        # Should suppress the error
        writer.write("Test message")

    def test_write_os_error(self):
        stream = Mock()
        stream.write.side_effect = OSError("OS Error")
        writer = OutputWriter(stream)
        # Should suppress the error
        writer.write("Test message")
