"""Tests for risk assessor module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.common.emergency_position_manager_helpers.risk_assessor import (
    PositionRiskAssessment,
    RiskAssessor,
    RiskLimits,
    create_test_risk_limits,
)


class TestRiskLimitsInit:
    """Tests for RiskLimits initialization."""

    def test_initializes_with_valid_values(self) -> None:
        """Initializes with valid values."""
        limits = RiskLimits(
            max_position_value_cents=10000,
            max_total_exposure_cents=50000,
            max_unrealized_loss_cents=5000,
            max_position_age_hours=24,
        )

        assert limits.max_position_value_cents == 10000
        assert limits.max_total_exposure_cents == 50000
        assert limits.max_unrealized_loss_cents == 5000
        assert limits.max_position_age_hours == 24

    def test_raises_on_zero_position_value(self) -> None:
        """Raises ValueError on zero max position value."""
        with pytest.raises(ValueError, match="Max position value must be positive"):
            RiskLimits(
                max_position_value_cents=0,
                max_total_exposure_cents=50000,
                max_unrealized_loss_cents=5000,
                max_position_age_hours=24,
            )

    def test_raises_on_negative_position_value(self) -> None:
        """Raises ValueError on negative max position value."""
        with pytest.raises(ValueError, match="Max position value must be positive"):
            RiskLimits(
                max_position_value_cents=-100,
                max_total_exposure_cents=50000,
                max_unrealized_loss_cents=5000,
                max_position_age_hours=24,
            )

    def test_raises_on_zero_total_exposure(self) -> None:
        """Raises ValueError on zero max total exposure."""
        with pytest.raises(ValueError, match="Max total exposure must be positive"):
            RiskLimits(
                max_position_value_cents=10000,
                max_total_exposure_cents=0,
                max_unrealized_loss_cents=5000,
                max_position_age_hours=24,
            )

    def test_raises_on_zero_unrealized_loss(self) -> None:
        """Raises ValueError on zero max unrealized loss."""
        with pytest.raises(ValueError, match="Max unrealized loss must be positive"):
            RiskLimits(
                max_position_value_cents=10000,
                max_total_exposure_cents=50000,
                max_unrealized_loss_cents=0,
                max_position_age_hours=24,
            )

    def test_raises_on_zero_position_age(self) -> None:
        """Raises ValueError on zero max position age."""
        with pytest.raises(ValueError, match="Max position age must be positive"):
            RiskLimits(
                max_position_value_cents=10000,
                max_total_exposure_cents=50000,
                max_unrealized_loss_cents=5000,
                max_position_age_hours=0,
            )


class TestPositionRiskAssessmentRiskScore:
    """Tests for PositionRiskAssessment.risk_score."""

    def test_returns_zero_for_no_limits_exceeded(self) -> None:
        """Returns zero when no limits exceeded."""
        assessment = PositionRiskAssessment(
            ticker="KXBTC-25JAN01",
            current_value_cents=5000,
            unrealized_pnl_cents=100,
            position_age_hours=1.0,
            exceeds_value_limit=False,
            exceeds_loss_limit=False,
            exceeds_age_limit=False,
            requires_closure=False,
        )

        assert assessment.risk_score == 0.0

    def test_returns_0_4_for_value_limit_exceeded(self) -> None:
        """Returns 0.4 when value limit exceeded."""
        assessment = PositionRiskAssessment(
            ticker="KXBTC-25JAN01",
            current_value_cents=15000,
            unrealized_pnl_cents=100,
            position_age_hours=1.0,
            exceeds_value_limit=True,
            exceeds_loss_limit=False,
            exceeds_age_limit=False,
            requires_closure=True,
        )

        assert assessment.risk_score == 0.4

    def test_returns_0_4_for_loss_limit_exceeded(self) -> None:
        """Returns 0.4 when loss limit exceeded."""
        assessment = PositionRiskAssessment(
            ticker="KXBTC-25JAN01",
            current_value_cents=5000,
            unrealized_pnl_cents=-6000,
            position_age_hours=1.0,
            exceeds_value_limit=False,
            exceeds_loss_limit=True,
            exceeds_age_limit=False,
            requires_closure=True,
        )

        assert assessment.risk_score == 0.4

    def test_returns_0_2_for_age_limit_exceeded(self) -> None:
        """Returns 0.2 when age limit exceeded."""
        assessment = PositionRiskAssessment(
            ticker="KXBTC-25JAN01",
            current_value_cents=5000,
            unrealized_pnl_cents=100,
            position_age_hours=30.0,
            exceeds_value_limit=False,
            exceeds_loss_limit=False,
            exceeds_age_limit=True,
            requires_closure=True,
        )

        assert assessment.risk_score == 0.2

    def test_returns_0_8_for_value_and_loss_exceeded(self) -> None:
        """Returns 0.8 when both value and loss limits exceeded."""
        assessment = PositionRiskAssessment(
            ticker="KXBTC-25JAN01",
            current_value_cents=15000,
            unrealized_pnl_cents=-6000,
            position_age_hours=1.0,
            exceeds_value_limit=True,
            exceeds_loss_limit=True,
            exceeds_age_limit=False,
            requires_closure=True,
        )

        assert assessment.risk_score == 0.8

    def test_caps_at_1_0_for_all_exceeded(self) -> None:
        """Caps at 1.0 when all limits exceeded."""
        assessment = PositionRiskAssessment(
            ticker="KXBTC-25JAN01",
            current_value_cents=15000,
            unrealized_pnl_cents=-6000,
            position_age_hours=30.0,
            exceeds_value_limit=True,
            exceeds_loss_limit=True,
            exceeds_age_limit=True,
            requires_closure=True,
        )

        assert assessment.risk_score == 1.0


class TestRiskAssessorInit:
    """Tests for RiskAssessor initialization."""

    def test_initializes_with_risk_limits(self) -> None:
        """Initializes with risk limits."""
        limits = RiskLimits(
            max_position_value_cents=10000,
            max_total_exposure_cents=50000,
            max_unrealized_loss_cents=5000,
            max_position_age_hours=24,
        )

        assessor = RiskAssessor(risk_limits=limits)

        assert assessor.risk_limits is limits


class TestRiskAssessorAssessPositionRisk:
    """Tests for RiskAssessor.assess_position_risk."""

    @pytest.mark.asyncio
    async def test_assesses_position_within_limits(self) -> None:
        """Assesses position within all limits."""
        limits = RiskLimits(
            max_position_value_cents=10000,
            max_total_exposure_cents=50000,
            max_unrealized_loss_cents=5000,
            max_position_age_hours=24,
        )
        assessor = RiskAssessor(risk_limits=limits)
        position = MagicMock()
        position.ticker = "KXBTC-25JAN01"
        position.market_value_cents = 5000
        position.unrealized_pnl_cents = 100
        creation_time = datetime.now(timezone.utc) - timedelta(hours=1)

        with patch("src.common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value = datetime.now(timezone.utc)
            assessment = await assessor.assess_position_risk(position, creation_time)

        assert assessment.exceeds_value_limit is False
        assert assessment.exceeds_loss_limit is False
        assert assessment.exceeds_age_limit is False
        assert assessment.requires_closure is False

    @pytest.mark.asyncio
    async def test_detects_value_limit_exceeded(self) -> None:
        """Detects when value limit exceeded."""
        limits = RiskLimits(
            max_position_value_cents=10000,
            max_total_exposure_cents=50000,
            max_unrealized_loss_cents=5000,
            max_position_age_hours=24,
        )
        assessor = RiskAssessor(risk_limits=limits)
        position = MagicMock()
        position.ticker = "KXBTC-25JAN01"
        position.market_value_cents = 15000  # Exceeds 10000 limit
        position.unrealized_pnl_cents = 100
        creation_time = datetime.now(timezone.utc) - timedelta(hours=1)

        with patch("src.common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value = datetime.now(timezone.utc)
            assessment = await assessor.assess_position_risk(position, creation_time)

        assert assessment.exceeds_value_limit is True
        assert assessment.requires_closure is True

    @pytest.mark.asyncio
    async def test_detects_loss_limit_exceeded(self) -> None:
        """Detects when loss limit exceeded."""
        limits = RiskLimits(
            max_position_value_cents=10000,
            max_total_exposure_cents=50000,
            max_unrealized_loss_cents=5000,
            max_position_age_hours=24,
        )
        assessor = RiskAssessor(risk_limits=limits)
        position = MagicMock()
        position.ticker = "KXBTC-25JAN01"
        position.market_value_cents = 5000
        position.unrealized_pnl_cents = -6000  # Exceeds 5000 limit
        creation_time = datetime.now(timezone.utc) - timedelta(hours=1)

        with patch("src.common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value = datetime.now(timezone.utc)
            assessment = await assessor.assess_position_risk(position, creation_time)

        assert assessment.exceeds_loss_limit is True
        assert assessment.requires_closure is True

    @pytest.mark.asyncio
    async def test_detects_age_limit_exceeded(self) -> None:
        """Detects when age limit exceeded."""
        limits = RiskLimits(
            max_position_value_cents=10000,
            max_total_exposure_cents=50000,
            max_unrealized_loss_cents=5000,
            max_position_age_hours=24,
        )
        assessor = RiskAssessor(risk_limits=limits)
        position = MagicMock()
        position.ticker = "KXBTC-25JAN01"
        position.market_value_cents = 5000
        position.unrealized_pnl_cents = 100
        now = datetime.now(timezone.utc)
        creation_time = now - timedelta(hours=30)  # Exceeds 24 hours

        with patch("src.common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value = now
            assessment = await assessor.assess_position_risk(position, creation_time)

        assert assessment.exceeds_age_limit is True
        assert assessment.requires_closure is True

    @pytest.mark.asyncio
    async def test_logs_warning_when_closure_required(self) -> None:
        """Logs warning when closure required."""
        limits = RiskLimits(
            max_position_value_cents=10000,
            max_total_exposure_cents=50000,
            max_unrealized_loss_cents=5000,
            max_position_age_hours=24,
        )
        assessor = RiskAssessor(risk_limits=limits)
        position = MagicMock()
        position.ticker = "KXBTC-25JAN01"
        position.market_value_cents = 15000
        position.unrealized_pnl_cents = 100
        creation_time = datetime.now(timezone.utc) - timedelta(hours=1)

        with patch("src.common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value = datetime.now(timezone.utc)
            with patch(
                "src.common.emergency_position_manager_helpers.risk_assessor.logger"
            ) as mock_logger:
                await assessor.assess_position_risk(position, creation_time)

        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculates_correct_position_age(self) -> None:
        """Calculates correct position age in hours."""
        limits = RiskLimits(
            max_position_value_cents=10000,
            max_total_exposure_cents=50000,
            max_unrealized_loss_cents=5000,
            max_position_age_hours=24,
        )
        assessor = RiskAssessor(risk_limits=limits)
        position = MagicMock()
        position.ticker = "KXBTC-25JAN01"
        position.market_value_cents = 5000
        position.unrealized_pnl_cents = 100
        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        creation_time = datetime(2025, 1, 15, 6, 0, 0, tzinfo=timezone.utc)  # 6 hours ago

        with patch("src.common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value = now
            assessment = await assessor.assess_position_risk(position, creation_time)

        assert assessment.position_age_hours == 6.0

    @pytest.mark.asyncio
    async def test_handles_negative_market_value(self) -> None:
        """Handles negative market value (short position)."""
        limits = RiskLimits(
            max_position_value_cents=10000,
            max_total_exposure_cents=50000,
            max_unrealized_loss_cents=5000,
            max_position_age_hours=24,
        )
        assessor = RiskAssessor(risk_limits=limits)
        position = MagicMock()
        position.ticker = "KXBTC-25JAN01"
        position.market_value_cents = -15000  # Negative but abs > limit
        position.unrealized_pnl_cents = 100
        creation_time = datetime.now(timezone.utc) - timedelta(hours=1)

        with patch("src.common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value = datetime.now(timezone.utc)
            assessment = await assessor.assess_position_risk(position, creation_time)

        assert assessment.exceeds_value_limit is True


class TestCreateTestRiskLimits:
    """Tests for create_test_risk_limits function."""

    def test_creates_limits_with_max_test_risk(self) -> None:
        """Creates limits based on max test risk."""
        limits = create_test_risk_limits(max_test_risk_cents=10000)

        assert limits.max_position_value_cents == 5000  # 10000 // 2
        assert limits.max_total_exposure_cents == 10000
        assert limits.max_unrealized_loss_cents == 2500  # 10000 // 4
        assert limits.max_position_age_hours == 24

    def test_creates_limits_with_large_value(self) -> None:
        """Creates limits with large max test risk."""
        limits = create_test_risk_limits(max_test_risk_cents=100000)

        assert limits.max_position_value_cents == 50000
        assert limits.max_total_exposure_cents == 100000
        assert limits.max_unrealized_loss_cents == 25000
        assert limits.max_position_age_hours == 24
