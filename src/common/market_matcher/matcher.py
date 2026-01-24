"""Market matcher for cross-platform event matching."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Sequence

import numpy as np

from .converters import _try_parse_float
from .embedding_service import EmbeddingService
from .types import MarketMatch, MatchCandidate

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_EXPIRY_WINDOW_HOURS = 24.0
_SIMILARITY_THRESHOLD = 0.75
_STRIKE_TOLERANCE_PERCENT = 0.05


def _parse_strike_from_outcome(outcome: str) -> float | None:
    """Attempt to extract a numeric strike from a poly token outcome string."""
    patterns = [
        r"(?:above|over|greater than|>=?)\s*\$?([\d,]+\.?\d*)",
        r"(?:below|under|less than|<=?)\s*\$?([\d,]+\.?\d*)",
        r"\$?([\d,]+\.?\d*)\s*(?:or more|or less|\+)",
        r"^([\d,]+\.?\d*)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, outcome, re.IGNORECASE)
        if match:
            value_str = match.group(1).replace(",", "")
            parsed = _try_parse_float(value_str)
            if parsed is not None:
                return parsed
    return None


def _strikes_match_exact(
    kalshi_floor: float | None,
    kalshi_cap: float | None,
    poly_floor: float | None,
    poly_cap: float | None,
) -> tuple[bool, bool]:
    """Check if Kalshi and Poly strikes match exactly.

    Returns:
        Tuple of (has_numeric_strikes, strikes_match).
        - If neither has numeric strikes: (False, True) - pass, rely on embeddings
        - If only one has numeric strikes: (True, False) - fail, can't match
        - If both have numeric strikes: (True, strikes_equal) - must match exactly
    """
    kalshi_strike = _effective_strike(kalshi_floor, kalshi_cap)
    poly_strike = _effective_strike(poly_floor, poly_cap)

    # Neither has numeric strikes - let embeddings handle it
    if kalshi_strike is None and poly_strike is None:
        return False, True

    # Only one has numeric strikes - can't match
    if kalshi_strike is None or poly_strike is None:
        return True, False

    # Both have numeric strikes - must match exactly
    return True, kalshi_strike == poly_strike


def _effective_strike(floor: float | None, cap: float | None) -> float | None:
    """Compute effective strike from floor/cap bounds."""
    if floor is not None and cap is not None:
        if cap == float("inf"):
            return floor
        if floor == 0 or floor == float("-inf"):
            return cap
        return (floor + cap) / 2
    if floor is not None:
        return floor
    if cap is not None:
        return cap
    return None


def _expiry_delta_hours(expiry_a: datetime, expiry_b: datetime) -> float:
    """Compute absolute difference in hours between two expiry times."""
    delta = abs((expiry_a - expiry_b).total_seconds())
    return delta / 3600.0


def _filter_by_expiry_window(
    candidates: Sequence[MatchCandidate],
    reference_time: datetime,
    window_hours: float,
) -> list[MatchCandidate]:
    """Filter candidates to those expiring within window of reference time."""
    results: list[MatchCandidate] = []
    for candidate in candidates:
        delta = _expiry_delta_hours(candidate.expiry, reference_time)
        if delta <= window_hours:
            results.append(candidate)
    return results


def _build_match_from_pair(
    kalshi_market: MatchCandidate,
    poly_market: MatchCandidate,
    similarity: float,
    expiry_window_hours: float,
) -> MarketMatch | None:
    """Build a MarketMatch from a pair if it passes expiry/strike filters."""
    expiry_delta = _expiry_delta_hours(kalshi_market.expiry, poly_market.expiry)
    if expiry_delta > expiry_window_hours:
        return None

    has_numeric, strike_ok = _strikes_match_exact(
        kalshi_market.floor_strike,
        kalshi_market.cap_strike,
        poly_market.floor_strike,
        poly_market.cap_strike,
    )

    return MarketMatch(
        kalshi_market_id=kalshi_market.market_id,
        poly_market_id=poly_market.market_id,
        title_similarity=similarity,
        expiry_delta_hours=expiry_delta,
        strike_match=strike_ok,
    )


def _find_matches_from_matrix(
    kalshi_markets: Sequence[MatchCandidate],
    poly_markets: Sequence[MatchCandidate],
    sim_matrix: np.ndarray,
    similarity_threshold: float,
    expiry_window_hours: float,
) -> list[MarketMatch]:
    """Find matches from a similarity matrix."""
    matches: list[MarketMatch] = []
    for i, kalshi_market in enumerate(kalshi_markets):
        for j, poly_market in enumerate(poly_markets):
            similarity = float(sim_matrix[i, j])
            if similarity < similarity_threshold:
                continue
            match = _build_match_from_pair(kalshi_market, poly_market, similarity, expiry_window_hours)
            if match:
                matches.append(match)
    return matches


def _find_filtered_matches(
    kalshi_markets: Sequence[MatchCandidate],
    poly_markets: Sequence[MatchCandidate],
    title_sim: np.ndarray,
    desc_sim: np.ndarray,
    expiry_window_hours: float,
    skip_strike_filter: bool = False,
) -> list[MarketMatch]:
    """Find matches that pass expiry and optionally strike filters."""
    matches: list[MarketMatch] = []
    total_pairs = len(kalshi_markets) * len(poly_markets)
    failed_expiry = 0
    failed_strike = 0

    for i, kalshi_market in enumerate(kalshi_markets):
        for j, poly_market in enumerate(poly_markets):
            # Check expiry first
            expiry_delta = _expiry_delta_hours(kalshi_market.expiry, poly_market.expiry)
            if expiry_delta > expiry_window_hours:
                failed_expiry += 1
                continue

            # Check strike match (unless skipped)
            strike_ok = True
            if not skip_strike_filter:
                has_numeric, strike_ok = _strikes_match_exact(
                    kalshi_market.floor_strike,
                    kalshi_market.cap_strike,
                    poly_market.floor_strike,
                    poly_market.cap_strike,
                )
                if not strike_ok:
                    failed_strike += 1
                    continue

            combined_sim = (float(title_sim[i, j]) + float(desc_sim[i, j])) / 2
            matches.append(
                MarketMatch(
                    kalshi_market_id=kalshi_market.market_id,
                    poly_market_id=poly_market.market_id,
                    title_similarity=combined_sim,
                    expiry_delta_hours=expiry_delta,
                    strike_match=strike_ok,
                )
            )

    if skip_strike_filter:
        filter_desc = "expiry only"
    else:
        filter_desc = "expiry + strike"
    logger.info(
        "Filter results (%s): %d total pairs | %d failed expiry (>%.0fh) | %d failed strike | %d passed",
        filter_desc,
        total_pairs,
        failed_expiry,
        expiry_window_hours,
        failed_strike,
        len(matches),
    )
    return matches


async def _compute_cached_similarity_matrices(
    embedding_service: EmbeddingService,
    kalshi_markets: Sequence[MatchCandidate],
    poly_markets: Sequence[MatchCandidate],
    redis: "Redis",
) -> tuple[np.ndarray, np.ndarray]:
    """Compute title and description similarity matrices using cached embeddings."""
    kalshi_titles = [m.title.strip() for m in kalshi_markets]
    kalshi_descs = [m.description.strip() for m in kalshi_markets]
    poly_titles = [m.title.strip() for m in poly_markets]
    poly_descs = [m.description.strip() for m in poly_markets]

    kalshi_title_emb = await embedding_service.embed_with_cache(kalshi_titles, redis)
    kalshi_desc_emb = await embedding_service.embed_with_cache(kalshi_descs, redis)
    poly_title_emb = await embedding_service.embed_with_cache(poly_titles, redis)
    poly_desc_emb = await embedding_service.embed_with_cache(poly_descs, redis)

    title_sim = embedding_service.compute_similarity_matrix(kalshi_title_emb, poly_title_emb)
    desc_sim = embedding_service.compute_similarity_matrix(kalshi_desc_emb, poly_desc_emb)
    return title_sim, desc_sim


class MarketMatcher:
    """Matches markets across Kalshi and Polymarket platforms."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        similarity_threshold: float = _SIMILARITY_THRESHOLD,
        expiry_window_hours: float = _EXPIRY_WINDOW_HOURS,
    ) -> None:
        """Initialize the market matcher.

        Args:
            embedding_service: Service for computing text embeddings.
            similarity_threshold: Minimum cosine similarity for a match.
            expiry_window_hours: Maximum hours difference in expiry for matching.
        """
        self._embedding_service = embedding_service
        self._similarity_threshold = similarity_threshold
        self._expiry_window_hours = expiry_window_hours

    async def match(
        self,
        kalshi_markets: Sequence[MatchCandidate],
        poly_markets: Sequence[MatchCandidate],
    ) -> list[MarketMatch]:
        """Find matching markets between Kalshi and Polymarket."""
        if not kalshi_markets or not poly_markets:
            return []

        kalshi_texts = [f"{m.title} {m.description}".strip() for m in kalshi_markets]
        poly_texts = [f"{m.title} {m.description}".strip() for m in poly_markets]
        logger.info("Computing embeddings for %d Kalshi and %d Poly markets", len(kalshi_texts), len(poly_texts))

        kalshi_emb = await self._embedding_service.embed(kalshi_texts)
        poly_emb = await self._embedding_service.embed(poly_texts)
        sim_matrix = self._embedding_service.compute_similarity_matrix(kalshi_emb, poly_emb)

        matches = _find_matches_from_matrix(kalshi_markets, poly_markets, sim_matrix, self._similarity_threshold, self._expiry_window_hours)
        matches.sort(key=lambda m: (-m.title_similarity, m.expiry_delta_hours))
        logger.info("Found %d potential matches", len(matches))
        return matches

    async def match_with_strike_filter(
        self,
        kalshi_markets: Sequence[MatchCandidate],
        poly_markets: Sequence[MatchCandidate],
    ) -> list[MarketMatch]:
        """Find matching markets, filtering to only those with matching strikes."""
        all_matches = await self.match(kalshi_markets, poly_markets)
        return [m for m in all_matches if m.strike_match]

    async def match_with_cache_and_strike_filter(
        self,
        kalshi_markets: Sequence[MatchCandidate],
        poly_markets: Sequence[MatchCandidate],
        redis: "Redis",
        top_n: int = 10,
    ) -> list[MarketMatch]:
        """Find matching markets using cached embeddings, filtering by strike match."""
        all_matches = await self.match_with_cache(kalshi_markets, poly_markets, redis, top_n, skip_strike_filter=False)
        return [m for m in all_matches if m.strike_match]

    async def match_with_cache(
        self,
        kalshi_markets: Sequence[MatchCandidate],
        poly_markets: Sequence[MatchCandidate],
        redis: "Redis",
        top_n: int = 10,
        skip_strike_filter: bool = False,
    ) -> list[MarketMatch]:
        """Find matching markets using cached embeddings."""
        if not kalshi_markets or not poly_markets:
            return []

        logger.info(
            "Computing separate title/description embeddings for %d Kalshi and %d Poly markets",
            len(kalshi_markets),
            len(poly_markets),
        )

        # Log filter settings
        if skip_strike_filter:
            strike_mode = "disabled"
        else:
            strike_mode = "exact (if numeric)"
        logger.info(
            "Match filters: expiry_window=±%.0fh, strike_match=%s",
            self._expiry_window_hours,
            strike_mode,
        )

        # Log strike distribution for diagnostics
        kalshi_with_strikes = sum(1 for m in kalshi_markets if _effective_strike(m.floor_strike, m.cap_strike) is not None)
        poly_with_strikes = sum(1 for m in poly_markets if _effective_strike(m.floor_strike, m.cap_strike) is not None)
        logger.info(
            "Strike data: Kalshi %d/%d have numeric strikes, Poly %d/%d have numeric strikes",
            kalshi_with_strikes,
            len(kalshi_markets),
            poly_with_strikes,
            len(poly_markets),
        )

        title_sim, desc_sim = await _compute_cached_similarity_matrices(self._embedding_service, kalshi_markets, poly_markets, redis)
        matches = _find_filtered_matches(kalshi_markets, poly_markets, title_sim, desc_sim, self._expiry_window_hours, skip_strike_filter)

        matches.sort(key=lambda m: -m.title_similarity)
        top_matches = matches[:top_n]
        logger.info("Found %d matches after filtering, returning top %d", len(matches), len(top_matches))
        return top_matches


__all__ = ["MarketMatcher"]
