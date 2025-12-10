import importlib

MODULES = [
    "common.memory_monitor_helpers.alert_logger",
    "common.memory_monitor_helpers.collection_tracker",
    "common.memory_monitor_helpers.factory",
    "common.memory_monitor_helpers.monitoring_loop",
    "common.memory_monitor_helpers.snapshot_collector",
    "common.memory_monitor_helpers.status_formatter",
    "common.memory_monitor_helpers.trend_analyzer",
    "common.memory_monitor_helpers.trend_analyzer_helpers.alert_builder",
    "common.memory_monitor_helpers.trend_analyzer_helpers.growth_analyzer",
    "common.memory_monitor_helpers.trend_analyzer_helpers.trend_calculator",
    "common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.data_processor",
    "common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.key_scanner",
    "common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.station_scanner",
    "common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.temperature_extractor",
]


def test_memory_monitor_modules_importable():
    for module_path in MODULES:
        module = importlib.import_module(module_path)
        assert module is not None
