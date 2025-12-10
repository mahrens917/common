"""Tests for ServiceHealthAggregator dependency factory."""

from unittest.mock import MagicMock

from common.health import health_aggregator_factory
from common.health.health_aggregator_factory import (
    OptionalDependencies,
    ServiceHealthAggregatorDependencies,
    ServiceHealthAggregatorFactory,
)


def _simple_component(name):
    class Component:
        def __init__(self, *_, **__):
            self.name = name

    return Component


def test_create_builds_every_dependency(monkeypatch):
    """The factory should instantiate every helper component."""
    names = {
        "ProcessHealthMonitor": _simple_component("process"),
        "LogActivityMonitor": _simple_component("log"),
        "ServiceHealthChecker": _simple_component("checker"),
        "ErrorHandler": _simple_component("error"),
        "StatusAggregator": _simple_component("status"),
        "ResultBuilder": _simple_component("result"),
        "StatusFormatter": _simple_component("formatter"),
        "MultiServiceChecker": _simple_component("multi"),
    }

    for attr, implementation in names.items():
        monkeypatch.setattr(health_aggregator_factory, attr, implementation)

    deps = ServiceHealthAggregatorFactory.create("/tmp/logs", lambda: "ok")

    assert isinstance(deps, ServiceHealthAggregatorDependencies)
    assert deps.process_monitor.name == "process"
    assert deps.multi_checker.name == "multi"


def test_all_provided_helper_detects_missing():
    """_all_provided should reflect whether every dependency is present."""
    provided = OptionalDependencies(
        process_monitor=MagicMock(),
        log_monitor=MagicMock(),
        health_checker=MagicMock(),
        error_handler=MagicMock(),
        status_aggregator=MagicMock(),
        result_builder=MagicMock(),
        formatter=MagicMock(),
        multi_checker=MagicMock(),
    )

    assert ServiceHealthAggregatorFactory._all_provided(provided)

    missing = OptionalDependencies(log_monitor=None)
    assert not ServiceHealthAggregatorFactory._all_provided(missing)


def test_build_from_optional_uses_given_components():
    """Should raise if any optional dependency is missing and otherwise build."""
    optional = OptionalDependencies(
        process_monitor=MagicMock(),
        log_monitor=MagicMock(),
        health_checker=MagicMock(),
        error_handler=MagicMock(),
        status_aggregator=MagicMock(),
        result_builder=MagicMock(),
        formatter=MagicMock(),
        multi_checker=MagicMock(),
    )

    deps = ServiceHealthAggregatorFactory._build_from_optional(optional)

    assert deps.process_monitor is optional.process_monitor
    assert deps.multi_checker is optional.multi_checker


def test_create_or_use_returns_optional_when_complete(monkeypatch):
    """When every optional dependency is provided we simply reuse them."""
    sentinel = object()
    monkeypatch.setattr(
        ServiceHealthAggregatorFactory,
        "_build_from_optional",
        staticmethod(lambda optional: sentinel),
    )

    optional = OptionalDependencies(
        process_monitor=MagicMock(),
        log_monitor=MagicMock(),
        health_checker=MagicMock(),
        error_handler=MagicMock(),
        status_aggregator=MagicMock(),
        result_builder=MagicMock(),
        formatter=MagicMock(),
        multi_checker=MagicMock(),
    )

    result = ServiceHealthAggregatorFactory.create_or_use(
        "/tmp/logs", lambda: "ok", optional_deps=optional
    )

    assert result is sentinel


def test_create_or_use_merges_defaults_with_partial(monkeypatch):
    """Use provided optional components and merge others with defaults."""
    defaults = ServiceHealthAggregatorDependencies(
        process_monitor=MagicMock(name="def-process"),
        log_monitor=MagicMock(name="def-log"),
        health_checker=MagicMock(name="def-checker"),
        error_handler=MagicMock(name="def-error"),
        status_aggregator=MagicMock(name="def-status"),
        result_builder=MagicMock(name="def-result"),
        formatter=MagicMock(name="def-formatter"),
        multi_checker=MagicMock(name="def-multi"),
    )

    def fake_create(*args, **kwargs):
        return defaults

    monkeypatch.setattr(ServiceHealthAggregatorFactory, "create", staticmethod(fake_create))

    optional = OptionalDependencies(process_monitor=MagicMock(name="provided-process"))
    result = ServiceHealthAggregatorFactory.create_or_use(
        "/tmp/logs", lambda: "ok", optional_deps=optional
    )

    assert result.process_monitor is optional.process_monitor
    assert result.log_monitor is defaults.log_monitor
    assert result.multi_checker is defaults.multi_checker
