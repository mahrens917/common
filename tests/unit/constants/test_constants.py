"""Tests for common constants modules."""

from __future__ import annotations


class TestMathConstants:
    """Tests for math constants module."""

    def test_float_tolerance_is_small_positive(self) -> None:
        """FLOAT_TOLERANCE should be a small positive value."""
        from common.constants.math import FLOAT_TOLERANCE

        assert FLOAT_TOLERANCE > 0
        assert FLOAT_TOLERANCE < 1e-5

    def test_precision_constants_are_positive(self) -> None:
        """All precision constants should be positive."""
        from common.constants.math import (
            FINE_PRECISION,
            HIGH_PRECISION,
            STANDARD_PRECISION,
        )

        assert HIGH_PRECISION > 0
        assert STANDARD_PRECISION > 0
        assert FINE_PRECISION > 0

    def test_precision_ordering(self) -> None:
        """Precision constants should be ordered by sensitivity."""
        from common.constants.math import (
            FINE_PRECISION,
            HIGH_PRECISION,
            STANDARD_PRECISION,
        )

        assert HIGH_PRECISION < STANDARD_PRECISION < FINE_PRECISION

    def test_math_constants_all_exported(self) -> None:
        """All math constants should be in __all__."""
        from common.constants import math as math_module

        assert "FLOAT_TOLERANCE" in math_module.__all__
        assert "HIGH_PRECISION" in math_module.__all__
        assert "STANDARD_PRECISION" in math_module.__all__
        assert "FINE_PRECISION" in math_module.__all__


class TestNetworkConstants:
    """Tests for network constants module."""

    def test_http_ok_status_code(self) -> None:
        """HTTP_OK should be 200."""
        from common.constants.network import HTTP_OK

        assert HTTP_OK == 200

    def test_http_internal_server_error_status_code(self) -> None:
        """HTTP_INTERNAL_SERVER_ERROR should be 500."""
        from common.constants.network import HTTP_INTERNAL_SERVER_ERROR

        assert HTTP_INTERNAL_SERVER_ERROR == 500

    def test_websocket_abnormal_closure_code(self) -> None:
        """WEBSOCKET_ABNORMAL_CLOSURE should be 1006."""
        from common.constants.network import WEBSOCKET_ABNORMAL_CLOSURE

        assert WEBSOCKET_ABNORMAL_CLOSURE == 1006

    def test_network_constants_all_exported(self) -> None:
        """All network constants should be in __all__."""
        from common.constants import network as network_module

        assert "HTTP_OK" in network_module.__all__
        assert "HTTP_INTERNAL_SERVER_ERROR" in network_module.__all__
        assert "WEBSOCKET_ABNORMAL_CLOSURE" in network_module.__all__


class TestValidationConstants:
    """Tests for validation constants module."""

    def test_min_key_parts_is_positive(self) -> None:
        """MIN_KEY_PARTS should be a positive integer."""
        from common.constants.validation import MIN_KEY_PARTS

        assert MIN_KEY_PARTS > 0
        assert isinstance(MIN_KEY_PARTS, int)

    def test_min_trade_reason_length_is_positive(self) -> None:
        """MIN_TRADE_REASON_LENGTH should be a positive integer."""
        from common.constants.validation import MIN_TRADE_REASON_LENGTH

        assert MIN_TRADE_REASON_LENGTH > 0
        assert isinstance(MIN_TRADE_REASON_LENGTH, int)

    def test_utilization_warning_threshold_is_percentage(self) -> None:
        """UTILIZATION_WARNING_THRESHOLD should be a valid percentage."""
        from common.constants.validation import UTILIZATION_WARNING_THRESHOLD

        assert 0 < UTILIZATION_WARNING_THRESHOLD <= 100
        assert isinstance(UTILIZATION_WARNING_THRESHOLD, int)

    def test_validation_constants_all_exported(self) -> None:
        """All validation constants should be in __all__."""
        from common.constants import validation as validation_module

        assert "MIN_KEY_PARTS" in validation_module.__all__
        assert "MIN_TRADE_REASON_LENGTH" in validation_module.__all__
        assert "UTILIZATION_WARNING_THRESHOLD" in validation_module.__all__
