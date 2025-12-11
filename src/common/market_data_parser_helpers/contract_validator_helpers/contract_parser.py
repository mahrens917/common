"""Contract parsing wrapper."""

from ...market_data_parser import DeribitInstrumentParser


class ContractParser:
    """Wraps instrument parsing logic."""

    @staticmethod
    def parse_instrument(contract_name: str, expected_symbol: str):
        """Parse contract instrument with symbol validation."""
        return DeribitInstrumentParser.parse_instrument(contract_name, strict_symbol=expected_symbol)
