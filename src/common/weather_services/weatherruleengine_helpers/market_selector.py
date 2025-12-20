from __future__ import annotations

"""Market selection logic for rule engine."""


import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..market_repository import MarketRepository, MarketSnapshot

from ..rule_engine_helpers import MarketEvaluator, TemperatureCoercer

logger = logging.getLogger(__name__)


class MarketSelector:
    """Handles market selection logic for rule 4 application."""

    def __init__(self, repository: MarketRepository) -> None:
        self._repository = repository

    async def select_target_market(self, city_code: str, *, day_code: Optional[str], max_temp_f: float) -> Optional[MarketSnapshot]:
        """Select best market for rule 4 application."""
        best_snapshot, best_cap, best_floor = None, None, None
        async for snapshot in self._repository.iter_city_markets(city_code, day_code=day_code):
            cap, floor = MarketEvaluator.extract_strike_values(snapshot, TemperatureCoercer)
            strike_type = snapshot.strike_type.lower()

            if strike_type == "greater":
                if MarketEvaluator.evaluate_greater_market(max_temp_f, floor, snapshot, best_floor):
                    best_snapshot = snapshot
                    best_cap = cap
                    best_floor = floor
                continue

            if strike_type == "between":
                best_snapshot, best_cap, best_floor = MarketEvaluator.evaluate_between_market(
                    max_temp_f, cap, floor, snapshot, best_snapshot, best_cap, best_floor
                )

        return best_snapshot
