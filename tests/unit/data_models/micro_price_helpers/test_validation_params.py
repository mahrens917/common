"""Tests for validation params module."""

from common.data_models.micro_price_helpers.validation_params import (
    BasicOptionData,
    MathematicalRelationships,
    PostInitValidationParams,
    ValidationErrorParams,
)


class TestBasicOptionData:
    """Tests for BasicOptionData dataclass."""

    def test_creation_with_required_fields(self) -> None:
        """Creates instance with required fields."""
        data = BasicOptionData(
            strike=100.0,
            best_bid=0.05,
            best_ask=0.10,
            best_bid_size=10.0,
            best_ask_size=20.0,
            option_type="call",
        )

        assert data.strike == 100.0
        assert data.best_bid == 0.05
        assert data.best_ask == 0.10
        assert data.best_bid_size == 10.0
        assert data.best_ask_size == 20.0
        assert data.option_type == "call"

    def test_forward_price_defaults_to_none(self) -> None:
        """Forward price defaults to None."""
        data = BasicOptionData(
            strike=100.0,
            best_bid=0.05,
            best_ask=0.10,
            best_bid_size=10.0,
            best_ask_size=20.0,
            option_type="call",
        )

        assert data.forward_price is None

    def test_discount_factor_defaults_to_none(self) -> None:
        """Discount factor defaults to None."""
        data = BasicOptionData(
            strike=100.0,
            best_bid=0.05,
            best_ask=0.10,
            best_bid_size=10.0,
            best_ask_size=20.0,
            option_type="call",
        )

        assert data.discount_factor is None

    def test_optional_fields_can_be_set(self) -> None:
        """Optional fields can be set."""
        data = BasicOptionData(
            strike=100.0,
            best_bid=0.05,
            best_ask=0.10,
            best_bid_size=10.0,
            best_ask_size=20.0,
            option_type="put",
            forward_price=50000.0,
            discount_factor=0.99,
        )

        assert data.forward_price == 50000.0
        assert data.discount_factor == 0.99


class TestMathematicalRelationships:
    """Tests for MathematicalRelationships dataclass."""

    def test_creation_with_all_fields(self) -> None:
        """Creates instance with all fields."""
        relationships = MathematicalRelationships(
            best_bid=0.05,
            best_ask=0.10,
            best_bid_size=10.0,
            best_ask_size=20.0,
            absolute_spread=0.05,
            relative_spread=0.667,
            i_raw=0.333,
            p_raw=0.0667,
            g=0.5,
            h=0.5,
        )

        assert relationships.best_bid == 0.05
        assert relationships.best_ask == 0.10
        assert relationships.absolute_spread == 0.05
        assert relationships.relative_spread == 0.667
        assert relationships.i_raw == 0.333
        assert relationships.p_raw == 0.0667
        assert relationships.g == 0.5
        assert relationships.h == 0.5


class TestValidationErrorParams:
    """Tests for ValidationErrorParams dataclass."""

    def test_creation_with_all_fields(self) -> None:
        """Creates instance with all fields."""
        params = ValidationErrorParams(
            best_bid=0.05,
            best_ask=0.10,
            best_bid_size=10.0,
            best_ask_size=20.0,
            option_type="call",
            absolute_spread=0.05,
            i_raw=0.333,
            p_raw=0.0667,
        )

        assert params.best_bid == 0.05
        assert params.best_ask == 0.10
        assert params.best_bid_size == 10.0
        assert params.best_ask_size == 20.0
        assert params.option_type == "call"
        assert params.absolute_spread == 0.05
        assert params.i_raw == 0.333
        assert params.p_raw == 0.0667


class TestPostInitValidationParams:
    """Tests for PostInitValidationParams dataclass."""

    def test_creation_with_all_fields(self) -> None:
        """Creates instance with all fields."""
        params = PostInitValidationParams(
            strike=100.0,
            best_bid=0.05,
            best_ask=0.10,
            best_bid_size=10.0,
            best_ask_size=20.0,
            option_type="put",
            forward_price=50000.0,
            discount_factor=0.99,
            absolute_spread=0.05,
            relative_spread=0.667,
            i_raw=0.333,
            p_raw=0.0667,
            g=0.5,
            h=0.5,
        )

        assert params.strike == 100.0
        assert params.forward_price == 50000.0
        assert params.discount_factor == 0.99
        assert params.g == 0.5
        assert params.h == 0.5
