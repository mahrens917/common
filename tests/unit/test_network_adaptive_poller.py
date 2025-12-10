from common.network_adaptive_poller import NetworkAdaptivePoller

_CONST_20 = 20
_CONST_25 = 25
_CONST_40 = 40
_CONST_50 = 50
_CONST_60 = 60
_TEST_COUNT_3 = 3


def test_record_request_fast_network_reduces_interval():
    poller = NetworkAdaptivePoller(base_interval_seconds=30, min_interval_seconds=20)

    for _ in range(3):
        poller.record_request(request_time=5.0, success=True)

    assert poller.get_current_interval() == _CONST_25

    # Continue feeding fast successes to hit minimum
    for _ in range(10):
        poller.record_request(request_time=4.0, success=True)

    assert poller.get_current_interval() == _CONST_20  # min bound


def test_record_request_slow_network_increases_interval():
    poller = NetworkAdaptivePoller(base_interval_seconds=30, max_interval_seconds=60)

    for _ in range(3):
        poller.record_request(request_time=35.0, success=False)

    assert poller.get_current_interval() == _CONST_50

    # Additional slow metrics should respect max bound
    for _ in range(10):
        poller.record_request(request_time=40.0, success=False)

    assert poller.get_current_interval() == _CONST_60


def test_record_request_moderate_network_applies_gentle_backoff():
    poller = NetworkAdaptivePoller(base_interval_seconds=30)

    for _ in range(3):
        poller.record_request(request_time=22.0, success=True)

    assert poller.get_current_interval() == _CONST_40


def test_get_network_summary_requires_minimum_samples():
    poller = NetworkAdaptivePoller()
    poller.record_request(5.0, True)
    poller.record_request(6.0, True)

    assert poller.get_network_summary() is None

    poller.record_request(7.0, True)
    summary = poller.get_network_summary()

    assert summary["sample_size"] == _TEST_COUNT_3
    assert summary["current_interval_seconds"] == poller.get_current_interval()
    assert "network_type" in summary


def test_classify_network_type_boundaries():
    poller = NetworkAdaptivePoller()

    assert poller._classify_network_type(avg_time=8.0, success_rate=0.95) == "fast_reliable"
    assert poller._classify_network_type(avg_time=35.0, success_rate=0.60) == "slow_unreliable"
    assert poller._classify_network_type(avg_time=18.0, success_rate=0.9) == "moderate"
    assert poller._classify_network_type(avg_time=12.0, success_rate=0.9) == "good"
