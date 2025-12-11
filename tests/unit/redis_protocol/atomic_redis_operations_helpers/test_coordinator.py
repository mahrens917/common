"""Tests for AtomicOperationsCoordinator."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.redis_protocol.atomic_redis_operations_helpers.coordinator import (
    REDIS_ATOMIC_ERRORS,
    AtomicOperationsCoordinator,
)
from common.redis_protocol.atomic_redis_operations_helpers.data_fetcher import (
    RedisDataValidationError,
)


class TestAtomicOperationsCoordinator:
    """Tests for AtomicOperationsCoordinator class."""

    @pytest.fixture
    def mock_redis(self) -> Mock:
        """Create a mock Redis client."""
        return MagicMock(spec=Redis)

    @pytest.fixture
    def coordinator(self, mock_redis: Mock) -> AtomicOperationsCoordinator:
        """Create a coordinator instance with mocked components."""
        with patch("common.redis_protocol.atomic_redis_operations_helpers.coordinator.AtomicOperationsFactory") as mock_factory:
            mock_factory.create_components.return_value = {
                "transaction_writer": MagicMock(),
                "data_fetcher": MagicMock(),
                "field_validator": MagicMock(),
                "data_converter": MagicMock(),
                "spread_validator": MagicMock(),
                "deletion_validator": MagicMock(),
            }
            return AtomicOperationsCoordinator(mock_redis)

    def test_init_stores_redis_client(self, mock_redis: Mock) -> None:
        """Stores redis client."""
        with patch("common.redis_protocol.atomic_redis_operations_helpers.coordinator.AtomicOperationsFactory") as mock_factory:
            mock_factory.create_components.return_value = {
                "transaction_writer": MagicMock(),
                "data_fetcher": MagicMock(),
                "field_validator": MagicMock(),
                "data_converter": MagicMock(),
                "spread_validator": MagicMock(),
                "deletion_validator": MagicMock(),
            }
            coordinator = AtomicOperationsCoordinator(mock_redis)

        assert coordinator.redis is mock_redis

    def test_init_creates_components(self, mock_redis: Mock) -> None:
        """Creates all helper components."""
        with patch("common.redis_protocol.atomic_redis_operations_helpers.coordinator.AtomicOperationsFactory") as mock_factory:
            mock_factory.create_components.return_value = {
                "transaction_writer": MagicMock(),
                "data_fetcher": MagicMock(),
                "field_validator": MagicMock(),
                "data_converter": MagicMock(),
                "spread_validator": MagicMock(),
                "deletion_validator": MagicMock(),
            }
            coordinator = AtomicOperationsCoordinator(mock_redis)

        mock_factory.create_components.assert_called_once_with(mock_redis)
        assert coordinator.transaction_writer is not None
        assert coordinator.data_fetcher is not None
        assert coordinator.field_validator is not None
        assert coordinator.data_converter is not None
        assert coordinator.spread_validator is not None
        assert coordinator.deletion_validator is not None

    def test_init_sets_logger(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Sets logger."""
        assert coordinator.logger is not None


class TestAtomicMarketDataWrite:
    """Tests for atomic_market_data_write method."""

    @pytest.fixture
    def mock_redis(self) -> Mock:
        """Create a mock Redis client."""
        return MagicMock(spec=Redis)

    @pytest.fixture
    def coordinator(self, mock_redis: Mock) -> AtomicOperationsCoordinator:
        """Create a coordinator instance."""
        with patch("common.redis_protocol.atomic_redis_operations_helpers.coordinator.AtomicOperationsFactory") as mock_factory:
            mock_factory.create_components.return_value = {
                "transaction_writer": MagicMock(),
                "data_fetcher": MagicMock(),
                "field_validator": MagicMock(),
                "data_converter": MagicMock(),
                "spread_validator": MagicMock(),
                "deletion_validator": MagicMock(),
            }
            return AtomicOperationsCoordinator(mock_redis)

    @pytest.mark.asyncio
    async def test_delegates_to_transaction_writer(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Delegates to transaction writer."""
        coordinator.transaction_writer.atomic_market_data_write = AsyncMock(return_value=True)
        market_data = {"best_bid": 100, "best_ask": 101}

        result = await coordinator.atomic_market_data_write("test:key", market_data)

        assert result is True
        coordinator.transaction_writer.atomic_market_data_write.assert_called_once_with("test:key", market_data)

    @pytest.mark.asyncio
    async def test_returns_false_on_failure(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Returns False when write fails."""
        coordinator.transaction_writer.atomic_market_data_write = AsyncMock(return_value=False)
        market_data = {"best_bid": 100, "best_ask": 101}

        result = await coordinator.atomic_market_data_write("test:key", market_data)

        assert result is False


class TestSafeMarketDataRead:
    """Tests for safe_market_data_read method."""

    @pytest.fixture
    def mock_redis(self) -> Mock:
        """Create a mock Redis client."""
        return MagicMock(spec=Redis)

    @pytest.fixture
    def coordinator(self, mock_redis: Mock) -> AtomicOperationsCoordinator:
        """Create a coordinator instance."""
        with patch("common.redis_protocol.atomic_redis_operations_helpers.coordinator.AtomicOperationsFactory") as mock_factory:
            mock_components = {
                "transaction_writer": MagicMock(),
                "data_fetcher": MagicMock(),
                "field_validator": MagicMock(),
                "data_converter": MagicMock(),
                "spread_validator": MagicMock(),
                "deletion_validator": MagicMock(),
            }
            mock_factory.create_components.return_value = mock_components
            return AtomicOperationsCoordinator(mock_redis)

    @pytest.mark.asyncio
    async def test_uses_default_required_fields(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Uses default required fields when none provided."""
        raw_data = {
            "best_bid": "100",
            "best_ask": "101",
            "best_bid_size": "10",
            "best_ask_size": "20",
        }
        converted_data = {
            "best_bid": 100.0,
            "best_ask": 101.0,
            "best_bid_size": 10,
            "best_ask_size": 20,
        }

        coordinator.data_fetcher.fetch_market_data = AsyncMock(return_value=raw_data)
        coordinator.field_validator.ensure_required_fields = MagicMock()
        coordinator.data_converter.convert_market_payload = MagicMock(return_value=converted_data)
        coordinator.spread_validator.validate_bid_ask_spread = MagicMock()

        result = await coordinator.safe_market_data_read("test:key")

        assert result == converted_data
        coordinator.field_validator.ensure_required_fields.assert_called_once()
        call_args = coordinator.field_validator.ensure_required_fields.call_args
        assert set(call_args[0][1]) == {
            "best_bid",
            "best_ask",
            "best_bid_size",
            "best_ask_size",
        }

    @pytest.mark.asyncio
    async def test_uses_custom_required_fields(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Uses custom required fields when provided."""
        raw_data = {"custom_field": "value"}
        converted_data = {"custom_field": "value"}

        coordinator.data_fetcher.fetch_market_data = AsyncMock(return_value=raw_data)
        coordinator.field_validator.ensure_required_fields = MagicMock()
        coordinator.data_converter.convert_market_payload = MagicMock(return_value=converted_data)
        coordinator.spread_validator.validate_bid_ask_spread = MagicMock()

        result = await coordinator.safe_market_data_read("test:key", required_fields=["custom_field"])

        assert result == converted_data
        call_args = coordinator.field_validator.ensure_required_fields.call_args
        assert call_args[0][1] == ["custom_field"]

    @pytest.mark.asyncio
    async def test_successful_read_returns_converted_data(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Returns converted data on successful read."""
        raw_data = {"best_bid": "100", "best_ask": "101"}
        converted_data = {"best_bid": 100.0, "best_ask": 101.0}

        coordinator.data_fetcher.fetch_market_data = AsyncMock(return_value=raw_data)
        coordinator.field_validator.ensure_required_fields = MagicMock()
        coordinator.data_converter.convert_market_payload = MagicMock(return_value=converted_data)
        coordinator.spread_validator.validate_bid_ask_spread = MagicMock()

        result = await coordinator.safe_market_data_read("test:key")

        assert result == converted_data

    @pytest.mark.asyncio
    async def test_calls_all_validators_in_order(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Calls all validation steps in correct order."""
        raw_data = {"best_bid": "100"}
        converted_data = {"best_bid": 100.0}

        coordinator.data_fetcher.fetch_market_data = AsyncMock(return_value=raw_data)
        coordinator.field_validator.ensure_required_fields = MagicMock()
        coordinator.data_converter.convert_market_payload = MagicMock(return_value=converted_data)
        coordinator.spread_validator.validate_bid_ask_spread = MagicMock()

        await coordinator.safe_market_data_read("test:key")

        coordinator.data_fetcher.fetch_market_data.assert_called_once_with("test:key")
        coordinator.field_validator.ensure_required_fields.assert_called_once()
        coordinator.data_converter.convert_market_payload.assert_called_once()
        coordinator.spread_validator.validate_bid_ask_spread.assert_called_once()

    @pytest.mark.asyncio
    async def test_retries_on_validation_error(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Retries when validation error occurs."""
        raw_data = {"best_bid": "100"}
        converted_data = {"best_bid": 100.0}

        coordinator.data_fetcher.fetch_market_data = AsyncMock(
            side_effect=[
                RedisDataValidationError("validation failed"),
                raw_data,
            ]
        )
        coordinator.field_validator.ensure_required_fields = MagicMock()
        coordinator.data_converter.convert_market_payload = MagicMock(return_value=converted_data)
        coordinator.spread_validator.validate_bid_ask_spread = MagicMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await coordinator.safe_market_data_read("test:key")

        assert result == converted_data
        assert coordinator.data_fetcher.fetch_market_data.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_validation_retries(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Raises error after max retries exceeded for validation errors."""
        coordinator.data_fetcher.fetch_market_data = AsyncMock(side_effect=RedisDataValidationError("validation failed"))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RedisDataValidationError):
                await coordinator.safe_market_data_read("test:key")

    @pytest.mark.asyncio
    async def test_retries_on_redis_error(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Retries when Redis error occurs."""
        raw_data = {"best_bid": "100"}
        converted_data = {"best_bid": 100.0}

        coordinator.data_fetcher.fetch_market_data = AsyncMock(
            side_effect=[
                RedisError("connection error"),
                raw_data,
            ]
        )
        coordinator.field_validator.ensure_required_fields = MagicMock()
        coordinator.data_converter.convert_market_payload = MagicMock(return_value=converted_data)
        coordinator.spread_validator.validate_bid_ask_spread = MagicMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await coordinator.safe_market_data_read("test:key")

        assert result == converted_data

    @pytest.mark.asyncio
    async def test_raises_after_max_redis_error_retries(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Raises error after max retries exceeded for Redis errors."""
        coordinator.data_fetcher.fetch_market_data = AsyncMock(side_effect=RedisError("connection error"))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RedisDataValidationError) as exc_info:
                await coordinator.safe_market_data_read("test:key")

        assert "Error reading market data" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handles_connection_error(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Handles ConnectionError properly."""
        raw_data = {"best_bid": "100"}
        converted_data = {"best_bid": 100.0}

        coordinator.data_fetcher.fetch_market_data = AsyncMock(
            side_effect=[
                ConnectionError("connection lost"),
                raw_data,
            ]
        )
        coordinator.field_validator.ensure_required_fields = MagicMock()
        coordinator.data_converter.convert_market_payload = MagicMock(return_value=converted_data)
        coordinator.spread_validator.validate_bid_ask_spread = MagicMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await coordinator.safe_market_data_read("test:key")

        assert result == converted_data

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Handles TimeoutError properly."""
        raw_data = {"best_bid": "100"}
        converted_data = {"best_bid": 100.0}

        coordinator.data_fetcher.fetch_market_data = AsyncMock(
            side_effect=[
                TimeoutError("timeout"),
                raw_data,
            ]
        )
        coordinator.field_validator.ensure_required_fields = MagicMock()
        coordinator.data_converter.convert_market_payload = MagicMock(return_value=converted_data)
        coordinator.spread_validator.validate_bid_ask_spread = MagicMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await coordinator.safe_market_data_read("test:key")

        assert result == converted_data

    @pytest.mark.asyncio
    async def test_handles_runtime_error(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Handles RuntimeError properly."""
        raw_data = {"best_bid": "100"}
        converted_data = {"best_bid": 100.0}

        coordinator.data_fetcher.fetch_market_data = AsyncMock(
            side_effect=[
                RuntimeError("runtime error"),
                raw_data,
            ]
        )
        coordinator.field_validator.ensure_required_fields = MagicMock()
        coordinator.data_converter.convert_market_payload = MagicMock(return_value=converted_data)
        coordinator.spread_validator.validate_bid_ask_spread = MagicMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await coordinator.safe_market_data_read("test:key")

        assert result == converted_data

    @pytest.mark.asyncio
    async def test_handles_value_error(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Handles ValueError properly."""
        raw_data = {"best_bid": "100"}
        converted_data = {"best_bid": 100.0}

        coordinator.data_fetcher.fetch_market_data = AsyncMock(
            side_effect=[
                ValueError("invalid value"),
                raw_data,
            ]
        )
        coordinator.field_validator.ensure_required_fields = MagicMock()
        coordinator.data_converter.convert_market_payload = MagicMock(return_value=converted_data)
        coordinator.spread_validator.validate_bid_ask_spread = MagicMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await coordinator.safe_market_data_read("test:key")

        assert result == converted_data

    @pytest.mark.asyncio
    async def test_handles_type_error(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Handles TypeError properly."""
        raw_data = {"best_bid": "100"}
        converted_data = {"best_bid": 100.0}

        coordinator.data_fetcher.fetch_market_data = AsyncMock(
            side_effect=[
                TypeError("type error"),
                raw_data,
            ]
        )
        coordinator.field_validator.ensure_required_fields = MagicMock()
        coordinator.data_converter.convert_market_payload = MagicMock(return_value=converted_data)
        coordinator.spread_validator.validate_bid_ask_spread = MagicMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await coordinator.safe_market_data_read("test:key")

        assert result == converted_data

    @pytest.mark.asyncio
    async def test_logs_debug_on_success(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Logs debug message on successful read."""
        raw_data = {"best_bid": "100"}
        converted_data = {"best_bid": 100.0}

        coordinator.data_fetcher.fetch_market_data = AsyncMock(return_value=raw_data)
        coordinator.field_validator.ensure_required_fields = MagicMock()
        coordinator.data_converter.convert_market_payload = MagicMock(return_value=converted_data)
        coordinator.spread_validator.validate_bid_ask_spread = MagicMock()
        coordinator.logger = MagicMock()

        await coordinator.safe_market_data_read("test:key")

        coordinator.logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_logs_exception_on_error(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Logs exception on error."""
        coordinator.data_fetcher.fetch_market_data = AsyncMock(side_effect=RedisError("error"))
        coordinator.logger = MagicMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RedisDataValidationError):
                await coordinator.safe_market_data_read("test:key")

        coordinator.logger.exception.assert_called()


class TestAtomicDeleteIfInvalid:
    """Tests for atomic_delete_if_invalid method."""

    @pytest.fixture
    def mock_redis(self) -> Mock:
        """Create a mock Redis client."""
        return MagicMock(spec=Redis)

    @pytest.fixture
    def coordinator(self, mock_redis: Mock) -> AtomicOperationsCoordinator:
        """Create a coordinator instance."""
        with patch("common.redis_protocol.atomic_redis_operations_helpers.coordinator.AtomicOperationsFactory") as mock_factory:
            mock_factory.create_components.return_value = {
                "transaction_writer": MagicMock(),
                "data_fetcher": MagicMock(),
                "field_validator": MagicMock(),
                "data_converter": MagicMock(),
                "spread_validator": MagicMock(),
                "deletion_validator": MagicMock(),
            }
            return AtomicOperationsCoordinator(mock_redis)

    @pytest.mark.asyncio
    async def test_delegates_to_deletion_validator(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Delegates to deletion validator."""
        coordinator.deletion_validator.atomic_delete_if_invalid = AsyncMock(return_value=True)
        validation_data: Dict[str, Any] = {"best_bid": 0, "best_ask": 0}

        result = await coordinator.atomic_delete_if_invalid("test:key", validation_data)

        assert result is True
        coordinator.deletion_validator.atomic_delete_if_invalid.assert_called_once_with("test:key", validation_data)

    @pytest.mark.asyncio
    async def test_returns_false_when_not_deleted(self, coordinator: AtomicOperationsCoordinator) -> None:
        """Returns False when data is valid and not deleted."""
        coordinator.deletion_validator.atomic_delete_if_invalid = AsyncMock(return_value=False)
        validation_data: Dict[str, Any] = {"best_bid": 100, "best_ask": 101}

        result = await coordinator.atomic_delete_if_invalid("test:key", validation_data)

        assert result is False


class TestRedisAtomicErrors:
    """Tests for REDIS_ATOMIC_ERRORS constant."""

    def test_includes_redis_error(self) -> None:
        """Includes RedisError."""
        assert RedisError in REDIS_ATOMIC_ERRORS

    def test_includes_connection_error(self) -> None:
        """Includes ConnectionError."""
        assert ConnectionError in REDIS_ATOMIC_ERRORS

    def test_includes_timeout_error(self) -> None:
        """Includes TimeoutError."""
        assert TimeoutError in REDIS_ATOMIC_ERRORS

    def test_includes_runtime_error(self) -> None:
        """Includes RuntimeError."""
        assert RuntimeError in REDIS_ATOMIC_ERRORS

    def test_includes_value_error(self) -> None:
        """Includes ValueError."""
        assert ValueError in REDIS_ATOMIC_ERRORS

    def test_includes_type_error(self) -> None:
        """Includes TypeError."""
        assert TypeError in REDIS_ATOMIC_ERRORS

    def test_includes_validation_error(self) -> None:
        """Includes RedisDataValidationError."""
        assert RedisDataValidationError in REDIS_ATOMIC_ERRORS


class TestActualImplementations:
    """Tests for actual method implementations (not mocked)."""

    @pytest.fixture
    def mock_redis(self) -> Mock:
        """Create a mock Redis client."""
        redis_mock = MagicMock(spec=Redis)
        # Mock the pipeline context manager
        pipeline_mock = MagicMock()
        pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
        pipeline_mock.__aexit__ = AsyncMock(return_value=None)
        pipeline_mock.execute = AsyncMock(return_value=[1])
        pipeline_mock.hset = MagicMock()
        redis_mock.pipeline = MagicMock(return_value=pipeline_mock)
        redis_mock.hgetall = AsyncMock(
            return_value={
                "best_bid": "100.5",
                "best_ask": "101.5",
                "best_bid_size": "10",
                "best_ask_size": "20",
            }
        )
        redis_mock.delete = AsyncMock(return_value=1)
        return redis_mock

    @pytest.mark.asyncio
    async def test_actual_atomic_write_success(self, mock_redis: Mock) -> None:
        """Test actual atomic write implementation."""
        coordinator = AtomicOperationsCoordinator(mock_redis)
        market_data = {"best_bid": 100.5, "best_ask": 101.5}

        result = await coordinator.atomic_market_data_write("test:key", market_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_actual_safe_read_success(self, mock_redis: Mock) -> None:
        """Test actual safe read implementation."""
        coordinator = AtomicOperationsCoordinator(mock_redis)

        result = await coordinator.safe_market_data_read("test:key")

        assert "best_bid" in result
        assert isinstance(result["best_bid"], float)

    @pytest.mark.asyncio
    async def test_actual_safe_read_with_retry_on_validation_error(self, mock_redis: Mock) -> None:
        """Test actual safe read retries on validation error."""
        coordinator = AtomicOperationsCoordinator(mock_redis)
        # First call fails, second succeeds
        mock_redis.hgetall = AsyncMock(
            side_effect=[
                {},  # Empty data triggers validation error
                {
                    "best_bid": "100.5",
                    "best_ask": "101.5",
                    "best_bid_size": "10",
                    "best_ask_size": "20",
                },
            ]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await coordinator.safe_market_data_read("test:key")

        assert "best_bid" in result

    @pytest.mark.asyncio
    async def test_actual_safe_read_raises_on_missing_fields(self, mock_redis: Mock) -> None:
        """Test actual safe read raises when required fields missing."""
        coordinator = AtomicOperationsCoordinator(mock_redis)
        mock_redis.hgetall = AsyncMock(return_value={"other_field": "value"})

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RedisDataValidationError):
                await coordinator.safe_market_data_read("test:key")

    @pytest.mark.asyncio
    async def test_actual_safe_read_raises_on_redis_error(self, mock_redis: Mock) -> None:
        """Test actual safe read raises on Redis error after retries."""
        coordinator = AtomicOperationsCoordinator(mock_redis)
        mock_redis.hgetall = AsyncMock(side_effect=RedisError("connection failed"))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RedisDataValidationError) as exc_info:
                await coordinator.safe_market_data_read("test:key")

        assert "Error reading market data" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_actual_safe_read_with_custom_fields(self, mock_redis: Mock) -> None:
        """Test actual safe read with custom required fields."""
        coordinator = AtomicOperationsCoordinator(mock_redis)
        mock_redis.hgetall = AsyncMock(return_value={"custom_field": "100"})

        result = await coordinator.safe_market_data_read("test:key", required_fields=["custom_field"])

        assert "custom_field" in result

    @pytest.mark.asyncio
    async def test_actual_delete_if_invalid_deletes_on_zero_bid(self, mock_redis: Mock) -> None:
        """Test actual delete when bid is zero."""
        coordinator = AtomicOperationsCoordinator(mock_redis)
        validation_data = {
            "best_bid": 0,
            "best_ask": 100,
            "best_bid_size": 10,
            "best_ask_size": 20,
        }

        result = await coordinator.atomic_delete_if_invalid("test:key", validation_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_actual_delete_if_invalid_keeps_valid_data(self, mock_redis: Mock) -> None:
        """Test actual delete keeps valid data."""
        coordinator = AtomicOperationsCoordinator(mock_redis)
        validation_data = {
            "best_bid": 100,
            "best_ask": 101,
            "best_bid_size": 10,
            "best_ask_size": 20,
        }

        result = await coordinator.atomic_delete_if_invalid("test:key", validation_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_actual_safe_read_handles_asyncio_timeout(self, mock_redis: Mock) -> None:
        """Test actual safe read handles asyncio.TimeoutError."""
        import asyncio

        coordinator = AtomicOperationsCoordinator(mock_redis)
        mock_redis.hgetall = AsyncMock(
            side_effect=[
                asyncio.TimeoutError("timeout"),
                {
                    "best_bid": "100.5",
                    "best_ask": "101.5",
                    "best_bid_size": "10",
                    "best_ask_size": "20",
                },
            ]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await coordinator.safe_market_data_read("test:key")

        assert "best_bid" in result
