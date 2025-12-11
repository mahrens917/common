"""Tests for emergency position manager module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.emergency_position_manager import EmergencyPositionManager
from common.emergency_position_manager_helpers.risk_assessor import (
    RiskLimits,
    create_test_risk_limits,
)

# Default test risk value in cents
TEST_RISK_CENTS = 10000


class TestEmergencyPositionManagerInit:
    """Tests for EmergencyPositionManager initialization."""

    def test_raises_without_trade_store(self) -> None:
        """Raises ValueError when trading client lacks trade store."""
        trading_client = MagicMock()
        trading_client.trade_store = None
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)

        with pytest.raises(ValueError, match="trade store"):
            EmergencyPositionManager(trading_client, risk_limits)

    def test_initializes_with_valid_client(self) -> None:
        """Initializes successfully with valid trading client."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)

        manager = EmergencyPositionManager(trading_client, risk_limits)

        assert manager.trading_client is trading_client
        assert manager.risk_limits is risk_limits
        assert manager.monitored_positions == {}

    def test_creates_risk_assessor(self) -> None:
        """Creates RiskAssessor with provided limits."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)

        manager = EmergencyPositionManager(trading_client, risk_limits)

        assert manager.risk_assessor is not None

    def test_creates_position_closer(self) -> None:
        """Creates PositionCloser with trading client."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)

        manager = EmergencyPositionManager(trading_client, risk_limits)

        assert manager.position_closer is not None

    def test_creates_limit_enforcer(self) -> None:
        """Creates LimitEnforcer."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)

        manager = EmergencyPositionManager(trading_client, risk_limits)

        assert manager.limit_enforcer is not None

    def test_creates_stop_loss_monitor(self) -> None:
        """Creates StopLossMonitor."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)

        manager = EmergencyPositionManager(trading_client, risk_limits)

        assert manager.stop_loss_monitor is not None


class TestEmergencyPositionManagerRegisterPosition:
    """Tests for EmergencyPositionManager.register_position."""

    def test_registers_position_with_ticker(self) -> None:
        """Registers position with given ticker."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)
        manager = EmergencyPositionManager(trading_client, risk_limits)

        with patch("common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            manager.register_position("TEST-TICKER")

        assert "TEST-TICKER" in manager.monitored_positions

    def test_uses_custom_creation_time(self) -> None:
        """Uses custom creation time when provided."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)
        manager = EmergencyPositionManager(trading_client, risk_limits)
        custom_time = datetime(2025, 1, 10, 8, 0, 0, tzinfo=timezone.utc)

        manager.register_position("TEST-TICKER", custom_time)

        assert manager.monitored_positions["TEST-TICKER"] == custom_time


class TestEmergencyPositionManagerUnregisterPosition:
    """Tests for EmergencyPositionManager.unregister_position."""

    def test_unregisters_existing_position(self) -> None:
        """Unregisters existing position."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)
        manager = EmergencyPositionManager(trading_client, risk_limits)
        manager.monitored_positions["TEST-TICKER"] = datetime.now(timezone.utc)

        manager.unregister_position("TEST-TICKER")

        assert "TEST-TICKER" not in manager.monitored_positions

    def test_handles_nonexistent_position(self) -> None:
        """Handles unregistering position that does not exist."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)
        manager = EmergencyPositionManager(trading_client, risk_limits)

        # Should not raise
        manager.unregister_position("NONEXISTENT")


class TestEmergencyPositionManagerAssessPositionRisk:
    """Tests for EmergencyPositionManager.assess_position_risk."""

    @pytest.mark.asyncio
    async def test_assesses_position_risk(self) -> None:
        """Assesses risk for given position."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)
        manager = EmergencyPositionManager(trading_client, risk_limits)

        position = MagicMock()
        position.ticker = "TEST-TICKER"
        position.last_updated = datetime.now(timezone.utc)
        position.market_value_cents = 1000
        position.total_cost_cents = 800
        position.quantity = 5

        manager.risk_assessor.assess_position_risk = AsyncMock()

        await manager.assess_position_risk(position)

        manager.risk_assessor.assess_position_risk.assert_called_once()


class TestEmergencyPositionManagerEmergencyClosePosition:
    """Tests for EmergencyPositionManager.emergency_close_position."""

    @pytest.mark.asyncio
    async def test_closes_position_and_unregisters(self) -> None:
        """Closes position and unregisters on success."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)
        manager = EmergencyPositionManager(trading_client, risk_limits)
        manager.monitored_positions["TEST-TICKER"] = datetime.now(timezone.utc)

        position = MagicMock()
        position.ticker = "TEST-TICKER"

        manager.position_closer.emergency_close_position = AsyncMock(return_value=(True, MagicMock(), "Closed successfully"))

        success, response, message = await manager.emergency_close_position(position)

        assert success is True
        assert "TEST-TICKER" not in manager.monitored_positions

    @pytest.mark.asyncio
    async def test_keeps_position_registered_on_failure(self) -> None:
        """Keeps position registered when close fails."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)
        manager = EmergencyPositionManager(trading_client, risk_limits)
        manager.monitored_positions["TEST-TICKER"] = datetime.now(timezone.utc)

        position = MagicMock()
        position.ticker = "TEST-TICKER"

        manager.position_closer.emergency_close_position = AsyncMock(return_value=(False, None, "Failed to close"))

        success, response, message = await manager.emergency_close_position(position)

        assert success is False
        assert "TEST-TICKER" in manager.monitored_positions


class TestEmergencyPositionManagerEmergencyCloseAllPositions:
    """Tests for EmergencyPositionManager.emergency_close_all_positions."""

    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_positions(self) -> None:
        """Returns empty dict when no monitored positions."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        trading_client.get_portfolio_positions = AsyncMock(return_value=[])
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)
        manager = EmergencyPositionManager(trading_client, risk_limits)

        results = await manager.emergency_close_all_positions()

        assert results == {}

    @pytest.mark.asyncio
    async def test_closes_all_monitored_positions(self) -> None:
        """Closes all monitored positions."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)
        manager = EmergencyPositionManager(trading_client, risk_limits)

        position1 = MagicMock()
        position1.ticker = "TICKER-1"
        position2 = MagicMock()
        position2.ticker = "TICKER-2"

        manager.monitored_positions["TICKER-1"] = datetime.now(timezone.utc)
        manager.monitored_positions["TICKER-2"] = datetime.now(timezone.utc)

        trading_client.get_portfolio_positions = AsyncMock(return_value=[position1, position2])
        manager.position_closer.emergency_close_position = AsyncMock(return_value=(True, MagicMock(), "Closed"))

        results = await manager.emergency_close_all_positions()

        assert len(results) == 2
        assert results["TICKER-1"][0] is True
        assert results["TICKER-2"][0] is True


class TestEmergencyPositionManagerMonitorAndEnforceLimits:
    """Tests for EmergencyPositionManager.monitor_and_enforce_limits."""

    @pytest.mark.asyncio
    async def test_delegates_to_limit_enforcer(self) -> None:
        """Delegates to limit enforcer."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)
        manager = EmergencyPositionManager(trading_client, risk_limits)
        manager.monitored_positions["TEST-TICKER"] = datetime.now(timezone.utc)

        manager.limit_enforcer.monitor_and_enforce_limits = AsyncMock(return_value=[])

        await manager.monitor_and_enforce_limits()

        manager.limit_enforcer.monitor_and_enforce_limits.assert_called_once()


class TestEmergencyPositionManagerCreateStopLossMonitor:
    """Tests for EmergencyPositionManager.create_stop_loss_monitor."""

    @pytest.mark.asyncio
    async def test_delegates_to_stop_loss_monitor(self) -> None:
        """Delegates to stop loss monitor."""
        trading_client = MagicMock()
        trading_client.trade_store = MagicMock()
        risk_limits = create_test_risk_limits(TEST_RISK_CENTS)
        manager = EmergencyPositionManager(trading_client, risk_limits)

        manager.stop_loss_monitor.create_stop_loss_monitor = AsyncMock()

        await manager.create_stop_loss_monitor("TEST-TICKER", 500)

        manager.stop_loss_monitor.create_stop_loss_monitor.assert_called_once()


class TestCreateTestRiskLimits:
    """Tests for create_test_risk_limits function."""

    def test_creates_risk_limits(self) -> None:
        """Creates RiskLimits with test values."""
        limits = create_test_risk_limits(TEST_RISK_CENTS)

        assert isinstance(limits, RiskLimits)
        assert limits.max_position_value_cents > 0
        assert limits.max_total_exposure_cents > 0
        assert limits.max_unrealized_loss_cents > 0
