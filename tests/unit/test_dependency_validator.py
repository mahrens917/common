from types import SimpleNamespace

import pytest

from common.dependency_validator import (
    DependencyValidator,
    LDMNotInstalledError,
)


def test_validate_ldm_dependencies_missing(monkeypatch):
    monkeypatch.setattr("common.dependency_validator.shutil.which", lambda _: None)

    with pytest.raises(LDMNotInstalledError):
        DependencyValidator.validate_ldm_dependencies()


def test_validate_ldm_dependencies_success(monkeypatch):
    monkeypatch.setattr("common.dependency_validator.shutil.which", lambda _: "/usr/bin/pqstream")

    DependencyValidator.validate_ldm_dependencies()


def test_validate_service_dependencies_invokes_weather_validation(monkeypatch):
    called = {"value": False}

    def fake_weather_validation():
        called["value"] = True

    monkeypatch.setattr(
        DependencyValidator,
        "_validate_weather_service_dependencies",
        fake_weather_validation,
    )

    config = SimpleNamespace(services={"weather": {"enabled": True}})

    DependencyValidator.validate_service_dependencies(config)
    assert called["value"]


def test_validate_service_dependencies_skips_when_disabled(monkeypatch):
    def should_not_run():
        raise AssertionError("Weather validation should not run when disabled")

    monkeypatch.setattr(
        DependencyValidator,
        "_validate_weather_service_dependencies",
        should_not_run,
    )

    config = SimpleNamespace(services={"weather": {"enabled": False}})

    DependencyValidator.validate_service_dependencies(config)


def test_validate_weather_dependencies_requires_ldm(monkeypatch):
    calls = {"count": 0}

    def fake_validate():
        calls["count"] += 1

    settings = SimpleNamespace(
        sources=SimpleNamespace(asos_source="ldm"),
    )

    monkeypatch.setattr("common.dependency_validator.get_weather_settings", lambda: settings)
    monkeypatch.setattr(
        DependencyValidator,
        "validate_ldm_dependencies",
        fake_validate,
    )

    DependencyValidator._validate_weather_service_dependencies()
    assert calls["count"] == 1


def test_validate_weather_dependencies_skips_non_ldm(monkeypatch):
    def should_not_run():
        raise AssertionError("LDM validation should not run for non-ldm sources")

    settings = SimpleNamespace(
        sources=SimpleNamespace(asos_source="https"),
    )

    monkeypatch.setattr("common.dependency_validator.get_weather_settings", lambda: settings)
    monkeypatch.setattr(
        DependencyValidator,
        "validate_ldm_dependencies",
        should_not_run,
    )

    DependencyValidator._validate_weather_service_dependencies()


def test_get_dependency_status_reports_ldm(monkeypatch):
    monkeypatch.setattr(
        DependencyValidator,
        "validate_ldm_dependencies",
        lambda: None,
    )

    status = DependencyValidator.get_dependency_status()
    assert status["ldm"] is True

    def raise_missing():
        raise LDMNotInstalledError("missing pqstream")

    monkeypatch.setattr(
        DependencyValidator,
        "validate_ldm_dependencies",
        raise_missing,
    )

    status = DependencyValidator.get_dependency_status()
    assert status["ldm"] is False
