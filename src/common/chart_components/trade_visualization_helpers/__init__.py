"""Helpers for trade visualization on charts."""

from .annotation_parameters import TradeAnnotationParameters, TradeShadingParameters
from .precondition_checker import should_annotate_trades
from .visualizer_manager import VisualizerManager

__all__ = [
    "TradeAnnotationParameters",
    "TradeShadingParameters",
    "should_annotate_trades",
    "VisualizerManager",
]
