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

    prob_map = {"KEY_A": 0.1, "KEY_C": 0.3}

    async def fake_pipeline_fetch(_redis_client, matching_keys):
        return [prob_map.get(k) for k in matching_keys]

    pipeline_mock = AsyncMock(side_effect=fake_pipeline_fetch)
    monkeypatch.setattr(
        probability_calculator,
        "_fetch_probabilities_pipeline",
        pipeline_mock,
    )

    result = await calculate_range_probability(redis_client, "USD", 5.0, 25.0)

    assert result == pytest.approx(0.4)
    pipeline_mock.assert_called_once()
    called_keys = pipeline_mock.call_args[0][1]
    assert "KEY_A" in called_keys
    assert "KEY_C" in called_keys
