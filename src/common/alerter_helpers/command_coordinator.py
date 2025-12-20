"""Command coordinator to delegate command handling."""

from typing import Any, Dict


class CommandCoordinator:
    """Coordinates command handling by delegating to specific handlers."""

    def __init__(self, chart_manager, send_alert_callback, send_chart_callback):
        """Initialize with dependencies."""
        self.chart_mgr = chart_manager
        self.send_alert = send_alert_callback
        self.send_chart = send_chart_callback

    async def handle_help(self, msg: Dict[str, Any]) -> None:
        """Handle /help command."""
        from .command_handlers import HelpCommandHandler

        await HelpCommandHandler().handle(self.send_alert)

    async def handle_load(self, msg: Dict[str, Any]) -> None:
        """Handle /load command."""
        self.chart_mgr.ensure_chart_dependencies_initialized()
        from .command_handlers import LoadCommandHandler

        await LoadCommandHandler(
            self.chart_mgr.chart_generator, self.send_alert, self.send_chart
        ).handle(msg)

    async def handle_pnl(self, msg: Dict[str, Any]) -> None:
        """Handle /pnl command."""
        self.chart_mgr.ensure_chart_dependencies_initialized()
        from .command_handlers import PnlCommandHandler

        await PnlCommandHandler(
            self.chart_mgr.pnl_reporter,
            self.chart_mgr.chart_generator,
            self.send_alert,
            self.send_chart,
            self.chart_mgr.ensure_pnl_reporter,
        ).handle(msg)

    async def handle_price(self, msg: Dict[str, Any]) -> None:
        """Handle /price command."""
        self.chart_mgr.ensure_chart_dependencies_initialized()
        from .command_handlers import PriceCommandHandler

        await PriceCommandHandler(self.send_alert, self.send_chart).handle(msg)

    async def handle_temp(self, msg: Dict[str, Any]) -> None:
        """Handle /temp command."""
        self.chart_mgr.ensure_chart_dependencies_initialized()
        from .command_handlers import TempCommandHandler

        await TempCommandHandler(
            self.chart_mgr.chart_generator, self.send_alert, self.send_chart
        ).handle(msg)
