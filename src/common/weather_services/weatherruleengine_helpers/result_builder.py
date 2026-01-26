from __future__ import annotations

"""Result building logic for rule engine."""


import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..market_repository import MarketRepository, MarketSnapshot
    from ..rule_engine import MidpointSignalResult

logger = logging.getLogger(__name__)


class ResultBuilder:
    """Handles result construction and field application for rule engine."""

    def __init__(self, repository: MarketRepository) -> None:
        self._repository = repository

    async def apply_market_fields_and_return_result(
        self,
        target_snapshot: MarketSnapshot,
        station_icao: str,
        max_temp_f: float,
        result_class: type,
    ) -> MidpointSignalResult:
        """Set market fields and return result."""
        explanation = f"⏰ MIDPOINT: Taking {max_temp_f}°F as final high → Buying YES"
        await self._repository.set_market_fields(
            target_snapshot.key,
            {
                "t_ask": "99",
                "weather_explanation": explanation,
                "last_rule_applied": "rule_4",
                "intended_action": "BUY",
                "intended_side": "YES",
                "rule_triggered": "rule_4",
            },
        )
        logger.info(
            "WeatherRuleEngine: Rule 4 applied to %s for station %s",
            target_snapshot.ticker,
            station_icao,
        )
        return result_class(
            station_icao=station_icao,
            market_key=target_snapshot.key,
            ticker=target_snapshot.ticker,
            max_temp_f=max_temp_f,
            explanation=explanation,
        )
