"""Tests for dependency checker module."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.dependency_monitor_helpers.dependency_checker import (
    DependencyChecker,
    DependencyConfig,
    DependencyState,
    DependencyStatus,
)


class TestDependencyStatus:
    """Tests for DependencyStatus enum."""

    def test_available_value(self) -> None:
        """AVAILABLE has correct value."""
        assert DependencyStatus.AVAILABLE.value == "available"

    def test_unavailable_value(self) -> None:
        """UNAVAILABLE has correct value."""
        assert DependencyStatus.UNAVAILABLE.value == "unavailable"

    def test_unknown_value(self) -> None:
        """UNKNOWN has correct value."""
        assert DependencyStatus.UNKNOWN.value == "unknown"


class TestDependencyConfig:
    """Tests for DependencyConfig dataclass."""

    def test_required_fields(self) -> None:
        """Creates config with required fields."""
        config = DependencyConfig(name="redis", check_function=lambda: True)

        assert config.name == "redis"
        assert config.check_function is not None

    def test_default_check_interval(self) -> None:
        """Default check interval is 30 seconds."""
        config = DependencyConfig(name="redis", check_function=lambda: True)

        assert config.check_interval_seconds == 30.0

    def test_default_max_check_interval(self) -> None:
        """Default max check interval is 300 seconds."""
        config = DependencyConfig(name="redis", check_function=lambda: True)

        assert config.max_check_interval_seconds == 300.0

    def test_default_backoff_multiplier(self) -> None:
        """Default backoff multiplier is 1.5."""
        config = DependencyConfig(name="redis", check_function=lambda: True)

        assert config.backoff_multiplier == 1.5

    def test_default_required(self) -> None:
        """Default required is True."""
        config = DependencyConfig(name="redis", check_function=lambda: True)

        assert config.required is True

    def test_custom_values(self) -> None:
        """Creates config with custom values."""
        config = DependencyConfig(
            name="optional_dep",
            check_function=lambda: True,
            check_interval_seconds=60.0,
            max_check_interval_seconds=600.0,
            backoff_multiplier=2.0,
            required=False,
        )

        assert config.check_interval_seconds == 60.0
        assert config.max_check_interval_seconds == 600.0
        assert config.backoff_multiplier == 2.0
        assert config.required is False


class TestDependencyState:
    """Tests for DependencyState dataclass."""

    def test_creates_with_config(self) -> None:
        """Creates state with config."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config)

        assert state.config == config

    def test_default_status_unknown(self) -> None:
        """Default status is UNKNOWN."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config)

        assert state.status == DependencyStatus.UNKNOWN

    def test_default_last_check_time(self) -> None:
        """Default last check time is 0."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config)

        assert state.last_check_time == 0.0

    def test_default_consecutive_failures(self) -> None:
        """Default consecutive failures is 0."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config)

        assert state.consecutive_failures == 0

    def test_default_consecutive_successes(self) -> None:
        """Default consecutive successes is 0."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config)

        assert state.consecutive_successes == 0

    def test_default_current_check_interval(self) -> None:
        """Default current check interval is 0."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config)

        assert state.current_check_interval == 0.0

    def test_default_last_status_change_time(self) -> None:
        """Default last status change time is 0."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config)

        assert state.last_status_change_time == 0.0


class TestDependencyChecker:
    """Tests for DependencyChecker class."""

    def test_init_stores_service_name(self) -> None:
        """Stores service name."""
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)

        assert checker.service_name == "test_service"

    def test_init_stores_callback_executor(self) -> None:
        """Stores callback executor."""
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)

        assert checker.callback_executor == executor


class TestCheckDependency:
    """Tests for check_dependency method."""

    @pytest.mark.asyncio
    async def test_updates_last_check_time(self) -> None:
        """Updates last check time."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config)
        executor = MagicMock()
        executor.invoke_check_function = AsyncMock(return_value=(True, None))

        checker = DependencyChecker("test_service", executor)
        before = time.time()
        await checker.check_dependency(state)
        after = time.time()

        assert before <= state.last_check_time <= after

    @pytest.mark.asyncio
    async def test_returns_available_when_check_succeeds(self) -> None:
        """Returns AVAILABLE when check function returns truthy."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config)
        executor = MagicMock()
        executor.invoke_check_function = AsyncMock(return_value=(True, None))

        checker = DependencyChecker("test_service", executor)
        result = await checker.check_dependency(state)

        assert result == DependencyStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_returns_unavailable_when_check_returns_false(self) -> None:
        """Returns UNAVAILABLE when check function returns False."""
        config = DependencyConfig(name="redis", check_function=lambda: False)
        state = DependencyState(config=config)
        executor = MagicMock()
        executor.invoke_check_function = AsyncMock(return_value=(False, None))

        checker = DependencyChecker("test_service", executor)
        result = await checker.check_dependency(state)

        assert result == DependencyStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_returns_unavailable_when_check_errors(self) -> None:
        """Returns UNAVAILABLE when check function raises error."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config)
        executor = MagicMock()
        executor.invoke_check_function = AsyncMock(return_value=(None, Exception("test error")))

        checker = DependencyChecker("test_service", executor)
        result = await checker.check_dependency(state)

        assert result == DependencyStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_calls_notifier_on_status_change(self) -> None:
        """Calls notifier callback when status changes."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, status=DependencyStatus.UNKNOWN)
        executor = MagicMock()
        executor.invoke_check_function = AsyncMock(return_value=(True, None))
        notifier = AsyncMock()

        checker = DependencyChecker("test_service", executor)
        await checker.check_dependency(state, notifier)

        notifier.assert_called_once()
        call_args = notifier.call_args[0]
        assert call_args[0] == "redis"
        assert call_args[1] == DependencyStatus.UNKNOWN
        assert call_args[2] == DependencyStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_does_not_call_notifier_when_status_unchanged(self) -> None:
        """Does not call notifier when status unchanged."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, status=DependencyStatus.AVAILABLE)
        executor = MagicMock()
        executor.invoke_check_function = AsyncMock(return_value=(True, None))
        notifier = AsyncMock()

        checker = DependencyChecker("test_service", executor)
        await checker.check_dependency(state, notifier)

        notifier.assert_not_called()


class TestHandleCheckError:
    """Tests for _handle_check_error method."""

    @pytest.mark.asyncio
    async def test_sets_status_to_unavailable(self) -> None:
        """Sets status to UNAVAILABLE."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, status=DependencyStatus.UNKNOWN)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        await checker._handle_check_error(state, time.time(), None)

        assert state.status == DependencyStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_increments_consecutive_failures(self) -> None:
        """Increments consecutive failures."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, consecutive_failures=2)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        await checker._handle_check_error(state, time.time(), None)

        assert state.consecutive_failures == 3

    @pytest.mark.asyncio
    async def test_resets_consecutive_successes(self) -> None:
        """Resets consecutive successes to 0."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, consecutive_successes=5)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        await checker._handle_check_error(state, time.time(), None)

        assert state.consecutive_successes == 0

    @pytest.mark.asyncio
    async def test_applies_backoff_to_interval(self) -> None:
        """Applies backoff multiplier to check interval."""
        config = DependencyConfig(name="redis", check_function=lambda: True, backoff_multiplier=2.0)
        state = DependencyState(config=config, current_check_interval=10.0)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        await checker._handle_check_error(state, time.time(), None)

        assert state.current_check_interval == 20.0

    @pytest.mark.asyncio
    async def test_caps_interval_at_max(self) -> None:
        """Caps interval at max check interval."""
        config = DependencyConfig(
            name="redis",
            check_function=lambda: True,
            max_check_interval_seconds=100.0,
            backoff_multiplier=2.0,
        )
        state = DependencyState(config=config, current_check_interval=80.0)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        await checker._handle_check_error(state, time.time(), None)

        assert state.current_check_interval == 100.0

    @pytest.mark.asyncio
    async def test_calls_notifier_on_status_change(self) -> None:
        """Calls notifier when status changes."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, status=DependencyStatus.AVAILABLE)
        executor = MagicMock()
        notifier = AsyncMock()

        checker = DependencyChecker("test_service", executor)
        await checker._handle_check_error(state, time.time(), notifier)

        notifier.assert_called_once()
        call_args = notifier.call_args[0]
        assert call_args[0] == "redis"
        assert call_args[1] == DependencyStatus.AVAILABLE
        assert call_args[2] == DependencyStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_does_not_call_notifier_when_already_unavailable(self) -> None:
        """Does not call notifier when already UNAVAILABLE."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, status=DependencyStatus.UNAVAILABLE)
        executor = MagicMock()
        notifier = AsyncMock()

        checker = DependencyChecker("test_service", executor)
        await checker._handle_check_error(state, time.time(), notifier)

        notifier.assert_not_called()

    @pytest.mark.asyncio
    async def test_updates_last_status_change_time(self) -> None:
        """Updates last status change time on status change."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, status=DependencyStatus.AVAILABLE)
        executor = MagicMock()
        current_time = time.time()

        checker = DependencyChecker("test_service", executor)
        await checker._handle_check_error(state, current_time, None)

        assert state.last_status_change_time == current_time


class TestUpdateState:
    """Tests for _update_state method."""

    @pytest.mark.asyncio
    async def test_available_resets_failures(self) -> None:
        """AVAILABLE status resets consecutive failures."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, consecutive_failures=5)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        await checker._update_state(state, DependencyStatus.AVAILABLE, time.time(), None)

        assert state.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_available_increments_successes(self) -> None:
        """AVAILABLE status increments consecutive successes."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, consecutive_successes=2)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        await checker._update_state(state, DependencyStatus.AVAILABLE, time.time(), None)

        assert state.consecutive_successes == 3

    @pytest.mark.asyncio
    async def test_available_resets_interval_to_base(self) -> None:
        """AVAILABLE status resets interval to base interval."""
        config = DependencyConfig(
            name="redis", check_function=lambda: True, check_interval_seconds=30.0
        )
        state = DependencyState(config=config, current_check_interval=120.0)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        await checker._update_state(state, DependencyStatus.AVAILABLE, time.time(), None)

        assert state.current_check_interval == 30.0

    @pytest.mark.asyncio
    async def test_unavailable_resets_successes(self) -> None:
        """UNAVAILABLE status resets consecutive successes."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, consecutive_successes=5)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        await checker._update_state(state, DependencyStatus.UNAVAILABLE, time.time(), None)

        assert state.consecutive_successes == 0

    @pytest.mark.asyncio
    async def test_unavailable_increments_failures(self) -> None:
        """UNAVAILABLE status increments consecutive failures."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, consecutive_failures=2)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        await checker._update_state(state, DependencyStatus.UNAVAILABLE, time.time(), None)

        assert state.consecutive_failures == 3

    @pytest.mark.asyncio
    async def test_unavailable_applies_backoff(self) -> None:
        """UNAVAILABLE status applies backoff to interval."""
        config = DependencyConfig(name="redis", check_function=lambda: True, backoff_multiplier=2.0)
        state = DependencyState(config=config, current_check_interval=10.0)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        await checker._update_state(state, DependencyStatus.UNAVAILABLE, time.time(), None)

        assert state.current_check_interval == 20.0

    @pytest.mark.asyncio
    async def test_unavailable_caps_interval_at_max(self) -> None:
        """UNAVAILABLE status caps interval at max."""
        config = DependencyConfig(
            name="redis",
            check_function=lambda: True,
            max_check_interval_seconds=50.0,
            backoff_multiplier=2.0,
        )
        state = DependencyState(config=config, current_check_interval=40.0)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        await checker._update_state(state, DependencyStatus.UNAVAILABLE, time.time(), None)

        assert state.current_check_interval == 50.0

    @pytest.mark.asyncio
    async def test_updates_status(self) -> None:
        """Updates state status."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, status=DependencyStatus.UNKNOWN)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        await checker._update_state(state, DependencyStatus.AVAILABLE, time.time(), None)

        assert state.status == DependencyStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_updates_last_status_change_time(self) -> None:
        """Updates last status change time."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, status=DependencyStatus.UNKNOWN)
        executor = MagicMock()
        current_time = time.time()

        checker = DependencyChecker("test_service", executor)
        await checker._update_state(state, DependencyStatus.AVAILABLE, current_time, None)

        assert state.last_status_change_time == current_time

    @pytest.mark.asyncio
    async def test_calls_notifier_on_status_change(self) -> None:
        """Calls notifier on status change."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, status=DependencyStatus.UNKNOWN)
        executor = MagicMock()
        notifier = AsyncMock()

        checker = DependencyChecker("test_service", executor)
        await checker._update_state(state, DependencyStatus.AVAILABLE, time.time(), notifier)

        notifier.assert_called_once()
        call_args = notifier.call_args[0]
        assert call_args[0] == "redis"
        assert call_args[1] == DependencyStatus.UNKNOWN
        assert call_args[2] == DependencyStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_does_not_call_notifier_when_status_unchanged(self) -> None:
        """Does not call notifier when status unchanged."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config, status=DependencyStatus.AVAILABLE)
        executor = MagicMock()
        notifier = AsyncMock()

        checker = DependencyChecker("test_service", executor)
        await checker._update_state(state, DependencyStatus.AVAILABLE, time.time(), notifier)

        notifier.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_new_status(self) -> None:
        """Returns new status."""
        config = DependencyConfig(name="redis", check_function=lambda: True)
        state = DependencyState(config=config)
        executor = MagicMock()

        checker = DependencyChecker("test_service", executor)
        result = await checker._update_state(state, DependencyStatus.AVAILABLE, time.time(), None)

        assert result == DependencyStatus.AVAILABLE
