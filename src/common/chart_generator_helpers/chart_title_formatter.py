from __future__ import annotations

"""Helper for formatting chart titles"""


class ChartTitleFormatter:
    """Formats chart titles with current values"""

    def format_load_chart_title(self, service_name: str) -> str:
        """Format title for load chart"""
        if service_name.lower() == "deribit":
            return "Deribit Updates / min"
        elif service_name.lower() == "kalshi":
            return "Kalshi Updates / min"
        else:
            return f"{service_name.title()} Updates / min"

    def format_system_chart_title(self, metric_type: str) -> str:
        """Format title for system metrics chart"""
        if metric_type == "cpu":
            return "CPU (per minute)"
        else:  # memory
            return "Memory (per minute)"

    def format_price_chart_title(self, symbol: str, current_price: float) -> str:
        """Format title for price chart with current price"""
        formatted_current_price = f"${current_price:,.0f}" if current_price == int(current_price) else f"${current_price:,.2f}"
        return f"{symbol} Price History (Current: {formatted_current_price})"
