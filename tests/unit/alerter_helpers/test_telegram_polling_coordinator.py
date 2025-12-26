"""Tests for alerter_helpers.telegram_polling_coordinator module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from common.alerter_helpers.telegram_polling_coordinator import (
    TelegramCoordinatorConfig,
    TelegramCoordinatorDependencies,
    TelegramPollingCoordinator,
)

# Test constants
TEST_TELEGRAM_TIMEOUT_SECONDS = 40


class TestTelegramCoordinatorConfig:
    """Tests for TelegramCoordinatorConfig dataclass."""

    def test_stores_all_fields(self) -> None:
        """Test config stores all fields."""
        mock_client = MagicMock()
        config = TelegramCoordinatorConfig(
            telegram_client=mock_client,
            telegram_timeout_seconds=30,
            telegram_long_poll_timeout_seconds=60,
        )

        assert config.telegram_client is mock_client
        assert config.telegram_timeout_seconds == 30
        assert config.telegram_long_poll_timeout_seconds == 60

    def test_is_frozen(self) -> None:
        """Test config is frozen (immutable)."""
        config = TelegramCoordinatorConfig(
            telegram_client=None,
            telegram_timeout_seconds=30,
            telegram_long_poll_timeout_seconds=60,
        )

        with pytest.raises(AttributeError):
            config.telegram_timeout_seconds = TEST_TELEGRAM_TIMEOUT_SECONDS


class TestTelegramCoordinatorDependencies:
    """Tests for TelegramCoordinatorDependencies dataclass."""

    def test_stores_all_fields(self) -> None:
        """Test dependencies stores all fields."""
        mock_rate = MagicMock()
        mock_executor = MagicMock()
        mock_backoff = MagicMock()
        mock_processor = MagicMock()
        mock_starter = MagicMock()

        deps = TelegramCoordinatorDependencies(
            rate_limit_handler=mock_rate,
            request_executor=mock_executor,
            backoff_manager=mock_backoff,
            update_processor=mock_processor,
            queue_processor_starter=mock_starter,
        )

        assert deps.rate_limit_handler is mock_rate
        assert deps.request_executor is mock_executor
        assert deps.backoff_manager is mock_backoff
        assert deps.update_processor is mock_processor
        assert deps.queue_processor_starter is mock_starter


class TestTelegramPollingCoordinatorInit:
    """Tests for TelegramPollingCoordinator initialization."""

    def test_stores_config_and_dependencies(self) -> None:
        """Test stores config and dependencies."""
        mock_client = MagicMock()
        config = TelegramCoordinatorConfig(
            telegram_client=mock_client,
            telegram_timeout_seconds=30,
            telegram_long_poll_timeout_seconds=60,
        )
        deps = TelegramCoordinatorDependencies(
            rate_limit_handler=MagicMock(),
            request_executor=MagicMock(),
            backoff_manager=MagicMock(),
            update_processor=MagicMock(),
            queue_processor_starter=MagicMock(),
        )

        coordinator = TelegramPollingCoordinator(config, deps)

        assert coordinator.telegram_client is mock_client
        assert coordinator.telegram_timeout_seconds == 30
        assert coordinator.telegram_long_poll_timeout_seconds == 60


class TestTelegramPollingCoordinatorPollUpdates:
    """Tests for poll_updates method."""

    @pytest.mark.asyncio
    async def test_returns_when_cannot_poll(self) -> None:
        """Test returns early when cannot poll."""
        config = TelegramCoordinatorConfig(
            telegram_client=MagicMock(),
            telegram_timeout_seconds=30,
            telegram_long_poll_timeout_seconds=60,
        )
        mock_backoff = MagicMock()
        mock_backoff.should_skip_operation.return_value = True
        deps = TelegramCoordinatorDependencies(
            rate_limit_handler=MagicMock(),
            request_executor=MagicMock(),
            backoff_manager=mock_backoff,
            update_processor=MagicMock(),
            queue_processor_starter=MagicMock(),
        )

        coordinator = TelegramPollingCoordinator(config, deps)
        await coordinator.poll_updates()

        # Should not try to execute request
        deps.request_executor.execute_polling_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_when_rate_limited(self) -> None:
        """Test returns early when rate limited."""
        config = TelegramCoordinatorConfig(
            telegram_client=MagicMock(),
            telegram_timeout_seconds=30,
            telegram_long_poll_timeout_seconds=60,
        )
        mock_rate = MagicMock()
        mock_rate.is_backoff_active.return_value = True
        mock_backoff = MagicMock()
        mock_backoff.should_skip_operation.return_value = False
        deps = TelegramCoordinatorDependencies(
            rate_limit_handler=mock_rate,
            request_executor=MagicMock(),
            backoff_manager=mock_backoff,
            update_processor=MagicMock(),
            queue_processor_starter=MagicMock(),
        )

        coordinator = TelegramPollingCoordinator(config, deps)
        await coordinator.poll_updates()

        # Should not try to execute request
        deps.request_executor.execute_polling_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_when_client_unavailable(self) -> None:
        """Test returns when telegram client is None."""
        config = TelegramCoordinatorConfig(
            telegram_client=None,
            telegram_timeout_seconds=30,
            telegram_long_poll_timeout_seconds=60,
        )
        mock_rate = MagicMock()
        mock_rate.is_backoff_active.return_value = False
        mock_backoff = MagicMock()
        mock_backoff.should_skip_operation.return_value = False
        deps = TelegramCoordinatorDependencies(
            rate_limit_handler=mock_rate,
            request_executor=MagicMock(),
            backoff_manager=mock_backoff,
            update_processor=MagicMock(),
            queue_processor_starter=MagicMock(),
        )

        coordinator = TelegramPollingCoordinator(config, deps)
        await coordinator.poll_updates()

        # Should not try to execute request
        deps.request_executor.execute_polling_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self) -> None:
        """Test handles timeout error gracefully."""
        mock_client = MagicMock()
        mock_client.base_url = "https://api.telegram.org/bot123"
        config = TelegramCoordinatorConfig(
            telegram_client=mock_client,
            telegram_timeout_seconds=30,
            telegram_long_poll_timeout_seconds=60,
        )
        mock_rate = MagicMock()
        mock_rate.is_backoff_active.return_value = False
        mock_backoff = MagicMock()
        mock_backoff.should_skip_operation.return_value = False
        mock_processor = MagicMock()
        mock_processor.last_update_id = 0
        deps = TelegramCoordinatorDependencies(
            rate_limit_handler=mock_rate,
            request_executor=MagicMock(),
            backoff_manager=mock_backoff,
            update_processor=mock_processor,
            queue_processor_starter=MagicMock(),
        )

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_session.__aexit__ = AsyncMock()
            mock_session_cls.return_value = mock_session

            coordinator = TelegramPollingCoordinator(config, deps)
            # Should not raise
            await coordinator.poll_updates()

    @pytest.mark.asyncio
    async def test_handles_client_error(self) -> None:
        """Test handles client error and records failure."""
        mock_client = MagicMock()
        mock_client.base_url = "https://api.telegram.org/bot123"
        config = TelegramCoordinatorConfig(
            telegram_client=mock_client,
            telegram_timeout_seconds=30,
            telegram_long_poll_timeout_seconds=60,
        )
        mock_rate = MagicMock()
        mock_rate.is_backoff_active.return_value = False
        mock_backoff = MagicMock()
        mock_backoff.should_skip_operation.return_value = False
        mock_processor = MagicMock()
        mock_processor.last_update_id = 0
        deps = TelegramCoordinatorDependencies(
            rate_limit_handler=mock_rate,
            request_executor=MagicMock(),
            backoff_manager=mock_backoff,
            update_processor=mock_processor,
            queue_processor_starter=MagicMock(),
        )

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError())
            mock_session.__aexit__ = AsyncMock()
            mock_session_cls.return_value = mock_session

            coordinator = TelegramPollingCoordinator(config, deps)
            await coordinator.poll_updates()

            mock_backoff.record_failure.assert_called_once()


class TestTelegramPollingCoordinatorCanPoll:
    """Tests for _can_poll method."""

    def test_calls_queue_processor_starter(self) -> None:
        """Test calls queue processor starter."""
        config = TelegramCoordinatorConfig(
            telegram_client=MagicMock(),
            telegram_timeout_seconds=30,
            telegram_long_poll_timeout_seconds=60,
        )
        mock_starter = MagicMock()
        mock_backoff = MagicMock()
        mock_backoff.should_skip_operation.return_value = False
        deps = TelegramCoordinatorDependencies(
            rate_limit_handler=MagicMock(),
            request_executor=MagicMock(),
            backoff_manager=mock_backoff,
            update_processor=MagicMock(),
            queue_processor_starter=mock_starter,
        )

        coordinator = TelegramPollingCoordinator(config, deps)
        coordinator._can_poll()

        mock_starter.assert_called_once()

    def test_returns_false_when_should_skip(self) -> None:
        """Test returns False when should skip operation."""
        config = TelegramCoordinatorConfig(
            telegram_client=MagicMock(),
            telegram_timeout_seconds=30,
            telegram_long_poll_timeout_seconds=60,
        )
        mock_backoff = MagicMock()
        mock_backoff.should_skip_operation.return_value = True
        deps = TelegramCoordinatorDependencies(
            rate_limit_handler=MagicMock(),
            request_executor=MagicMock(),
            backoff_manager=mock_backoff,
            update_processor=MagicMock(),
            queue_processor_starter=MagicMock(),
        )

        coordinator = TelegramPollingCoordinator(config, deps)
        result = coordinator._can_poll()

        assert result is False


class TestTelegramPollingCoordinatorCreatePollingConfig:
    """Tests for _create_polling_config method."""

    def test_creates_config_with_client(self) -> None:
        """Test creates polling config with client."""
        mock_client = MagicMock()
        mock_client.base_url = "https://api.telegram.org/bot123"
        config = TelegramCoordinatorConfig(
            telegram_client=mock_client,
            telegram_timeout_seconds=30,
            telegram_long_poll_timeout_seconds=60,
        )
        mock_processor = MagicMock()
        mock_processor.last_update_id = 100
        deps = TelegramCoordinatorDependencies(
            rate_limit_handler=MagicMock(),
            request_executor=MagicMock(),
            backoff_manager=MagicMock(),
            update_processor=mock_processor,
            queue_processor_starter=MagicMock(),
        )

        coordinator = TelegramPollingCoordinator(config, deps)
        result = coordinator._create_polling_config()

        assert result.url == "https://api.telegram.org/bot123/getUpdates"
        assert result.params["offset"] == 101
        assert result.long_poll_timeout == 60

    def test_raises_when_client_none(self) -> None:
        """Test raises RuntimeError when client is None."""
        config = TelegramCoordinatorConfig(
            telegram_client=None,
            telegram_timeout_seconds=30,
            telegram_long_poll_timeout_seconds=60,
        )
        deps = TelegramCoordinatorDependencies(
            rate_limit_handler=MagicMock(),
            request_executor=MagicMock(),
            backoff_manager=MagicMock(),
            update_processor=MagicMock(),
            queue_processor_starter=MagicMock(),
        )

        coordinator = TelegramPollingCoordinator(config, deps)

        with pytest.raises(RuntimeError):
            coordinator._create_polling_config()

    def test_calculates_default_long_poll_timeout(self) -> None:
        """Test calculates default long poll timeout."""
        mock_client = MagicMock()
        mock_client.base_url = "https://api.telegram.org/bot123"
        config = TelegramCoordinatorConfig(
            telegram_client=mock_client,
            telegram_timeout_seconds=30,
            telegram_long_poll_timeout_seconds=0,  # No explicit timeout
        )
        mock_processor = MagicMock()
        mock_processor.last_update_id = 0
        deps = TelegramCoordinatorDependencies(
            rate_limit_handler=MagicMock(),
            request_executor=MagicMock(),
            backoff_manager=MagicMock(),
            update_processor=mock_processor,
            queue_processor_starter=MagicMock(),
        )

        coordinator = TelegramPollingCoordinator(config, deps)
        result = coordinator._create_polling_config()

        # Should be max(25, 30*2) = 60
        assert result.long_poll_timeout == 60
