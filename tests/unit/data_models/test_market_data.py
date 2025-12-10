"""Unit tests for common data_models market_data module."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from common.data_models.market_data import (
    DeribitFuturesData,
    DeribitOptionData,
    Instrument,
    MicroPriceMetrics,
    MicroPriceOptionData,
)


class TestDeribitFuturesData:
    """Tests for DeribitFuturesData dataclass."""

    def test_valid_creation_required_fields_only(self):
        """Test creating DeribitFuturesData with required fields."""
        now = datetime.now(timezone.utc)
        data = DeribitFuturesData(
            instrument_name="BTC-29DEC23",
            underlying="BTC",
            expiry_timestamp=1703865600,
            bid_price=45000.0,
            ask_price=45100.0,
            best_bid_size=10.0,
            best_ask_size=8.0,
            timestamp=now,
        )

        assert data.instrument_name == "BTC-29DEC23"
        assert data.underlying == "BTC"
        assert data.expiry_timestamp == 1703865600
        assert data.bid_price == 45000.0
        assert data.ask_price == 45100.0
        assert data.best_bid_size == 10.0
        assert data.best_ask_size == 8.0
        assert data.timestamp == now
        # Check auto-set values
        assert data.best_bid == 45000.0
        assert data.best_ask == 45100.0

    def test_valid_creation_with_optional_fields(self):
        """Test creating DeribitFuturesData with optional fields."""
        now = datetime.now(timezone.utc)
        data = DeribitFuturesData(
            instrument_name="BTC-29DEC23",
            underlying="BTC",
            expiry_timestamp=1703865600,
            bid_price=45000.0,
            ask_price=45100.0,
            best_bid_size=10.0,
            best_ask_size=8.0,
            timestamp=now,
            best_bid=45010.0,
            best_ask=45090.0,
            index_price=45050.0,
            open_interest=1000.0,
            volume_24h=5000.0,
        )

        assert data.best_bid == 45010.0  # Uses provided value
        assert data.best_ask == 45090.0  # Uses provided value
        assert data.index_price == 45050.0
        assert data.open_interest == 1000.0
        assert data.volume_24h == 5000.0

    def test_negative_bid_price_raises_error(self):
        """Test that negative bid price raises ValueError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Bid price cannot be negative"):
            DeribitFuturesData(
                instrument_name="BTC-29DEC23",
                underlying="BTC",
                expiry_timestamp=1703865600,
                bid_price=-100.0,
                ask_price=45100.0,
                best_bid_size=10.0,
                best_ask_size=8.0,
                timestamp=now,
            )

    def test_negative_ask_price_raises_error(self):
        """Test that negative ask price raises ValueError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Ask price cannot be negative"):
            DeribitFuturesData(
                instrument_name="BTC-29DEC23",
                underlying="BTC",
                expiry_timestamp=1703865600,
                bid_price=45000.0,
                ask_price=-100.0,
                best_bid_size=10.0,
                best_ask_size=8.0,
                timestamp=now,
            )

    def test_ask_less_than_bid_raises_error(self):
        """Test that ask < bid raises ValueError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Ask price .* must be >= bid price"):
            DeribitFuturesData(
                instrument_name="BTC-29DEC23",
                underlying="BTC",
                expiry_timestamp=1703865600,
                bid_price=45100.0,
                ask_price=45000.0,
                best_bid_size=10.0,
                best_ask_size=8.0,
                timestamp=now,
            )

    def test_negative_bid_size_raises_error(self):
        """Test that negative bid size raises ValueError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Bid size cannot be negative"):
            DeribitFuturesData(
                instrument_name="BTC-29DEC23",
                underlying="BTC",
                expiry_timestamp=1703865600,
                bid_price=45000.0,
                ask_price=45100.0,
                best_bid_size=-10.0,
                best_ask_size=8.0,
                timestamp=now,
            )

    def test_negative_ask_size_raises_error(self):
        """Test that negative ask size raises ValueError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Ask size cannot be negative"):
            DeribitFuturesData(
                instrument_name="BTC-29DEC23",
                underlying="BTC",
                expiry_timestamp=1703865600,
                bid_price=45000.0,
                ask_price=45100.0,
                best_bid_size=10.0,
                best_ask_size=-8.0,
                timestamp=now,
            )


class TestDeribitOptionData:
    """Tests for DeribitOptionData dataclass."""

    def test_valid_creation_required_fields_only(self):
        """Test creating DeribitOptionData with required fields."""
        now = datetime.now(timezone.utc)
        data = DeribitOptionData(
            instrument_name="BTC-29DEC23-45000-C",
            underlying="BTC",
            strike=45000.0,
            expiry_timestamp=1703865600,
            option_type="call",
            bid_price=1500.0,
            ask_price=1550.0,
            best_bid_size=5.0,
            best_ask_size=3.0,
            timestamp=now,
        )

        assert data.instrument_name == "BTC-29DEC23-45000-C"
        assert data.underlying == "BTC"
        assert data.strike == 45000.0
        assert data.expiry_timestamp == 1703865600
        assert data.option_type == "call"
        assert data.bid_price == 1500.0
        assert data.ask_price == 1550.0
        assert data.best_bid_size == 5.0
        assert data.best_ask_size == 3.0
        assert data.cf_conversion_applied is False
        assert data.cf_conversion_factor is None

    def test_valid_creation_with_greeks(self):
        """Test creating DeribitOptionData with Greeks."""
        now = datetime.now(timezone.utc)
        data = DeribitOptionData(
            instrument_name="BTC-29DEC23-45000-C",
            underlying="BTC",
            strike=45000.0,
            expiry_timestamp=1703865600,
            option_type="call",
            bid_price=1500.0,
            ask_price=1550.0,
            best_bid_size=5.0,
            best_ask_size=3.0,
            timestamp=now,
            delta=0.5,
            gamma=0.00001,
            theta=-10.0,
            vega=50.0,
            rho=20.0,
            implied_volatility=0.65,
        )

        assert data.delta == 0.5
        assert data.gamma == 0.00001
        assert data.theta == -10.0
        assert data.vega == 50.0
        assert data.rho == 20.0
        assert data.implied_volatility == 0.65

    def test_valid_creation_with_cf_conversion(self):
        """Test creating DeribitOptionData with CF conversion metadata."""
        now = datetime.now(timezone.utc)
        data = DeribitOptionData(
            instrument_name="BTC-29DEC23-45000-C",
            underlying="BTC",
            strike=45000.0,
            expiry_timestamp=1703865600,
            option_type="call",
            bid_price=1500.0,
            ask_price=1550.0,
            best_bid_size=5.0,
            best_ask_size=3.0,
            timestamp=now,
            cf_conversion_applied=True,
            cf_conversion_factor=1.05,
        )

        assert data.cf_conversion_applied is True
        assert data.cf_conversion_factor == 1.05

    def test_zero_strike_raises_error(self):
        """Test that zero strike raises ValueError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Strike price must be positive"):
            DeribitOptionData(
                instrument_name="BTC-29DEC23-0-C",
                underlying="BTC",
                strike=0.0,
                expiry_timestamp=1703865600,
                option_type="call",
                bid_price=1500.0,
                ask_price=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
            )

    def test_negative_strike_raises_error(self):
        """Test that negative strike raises ValueError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Strike price must be positive"):
            DeribitOptionData(
                instrument_name="BTC-29DEC23--1000-C",
                underlying="BTC",
                strike=-1000.0,
                expiry_timestamp=1703865600,
                option_type="call",
                bid_price=1500.0,
                ask_price=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
            )

    def test_negative_bid_price_raises_error(self):
        """Test that negative bid price raises ValueError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Bid price cannot be negative"):
            DeribitOptionData(
                instrument_name="BTC-29DEC23-45000-C",
                underlying="BTC",
                strike=45000.0,
                expiry_timestamp=1703865600,
                option_type="call",
                bid_price=-100.0,
                ask_price=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
            )

    def test_ask_less_than_bid_raises_error(self):
        """Test that ask < bid raises ValueError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Ask price .* must be >= bid price"):
            DeribitOptionData(
                instrument_name="BTC-29DEC23-45000-C",
                underlying="BTC",
                strike=45000.0,
                expiry_timestamp=1703865600,
                option_type="call",
                bid_price=1550.0,
                ask_price=1500.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
            )


class TestMicroPriceMetrics:
    """Tests for MicroPriceMetrics dataclass."""

    def test_valid_creation(self):
        """Test creating MicroPriceMetrics with all fields."""
        metrics = MicroPriceMetrics(
            absolute_spread=50.0,
            relative_spread=0.001,
            i_raw=1500.0,
            p_raw=0.03,
            g=0.95,
            h=1.05,
        )

        assert metrics.absolute_spread == 50.0
        assert metrics.relative_spread == 0.001
        assert metrics.i_raw == 1500.0
        assert metrics.p_raw == 0.03
        assert metrics.g == 0.95
        assert metrics.h == 1.05

    def test_frozen_immutable(self):
        """Test that MicroPriceMetrics is frozen/immutable."""
        metrics = MicroPriceMetrics(
            absolute_spread=50.0,
            relative_spread=0.001,
            i_raw=1500.0,
            p_raw=0.03,
            g=0.95,
            h=1.05,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            metrics.g = 0.99


class TestMicroPriceOptionData:
    """Tests for MicroPriceOptionData dataclass."""

    def test_valid_creation(self):
        """Test creating MicroPriceOptionData with all required fields."""
        now = datetime.now(timezone.utc)
        expiry = datetime(2023, 12, 29, tzinfo=timezone.utc)

        with (
            patch("common.data_models.market_data.MicroPriceValidator.validate_basic_option_data"),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_micro_price_calculations"
            ),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_mathematical_relationships"
            ),
        ):
            data = MicroPriceOptionData(
                instrument_name="BTC-29DEC23-45000-C",
                underlying="BTC",
                strike=45000.0,
                expiry=expiry,
                option_type="call",
                best_bid=1500.0,
                best_ask=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
                absolute_spread=50.0,
                relative_spread=0.001,
                i_raw=1500.0,
                p_raw=0.03,
                g=0.95,
                h=1.05,
            )

            assert data.instrument_name == "BTC-29DEC23-45000-C"
            assert data.strike == 45000.0
            assert data.option_type == "call"
            assert data.absolute_spread == 50.0
            assert data.g == 0.95
            assert data.h == 1.05

    def test_validation_called_on_init(self):
        """Test that validation is called during initialization."""
        now = datetime.now(timezone.utc)
        expiry = datetime(2023, 12, 29, tzinfo=timezone.utc)

        with (
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_basic_option_data"
            ) as mock_validate,
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_micro_price_calculations"
            ),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_mathematical_relationships"
            ),
        ):
            MicroPriceOptionData(
                instrument_name="BTC-29DEC23-45000-C",
                underlying="BTC",
                strike=45000.0,
                expiry=expiry,
                option_type="call",
                best_bid=1500.0,
                best_ask=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
                absolute_spread=50.0,
                relative_spread=0.001,
                i_raw=1500.0,
                p_raw=0.03,
                g=0.95,
                h=1.05,
            )

            mock_validate.assert_called_once()


class TestMicroPriceOptionDataMethods:
    """Tests for MicroPriceOptionData methods (delegated to helpers)."""

    def test_validate_micro_price_constraints(self):
        """Test validate_micro_price_constraints method."""
        now = datetime.now(timezone.utc)
        expiry = datetime(2023, 12, 29, tzinfo=timezone.utc)

        with (
            patch("common.data_models.market_data.MicroPriceValidator.validate_basic_option_data"),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_micro_price_calculations"
            ),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_mathematical_relationships"
            ),
        ):
            data = MicroPriceOptionData(
                instrument_name="BTC-29DEC23-45000-C",
                underlying="BTC",
                strike=45000.0,
                expiry=expiry,
                option_type="call",
                best_bid=1500.0,
                best_ask=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
                absolute_spread=50.0,
                relative_spread=0.001,
                i_raw=1500.0,
                p_raw=0.03,
                g=0.95,
                h=1.05,
            )

        with patch(
            "common.data_models.market_data.MicroPriceValidator.validate_micro_price_constraints",
            return_value=True,
        ):
            result = data.validate_micro_price_constraints()
            assert result is True

    def test_is_valid(self):
        """Test is_valid method."""
        now = datetime.now(timezone.utc)
        expiry = datetime(2023, 12, 29, tzinfo=timezone.utc)

        with (
            patch("common.data_models.market_data.MicroPriceValidator.validate_basic_option_data"),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_micro_price_calculations"
            ),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_mathematical_relationships"
            ),
        ):
            data = MicroPriceOptionData(
                instrument_name="BTC-29DEC23-45000-C",
                underlying="BTC",
                strike=45000.0,
                expiry=expiry,
                option_type="call",
                best_bid=1500.0,
                best_ask=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
                absolute_spread=50.0,
                relative_spread=0.001,
                i_raw=1500.0,
                p_raw=0.03,
                g=0.95,
                h=1.05,
            )

        with patch(
            "common.data_models.market_data.MicroPriceValidator.get_validation_errors",
            return_value=[],
        ):
            assert data.is_valid() is True

    def test_get_validation_errors(self):
        """Test get_validation_errors method."""
        now = datetime.now(timezone.utc)
        expiry = datetime(2023, 12, 29, tzinfo=timezone.utc)

        with (
            patch("common.data_models.market_data.MicroPriceValidator.validate_basic_option_data"),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_micro_price_calculations"
            ),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_mathematical_relationships"
            ),
        ):
            data = MicroPriceOptionData(
                instrument_name="BTC-29DEC23-45000-C",
                underlying="BTC",
                strike=45000.0,
                expiry=expiry,
                option_type="call",
                best_bid=1500.0,
                best_ask=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
                absolute_spread=50.0,
                relative_spread=0.001,
                i_raw=1500.0,
                p_raw=0.03,
                g=0.95,
                h=1.05,
            )

        with patch(
            "common.data_models.market_data.MicroPriceValidator.get_validation_errors",
            return_value=["Error 1", "Error 2"],
        ):
            errors = data.get_validation_errors()
            assert errors == ["Error 1", "Error 2"]

    def test_intrinsic_value(self):
        """Test intrinsic_value method."""
        now = datetime.now(timezone.utc)
        expiry = datetime(2023, 12, 29, tzinfo=timezone.utc)

        with (
            patch("common.data_models.market_data.MicroPriceValidator.validate_basic_option_data"),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_micro_price_calculations"
            ),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_mathematical_relationships"
            ),
        ):
            data = MicroPriceOptionData(
                instrument_name="BTC-29DEC23-45000-C",
                underlying="BTC",
                strike=45000.0,
                expiry=expiry,
                option_type="call",
                best_bid=1500.0,
                best_ask=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
                absolute_spread=50.0,
                relative_spread=0.001,
                i_raw=1500.0,
                p_raw=0.03,
                g=0.95,
                h=1.05,
            )

        with patch(
            "common.data_models.market_data.MicroPriceCalculator.compute_intrinsic_value",
            return_value=2000.0,
        ):
            intrinsic = data.intrinsic_value(47000.0)
            assert intrinsic == 2000.0

    def test_time_value(self):
        """Test time_value method."""
        now = datetime.now(timezone.utc)
        expiry = datetime(2023, 12, 29, tzinfo=timezone.utc)

        with (
            patch("common.data_models.market_data.MicroPriceValidator.validate_basic_option_data"),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_micro_price_calculations"
            ),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_mathematical_relationships"
            ),
        ):
            data = MicroPriceOptionData(
                instrument_name="BTC-29DEC23-45000-C",
                underlying="BTC",
                strike=45000.0,
                expiry=expiry,
                option_type="call",
                best_bid=1500.0,
                best_ask=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
                absolute_spread=50.0,
                relative_spread=0.001,
                i_raw=1500.0,
                p_raw=0.03,
                g=0.95,
                h=1.05,
            )

        with patch(
            "common.data_models.market_data.MicroPriceCalculator.compute_time_value",
            return_value=500.0,
        ):
            time_val = data.time_value(47000.0)
            assert time_val == 500.0


class TestMicroPriceOptionDataProperties:
    """Tests for MicroPriceOptionData properties."""

    def test_is_future_property(self):
        """Test is_future property."""
        now = datetime.now(timezone.utc)
        expiry = datetime(2023, 12, 29, tzinfo=timezone.utc)

        with (
            patch("common.data_models.market_data.MicroPriceValidator.validate_basic_option_data"),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_micro_price_calculations"
            ),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_mathematical_relationships"
            ),
        ):
            data = MicroPriceOptionData(
                instrument_name="BTC-29DEC23-45000-C",
                underlying="BTC",
                strike=45000.0,
                expiry=expiry,
                option_type="call",
                best_bid=1500.0,
                best_ask=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
                absolute_spread=50.0,
                relative_spread=0.001,
                i_raw=1500.0,
                p_raw=0.03,
                g=0.95,
                h=1.05,
            )

        with patch(
            "common.data_models.market_data.MicroPriceProperties.get_is_future",
            return_value=False,
        ):
            assert data.is_future is False

    def test_bid_price_property(self):
        """Test bid_price property."""
        now = datetime.now(timezone.utc)
        expiry = datetime(2023, 12, 29, tzinfo=timezone.utc)

        with (
            patch("common.data_models.market_data.MicroPriceValidator.validate_basic_option_data"),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_micro_price_calculations"
            ),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_mathematical_relationships"
            ),
        ):
            data = MicroPriceOptionData(
                instrument_name="BTC-29DEC23-45000-C",
                underlying="BTC",
                strike=45000.0,
                expiry=expiry,
                option_type="call",
                best_bid=1500.0,
                best_ask=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
                absolute_spread=50.0,
                relative_spread=0.001,
                i_raw=1500.0,
                p_raw=0.03,
                g=0.95,
                h=1.05,
            )

        with patch(
            "common.data_models.market_data.MicroPriceProperties.get_bid_price",
            return_value=1500.0,
        ):
            assert data.bid_price == 1500.0

    def test_mid_price_property(self):
        """Test mid_price property."""
        now = datetime.now(timezone.utc)
        expiry = datetime(2023, 12, 29, tzinfo=timezone.utc)

        with (
            patch("common.data_models.market_data.MicroPriceValidator.validate_basic_option_data"),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_micro_price_calculations"
            ),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_mathematical_relationships"
            ),
        ):
            data = MicroPriceOptionData(
                instrument_name="BTC-29DEC23-45000-C",
                underlying="BTC",
                strike=45000.0,
                expiry=expiry,
                option_type="call",
                best_bid=1500.0,
                best_ask=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
                absolute_spread=50.0,
                relative_spread=0.001,
                i_raw=1500.0,
                p_raw=0.03,
                g=0.95,
                h=1.05,
            )

        with patch(
            "common.data_models.market_data.MicroPriceProperties.get_mid_price",
            return_value=1525.0,
        ):
            assert data.mid_price == 1525.0

    def test_is_call_property(self):
        """Test is_call property."""
        now = datetime.now(timezone.utc)
        expiry = datetime(2023, 12, 29, tzinfo=timezone.utc)

        with (
            patch("common.data_models.market_data.MicroPriceValidator.validate_basic_option_data"),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_micro_price_calculations"
            ),
            patch(
                "common.data_models.market_data.MicroPriceValidator.validate_mathematical_relationships"
            ),
        ):
            data = MicroPriceOptionData(
                instrument_name="BTC-29DEC23-45000-C",
                underlying="BTC",
                strike=45000.0,
                expiry=expiry,
                option_type="call",
                best_bid=1500.0,
                best_ask=1550.0,
                best_bid_size=5.0,
                best_ask_size=3.0,
                timestamp=now,
                absolute_spread=50.0,
                relative_spread=0.001,
                i_raw=1500.0,
                p_raw=0.03,
                g=0.95,
                h=1.05,
            )

        with patch(
            "common.data_models.market_data.MicroPriceProperties.check_is_call",
            return_value=True,
        ):
            assert data.is_call is True


class TestInstrument:
    """Tests for Instrument dataclass."""

    def test_valid_creation_required_fields_only(self):
        """Test creating Instrument with required fields."""
        inst = Instrument(instrument_name="BTC-PERPETUAL", underlying="BTC", expiry_timestamp=0)

        assert inst.instrument_name == "BTC-PERPETUAL"
        assert inst.underlying == "BTC"
        assert inst.expiry_timestamp == 0
        assert inst.bid_price is None
        assert inst.ask_price is None

    def test_valid_creation_with_all_fields(self):
        """Test creating Instrument with all fields."""
        now = datetime.now(timezone.utc)
        inst = Instrument(
            instrument_name="BTC-29DEC23",
            underlying="BTC",
            expiry_timestamp=1703865600,
            bid_price=45000.0,
            ask_price=45100.0,
            last_price=45050.0,
            best_bid_size=10.0,
            best_ask_size=8.0,
            timestamp=now,
        )

        assert inst.bid_price == 45000.0
        assert inst.ask_price == 45100.0
        assert inst.last_price == 45050.0
        assert inst.best_bid_size == 10.0
        assert inst.best_ask_size == 8.0
        assert inst.timestamp == now

    def test_negative_bid_price_raises_error(self):
        """Test that negative bid price raises ValueError."""
        with pytest.raises(ValueError, match="Bid price cannot be negative"):
            Instrument(
                instrument_name="BTC-PERPETUAL",
                underlying="BTC",
                expiry_timestamp=0,
                bid_price=-100.0,
            )

    def test_negative_ask_price_raises_error(self):
        """Test that negative ask price raises ValueError."""
        with pytest.raises(ValueError, match="Ask price cannot be negative"):
            Instrument(
                instrument_name="BTC-PERPETUAL",
                underlying="BTC",
                expiry_timestamp=0,
                ask_price=-100.0,
            )

    def test_ask_less_than_bid_raises_error(self):
        """Test that ask < bid raises ValueError."""
        with pytest.raises(ValueError, match="Ask price .* must be >= bid price"):
            Instrument(
                instrument_name="BTC-PERPETUAL",
                underlying="BTC",
                expiry_timestamp=0,
                bid_price=45100.0,
                ask_price=45000.0,
            )

    def test_none_prices_do_not_raise_error(self):
        """Test that None prices do not trigger validation errors."""
        # Should not raise any exception
        inst = Instrument(
            instrument_name="BTC-PERPETUAL",
            underlying="BTC",
            expiry_timestamp=0,
            bid_price=None,
            ask_price=None,
        )

        assert inst.bid_price is None
        assert inst.ask_price is None
