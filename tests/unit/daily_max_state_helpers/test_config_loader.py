"""Tests for the METAR ConfigLoader helper."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.common.daily_max_state_helpers import config_loader as loader_module
from src.common.daily_max_state_helpers.config_loader import (
    ConfigLoader,
    MetarConfigLoadError,
)
from src.common.exceptions import ConfigurationError


def _patch_loader(
    monkeypatch,
    *,
    load_exception=None,
    load_data=None,
    section_exception=None,
    section_result=None,
):
    class DummyLoader:
        def __init__(self, config_dir: Path) -> None:
            self.config_dir = config_dir

        def load_json_file(self, name: str) -> dict:
            if load_exception:
                raise load_exception
            return load_data or {"data_sources": {"sample_source": {"info": "ok"}}}

        def get_section(self, data, section: str):
            if section_exception:
                raise section_exception
            if section_result is not None:
                return section_result
            return data.get(section, {})

    monkeypatch.setattr(loader_module, "BaseConfigLoader", DummyLoader)


def test_load_metar_config_returns_data(monkeypatch):
    _patch_loader(monkeypatch)

    loader = ConfigLoader()
    data = loader.load_metar_config()

    assert data == {"sample_source": {"info": "ok"}}


@pytest.mark.parametrize(
    "exception,match",
    [
        (FileNotFoundError(), "METAR config file not found"),
        (ConfigurationError("bad config"), "bad config"),
        (OSError("disk error"), "Failed to read METAR config"),
    ],
)
def test_load_metar_config_wraps_loader_errors(monkeypatch, exception, match):
    _patch_loader(monkeypatch, load_exception=exception)

    loader = ConfigLoader()
    with pytest.raises(MetarConfigLoadError, match=match):
        loader.load_metar_config()


def test_load_metar_config_handles_missing_section(monkeypatch):
    _patch_loader(monkeypatch, section_result={})

    loader = ConfigLoader()
    with pytest.raises(
        MetarConfigLoadError, match="METAR config contains no data source definitions"
    ):
        loader.load_metar_config()


def test_load_metar_config_handles_section_error(monkeypatch):
    config_error = ConfigurationError("section failure")
    _patch_loader(monkeypatch, section_exception=config_error)

    loader = ConfigLoader()
    with pytest.raises(MetarConfigLoadError, match="section failure"):
        loader.load_metar_config()
