"""Tests for field_reset_applicator_with_alert module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.dawn_reset_service_helpers.field_reset_applicator_with_alert import (
    FieldResetApplicatorWithAlert,
    FieldResetContext,
)


@pytest.fixture
def mock_field_reset_manager():
    """Create a mock field reset manager."""
    manager = MagicMock()
    manager.apply_reset_logic = MagicMock(return_value="reset_value")
    return manager


@pytest.fixture
def mock_alert_manager():
    """Create a mock alert manager."""
    manager = AsyncMock()
    manager.send_reset_alert = AsyncMock()
    return manager


@pytest.fixture
def daily_reset_fields():
    """Create a set of daily reset fields."""
    return {"field1", "field2", "precipitation"}


@pytest.fixture
def mock_should_reset_callback():
    """Create a mock should reset callback."""
    callback = MagicMock(return_value=(True, datetime(2023, 1, 1, 6, 0, 0)))
    return callback


@pytest.fixture
def applicator(
    mock_field_reset_manager,
    mock_alert_manager,
    daily_reset_fields,
    mock_should_reset_callback,
):
    """Create a FieldResetApplicatorWithAlert instance."""
    return FieldResetApplicatorWithAlert(
        field_reset_manager=mock_field_reset_manager,
        alert_manager=mock_alert_manager,
        daily_reset_fields=daily_reset_fields,
        should_reset_callback=mock_should_reset_callback,
    )


def test_field_reset_context_creation():
    """Test FieldResetContext dataclass creation."""
    context = FieldResetContext(
        field_name="precipitation",
        current_value=10.5,
        previous_data={"precipitation": 5.0},
        latitude=40.7128,
        longitude=-74.0060,
        station_id="NYC_001",
        current_timestamp=datetime(2023, 1, 1, 12, 0, 0),
    )

    assert context.field_name == "precipitation"
    assert context.current_value == 10.5
    assert context.previous_data == {"precipitation": 5.0}
    assert context.latitude == 40.7128
    assert context.longitude == -74.0060
    assert context.station_id == "NYC_001"
    assert context.current_timestamp == datetime(2023, 1, 1, 12, 0, 0)


def test_field_reset_context_default_timestamp():
    """Test FieldResetContext with default timestamp."""
    context = FieldResetContext(
        field_name="precipitation",
        current_value=10.5,
        previous_data={},
        latitude=40.7128,
        longitude=-74.0060,
        station_id="NYC_001",
    )

    assert context.current_timestamp is None


@pytest.mark.asyncio
async def test_apply_field_resets_with_alert_using_context(
    applicator, mock_field_reset_manager, mock_alert_manager, mock_should_reset_callback
):
    """Test apply_field_resets_with_alert using FieldResetContext."""
    context = FieldResetContext(
        field_name="field1",
        current_value=20.0,
        previous_data={"field1": 15.0},
        latitude=40.7128,
        longitude=-74.0060,
        station_id="STATION_001",
        current_timestamp=datetime(2023, 1, 1, 12, 0, 0),
    )

    final_value, should_reset, boundary = await applicator.apply_field_resets_with_alert(context)

    assert final_value == "reset_value"
    assert should_reset is True
    assert boundary == datetime(2023, 1, 1, 6, 0, 0)

    mock_should_reset_callback.assert_called_once_with(
        "field1",
        40.7128,
        -74.0060,
        {"field1": 15.0},
        datetime(2023, 1, 1, 12, 0, 0),
    )
    mock_alert_manager.send_reset_alert.assert_called_once_with("STATION_001", "field1", True, 15.0, 20.0)
    mock_field_reset_manager.apply_reset_logic.assert_called_once_with("field1", 20.0, {"field1": 15.0}, True)


@pytest.mark.asyncio
async def test_apply_field_resets_with_alert_using_parameters(
    applicator, mock_field_reset_manager, mock_alert_manager, mock_should_reset_callback
):
    """Test apply_field_resets_with_alert using explicit parameters."""
    final_value, should_reset, boundary = await applicator.apply_field_resets_with_alert(
        field_name="field2",
        current_value=30.0,
        previous_data={"field2": 25.0},
        latitude=34.0522,
        longitude=-118.2437,
        station_id="LA_001",
        current_timestamp=datetime(2023, 1, 2, 14, 0, 0),
    )

    assert final_value == "reset_value"
    assert should_reset is True
    assert boundary == datetime(2023, 1, 1, 6, 0, 0)

    mock_should_reset_callback.assert_called_once_with(
        "field2",
        34.0522,
        -118.2437,
        {"field2": 25.0},
        datetime(2023, 1, 2, 14, 0, 0),
    )
    mock_alert_manager.send_reset_alert.assert_called_once_with("LA_001", "field2", True, 25.0, 30.0)


@pytest.mark.asyncio
async def test_apply_field_resets_with_alert_defaults(applicator, mock_field_reset_manager):
    """Test apply_field_resets_with_alert with default parameter values."""
    final_value, should_reset, boundary = await applicator.apply_field_resets_with_alert(
        field_name="field1",
        current_value=10.0,
    )

    assert final_value == "reset_value"
    mock_field_reset_manager.apply_reset_logic.assert_called_once()
    call_args = mock_field_reset_manager.apply_reset_logic.call_args
    assert call_args[0][0] == "field1"
    assert call_args[0][1] == 10.0
    assert call_args[0][2] == {}


@pytest.mark.asyncio
async def test_apply_field_resets_with_alert_none_values(applicator, mock_field_reset_manager):
    """Test apply_field_resets_with_alert with None lat/lon converts to 0.0."""
    await applicator.apply_field_resets_with_alert(
        field_name="field1",
        current_value=10.0,
        previous_data={},
        latitude=None,
        longitude=None,
        station_id="STATION_002",
    )

    mock_should_reset_callback = applicator.should_reset_callback
    call_args = mock_should_reset_callback.call_args
    assert call_args[0][1] == 0.0
    assert call_args[0][2] == 0.0


@pytest.mark.asyncio
async def test_apply_field_resets_not_in_daily_reset_fields(applicator, mock_alert_manager, mock_should_reset_callback):
    """Test apply_field_resets_with_alert for field not in daily_reset_fields."""
    final_value, should_reset, boundary = await applicator.apply_field_resets_with_alert(
        field_name="not_a_reset_field",
        current_value=100.0,
        previous_data={},
        latitude=40.0,
        longitude=-70.0,
        station_id="STATION_003",
    )

    assert final_value == 100.0
    assert should_reset is False
    assert boundary is None

    mock_should_reset_callback.assert_not_called()
    mock_alert_manager.send_reset_alert.assert_not_called()


@pytest.mark.asyncio
async def test_apply_field_resets_no_reset_needed(applicator, mock_field_reset_manager, mock_alert_manager):
    """Test apply_field_resets_with_alert when callback returns False."""
    applicator.should_reset_callback = MagicMock(return_value=(False, None))

    final_value, should_reset, boundary = await applicator.apply_field_resets_with_alert(
        field_name="field1",
        current_value=50.0,
        previous_data={"field1": 45.0},
        latitude=40.0,
        longitude=-70.0,
        station_id="STATION_004",
    )

    assert final_value == "reset_value"
    assert should_reset is False
    assert boundary is None

    mock_alert_manager.send_reset_alert.assert_called_once_with("STATION_004", "field1", False, 45.0, 50.0)
    mock_field_reset_manager.apply_reset_logic.assert_called_once_with("field1", 50.0, {"field1": 45.0}, False)


@pytest.mark.asyncio
async def test_send_reset_alert(applicator, mock_alert_manager):
    """Test _send_reset_alert method."""
    await applicator._send_reset_alert(
        station_id="STATION_005",
        field_name="precipitation",
        was_reset=True,
        previous_value=5.0,
        new_value=0.0,
    )

    mock_alert_manager.send_reset_alert.assert_called_once_with("STATION_005", "precipitation", True, 5.0, 0.0)
