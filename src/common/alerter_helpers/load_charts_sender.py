"""Helper for sending load monitoring charts."""

import logging
import traceback

from ..chart_generator import InsufficientDataError, ProgressNotificationError
from ..price_path_calculator import PricePathComputationError
from .chart_batch_sender import ChartBatchSender

logger = logging.getLogger(__name__)


class LoadChartsSender:
    """Handles generation and sending of load monitoring charts."""

    def __init__(self, chart_generator, send_chart_image_callback, send_alert_callback):
        """Initialize with dependencies."""
        self.chart_generator = chart_generator
        self.send_chart_image = send_chart_image_callback
        self.send_alert = send_alert_callback

    async def send_load_charts(self, hours: int = 24) -> bool:
        """Generate and send load monitoring charts via Telegram."""
        try:
            chart_paths = await self.chart_generator.generate_load_charts(hours=hours)
            if not chart_paths:
                return False

            batch_sender = ChartBatchSender(self.chart_generator, self.send_chart_image, self.send_alert)
            success_count = await batch_sender.send_charts_batch(chart_paths, "")
            return success_count == len(chart_paths)

        except InsufficientDataError as e:
            error_msg = f"❌ Cannot generate charts: {str(e)}"
            logger.exception(f"[Monitor] ")
            await self.send_alert(error_msg)
            return False
        except (
            PricePathComputationError,
            ProgressNotificationError,
            RuntimeError,
            ValueError,
            OSError,
        ) as exc:
            error_msg = f"❌ Error generating charts: {str(exc)}"
            logger.exception(f"[Monitor] ")
            logger.exception(f"[Monitor] Full traceback: {traceback.format_exc()}")
            await self.send_alert(error_msg)
            return False
