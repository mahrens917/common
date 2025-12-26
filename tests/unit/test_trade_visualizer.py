"""Tests for TradeVisualizer module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from matplotlib.axes import Axes

from common.data_models.trade_record import TradeRecord, TradeSide
from common.redis_protocol.trade_store import TradeStoreError
from common.trade_visualizer import (
    MarketState,
    TradeShading,
    TradeVisualizer,
    create_trade_visualizer,
)
from common.trade_visualizer_helpers import (
    LiquidityFetcher,
    RedisFetcher,
    ShadingBuilder,
    TradeFetcher,
)

# Test constants (data_guard requirement)
TEST_STATION_ICAO = "KJFK"
TEST_ORDER_ID = "order-123"
TEST_MARKET_TICKER = "KXHIGH-KJFK"
TEST_MARKET_CATEGORY = "weather"
TEST_TRADE_RULE = "rule_1"
TEST_TRADE_REASON = "initial-entry"
TEST_PRICE_CENTS = 55
TEST_QUANTITY = 10
TEST_FEE_CENTS = 5
TEST_COST_CENTS = TEST_PRICE_CENTS * TEST_QUANTITY + TEST_FEE_CENTS
TEST_START_TIME = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
TEST_END_TIME = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
TEST_TRADE_TIMESTAMP = datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc)
TEST_TEMPERATURE_TIMESTAMPS = [
    datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
    datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc),
    datetime(2024, 1, 15, 11, 30, tzinfo=timezone.utc),
]
TEST_KALSHI_STRIKES = [50.0, 55.0, 60.0, 65.0, 70.0]
TEST_BUY_COLOR = "#90EE90"
TEST_SELL_COLOR = "#FFB6C1"
TEST_UNEXECUTED_COLOR = "#808080"
TEST_ALPHA = 0.3


def _create_test_trade(**overrides) -> TradeRecord:
    """Create a test trade record with default values."""
    data = {
        "order_id": TEST_ORDER_ID,
        "market_ticker": TEST_MARKET_TICKER,
        "trade_timestamp": TEST_TRADE_TIMESTAMP,
        "trade_side": TradeSide.YES,
        "quantity": TEST_QUANTITY,
        "price_cents": TEST_PRICE_CENTS,
        "fee_cents": TEST_FEE_CENTS,
        "cost_cents": TEST_COST_CENTS,
        "market_category": TEST_MARKET_CATEGORY,
        "weather_station": TEST_STATION_ICAO,
        "trade_rule": TEST_TRADE_RULE,
        "trade_reason": TEST_TRADE_REASON,
    }
    data.update(overrides)
    if "cost_cents" not in overrides and any(k in overrides for k in ["price_cents", "quantity", "fee_cents"]):
        data["cost_cents"] = data["price_cents"] * data["quantity"] + data["fee_cents"]
    return TradeRecord(**data)


def _create_test_market_state(**overrides) -> MarketState:
    """Create a test market state with default values."""
    data = {
        "market_ticker": TEST_MARKET_TICKER,
        "timestamp": TEST_TRADE_TIMESTAMP,
        "yes_bid": 50,
        "yes_ask": 60,
        "traded": False,
        "min_strike_price_cents": 50.0,
        "max_strike_price_cents": 70.0,
    }
    data.update(overrides)
    return MarketState(**data)


@pytest.fixture
def mock_trade_store():
    """Create a mock TradeStore."""
    store = AsyncMock()
    store.initialize.return_value = True
    store.close.return_value = None
    return store


@pytest.fixture
def mock_kalshi_store():
    """Create a mock KalshiStore."""
    store = AsyncMock()
    store.initialize.return_value = True
    store.close.return_value = None
    return store


@pytest.fixture
def mock_trade_fetcher():
    """Create a mock TradeFetcher."""
    return Mock(spec=TradeFetcher)


@pytest.fixture
def mock_liquidity_fetcher():
    """Create a mock LiquidityFetcher."""
    return Mock(spec=LiquidityFetcher)


@pytest.fixture
def mock_shading_builder():
    """Create a mock ShadingBuilder."""
    builder = Mock(spec=ShadingBuilder)
    builder.EXECUTED_BUY_COLOR = TEST_BUY_COLOR
    builder.EXECUTED_SELL_COLOR = TEST_SELL_COLOR
    builder.UNEXECUTED_COLOR = TEST_UNEXECUTED_COLOR
    builder.DEFAULT_ALPHA = TEST_ALPHA
    return builder


@pytest.fixture
def mock_redis_fetcher():
    """Create a mock RedisFetcher."""
    return Mock(spec=RedisFetcher)


@pytest.fixture
def trade_visualizer(
    mock_trade_store,
    mock_kalshi_store,
    mock_trade_fetcher,
    mock_liquidity_fetcher,
    mock_shading_builder,
    mock_redis_fetcher,
):
    """Create a TradeVisualizer with mocked dependencies."""
    return TradeVisualizer(
        trade_store=mock_trade_store,
        kalshi_store=mock_kalshi_store,
        trade_fetcher=mock_trade_fetcher,
        liquidity_fetcher=mock_liquidity_fetcher,
        shading_builder=mock_shading_builder,
        redis_fetcher=mock_redis_fetcher,
    )


def test_create_trade_visualizer_factory():
    """Test the factory function creates a TradeVisualizer with real dependencies."""
    with (
        patch("common.trade_visualizer.TradeStore"),
        patch("common.trade_visualizer.KalshiStore"),
        patch("common.trade_visualizer.TradeFetcher"),
        patch("common.trade_visualizer.LiquidityFetcher"),
        patch("common.trade_visualizer.ShadingBuilder"),
        patch("common.trade_visualizer.RedisFetcher"),
    ):
        visualizer = create_trade_visualizer()
        assert isinstance(visualizer, TradeVisualizer)


def test_trade_visualizer_initialization(trade_visualizer, mock_shading_builder):
    """Test TradeVisualizer initializes with correct attributes."""
    assert trade_visualizer._shading_builder == mock_shading_builder
    assert trade_visualizer.EXECUTED_BUY_COLOR == TEST_BUY_COLOR
    assert trade_visualizer.EXECUTED_SELL_COLOR == TEST_SELL_COLOR
    assert trade_visualizer.UNEXECUTED_COLOR == TEST_UNEXECUTED_COLOR
    assert trade_visualizer.DEFAULT_ALPHA == TEST_ALPHA


def test_trade_visualizer_initialization_with_missing_attributes():
    """Test TradeVisualizer uses default colors when builder lacks attributes."""
    mock_builder = Mock(spec=ShadingBuilder)
    del mock_builder.EXECUTED_BUY_COLOR
    del mock_builder.EXECUTED_SELL_COLOR
    del mock_builder.UNEXECUTED_COLOR
    del mock_builder.DEFAULT_ALPHA

    visualizer = TradeVisualizer(
        trade_store=AsyncMock(),
        kalshi_store=AsyncMock(),
        trade_fetcher=Mock(),
        liquidity_fetcher=Mock(),
        shading_builder=mock_builder,
        redis_fetcher=Mock(),
    )

    assert visualizer.EXECUTED_BUY_COLOR == "#90EE90"
    assert visualizer.EXECUTED_SELL_COLOR == "#FFB6C1"
    assert visualizer.UNEXECUTED_COLOR == "#808080"
    assert visualizer.DEFAULT_ALPHA == 0.3


@pytest.mark.asyncio
async def test_initialize_success(trade_visualizer, mock_trade_store, mock_kalshi_store):
    """Test successful initialization of stores."""
    result = await trade_visualizer.initialize()

    assert result is True
    mock_trade_store.initialize.assert_awaited_once()
    mock_kalshi_store.initialize.assert_awaited_once()


@pytest.mark.asyncio
async def test_initialize_trade_store_failure(trade_visualizer, mock_trade_store):
    """Test initialization fails when TradeStore fails."""
    mock_trade_store.initialize.return_value = False

    with pytest.raises(TradeStoreError, match="Failed to initialize Trade store"):
        await trade_visualizer.initialize()


@pytest.mark.asyncio
async def test_initialize_kalshi_store_failure(trade_visualizer, mock_trade_store, mock_kalshi_store):
    """Test initialization fails when KalshiStore fails."""
    mock_trade_store.initialize.return_value = True
    mock_kalshi_store.initialize.return_value = False

    with pytest.raises(RuntimeError, match="Failed to initialize Kalshi store"):
        await trade_visualizer.initialize()


@pytest.mark.asyncio
async def test_close(trade_visualizer, mock_trade_store, mock_kalshi_store):
    """Test closing stores."""
    await trade_visualizer.close()

    mock_trade_store.close.assert_awaited_once()
    mock_kalshi_store.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_trade_shadings_for_station_with_trades(trade_visualizer):
    """Test getting trade shadings with executed trades."""
    test_trade = _create_test_trade()
    test_shading = TradeShading(
        start_time=TEST_START_TIME,
        end_time=TEST_END_TIME,
        y_min=50.0,
        y_max=60.0,
        color=TEST_BUY_COLOR,
        alpha=TEST_ALPHA,
        label="Test shading",
    )

    with (
        patch.object(
            trade_visualizer,
            "_get_executed_trades_for_station",
            new_callable=AsyncMock,
            return_value=[test_trade],
        ),
        patch.object(
            trade_visualizer,
            "_create_executed_trade_shading",
            return_value=test_shading,
        ),
        patch.object(
            trade_visualizer,
            "_get_market_liquidity_states",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        shadings = await trade_visualizer.get_trade_shadings_for_station(
            TEST_STATION_ICAO,
            TEST_START_TIME,
            TEST_END_TIME,
            TEST_TEMPERATURE_TIMESTAMPS,
            TEST_KALSHI_STRIKES,
        )

        assert len(shadings) == 1
        assert shadings[0] == test_shading


@pytest.mark.asyncio
async def test_get_trade_shadings_for_station_with_liquidity_states(trade_visualizer):
    """Test getting trade shadings with liquidity states."""
    test_state = _create_test_market_state(yes_bid=0, yes_ask=100)
    test_shading = TradeShading(
        start_time=TEST_START_TIME,
        end_time=TEST_END_TIME,
        y_min=50.0,
        y_max=60.0,
        color=TEST_UNEXECUTED_COLOR,
        alpha=TEST_ALPHA,
        label="No liquidity",
    )

    with (
        patch.object(
            trade_visualizer,
            "_get_executed_trades_for_station",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(
            trade_visualizer,
            "_get_market_liquidity_states",
            new_callable=AsyncMock,
            return_value=[test_state],
        ),
        patch.object(trade_visualizer, "_is_no_liquidity_state", return_value=True),
        patch.object(
            trade_visualizer,
            "_create_no_liquidity_shading",
            return_value=test_shading,
        ),
    ):
        shadings = await trade_visualizer.get_trade_shadings_for_station(
            TEST_STATION_ICAO,
            TEST_START_TIME,
            TEST_END_TIME,
            TEST_TEMPERATURE_TIMESTAMPS,
            TEST_KALSHI_STRIKES,
        )

        assert len(shadings) == 1
        assert shadings[0] == test_shading


@pytest.mark.asyncio
async def test_get_trade_shadings_for_station_filters_none_shadings(trade_visualizer):
    """Test that None shadings are filtered out."""
    test_trade = _create_test_trade()

    with (
        patch.object(
            trade_visualizer,
            "_get_executed_trades_for_station",
            new_callable=AsyncMock,
            return_value=[test_trade],
        ),
        patch.object(trade_visualizer, "_create_executed_trade_shading", return_value=None),
        patch.object(
            trade_visualizer,
            "_get_market_liquidity_states",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        shadings = await trade_visualizer.get_trade_shadings_for_station(
            TEST_STATION_ICAO,
            TEST_START_TIME,
            TEST_END_TIME,
            TEST_TEMPERATURE_TIMESTAMPS,
            TEST_KALSHI_STRIKES,
        )

        assert len(shadings) == 0


@pytest.mark.asyncio
async def test_get_trade_shadings_for_station_handles_os_error(trade_visualizer):
    """Test handling of OSError returns empty list."""
    with patch.object(
        trade_visualizer,
        "_get_executed_trades_for_station",
        new_callable=AsyncMock,
        side_effect=OSError("Connection failed"),
    ):
        shadings = await trade_visualizer.get_trade_shadings_for_station(
            TEST_STATION_ICAO,
            TEST_START_TIME,
            TEST_END_TIME,
            TEST_TEMPERATURE_TIMESTAMPS,
            TEST_KALSHI_STRIKES,
        )

        assert shadings == []


@pytest.mark.asyncio
async def test_get_trade_shadings_for_station_handles_connection_error(
    trade_visualizer,
):
    """Test handling of ConnectionError returns empty list."""
    with patch.object(
        trade_visualizer,
        "_get_executed_trades_for_station",
        new_callable=AsyncMock,
        side_effect=ConnectionError("Connection failed"),
    ):
        shadings = await trade_visualizer.get_trade_shadings_for_station(
            TEST_STATION_ICAO,
            TEST_START_TIME,
            TEST_END_TIME,
            TEST_TEMPERATURE_TIMESTAMPS,
            TEST_KALSHI_STRIKES,
        )

        assert shadings == []


@pytest.mark.asyncio
async def test_get_trade_shadings_for_station_handles_runtime_error(trade_visualizer):
    """Test handling of RuntimeError returns empty list."""
    with patch.object(
        trade_visualizer,
        "_get_executed_trades_for_station",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Runtime error"),
    ):
        shadings = await trade_visualizer.get_trade_shadings_for_station(
            TEST_STATION_ICAO,
            TEST_START_TIME,
            TEST_END_TIME,
            TEST_TEMPERATURE_TIMESTAMPS,
            TEST_KALSHI_STRIKES,
        )

        assert shadings == []


@pytest.mark.asyncio
async def test_get_trade_shadings_for_station_handles_value_error(trade_visualizer):
    """Test handling of ValueError returns empty list."""
    with patch.object(
        trade_visualizer,
        "_get_executed_trades_for_station",
        new_callable=AsyncMock,
        side_effect=ValueError("Invalid value"),
    ):
        shadings = await trade_visualizer.get_trade_shadings_for_station(
            TEST_STATION_ICAO,
            TEST_START_TIME,
            TEST_END_TIME,
            TEST_TEMPERATURE_TIMESTAMPS,
            TEST_KALSHI_STRIKES,
        )

        assert shadings == []


@pytest.mark.asyncio
async def test_get_trade_shadings_for_station_propagates_cancelled_error(
    trade_visualizer,
):
    """Test that CancelledError is propagated."""
    import asyncio

    with patch.object(
        trade_visualizer,
        "_get_executed_trades_for_station",
        new_callable=AsyncMock,
        side_effect=asyncio.CancelledError(),
    ):
        with pytest.raises(asyncio.CancelledError):
            await trade_visualizer.get_trade_shadings_for_station(
                TEST_STATION_ICAO,
                TEST_START_TIME,
                TEST_END_TIME,
                TEST_TEMPERATURE_TIMESTAMPS,
                TEST_KALSHI_STRIKES,
            )


def test_apply_trade_shadings_to_chart(trade_visualizer, mock_shading_builder):
    """Test applying trade shadings to matplotlib chart."""
    mock_ax = Mock(spec=Axes)
    test_shadings = [
        TradeShading(
            start_time=TEST_START_TIME,
            end_time=TEST_END_TIME,
            y_min=50.0,
            y_max=60.0,
            color=TEST_BUY_COLOR,
            alpha=TEST_ALPHA,
            label="Test",
        )
    ]

    trade_visualizer.apply_trade_shadings_to_chart(mock_ax, test_shadings, TEST_TEMPERATURE_TIMESTAMPS)

    mock_shading_builder.apply_trade_shadings_to_chart.assert_called_once_with(mock_ax, test_shadings, TEST_TEMPERATURE_TIMESTAMPS)


def test_create_executed_trade_shading(trade_visualizer, mock_shading_builder):
    """Test creating executed trade shading through test hooks."""
    test_trade = _create_test_trade()
    expected_shading = TradeShading(
        start_time=TEST_START_TIME,
        end_time=TEST_END_TIME,
        y_min=50.0,
        y_max=60.0,
        color=TEST_BUY_COLOR,
        alpha=TEST_ALPHA,
        label="Test",
    )

    with patch(
        "common.trade_visualizer.create_executed_trade_shading",
        return_value=expected_shading,
    ):
        result = trade_visualizer._create_executed_trade_shading(test_trade, TEST_KALSHI_STRIKES, TEST_TEMPERATURE_TIMESTAMPS)

        assert result == expected_shading


def test_create_no_liquidity_shading(trade_visualizer, mock_shading_builder):
    """Test creating no liquidity shading through test hooks."""
    test_state = _create_test_market_state()
    expected_shading = TradeShading(
        start_time=TEST_START_TIME,
        end_time=TEST_END_TIME,
        y_min=50.0,
        y_max=60.0,
        color=TEST_UNEXECUTED_COLOR,
        alpha=TEST_ALPHA,
        label="No liquidity",
    )

    with patch(
        "common.trade_visualizer.create_no_liquidity_shading",
        return_value=expected_shading,
    ):
        result = trade_visualizer._create_no_liquidity_shading(test_state, TEST_KALSHI_STRIKES, TEST_TEMPERATURE_TIMESTAMPS)

        assert result == expected_shading


def test_is_no_liquidity_state(trade_visualizer, mock_shading_builder):
    """Test checking if state represents no liquidity through test hooks."""
    test_state = _create_test_market_state()

    with patch("common.trade_visualizer.is_no_liquidity_state", return_value=True) as mock_check:
        result = trade_visualizer._is_no_liquidity_state(test_state)

        assert result is True
        mock_check.assert_called_once_with(mock_shading_builder, test_state)


@pytest.mark.asyncio
async def test_get_executed_trades_for_station_test_hook(trade_visualizer, mock_redis_fetcher):
    """Test getting executed trades through test hooks."""
    test_trades = [_create_test_trade()]

    mock_redis = AsyncMock()
    mock_redis_fetcher.get_executed_trades_for_station.return_value = test_trades

    with patch(
        "common.trade_visualizer.get_redis_connection",
        new_callable=AsyncMock,
        return_value=mock_redis,
    ):
        result = await trade_visualizer._get_executed_trades_for_station(TEST_STATION_ICAO, TEST_START_TIME, TEST_END_TIME)

        assert result == test_trades
        mock_redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_market_liquidity_states_test_hook(trade_visualizer, mock_redis_fetcher):
    """Test getting market liquidity states through test hooks."""
    test_states = [_create_test_market_state()]

    mock_redis = AsyncMock()
    mock_redis_fetcher.get_market_liquidity_states.return_value = test_states

    with patch(
        "common.trade_visualizer.get_redis_connection",
        new_callable=AsyncMock,
        return_value=mock_redis,
    ):
        result = await trade_visualizer._get_market_liquidity_states(TEST_STATION_ICAO, TEST_START_TIME, TEST_END_TIME)

        assert result == test_states
        mock_redis.aclose.assert_awaited_once()


def test_safe_float_test_hook(trade_visualizer, mock_liquidity_fetcher):
    """Test safe float conversion through test hooks."""
    test_value = "55.5"
    expected_result = 55.5

    with patch("common.trade_visualizer.safe_float", return_value=expected_result):
        result = trade_visualizer._safe_float(test_value)

        assert result == expected_result
