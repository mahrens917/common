import importlib

import pytest

from common.redis_schema import analytics
from common.redis_schema.analytics import PdfSurfaceKey, ProbabilitySliceKey, SurfaceType
from common.redis_schema.validators import _registered_prefixes


@pytest.fixture(autouse=True)
def reload_analytics_module():
    importlib.reload(analytics)
    yield
    _registered_prefixes.clear()


def test_pdf_surface_key_renders_with_optional_grid_point():
    key = PdfSurfaceKey(
        currency="USD",
        surface_type=SurfaceType.INTENSITY,
        expiry_iso="2025-01-01T000000Z",
        strike="45000",
        grid_point="ATM",
    ).key()

    assert key == "analytics:pdf:usd:surface:intensity:2025-01-01t000000z:45000:atm"


def test_pdf_surface_key_without_grid_point():
    key = PdfSurfaceKey(
        currency="EUR",
        surface_type=SurfaceType.BID,
        expiry_iso="2025-06-30",
        strike="5000",
    ).key()

    assert key == "analytics:pdf:eur:surface:bid:2025-06-30:5000"


def test_probability_slice_key_sanitizes_segments():
    key = ProbabilitySliceKey(
        currency="BTC Futures", expiry_iso="2025-01-01", slice_name="Bucket_42"
    ).key()

    assert key == "analytics:probability:btc_futures:2025-01-01:bucket_42"


def test_probability_slice_key_rejects_invalid_characters():
    with pytest.raises(ValueError):
        ProbabilitySliceKey(currency="BTC", expiry_iso="2025-01-01", slice_name=">42%").key()


def test_pdf_surface_key_rejects_invalid_expiry_format():
    with pytest.raises(ValueError):
        PdfSurfaceKey(
            currency="USD",
            surface_type=SurfaceType.BID,
            expiry_iso="2025-01-01T00:00:00Z",
            strike="45000",
        ).key()
