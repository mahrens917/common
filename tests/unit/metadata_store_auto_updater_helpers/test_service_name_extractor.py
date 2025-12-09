from src.common.metadata_store_auto_updater_helpers.service_name_extractor import (
    ServiceNameExtractor,
)


class TestServiceNameExtractor:
    def test_extract_service_name(self):
        extractor = ServiceNameExtractor()

        assert extractor.extract_service_name("history:deribit") == "deribit"
        assert extractor.extract_service_name("history:deribit:") == "deribit"
        assert extractor.extract_service_name("history:deribit:key") == "deribit"
        assert extractor.extract_service_name("history:KAUS") == "weather"
        assert extractor.extract_service_name("history:unknown") is None
        assert extractor.extract_service_name("invalid") is None
