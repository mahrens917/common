"""Tests for alerter_helpers.price_validation_tracker module."""

from unittest.mock import patch

import pytest

from common.alerter_helpers.price_validation_tracker import PriceValidationTracker


class TestPriceValidationTrackerInit:
    """Tests for PriceValidationTracker initialization."""

    def test_initializes_empty_alerts(self) -> None:
        """Test initializes with empty active alerts."""
        tracker = PriceValidationTracker()

        assert tracker.active_price_alerts == {}


class TestPriceValidationTrackerShouldSendAlert:
    """Tests for should_send_alert method."""

    @patch("common.alerter_helpers.price_validation_tracker.time.time")
    def test_sends_first_alert(self, mock_time) -> None:
        """Test sends first alert for currency."""
        mock_time.return_value = 1000.0
        tracker = PriceValidationTracker()
        details = {"kalshi_price": 100000, "cfb_price": 99000, "diff": 1000}

        result = tracker.should_send_alert("BTC", details)

        assert result is True
        assert "cfb_price_validation_BTC" in tracker.active_price_alerts
        assert tracker.active_price_alerts["cfb_price_validation_BTC"]["currency"] == "BTC"
        assert tracker.active_price_alerts["cfb_price_validation_BTC"]["first_alert_time"] == 1000.0
        assert tracker.active_price_alerts["cfb_price_validation_BTC"]["details"] == details

    def test_suppresses_subsequent_alert(self) -> None:
        """Test suppresses subsequent alerts for same currency."""
        tracker = PriceValidationTracker()
        details1 = {"kalshi_price": 100000, "cfb_price": 99000}
        details2 = {"kalshi_price": 100000, "cfb_price": 98000}

        # First alert should send
        result1 = tracker.should_send_alert("BTC", details1)
        # Second alert should be suppressed
        result2 = tracker.should_send_alert("BTC", details2)

        assert result1 is True
        assert result2 is False

    def test_tracks_currencies_independently(self) -> None:
        """Test tracks different currencies independently."""
        tracker = PriceValidationTracker()
        btc_details = {"kalshi_price": 100000, "cfb_price": 99000}
        eth_details = {"kalshi_price": 4000, "cfb_price": 3900}

        # Both should send - different currencies
        result_btc = tracker.should_send_alert("BTC", btc_details)
        result_eth = tracker.should_send_alert("ETH", eth_details)

        assert result_btc is True
        assert result_eth is True
        assert "cfb_price_validation_BTC" in tracker.active_price_alerts
        assert "cfb_price_validation_ETH" in tracker.active_price_alerts


class TestPriceValidationTrackerClearAlert:
    """Tests for clear_alert method."""

    def test_clears_active_alert(self) -> None:
        """Test clears active alert."""
        tracker = PriceValidationTracker()
        tracker.should_send_alert("BTC", {"price": 100000})

        result = tracker.clear_alert("BTC")

        assert result is True
        assert "cfb_price_validation_BTC" not in tracker.active_price_alerts

    def test_returns_false_for_inactive_alert(self) -> None:
        """Test returns False when no active alert."""
        tracker = PriceValidationTracker()

        result = tracker.clear_alert("BTC")

        assert result is False

    def test_only_clears_specified_currency(self) -> None:
        """Test only clears specified currency."""
        tracker = PriceValidationTracker()
        tracker.should_send_alert("BTC", {"price": 100000})
        tracker.should_send_alert("ETH", {"price": 4000})

        tracker.clear_alert("BTC")

        assert "cfb_price_validation_BTC" not in tracker.active_price_alerts
        assert "cfb_price_validation_ETH" in tracker.active_price_alerts


class TestPriceValidationTrackerIsAlertActive:
    """Tests for is_alert_active method."""

    def test_returns_true_when_active(self) -> None:
        """Test returns True when alert is active."""
        tracker = PriceValidationTracker()
        tracker.should_send_alert("BTC", {"price": 100000})

        result = tracker.is_alert_active("BTC")

        assert result is True

    def test_returns_false_when_inactive(self) -> None:
        """Test returns False when alert is not active."""
        tracker = PriceValidationTracker()

        result = tracker.is_alert_active("BTC")

        assert result is False

    def test_returns_false_after_clearing(self) -> None:
        """Test returns False after clearing alert."""
        tracker = PriceValidationTracker()
        tracker.should_send_alert("BTC", {"price": 100000})
        tracker.clear_alert("BTC")

        result = tracker.is_alert_active("BTC")

        assert result is False


class TestPriceValidationTrackerAlertFlow:
    """Tests for complete alert flow scenarios."""

    def test_alert_reactivates_after_clear(self) -> None:
        """Test alert can be sent again after clearing."""
        tracker = PriceValidationTracker()

        # First alert
        result1 = tracker.should_send_alert("BTC", {"price": 100000})
        assert result1 is True

        # Suppressed
        result2 = tracker.should_send_alert("BTC", {"price": 100000})
        assert result2 is False

        # Clear
        tracker.clear_alert("BTC")

        # New alert should send
        result3 = tracker.should_send_alert("BTC", {"price": 100000})
        assert result3 is True

    def test_multiple_currencies_lifecycle(self) -> None:
        """Test multiple currencies with full lifecycle."""
        tracker = PriceValidationTracker()

        # Activate both
        tracker.should_send_alert("BTC", {"price": 100000})
        tracker.should_send_alert("ETH", {"price": 4000})

        # Both active
        assert tracker.is_alert_active("BTC") is True
        assert tracker.is_alert_active("ETH") is True

        # Clear BTC only
        tracker.clear_alert("BTC")

        # BTC inactive, ETH still active
        assert tracker.is_alert_active("BTC") is False
        assert tracker.is_alert_active("ETH") is True

        # BTC can alert again
        result = tracker.should_send_alert("BTC", {"price": 100000})
        assert result is True
