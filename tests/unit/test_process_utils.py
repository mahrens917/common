from types import SimpleNamespace

import pytest

from src.common.process_utils import FailedServiceMixin, collect_failed_services


def test_collect_failed_services_filters_by_status():
    process_info = {
        "engine": SimpleNamespace(status="running"),
        "pricing": SimpleNamespace(status="failed"),
        "router": SimpleNamespace(status="error"),
        "monitor": SimpleNamespace(status=None),
    }

    failed = collect_failed_services(process_info, ["failed", "error"])

    assert sorted(failed) == ["pricing", "router"]


def test_failed_service_mixin_requires_failed_states():
    class NoStatesMixin(FailedServiceMixin):
        pass

    instance = NoStatesMixin()

    with pytest.raises(AttributeError):
        instance.get_failed_services()


def test_failed_service_mixin_uses_process_info_when_present():
    class ServiceTracker(FailedServiceMixin):
        FAILED_SERVICE_STATES = ("failed", "error")

        def __init__(self, process_info=None):
            self.process_info = process_info

    tracker = ServiceTracker(
        process_info={
            "alpha": SimpleNamespace(status="failed"),
            "beta": SimpleNamespace(status="ready"),
            "gamma": SimpleNamespace(status="error"),
        }
    )

    assert tracker.get_failed_services() == ["alpha", "gamma"]

    assert ServiceTracker(process_info=None).get_failed_services() == []
