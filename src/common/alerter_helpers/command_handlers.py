"""Command handlers for Alerter Telegram commands."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, cast

from src.common.price_path_calculator import (
    MostProbablePricePathCalculator,
    PricePathComputationError,
)

from ..alerting import AlertSeverity
from ..chart_generator import ChartGenerator, InsufficientDataError, ProgressNotificationError

if TYPE_CHECKING:
    from src.monitor.pnl_reporter import PnlReporter

logger = logging.getLogger(__name__)

DEFAULT_TELEGRAM_MESSAGE_TEXT = ""


class ChartGeneratorProtocol(Protocol):
    """Subset of ChartGenerator used by command handlers."""

    async def generate_load_charts(self, hours: int = 24) -> Dict[str, str]: ...

    async def generate_pnl_charts(self, pnl_data: Dict[str, Any]) -> List[str]: ...

    async def generate_weather_charts(self) -> List[str]: ...

    async def generate_price_chart_with_path(self, symbol: str, prediction_horizon_days: Optional[int] = None) -> str: ...

    def cleanup_single_chart_file(self, chart_path: str) -> None: ...


class _ChartHandlerBase:
    """Shared initializer for handlers that use chart generation callbacks."""

    def __init__(
        self,
        chart_generator: Optional[ChartGeneratorProtocol],
        send_alert_callback,
        send_chart_image_callback,
    ):
        self.chart_generator = chart_generator
        self.send_alert = send_alert_callback
        self.send_chart_image = send_chart_image_callback


class HelpCommandHandler:
    """Handles /help command."""

    async def handle(self, send_alert_callback) -> None:
        """Handle /help command with updated command list."""
        commands = [
            "/pnl - P&L reports",
            "/markets - Market status",
            "/status - System status",
            "/jobs - Status of recurring jobs",
            "/temp - Temperature charts",
            "/price - Price charts",
            "/surface - Probability surface",
            "/trade - Toggle trading",
            "/load - Performance graphs",
            "/ping - Health check (pong)",
            "/restart - Restart all services",
            "/help - Show inline command help",
        ]
        help_text = "\n".join(commands)
        await send_alert_callback(help_text, alert_type="help_response")


class LoadCommandHandler(_ChartHandlerBase):
    """Handles /load command - generate and send load charts."""

    async def handle(self, message: Dict[str, Any]) -> None:
        """Handle /load command - generate and send load charts."""
        if self.chart_generator is None:
            await self.send_alert("❌ Chart generator unavailable; cannot produce load charts")
            return

        try:
            chart_paths = await self.chart_generator.generate_load_charts(hours=24)
        except InsufficientDataError as exc:
            logger.warning("Load command aborted: %s", exc)
            await self.send_alert(f"❌ Insufficient data for load charts")
            return
        except (
            PricePathComputationError,
            ProgressNotificationError,
            RuntimeError,
            ValueError,
            OSError,
        ):
            logger.error("Failed to generate load charts", exc_info=True)
            await self.send_alert(f"❌ Failed to generate load charts")
            return

        if not chart_paths:
            await self.send_alert("❌ No load charts generated")
            return

        from .chart_batch_sender import ChartBatchSender

        batch_sender = ChartBatchSender(self.chart_generator, self.send_chart_image, self.send_alert)
        success_count = await batch_sender.send_charts_batch(chart_paths, "")
        if success_count == 0:
            await self.send_alert("❌ Failed to send load charts")


class PnlCommandHandler:
    """Handles /pnl command - send daily trade summary."""

    def __init__(
        self,
        pnl_reporter: Optional[PnlReporter],
        chart_generator: Optional[ChartGeneratorProtocol],
        send_alert_callback,
        send_chart_image_callback,
        ensure_pnl_reporter_callback,
    ):
        self.pnl_reporter = pnl_reporter
        self.chart_generator = chart_generator
        self.send_alert = send_alert_callback
        self.send_chart_image = send_chart_image_callback
        self.ensure_pnl_reporter = ensure_pnl_reporter_callback

    async def handle(self, message: Dict[str, Any]) -> None:
        """Handle /pnl command - send daily trade summary."""
        reporter = await self.ensure_pnl_reporter()

        text = message.get("text")
        if not isinstance(text, str):
            text = DEFAULT_TELEGRAM_MESSAGE_TEXT
        tokens = text.strip().split()
        target_date = None

        if len(tokens) > 1:
            try:
                target_date = datetime.strptime(tokens[1], "%Y-%m-%d").date()
            except ValueError:
                await self.send_alert(
                    "❌ Invalid date format. Use /pnl YYYY-MM-DD",
                    severity=AlertSeverity.WARNING,
                    alert_type="pnl_report",
                )
                return

        summary_text, chart_payload = await reporter.build_full_report(target_date)
        await self.send_alert(
            summary_text,
            severity=AlertSeverity.INFO,
            alert_type="pnl_report",
        )

        if self.chart_generator is None:
            return

        try:
            chart_paths = await self.chart_generator.generate_pnl_charts(chart_payload)
        except InsufficientDataError as exc:
            logger.warning("P&L charts skipped: %s", exc)
            await self.send_alert(f"⚪ P&L charts unavailable")
            return
        except (
            PricePathComputationError,
            ProgressNotificationError,
            RuntimeError,
            ValueError,
            OSError,
        ) as exc:
            logger.error("Failed to generate P&L charts: %s", exc, exc_info=True)
            await self.send_alert(f"❌ Failed to generate P&L charts")
            return

        for path in chart_paths:
            try:
                await self.send_chart_image(path)
            finally:
                self.chart_generator.cleanup_single_chart_file(path)


class TempCommandHandler(_ChartHandlerBase):
    """Handles /temp command - generate and send weather charts."""

    async def handle(self, message: Dict[str, Any]) -> None:
        """Handle /temp command - generate and send weather charts."""
        if self.chart_generator is None:
            await self.send_alert("❌ Chart generator unavailable; cannot generate weather charts")
            return

        try:
            weather_chart_paths = await self.chart_generator.generate_weather_charts()
            for chart_path in weather_chart_paths:
                try:
                    await self.send_chart_image(chart_path, "")
                finally:
                    self.chart_generator.cleanup_single_chart_file(chart_path)
        except (
            InsufficientDataError,
            PricePathComputationError,
            ProgressNotificationError,
            RuntimeError,
            ValueError,
            OSError,
        ) as exc:
            error_msg = f"❌ Failed to generate weather charts: {str(exc)}"
            logger.exception("Weather command error")
            await self.send_alert(error_msg)


class PriceCommandHandler:
    """Handles /price command by sending short and long horizon charts."""

    def __init__(self, send_alert_callback, send_chart_image_callback):
        self.send_alert = send_alert_callback
        self.send_chart_image = send_chart_image_callback

    async def handle(self, message: Dict[str, Any]) -> None:
        """Handle /price command by sending short and long horizon charts."""
        tails = self._build_tail_specs()
        for currency in ("BTC", "ETH"):
            for tail_label, horizon_days, timeline_points in tails:
                await self._generate_price_chart(currency, tail_label, horizon_days, timeline_points)

    def _build_tail_specs(self) -> List[tuple[str, float, int]]:
        short_horizon = 12.0 / 24.0
        long_horizon = 365.0
        return [
            ("short", short_horizon, 12),
            ("long", long_horizon, max(12, int(round(long_horizon)))),
        ]

    async def _generate_price_chart(self, currency: str, tail_label: str, horizon_days: float, timeline_points: int) -> None:
        chart_path: Optional[str] = None
        generator: Optional[ChartGeneratorProtocol] = None

        def _progress(step: int, total: int) -> None:
            interval = max(1, total // 10) if total > 0 else 1
            if step == total or step % interval == 0:
                logger.info("↳ [%s %s] evaluating horizon %d/%d", currency, tail_label, step, total)

        try:
            from src.common.price_path_calculator_helpers.config import (
                PricePathCalculatorConfig,
            )

            config = PricePathCalculatorConfig(
                strike_count=200,
                min_moneyness=0.3,
                max_moneyness=3.0,
                timeline_points=timeline_points,
                min_horizon_days=1.0 / 24.0,
                surface_loader=None,
                progress_callback=_progress,
                dependencies=None,
            )
            calculator = MostProbablePricePathCalculator(config=config)
            horizon_days_int = max(1, int(round(horizon_days)))
            generator = cast(
                ChartGeneratorProtocol,
                ChartGenerator(price_path_calculator=calculator, prediction_horizon_days=horizon_days_int),
            )

            logger.info("Generating %s %s price chart", currency, tail_label)
            chart_path = await generator.generate_price_chart_with_path(currency, prediction_horizon_days=horizon_days_int)
            await self.send_chart_image(chart_path, "")
            logger.info("Sent %s %s price chart", currency, tail_label)
        except (
            PricePathComputationError,
            ProgressNotificationError,
            InsufficientDataError,
            RuntimeError,
            ValueError,
            OSError,
        ) as exc:
            logger.error(
                "Failed to generate or send %s %s chart: %s",
                currency,
                tail_label,
                exc,
                exc_info=True,
            )
            await self.send_alert(
                f"⚠️ Failed to send {currency} {tail_label} price chart",
                severity=AlertSeverity.WARNING,
                alert_type="price_chart_error",
            )
        finally:
            if generator and chart_path:
                try:
                    generator.cleanup_single_chart_file(chart_path)
                except (OSError, RuntimeError):
                    logger.debug("Cleanup failed for %s %s chart %s", currency, tail_label, chart_path)
