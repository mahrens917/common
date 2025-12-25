"""Send multiple charts in batch with cleanup."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ChartBatchSender:
    """Sends multiple charts and handles cleanup."""

    def __init__(self, chart_generator, send_chart_callback, send_alert_callback):
        """
        Initialize chart batch sender.

        Args:
            chart_generator: Chart generator instance
            send_chart_callback: Callback to send individual chart
            send_alert_callback: Callback to send alert messages
        """
        self.chart_generator = chart_generator
        self.send_chart_callback = send_chart_callback
        self.send_alert_callback = send_alert_callback

    async def send_charts_batch(self, chart_paths: Dict[str, str], caption_prefix: str = "📊") -> int:
        """
        Send multiple charts and return count of successful sends.

        Args:
            chart_paths: Dictionary mapping chart names to file paths
            caption_prefix: Prefix for chart captions

        Returns:
            Number of charts sent successfully
        """
        success_count = 0

        for chart_name, chart_path in chart_paths.items():
            try:
                # Only generate caption if prefix is provided
                if caption_prefix:
                    caption = f"{caption_prefix} {chart_name.title()} Load"
                else:
                    caption = ""
                if await self.send_chart_callback(chart_path, caption):
                    success_count += 1
                    logger.info(f"Successfully sent {chart_name} chart")
                    self.chart_generator.cleanup_single_chart_file(chart_path)
                else:
                    logger.error(f"Failed to send {chart_name} chart")
                    self.chart_generator.cleanup_single_chart_file(chart_path)
            except OSError:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
                logger.exception("Failed to send %s chart due to filesystem error: %s")
                self.chart_generator.cleanup_single_chart_file(chart_path)
                await self.send_alert_callback(f"❌ Failed to send {chart_name} chart")

        return success_count
