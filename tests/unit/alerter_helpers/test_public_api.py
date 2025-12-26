"""Tests for public_api module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.alerter_helpers.public_api import PublicAPI
from common.alerting import AlertSeverity


@pytest.fixture
def mock_component_manager() -> MagicMock:
    """Create a mock component manager."""
    manager = MagicMock()
    manager.telegram_enabled = True
    manager.authorized_user_ids = ["user1", "user2"]
    manager.get_telegram_component = MagicMock(return_value=MagicMock())
    manager.chart_mgr = MagicMock()
    manager.cmd_registry = MagicMock()
    manager.polling_coord = MagicMock()
    manager.polling_coord.poll_updates = AsyncMock()
    return manager


class TestPublicAPI:
    """Tests for PublicAPI class."""

    def test_init(self, mock_component_manager: MagicMock) -> None:
        """Test PublicAPI initialization."""
        api = PublicAPI(mock_component_manager)
        assert api._mgr is mock_component_manager

    @pytest.mark.asyncio
    async def test_send_alert(self, mock_component_manager: MagicMock) -> None:
        """Test send_alert method."""
        api = PublicAPI(mock_component_manager)

        with patch(
            "common.alerter_helpers.public_api.AlertOperations.send_alert",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            result = await api.send_alert(
                message="Test message",
                severity=AlertSeverity.WARNING,
                alert_type="test",
                details={"key": "value"},
                target_user_id="user1",
            )

            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] is True
            assert call_args[0][2] == "Test message"
            assert call_args[0][3] == AlertSeverity.WARNING
            assert call_args[0][4] == "test"
            assert call_args[0][5] == {"key": "value"}
            assert call_args[0][6] == "user1"

    @pytest.mark.asyncio
    async def test_send_alert_with_defaults(self, mock_component_manager: MagicMock) -> None:
        """Test send_alert with default parameters."""
        api = PublicAPI(mock_component_manager)

        with patch(
            "common.alerter_helpers.public_api.AlertOperations.send_alert",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            await api.send_alert(message="Test")

            call_args = mock_send.call_args
            assert call_args[0][3] == AlertSeverity.INFO
            assert call_args[0][4] == "general"
            assert call_args[0][5] is None
            assert call_args[0][6] is None

    @pytest.mark.asyncio
    async def test_send_chart_image(self, mock_component_manager: MagicMock) -> None:
        """Test send_chart_image method."""
        api = PublicAPI(mock_component_manager)

        with patch(
            "common.alerter_helpers.public_api.ChartOperations.send_chart_image",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            result = await api.send_chart_image(
                image_path="/path/to/chart.png",
                caption="Test caption",
                target_user_id="user1",
            )

            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] is True
            assert call_args[0][2] == ["user1", "user2"]
            assert call_args[0][3] == "/path/to/chart.png"
            assert call_args[0][4] == "Test caption"
            assert call_args[0][5] == "user1"

    @pytest.mark.asyncio
    async def test_send_chart_is_alias_for_send_chart_image(self, mock_component_manager: MagicMock) -> None:
        """Test that send_chart calls send_chart_image."""
        api = PublicAPI(mock_component_manager)

        with patch.object(api, "send_chart_image", new_callable=AsyncMock, return_value=True) as mock_send:
            result = await api.send_chart("/path/chart.png", "caption", "user1")

            assert result is True
            mock_send.assert_called_once_with("/path/chart.png", "caption", "user1")

    def test_set_metrics_recorder(self, mock_component_manager: MagicMock) -> None:
        """Test set_metrics_recorder method."""
        api = PublicAPI(mock_component_manager)
        recorder = MagicMock()

        api.set_metrics_recorder(recorder)

        mock_component_manager.chart_mgr.set_metrics_recorder.assert_called_once_with(recorder)

    def test_register_command_handler_with_telegram_enabled(self, mock_component_manager: MagicMock) -> None:
        """Test register_command_handler when Telegram is enabled."""
        api = PublicAPI(mock_component_manager)
        handler = MagicMock()

        api.register_command_handler("test_cmd", handler)

        mock_component_manager.cmd_registry.register_command_handler.assert_called_once_with("test_cmd", handler)

    def test_register_command_handler_with_telegram_disabled(self, mock_component_manager: MagicMock) -> None:
        """Test register_command_handler does nothing when Telegram is disabled."""
        mock_component_manager.telegram_enabled = False
        api = PublicAPI(mock_component_manager)
        handler = MagicMock()

        api.register_command_handler("test_cmd", handler)

        mock_component_manager.cmd_registry.register_command_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_poll_telegram_updates_with_telegram_enabled(self, mock_component_manager: MagicMock) -> None:
        """Test poll_telegram_updates when Telegram is enabled."""
        api = PublicAPI(mock_component_manager)

        await api.poll_telegram_updates()

        mock_component_manager.polling_coord.poll_updates.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_telegram_updates_with_telegram_disabled(self, mock_component_manager: MagicMock) -> None:
        """Test poll_telegram_updates does nothing when Telegram is disabled."""
        mock_component_manager.telegram_enabled = False
        api = PublicAPI(mock_component_manager)

        await api.poll_telegram_updates()

        mock_component_manager.polling_coord.poll_updates.assert_not_called()

    def test_should_send_price_validation_alert(self, mock_component_manager: MagicMock) -> None:
        """Test should_send_price_validation_alert method."""
        api = PublicAPI(mock_component_manager)

        with patch(
            "common.alerter_helpers.public_api.PriceValidationOperations.should_send_alert",
            return_value=True,
        ) as mock_check:
            result = api.should_send_price_validation_alert("BTC", {"price": 50000})

            assert result is True
            mock_check.assert_called_once()

    def test_clear_price_validation_alert(self, mock_component_manager: MagicMock) -> None:
        """Test clear_price_validation_alert method."""
        api = PublicAPI(mock_component_manager)

        with patch(
            "common.alerter_helpers.public_api.PriceValidationOperations.clear_alert",
            return_value=True,
        ) as mock_clear:
            result = api.clear_price_validation_alert("BTC")

            assert result is True
            mock_clear.assert_called_once()

    def test_is_price_validation_alert_active(self, mock_component_manager: MagicMock) -> None:
        """Test is_price_validation_alert_active method."""
        api = PublicAPI(mock_component_manager)

        with patch(
            "common.alerter_helpers.public_api.PriceValidationOperations.is_alert_active",
            return_value=True,
        ) as mock_check:
            result = api.is_price_validation_alert_active("ETH")

            assert result is True
            mock_check.assert_called_once()
