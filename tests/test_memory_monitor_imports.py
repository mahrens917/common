import importlib

MODULES = [
    "src.common.memory_monitor_helpers.alert_logger",
    "src.common.memory_monitor_helpers.collection_tracker",
    "src.common.memory_monitor_helpers.factory",
    "src.common.memory_monitor_helpers.monitoring_loop",
    "src.common.memory_monitor_helpers.snapshot_collector",
    "src.common.memory_monitor_helpers.status_formatter",
    "src.common.memory_monitor_helpers.trend_analyzer",
    "src.common.memory_monitor_helpers.trend_analyzer_helpers.alert_builder",
    "src.common.memory_monitor_helpers.trend_analyzer_helpers.growth_analyzer",
    "src.common.memory_monitor_helpers.trend_analyzer_helpers.trend_calculator",
    "src.common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.data_processor",
    "src.common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.key_scanner",
    "src.common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.station_scanner",
    "src.common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.temperature_extractor",
]


def test_memory_monitor_modules_importable():
    for module_path in MODULES:
        module = importlib.import_module(module_path)
        assert module is not None
