"""Risk assessment helper for emergency position management."""

import logging
from dataclasses import dataclass
from datetime import datetime

from ..data_models.trading import PortfolioPosition

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """Risk management limits for position management"""

    max_position_value_cents: int
    max_total_exposure_cents: int
    max_unrealized_loss_cents: int
    max_position_age_hours: int

    def __post_init__(self):
        if self.max_position_value_cents <= 0:
            raise ValueError("Max position value must be positive")
        if self.max_total_exposure_cents <= 0:
            raise ValueError("Max total exposure must be positive")
        if self.max_unrealized_loss_cents <= 0:
            raise ValueError("Max unrealized loss must be positive")
        if self.max_position_age_hours <= 0:
            raise ValueError("Max position age must be positive")


@dataclass
class PositionRiskAssessment:
    """Risk assessment for a position"""

    ticker: str
    current_value_cents: int
    unrealized_pnl_cents: int
    position_age_hours: float
    exceeds_value_limit: bool
    exceeds_loss_limit: bool
    exceeds_age_limit: bool
    requires_closure: bool

    @property
    def risk_score(self) -> float:
        """Calculate risk score (0-1, higher is riskier)"""
        score = 0.0
        if self.exceeds_value_limit:
            score += 0.4
        if self.exceeds_loss_limit:
            score += 0.4
        if self.exceeds_age_limit:
            score += 0.2
        return min(score, 1.0)


class RiskAssessor:
    """Assesses position risk against defined limits."""

    def __init__(self, risk_limits: RiskLimits):
        self.risk_limits = risk_limits

    async def assess_position_risk(self, position: PortfolioPosition, creation_time: datetime) -> PositionRiskAssessment:
        """
        Assess risk level of a position.

        Args:
            position: Position to assess
            creation_time: When position was created

        Returns:
            PositionRiskAssessment: Risk assessment results
        """
        from ..time_utils import get_current_utc

        position_age = get_current_utc() - creation_time
        position_age_hours = position_age.total_seconds() / 3600

        market_value = position.market_value_cents
        if market_value is None:
            market_value = int()

        unrealized_pnl = position.unrealized_pnl_cents
        if unrealized_pnl is None:
            unrealized_pnl = int()

        exceeds_value_limit = abs(market_value) > self.risk_limits.max_position_value_cents
        exceeds_loss_limit = unrealized_pnl < -self.risk_limits.max_unrealized_loss_cents
        exceeds_age_limit = position_age_hours > self.risk_limits.max_position_age_hours

        requires_closure = exceeds_value_limit or exceeds_loss_limit or exceeds_age_limit

        assessment = PositionRiskAssessment(
            ticker=position.ticker,
            current_value_cents=market_value,
            unrealized_pnl_cents=unrealized_pnl,
            position_age_hours=position_age_hours,
            exceeds_value_limit=exceeds_value_limit,
            exceeds_loss_limit=exceeds_loss_limit,
            exceeds_age_limit=exceeds_age_limit,
            requires_closure=requires_closure,
        )

        if requires_closure:
            logger.warning(
                f"[RiskAssessor] Position {position.ticker} requires closure: "
                f"value_limit={exceeds_value_limit}, loss_limit={exceeds_loss_limit}, "
                f"age_limit={exceeds_age_limit}"
            )

        return assessment


def create_test_risk_limits(max_test_risk_cents: int) -> RiskLimits:
    """
    Create conservative risk limits for testing.

    Args:
        max_test_risk_cents: Maximum total test risk

    Returns:
        RiskLimits configured for testing
    """
    return RiskLimits(
        max_position_value_cents=max_test_risk_cents // 2,
        max_total_exposure_cents=max_test_risk_cents,
        max_unrealized_loss_cents=max_test_risk_cents // 4,
        max_position_age_hours=24,
    )
