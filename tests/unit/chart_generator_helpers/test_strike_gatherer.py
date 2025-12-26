"""Tests for strike_gatherer module."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator_helpers.strike_gatherer import StrikeGatherer


@pytest.fixture
def mock_schema() -> MagicMock:
    """Create a mock schema."""
    schema = MagicMock()
    schema.kalshi_weather_prefix = "weather"
    return schema


@pytest.fixture
def mock_hash_decoder() -> MagicMock:
    """Create a mock hash decoder."""
    decoder = MagicMock()
    decoder.decode_weather_market_hash = MagicMock(return_value={"ticker": "TEST"})
    decoder.extract_strike_info = MagicMock(return_value=("single", 45.0, None))
    return decoder


@pytest.fixture
def mock_strike_accumulator() -> MagicMock:
    """Create a mock strike accumulator."""
    accumulator = MagicMock()
    accumulator.accumulate_strike_values = MagicMock()
    return accumulator


@pytest.fixture
def mock_expiration_validator() -> MagicMock:
    """Create a mock expiration validator."""
    validator = MagicMock()
    validator.market_expires_today = MagicMock(return_value=True)
    return validator


@pytest.fixture
def strike_gatherer(
    mock_schema: MagicMock,
    mock_hash_decoder: MagicMock,
    mock_strike_accumulator: MagicMock,
    mock_expiration_validator: MagicMock,
) -> StrikeGatherer:
    """Create a StrikeGatherer instance."""
    return StrikeGatherer(
        schema=mock_schema,
        hash_decoder=mock_hash_decoder,
        strike_accumulator=mock_strike_accumulator,
        expiration_validator=mock_expiration_validator,
    )


class TestStrikeGatherer:
    """Tests for StrikeGatherer class."""

    def test_init(
        self,
        mock_schema: MagicMock,
        mock_hash_decoder: MagicMock,
        mock_strike_accumulator: MagicMock,
        mock_expiration_validator: MagicMock,
    ) -> None:
        """Test StrikeGatherer initialization."""
        gatherer = StrikeGatherer(
            schema=mock_schema,
            hash_decoder=mock_hash_decoder,
            strike_accumulator=mock_strike_accumulator,
            expiration_validator=mock_expiration_validator,
        )

        assert gatherer.schema is mock_schema
        assert gatherer.hash_decoder is mock_hash_decoder
        assert gatherer.strike_accumulator is mock_strike_accumulator
        assert gatherer.expiration_validator is mock_expiration_validator

    @pytest.mark.asyncio
    async def test_gather_strikes_for_tokens_success(self, strike_gatherer: StrikeGatherer) -> None:
        """Test gathering strikes for tokens successfully."""
        redis_client = MagicMock()

        async def mock_scan_iter(match, count):
            yield b"weather:market1"

        redis_client.scan_iter = mock_scan_iter
        redis_client.hgetall = AsyncMock(return_value={b"ticker": b"TEST"})

        parse_fn = MagicMock()
        parse_fn.return_value.ticker = "TEST"

        with patch(
            "common.chart_generator_helpers.strike_gatherer.StrikeGatherer._collect_strikes_from_key",
            new_callable=AsyncMock,
            return_value=True,
        ):
            strikes, primary_found = await strike_gatherer.gather_strikes_for_tokens(
                redis_client=redis_client,
                tokens=["NYC"],
                parse_fn=parse_fn,
                today_et=date(2024, 12, 25),
                et_timezone=MagicMock(),
                today_market_date="2024-12-25",
            )

        assert primary_found is True

    @pytest.mark.asyncio
    async def test_gather_strikes_for_tokens_no_matches(self, strike_gatherer: StrikeGatherer) -> None:
        """Test gathering strikes when no matches found."""
        redis_client = MagicMock()

        async def mock_scan_iter(match, count):
            return
            yield

        redis_client.scan_iter = mock_scan_iter

        strikes, primary_found = await strike_gatherer.gather_strikes_for_tokens(
            redis_client=redis_client,
            tokens=["NYC"],
            parse_fn=MagicMock(),
            today_et=date(2024, 12, 25),
            et_timezone=MagicMock(),
            today_market_date="2024-12-25",
        )

        assert strikes == set()
        assert primary_found is False

    @pytest.mark.asyncio
    async def test_collect_strikes_from_key_list_success(self, strike_gatherer: StrikeGatherer) -> None:
        """Test collecting strikes from key list."""
        redis_client = MagicMock()
        redis_client.hgetall = AsyncMock(return_value={b"ticker": b"TEST"})

        with patch(
            "common.chart_generator_helpers.strike_gatherer.StrikeGatherer._collect_strikes_from_key",
            new_callable=AsyncMock,
            return_value=True,
        ):
            strikes = await strike_gatherer.collect_strikes_from_key_list(
                redis_client=redis_client,
                key_candidates=[b"weather:market1"],
                parse_fn=MagicMock(),
                today_et=date(2024, 12, 25),
                et_timezone=MagicMock(),
                today_market_date="2024-12-25",
            )

        assert isinstance(strikes, set)

    @pytest.mark.asyncio
    async def test_collect_strikes_from_key_skips_trading_signal(
        self,
        strike_gatherer: StrikeGatherer,
        mock_hash_decoder: MagicMock,
    ) -> None:
        """Test that trading signal keys are skipped."""
        redis_client = MagicMock()
        redis_client.hgetall = AsyncMock(return_value={b"ticker": b"TEST"})

        from common.chart_generator_helpers.config import StrikeCollectionContext

        context = StrikeCollectionContext(
            redis_client=redis_client,
            key_str="weather:market1:trading_signal",
            parse_fn=MagicMock(),
            today_et=date(2024, 12, 25),
            et_timezone=MagicMock(),
            today_market_date="2024-12-25",
            strikes=set(),
        )

        result = await strike_gatherer._collect_strikes_from_key(context=context)

        assert result is False
        mock_hash_decoder.decode_weather_market_hash.assert_not_called()

    @pytest.mark.asyncio
    async def test_collect_strikes_from_key_skips_position_state(
        self,
        strike_gatherer: StrikeGatherer,
        mock_hash_decoder: MagicMock,
    ) -> None:
        """Test that position state keys are skipped."""
        redis_client = MagicMock()
        redis_client.hgetall = AsyncMock(return_value={b"ticker": b"TEST"})

        from common.chart_generator_helpers.config import StrikeCollectionContext

        context = StrikeCollectionContext(
            redis_client=redis_client,
            key_str="weather:market1:position_state",
            parse_fn=MagicMock(),
            today_et=date(2024, 12, 25),
            et_timezone=MagicMock(),
            today_market_date="2024-12-25",
            strikes=set(),
        )

        result = await strike_gatherer._collect_strikes_from_key(context=context)

        assert result is False

    @pytest.mark.asyncio
    async def test_collect_strikes_from_key_handles_parse_error(
        self,
        strike_gatherer: StrikeGatherer,
    ) -> None:
        """Test that parse errors are handled gracefully."""
        redis_client = MagicMock()
        redis_client.hgetall = AsyncMock(return_value={b"ticker": b"TEST"})

        parse_fn = MagicMock(side_effect=ValueError("Parse error"))

        from common.chart_generator_helpers.config import StrikeCollectionContext

        context = StrikeCollectionContext(
            redis_client=redis_client,
            key_str="weather:market1",
            parse_fn=parse_fn,
            today_et=date(2024, 12, 25),
            et_timezone=MagicMock(),
            today_market_date="2024-12-25",
            strikes=set(),
        )

        result = await strike_gatherer._collect_strikes_from_key(context=context)

        assert result is False

    @pytest.mark.asyncio
    async def test_collect_strikes_from_key_returns_false_for_empty_data(
        self,
        strike_gatherer: StrikeGatherer,
    ) -> None:
        """Test returns False when market data is empty."""
        redis_client = MagicMock()
        redis_client.hgetall = AsyncMock(return_value={})

        parse_fn = MagicMock()
        parse_fn.return_value.ticker = "TEST"

        from common.chart_generator_helpers.config import StrikeCollectionContext

        with patch("common.redis_protocol.typing.ensure_awaitable", new_callable=AsyncMock, return_value={}):
            context = StrikeCollectionContext(
                redis_client=redis_client,
                key_str="weather:market1",
                parse_fn=parse_fn,
                today_et=date(2024, 12, 25),
                et_timezone=MagicMock(),
                today_market_date="2024-12-25",
                strikes=set(),
            )

            result = await strike_gatherer._collect_strikes_from_key(context=context)

        assert result is False
