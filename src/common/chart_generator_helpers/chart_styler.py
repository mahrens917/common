from __future__ import annotations

"""Helper for chart styling and configuration"""


class ChartStyler:
    """Provides chart styling configuration"""

    def __init__(self):
        # Chart dimensions
        self.chart_width_inches = 12
        self.chart_height_inches = 6
        self.dpi = 150

        # Color scheme
        self.background_color = "#f8f9fa"
        self.grid_color = "#e9ecef"
        self.primary_color = "#627EEA"
        self.secondary_color = "#6c757d"
        self.highlight_color = self.primary_color

        # Service-specific colors
        self.deribit_color = "#FF6B35"  # Orange for Deribit
        self.kalshi_color = "#4ECDC4"  # Teal for Kalshi
        self.cpu_color = "#FF9500"  # Orange for CPU
        self.memory_color = "#627EEA"  # Blue for Memory
