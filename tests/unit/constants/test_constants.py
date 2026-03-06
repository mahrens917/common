"""Tests for common constants modules."""

from __future__ import annotations

from common.constants import (
    FINE_PRECISION,
    FLOAT_TOLERANCE,
    HIGH_PRECISION,
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_OK,
    MIN_KEY_PARTS,
    MIN_TRADE_REASON_LENGTH,
    STANDARD_PRECISION,
    UTILIZATION_WARNING_THRESHOLD,
    WEBSOCKET_ABNORMAL_CLOSURE,
)


class TestMathConstants:
    """Tests for math constants."""

    def test_float_tolerance_is_small_positive(self) -> None:
        assert FLOAT_TOLERANCE > 0
        assert FLOAT_TOLERANCE < 1e-5

    def test_precision_constants_are_positive(self) -> None:
        assert HIGH_PRECISION > 0
        assert STANDARD_PRECISION > 0
        assert FINE_PRECISION > 0

    def test_precision_ordering(self) -> None:
        assert HIGH_PRECISION < STANDARD_PRECISION < FINE_PRECISION


class TestNetworkConstants:
    """Tests for network constants."""

    def test_http_ok_status_code(self) -> None:
        assert HTTP_OK == 200

    def test_http_internal_server_error_status_code(self) -> None:
        assert HTTP_INTERNAL_SERVER_ERROR == 500

    def test_websocket_abnormal_closure_code(self) -> None:
        assert WEBSOCKET_ABNORMAL_CLOSURE == 1006


class TestValidationConstants:
    """Tests for validation constants."""

    def test_min_key_parts_is_positive(self) -> None:
        assert MIN_KEY_PARTS > 0
        assert isinstance(MIN_KEY_PARTS, int)

    def test_min_trade_reason_length_is_positive(self) -> None:
        assert MIN_TRADE_REASON_LENGTH > 0
        assert isinstance(MIN_TRADE_REASON_LENGTH, int)

    def test_utilization_warning_threshold_is_percentage(self) -> None:
        assert 0 < UTILIZATION_WARNING_THRESHOLD <= 100
        assert isinstance(UTILIZATION_WARNING_THRESHOLD, int)
