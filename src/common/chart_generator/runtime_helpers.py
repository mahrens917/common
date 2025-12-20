"""Standalone helpers for the chart generator runtime module."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import redis

from common.redis_protocol.typing import ensure_awaitable
from src.common.chart_generator.exceptions import (
    InsufficientDataError,
    ProgressNotificationError,
)
from src.common.chart_generator_helpers.chart_file_manager import ChartFileManager
from src.common.chart_generator_helpers.float_utils import safe_float
from src.common.chart_generator_helpers.price_chart_creator import PriceChartCreator
from src.common.chart_generator_helpers.progress_notifier import ProgressNotifier

from .dependencies import mdates, os, plt

if TYPE_CHECKING:
    from .runtime import ChartGenerator

logger = logging.getLogger("src.monitor.chart_generator")
MIN_DATA_POINTS_FOR_CHART = 2


async def create_load_chart(generator: "ChartGenerator", service_name: str, hours: int) -> str:
    from common.metadata_store import MetadataStore

    metadata_store = MetadataStore()
    await metadata_store.initialize()
    try:
        history_data = await metadata_store.get_service_history(service_name, hours)
        if not history_data:
            raise InsufficientDataError(f"No history data available for {service_name}")
        timestamps: List[datetime] = []
        values: List[float] = []
        for entry in history_data:
            value = entry.get("messages_per_minute", entry.get("messages_per_second"))
            numeric_value = _coerce_into_float(value)
            if numeric_value is None:
                continue
            if numeric_value > 0:
                timestamps.append(entry["timestamp"])
                values.append(numeric_value)
        if len(timestamps) < MIN_DATA_POINTS_FOR_CHART:
            raise InsufficientDataError(
                f"Insufficient data points for {service_name}: {len(timestamps)}"
            )
    finally:
        await metadata_store.cleanup()

    chart_title = f"{service_name.capitalize()} Updates / min"
    load_formatter = lambda x: f"{x:,.0f}"
    return await generator.generate_unified_chart(
        timestamps=timestamps,
        values=values,
        chart_title=chart_title,
        y_label="",
        value_formatter_func=load_formatter,
        line_color=getattr(generator, "primary_color", "#627EEA"),
    )


async def create_system_chart(generator: "ChartGenerator", metric: str, hours: int) -> str:
    from common.redis_utils import get_redis_connection

    redis_client = await get_redis_connection()
    try:
        data = await ensure_awaitable(redis_client.hgetall(f"history:{metric}"))
    finally:
        await redis_client.aclose()
    if not data:
        raise InsufficientDataError(f"No history data available for {metric}")
    current_time = int(datetime.now(tz=timezone.utc).timestamp())
    start_time = current_time - (hours * 3600)
    timestamps: List[datetime] = []
    values: List[float] = []
    for datetime_str, value_str in data.items():
        try:
            if isinstance(datetime_str, bytes):
                datetime_str = datetime_str.decode()
            if isinstance(value_str, bytes):
                value_str = value_str.decode()
            dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            timestamp = int(dt.timestamp())
            numeric_value = float(value_str)
        except (ValueError, UnicodeDecodeError, TypeError):
            continue
        if timestamp >= start_time and numeric_value > 0:
            timestamps.append(datetime.fromtimestamp(timestamp, tz=timezone.utc))
            values.append(numeric_value)
    if len(timestamps) < MIN_DATA_POINTS_FOR_CHART:
        raise InsufficientDataError(f"Insufficient data points for {metric}: {len(timestamps)}")
    sorted_pairs = sorted(zip(timestamps, values))
    sorted_timestamps, sorted_values = zip(*sorted_pairs)
    timestamps = list(sorted_timestamps)
    values = list(sorted_values)
    metric_label = metric.upper() if metric.lower() == "cpu" else metric.capitalize()
    chart_title = f"{metric_label} (per minute)"
    pct_formatter = lambda x: f"{x:.1f}%"
    return await generator.generate_unified_chart(
        timestamps=list(timestamps),
        values=list(values),
        chart_title=chart_title,
        y_label="",
        value_formatter_func=pct_formatter,
        line_color=getattr(generator, "primary_color", "#627EEA"),
    )


async def get_city_tokens_for_icao(generator: "ChartGenerator", station_icao: str):
    from src.common.chart_generator_helpers.city_token_resolver import CityTokenResolver

    resolver = CityTokenResolver()
    return await resolver.get_city_tokens_for_icao(station_icao)


async def get_kalshi_strikes_for_station(
    generator: "ChartGenerator", station_icao: str
) -> List[float]:
    from common.redis_utils import get_redis_connection

    redis_client = await get_redis_connection()
    try:
        city_tokens, canonical_token = await generator.get_city_tokens_for_icao(station_icao)
        if not city_tokens and not canonical_token:
            raise RuntimeError(f"No Kalshi tokens available for {station_icao}")
        return await generator.strike_collector.get_kalshi_strikes_for_station(
            redis_client, station_icao, city_tokens, canonical_token
        )
    finally:
        await redis_client.aclose()


def notify_progress(generator: "ChartGenerator", message: str) -> None:
    callback = generator.progress_callback
    if callback is not None:
        try:
            callback(message)
        except (
            RuntimeError,
            ValueError,
            TypeError,
        ) as exc:  # pragma: no cover - delegated hook
            raise ProgressNotificationError("Progress callback failed") from exc
        return
    notifier = generator.progress_notifier
    if notifier is None:
        return
    notifier.notify_progress(message)


def safe_float_value(value: str | float | int | None) -> Optional[float]:
    if isinstance(value, (float, int)):
        return float(value)
    return safe_float(value)


def _coerce_into_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def generate_load_charts(generator: "ChartGenerator", hours: int = 24) -> Dict[str, str]:
    load_gen = generator.load_charts_generator
    if load_gen is not None:
        return await load_gen.generate_load_charts(hours, os)
    generated_paths: List[str] = []
    try:
        deribit_chart = await generator.create_load_chart("deribit", hours)
        generated_paths.append(deribit_chart)
        kalshi_chart = await generator.create_load_chart("kalshi", hours)
        generated_paths.append(kalshi_chart)
        cpu_chart = await generator.create_system_chart("cpu", hours)
        generated_paths.append(cpu_chart)
        memory_chart = await generator.create_system_chart("memory", hours)
        generated_paths.append(memory_chart)
    except asyncio.CancelledError:
        for path in generated_paths:
            try:
                os.unlink(path)
            except OSError:
                logger.warning("Failed to cleanup load chart %s", path)
        raise
    except (IOError, OSError, ValueError, RuntimeError, redis.RedisError):
        for path in generated_paths:
            try:
                os.unlink(path)
            except OSError:
                logger.warning("Failed to cleanup load chart %s", path)
        raise
    return {
        "deribit": deribit_chart,
        "kalshi": kalshi_chart,
        "cpu": cpu_chart,
        "memory": memory_chart,
    }


async def generate_price_chart_with_path(
    generator: "ChartGenerator", symbol: str, prediction_horizon_days: Optional[int] = None
) -> str:
    creator = generator.price_chart_creator
    if creator is not None:
        return await creator.create_price_chart(symbol, prediction_horizon_days)
    return await generator.create_price_chart(symbol, prediction_horizon_days)


async def create_price_chart_impl(
    generator: "ChartGenerator", symbol: str, prediction_horizon_days: Optional[int] = None
) -> str:
    creator = generator.price_chart_creator
    if creator is None:
        progress_notifier = generator.progress_notifier
        if progress_notifier is None:
            progress_notifier = ProgressNotifier(generator.progress_callback)
            generator.progress_notifier = progress_notifier
        creator = PriceChartCreator(
            primary_color=getattr(generator, "primary_color", "#627EEA"),
            price_path_calculator=generator.price_path_calculator,
            price_path_horizon_days=generator.price_path_horizon_days,
            progress_notifier=progress_notifier,
            generate_unified_chart_func=generator.generate_unified_chart,
        )
        generator.price_chart_creator = creator
    return await creator.create_price_chart(symbol, prediction_horizon_days)


def configure_time_axis_with_5_minute_alignment(
    generator: "ChartGenerator",
    ax,
    timestamps,
    chart_type: str = "default",
    station_coordinates=None,
) -> None:
    generator.time_configurator.configure_time_axis_with_5_minute_alignment(
        ax, timestamps, chart_type, station_coordinates, mdates=mdates, plt=plt
    )


def configure_time_axis(
    generator: "ChartGenerator",
    ax,
    timestamps,
    chart_type: str = "default",
    station_coordinates=None,
) -> None:
    if chart_type == "price":
        generator.time_configurator.configure_price_chart_axis(
            ax, timestamps, mdates=mdates, plt=plt
        )
        return

    configure_time_axis_with_5_minute_alignment(
        generator,
        ax,
        timestamps,
        chart_type=chart_type,
        station_coordinates=station_coordinates,
    )


def configure_price_chart_axis(generator: "ChartGenerator", ax, timestamps) -> None:
    generator.time_configurator.configure_price_chart_axis(ax, timestamps, mdates=mdates, plt=plt)


def get_chart_file_manager(generator: "ChartGenerator") -> ChartFileManager:
    manager = getattr(generator, "_chart_file_manager", None)
    if isinstance(manager, ChartFileManager):
        return manager
    manager = ChartFileManager(os_module=os)
    generator.chart_file_manager = manager
    return manager


def cleanup_chart_files(generator: "ChartGenerator", chart_paths: List[str]) -> None:
    manager = get_chart_file_manager(generator)
    manager.cleanup_chart_files(chart_paths)


def cleanup_single_chart_file(generator: "ChartGenerator", chart_path: str) -> None:
    manager = get_chart_file_manager(generator)
    manager.cleanup_single_chart_file(chart_path)
