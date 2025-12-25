"""Risk limit enforcement and monitoring."""

import asyncio
import logging
from typing import Dict, List

from ..data_models.trading import PortfolioPosition
from ..kalshi_trading_client import KalshiTradingClient
from ..trading_exceptions import KalshiTradingError
from .position_closer import PositionCloser
from .risk_assessor import PositionRiskAssessment, RiskAssessor, RiskLimits

logger = logging.getLogger(__name__)

MONITOR_ENFORCEMENT_ERRORS = (
    KalshiTradingError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
    ValueError,
    StopIteration,
)


class LimitEnforcer:
    """Monitors positions and enforces risk limits."""

    def __init__(
        self,
        trading_client: KalshiTradingClient,
        risk_assessor: RiskAssessor,
        position_closer: PositionCloser,
        risk_limits: RiskLimits,
    ):
        self.trading_client = trading_client
        self.risk_assessor = risk_assessor
        self.position_closer = position_closer
        self.risk_limits = risk_limits

    async def monitor_and_enforce_limits(self, monitored_positions: dict) -> List[PositionRiskAssessment]:
        """
        Monitor all positions and enforce risk limits.

        Args:
            monitored_positions: Dict mapping ticker to creation_time

        Returns:
            List of risk assessments for all monitored positions
        """
        assessments = []

        try:
            positions = await self.trading_client.get_portfolio_positions()

            for position in positions:
                if position.ticker in monitored_positions:
                    creation_time = monitored_positions[position.ticker]
                    assessment = await self.risk_assessor.assess_position_risk(position, creation_time)
                    assessments.append(assessment)

                    if assessment.requires_closure:
                        await self.position_closer.emergency_close_position(
                            position, f"Risk limit exceeded (score: {assessment.risk_score:.2f})"
                        )

            await _enforce_total_exposure(self, positions, monitored_positions, assessments)

        except MONITOR_ENFORCEMENT_ERRORS:  # Expected exception in operation  # policy_guard: allow-silent-handler
            logger.exception(f"[LimitEnforcer] Error monitoring positions: ")
        else:
            return assessments

        return assessments


async def _enforce_total_exposure(
    enforcer: LimitEnforcer,
    positions: List[PortfolioPosition],
    monitored_positions: dict,
    assessments: list,
) -> None:
    total_exposure = _calculate_total_exposure(positions, monitored_positions)
    if total_exposure <= enforcer.risk_limits.max_total_exposure_cents:
        return

    logger.warning(f"[LimitEnforcer] Total exposure {total_exposure}¢ " f"exceeds limit {enforcer.risk_limits.max_total_exposure_cents}¢")

    high_risk = _sorted_high_risk_assessments(assessments)
    await _close_until_within_limit(enforcer, high_risk, monitored_positions, positions)


def _calculate_total_exposure(positions: List[PortfolioPosition], monitored_positions: Dict) -> int:
    total = 0
    for position in positions:
        if position.ticker not in monitored_positions:
            continue
        market_value = position.market_value_cents
        if market_value is None:
            continue
        total += abs(market_value)
    return total


def _sorted_high_risk_assessments(assessments: list) -> List[PositionRiskAssessment]:
    high_risk = [assessment for assessment in assessments if assessment.requires_closure]
    high_risk.sort(key=lambda assessment: assessment.risk_score, reverse=True)
    return high_risk


async def _close_until_within_limit(
    enforcer: LimitEnforcer,
    assessments: List[PositionRiskAssessment],
    monitored_positions: dict,
    positions: List[PortfolioPosition],
) -> None:
    if not assessments:
        return

    positions_by_ticker = {position.ticker: position for position in positions}
    for assessment in assessments:
        position = positions_by_ticker.get(assessment.ticker)
        if not position:
            continue

        await enforcer.position_closer.emergency_close_position(position, "Total exposure limit")
        if await _is_total_exposure_within_limit(enforcer, monitored_positions):
            break


async def _is_total_exposure_within_limit(enforcer: LimitEnforcer, monitored_positions: dict) -> bool:
    remaining_positions = await enforcer.trading_client.get_portfolio_positions()
    total_exposure = _calculate_total_exposure(remaining_positions, monitored_positions)
    return total_exposure <= enforcer.risk_limits.max_total_exposure_cents
