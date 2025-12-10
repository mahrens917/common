"""Tests for contract parser."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from common.market_data_parser_helpers.contract_validator_helpers.contract_parser import (
    ContractParser,
)


class TestContractParser:
    """Tests for ContractParser class."""

    def test_parse_instrument_delegates_to_deribit_parser(self) -> None:
        """parse_instrument delegates to DeribitInstrumentParser."""
        with patch(
            "common.market_data_parser_helpers.contract_validator_helpers.contract_parser.DeribitInstrumentParser"
        ) as mock_parser:
            mock_result = MagicMock()
            mock_parser.parse_instrument.return_value = mock_result

            result = ContractParser.parse_instrument("BTC-25JAN01-100000-C", "BTC")

            mock_parser.parse_instrument.assert_called_once_with(
                "BTC-25JAN01-100000-C", strict_symbol="BTC"
            )
            assert result is mock_result

    def test_parse_instrument_passes_expected_symbol(self) -> None:
        """parse_instrument passes expected_symbol as strict_symbol."""
        with patch(
            "common.market_data_parser_helpers.contract_validator_helpers.contract_parser.DeribitInstrumentParser"
        ) as mock_parser:
            mock_parser.parse_instrument.return_value = MagicMock()

            ContractParser.parse_instrument("ETH-25FEB01-3000-P", "ETH")

            mock_parser.parse_instrument.assert_called_once_with(
                "ETH-25FEB01-3000-P", strict_symbol="ETH"
            )

    def test_parse_instrument_returns_parser_result(self) -> None:
        """parse_instrument returns result from DeribitInstrumentParser."""
        expected_result = {"parsed": True, "symbol": "BTC"}

        with patch(
            "common.market_data_parser_helpers.contract_validator_helpers.contract_parser.DeribitInstrumentParser"
        ) as mock_parser:
            mock_parser.parse_instrument.return_value = expected_result

            result = ContractParser.parse_instrument("BTC-25JAN01-100000-C", "BTC")

            assert result == expected_result
