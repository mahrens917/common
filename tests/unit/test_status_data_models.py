from common.status_data_models import (
    PriceData,
    RedisMetrics,
    ServiceInfo,
    ServiceStatus,
    StatusReportData,
    SystemMetrics,
    WeatherInfo,
)

_VAL_3500_0 = 3500.0
_VAL_50_0 = 50.0


def test_status_report_data_structure():
    service = ServiceInfo(
        "svc", ServiceStatus.RUNNING, process_id=123, memory_mb=64.5, messages_60s=42
    )
    metrics = SystemMetrics(
        cpu_percent=50.0, memory_percent=70.0, disk_percent=80.0, redis_process_id=456
    )
    redis = RedisMetrics(
        deribit_keys=10, kalshi_keys=20, cfb_keys=5, weather_keys=8, connection_healthy=True
    )
    price = PriceData(btc_price=45000.0, eth_price=3500.0)
    weather = [WeatherInfo("KJFK", 72.0, emoticon="sun")]

    report = StatusReportData(
        services=[service],
        system_metrics=metrics,
        redis_metrics=redis,
        price_data=price,
        weather_data=weather,
        kalshi_market_status={"market": "open"},
        tracker_status={"status": "green"},
    )

    assert report.services[0].name == "svc"
    assert report.system_metrics.cpu_percent == _VAL_50_0
    assert report.redis_metrics.connection_healthy
    assert report.price_data.eth_price == _VAL_3500_0
    assert report.weather_data[0].icao_code == "KJFK"
