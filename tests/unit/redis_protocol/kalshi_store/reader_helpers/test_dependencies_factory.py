import logging

from src.common.redis_protocol.kalshi_store.reader_helpers import dependencies_factory


def test_dependencies_factory_creates_components(monkeypatch):
    class DummyAdapter:
        pass

    monkeypatch.setattr(
        "src.common.redis_protocol.kalshi_store.reader_helpers.dependencies_factory.KalshiMetadataAdapter",
        DummyAdapter,
    )
    deps = dependencies_factory.KalshiMarketReaderDependenciesFactory.create(
        logger=logging.getLogger("tests"), metadata_adapter=DummyAdapter()
    )
    assert deps.ticker_parser is not None
    assert deps.market_aggregator is not None
    assert deps.snapshot_reader is not None
