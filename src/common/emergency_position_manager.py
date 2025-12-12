"""
Emergency Position Manager for Kalshi Live Trading Tests

This module provides emergency position closure capabilities, stop-loss mechanisms,
and risk management utilities for live trading tests. All operations follow
fail-fast principles with comprehensive error handling.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .data_models.trading import OrderResponse, PortfolioPosition
from .emergency_position_manager_helpers.limit_enforcer import LimitEnforcer
from .emergency_position_manager_helpers.position_closer import (
    TRADING_OPERATION_ERRORS,
    PositionCloser,
)
from .emergency_position_manager_helpers.risk_assessor import (
    PositionRiskAssessment,
    RiskAssessor,
    RiskLimits,
    create_test_risk_limits,
)
from .emergency_position_manager_helpers.stop_loss_monitor import StopLossMonitor
from .kalshi_trading_client import KalshiTradingClient

logger = logging.getLogger(__name__)

__all__ = [
    "EmergencyPositionManager",
    "RiskLimits",
    "PositionRiskAssessment",
    "create_test_risk_limits",
]


class EmergencyPositionManager:
    """Emergency position management for live trading tests."""

    def __init__(self, trading_client: KalshiTradingClient, risk_limits: RiskLimits):
        if getattr(trading_client, "trade_store", None) is None:
            raise ValueError("EmergencyPositionManager requires a trading client with a trade store")

        self.trading_client = trading_client
        self.risk_limits = risk_limits
        self.monitored_positions: Dict[str, datetime] = {}
        self.risk_assessor = RiskAssessor(risk_limits)
        self.position_closer = PositionCloser(trading_client)
        self.limit_enforcer = LimitEnforcer(trading_client, self.risk_assessor, self.position_closer, risk_limits)
        self.stop_loss_monitor = StopLossMonitor(trading_client, self.position_closer)
        logger.info(
            "[EmergencyPositionManager] Initialized with limits: max_value=%s¢, max_exposure=%s¢, max_loss=%s¢",
            risk_limits.max_position_value_cents,
            risk_limits.max_total_exposure_cents,
            risk_limits.max_unrealized_loss_cents,
        )

    def register_position(self, ticker: str, creation_time: Optional[datetime] = None) -> None:
        from .time_utils import get_current_utc

        self.monitored_positions[ticker] = creation_time or get_current_utc()
        logger.info("[EmergencyPositionManager] Registered position: %s", ticker)

    def unregister_position(self, ticker: str) -> None:
        if ticker in self.monitored_positions:
            del self.monitored_positions[ticker]
            logger.info("[EmergencyPositionManager] Unregistered position: %s", ticker)

    async def assess_position_risk(self, position: PortfolioPosition) -> PositionRiskAssessment:
        if position.ticker not in self.monitored_positions:
            logger.warning(
                "[EmergencyPositionManager] Auto-registering position %s before risk assessment",
                position.ticker,
            )
            self.register_position(position.ticker)
        creation_time = self.monitored_positions[position.ticker]
        return await self.risk_assessor.assess_position_risk(position, creation_time)

    async def emergency_close_position(
        self, position: PortfolioPosition, reason: str = "Emergency closure"
    ) -> Tuple[bool, Optional[OrderResponse], str]:
        success, response, message = await self.position_closer.emergency_close_position(position, reason)
        if success:
            self.unregister_position(position.ticker)
        return success, response, message

    async def emergency_close_all_positions(self) -> Dict[str, Tuple[bool, str]]:
        logger.warning("[EmergencyPositionManager] Emergency closing ALL positions")
        results: Dict[str, Tuple[bool, str]] = {}
        try:
            positions = await self.trading_client.get_portfolio_positions()
            monitored_positions = [p for p in positions if p.ticker in self.monitored_positions]
            if not monitored_positions:
                logger.info("[EmergencyPositionManager] No monitored positions to close")
                return {}
            for position in monitored_positions:
                success, _, message = await self.emergency_close_position(position, "Emergency close all")
                results[position.ticker] = (success, message)
                await asyncio.sleep(0.5)

            else:
                return results
        except TRADING_OPERATION_ERRORS:  # policy_guard: allow-silent-handler
            logger.exception("[EmergencyPositionManager] Failed to close all positions")
            return {"error": (False, "Failed to close all")}

    async def monitor_and_enforce_limits(self) -> List[PositionRiskAssessment]:
        return await self.limit_enforcer.monitor_and_enforce_limits(self.monitored_positions)

    async def create_stop_loss_monitor(self, ticker: str, stop_loss_cents: int, check_interval_seconds: float = 30.0) -> None:
        await self.stop_loss_monitor.create_stop_loss_monitor(ticker, stop_loss_cents, self.monitored_positions, check_interval_seconds)
