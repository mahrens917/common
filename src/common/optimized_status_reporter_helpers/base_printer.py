"""Shared base for status line printers."""

from .status_line import emit_status_line


class StatusLinePrinterBase:
    """Provides data coercion and status line emitter helpers."""

    def __init__(self, data_coercion):
        self.data_coercion = data_coercion
        self._emit_status_line = emit_status_line


__all__ = ["StatusLinePrinterBase"]
