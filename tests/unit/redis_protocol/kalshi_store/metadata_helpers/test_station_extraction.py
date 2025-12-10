import logging
from unittest.mock import MagicMock

import pytest

from common.redis_protocol.kalshi_store.metadata_helpers.station_extraction import (
    extract_station_from_ticker,
)
from common.redis_protocol.weather_station_resolver import WeatherStationMappingError

LOGGER = logging.getLogger(__name__)


def test_extract_station_from_ticker_skips_non_kxhigh():
    resolver = MagicMock()

    assert extract_station_from_ticker("GCUSTOM", resolver, LOGGER) is None
    resolver.extract_station.assert_not_called()


def test_extract_station_from_ticker_returns_station():
    resolver = MagicMock()
    resolver.extract_station.return_value = "KJFK"

    assert extract_station_from_ticker("KXHIGHTEST", resolver, LOGGER) == "KJFK"
    resolver.extract_station.assert_called_once()


def test_extract_station_from_ticker_returns_none_when_mapping_missing():
    resolver = MagicMock()
    resolver.extract_station.return_value = None

    assert extract_station_from_ticker("KXHIGHCHICAGO", resolver, LOGGER) is None
    resolver.extract_station.assert_called_once()


def test_extract_station_from_ticker_handles_mapping_error():
    resolver = MagicMock()
    resolver.extract_station.side_effect = WeatherStationMappingError("boom")

    assert extract_station_from_ticker("KXHIGHtest", resolver, LOGGER) is None
    resolver.extract_station.assert_called_once()
