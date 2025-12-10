"""Tests for the probability range calculator."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.data_models.modelstate_helpers import probability_calculator
from common.data_models.modelstate_helpers.probability_calculator import (
    calculate_range_probability,
)


@pytest.mark.asyncio
async def test_returns_none_when_no_keys(monkeypatch):
    """Should return None and log a warning when no keys are available."""
    redis_client = MagicMock()
    monkeypatch.setattr(
        probability_calculator,
        "fetch_probability_keys",
        AsyncMock(return_value=[]),
    )
    mock_logger = MagicMock()
    monkeypatch.setattr(probability_calculator, "logger", mock_logger)

    result = await calculate_range_probability(redis_client, "USD", 1.0, 5.0)

    assert result is None
    mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_skips_invalid_keys(monkeypatch):
    """Keys that cannot be decoded should be skipped and still return None."""
    redis_client = MagicMock()
    monkeypatch.setattr(
        probability_calculator,
        "fetch_probability_keys",
        AsyncMock(return_value=["bad"]),
    )
    monkeypatch.setattr(
        probability_calculator,
        "decode_redis_key",
        lambda key: None,
    )
    mock_logger = MagicMock()
    monkeypatch.setattr(probability_calculator, "logger", mock_logger)

    result = await calculate_range_probability(redis_client, "USD", 1.0, 5.0)

    assert result is None
    mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_accumulates_valid_probabilities(monkeypatch):
    """Valid keys within the strike range should accumulate probability."""
    redis_client = MagicMock()
    keys = ["key_a", "key_b", "key_c"]
    monkeypatch.setattr(
        probability_calculator,
        "fetch_probability_keys",
        AsyncMock(return_value=keys),
    )
    monkeypatch.setattr(
        probability_calculator,
        "decode_redis_key",
        lambda key: key.upper(),
    )
    strikes = {"KEY_A": "10", "KEY_B": "50", "KEY_C": "20"}
    monkeypatch.setattr(
        probability_calculator,
        "extract_strike_from_key",
        lambda key_str: strikes.get(key_str),
    )

    def in_range(strike_value: str, low: float, high: float) -> bool:
        return float(strike_value) >= low and float(strike_value) <= high

    monkeypatch.setattr(
        probability_calculator,
        "check_strike_in_range",
        in_range,
    )

    async def extract_probability(_redis_client, key_str):
        mapping = {"KEY_A": 0.1, "KEY_B": None, "KEY_C": 0.3}
        return mapping.get(key_str)

    extract_mock = AsyncMock(side_effect=extract_probability)
    monkeypatch.setattr(
        probability_calculator,
        "extract_probability_from_key",
        extract_mock,
    )

    result = await calculate_range_probability(redis_client, "USD", 5.0, 25.0)

    assert result == pytest.approx(0.4)
    extract_mock.assert_any_call(redis_client, "KEY_A")
    extract_mock.assert_any_call(redis_client, "KEY_C")
