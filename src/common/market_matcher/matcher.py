"""Market matcher for cross-platform event matching."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Sequence

import numpy as np

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
            try:
                return float(value_str)
            except ValueError:
                continue
    return None


def _strikes_match_exact(
    kalshi_floor: float | None,
    kalshi_cap: float | None,
    poly_floor: float | None,
    poly_cap: float | None,
) -> bool:
    """Check if Kalshi and Poly strikes match exactly."""
    kalshi_strike = _effective_strike(kalshi_floor, kalshi_cap)
    poly_strike = _effective_strike(poly_floor, poly_cap)

    # If either has no strike, can't compare
    if kalshi_strike is None or poly_strike is None:
        return False

    return kalshi_strike == poly_strike


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

    def match(
        self,
        kalshi_markets: Sequence[MatchCandidate],
        poly_markets: Sequence[MatchCandidate],
    ) -> list[MarketMatch]:
        """Find matching markets between Kalshi and Polymarket.

        Args:
            kalshi_markets: Kalshi market candidates.
            poly_markets: Polymarket market candidates.

        Returns:
            List of matched market pairs.
        """
        if not kalshi_markets or not poly_markets:
            return []

        kalshi_texts = [f"{m.title} {m.description}".strip() for m in kalshi_markets]
        poly_texts = [f"{m.title} {m.description}".strip() for m in poly_markets]

        logger.info(
            "Computing embeddings for %d Kalshi and %d Poly markets",
            len(kalshi_texts),
            len(poly_texts),
        )

        kalshi_embeddings = self._embedding_service.embed(kalshi_texts)
        poly_embeddings = self._embedding_service.embed(poly_texts)

        similarity_matrix = self._embedding_service.compute_similarity_matrix(
            kalshi_embeddings,
            poly_embeddings,
        )

        matches: list[MarketMatch] = []
        for i, kalshi_market in enumerate(kalshi_markets):
            for j, poly_market in enumerate(poly_markets):
                similarity = float(similarity_matrix[i, j])

                if similarity < self._similarity_threshold:
                    continue

                expiry_delta = _expiry_delta_hours(kalshi_market.expiry, poly_market.expiry)
                if expiry_delta > self._expiry_window_hours:
                    continue

                strike_ok = _strikes_match(
                    kalshi_market.floor_strike,
                    kalshi_market.cap_strike,
                    poly_market.floor_strike,
                    poly_market.cap_strike,
                )

                matches.append(
                    MarketMatch(
                        kalshi_market_id=kalshi_market.market_id,
                        poly_market_id=poly_market.market_id,
                        title_similarity=similarity,
                        expiry_delta_hours=expiry_delta,
                        strike_match=strike_ok,
                    )
                )

        matches.sort(key=lambda m: (-m.title_similarity, m.expiry_delta_hours))
        logger.info("Found %d potential matches", len(matches))
        return matches

    def match_with_strike_filter(
        self,
        kalshi_markets: Sequence[MatchCandidate],
        poly_markets: Sequence[MatchCandidate],
    ) -> list[MarketMatch]:
        """Find matching markets, filtering to only those with matching strikes.

        Args:
            kalshi_markets: Kalshi market candidates.
            poly_markets: Polymarket market candidates.

        Returns:
            List of matched market pairs where strikes also match.
        """
        all_matches = self.match(kalshi_markets, poly_markets)
        return [m for m in all_matches if m.strike_match]

    async def match_with_cache(
        self,
        kalshi_markets: Sequence[MatchCandidate],
        poly_markets: Sequence[MatchCandidate],
        redis: "Redis",
        top_n: int = 10,
    ) -> list[MarketMatch]:
        """Find matching markets using cached embeddings.

        Embeds title and description separately, combines similarities.
        Filters by expiry window (±24h) and exact strike match.
        Returns top N matches ranked by combined similarity.

        Args:
            kalshi_markets: Kalshi market candidates.
            poly_markets: Polymarket market candidates.
            redis: Redis connection for embedding cache.
            top_n: Number of top matches to return.

        Returns:
            List of top matched market pairs.
        """
        if not kalshi_markets or not poly_markets:
            return []

        # Separate title and description texts
        kalshi_titles = [m.title.strip() for m in kalshi_markets]
        kalshi_descs = [m.description.strip() for m in kalshi_markets]
        poly_titles = [m.title.strip() for m in poly_markets]
        poly_descs = [m.description.strip() for m in poly_markets]

        logger.info(
            "Computing separate title/description embeddings for %d Kalshi and %d Poly markets",
            len(kalshi_markets),
            len(poly_markets),
        )

        # Embed titles and descriptions separately
        kalshi_title_emb = await self._embedding_service.embed_with_cache(kalshi_titles, redis)
        kalshi_desc_emb = await self._embedding_service.embed_with_cache(kalshi_descs, redis)
        poly_title_emb = await self._embedding_service.embed_with_cache(poly_titles, redis)
        poly_desc_emb = await self._embedding_service.embed_with_cache(poly_descs, redis)

        # Compute separate similarity matrices
        title_sim = self._embedding_service.compute_similarity_matrix(kalshi_title_emb, poly_title_emb)
        desc_sim = self._embedding_service.compute_similarity_matrix(kalshi_desc_emb, poly_desc_emb)

        matches: list[MarketMatch] = []
        for i, kalshi_market in enumerate(kalshi_markets):
            for j, poly_market in enumerate(poly_markets):
                # Check expiry within window
                expiry_delta = _expiry_delta_hours(kalshi_market.expiry, poly_market.expiry)
                if expiry_delta > self._expiry_window_hours:
                    continue

                # Check exact strike match
                strike_ok = _strikes_match_exact(
                    kalshi_market.floor_strike,
                    kalshi_market.cap_strike,
                    poly_market.floor_strike,
                    poly_market.cap_strike,
                )
                if not strike_ok:
                    continue

                # Combined similarity (average of title and description)
                title_similarity = float(title_sim[i, j])
                desc_similarity = float(desc_sim[i, j])
                combined_similarity = (title_similarity + desc_similarity) / 2

                matches.append(
                    MarketMatch(
                        kalshi_market_id=kalshi_market.market_id,
                        poly_market_id=poly_market.market_id,
                        title_similarity=combined_similarity,
                        expiry_delta_hours=expiry_delta,
                        strike_match=strike_ok,
                    )
                )

        # Rank by combined similarity, return top N
        matches.sort(key=lambda m: -m.title_similarity)
        top_matches = matches[:top_n]
        logger.info("Found %d matches after filtering, returning top %d", len(matches), len(top_matches))
        return top_matches

    async def match_with_cache_and_strike_filter(
        self,
        kalshi_markets: Sequence[MatchCandidate],
        poly_markets: Sequence[MatchCandidate],
        redis: "Redis",
        top_n: int = 10,
    ) -> list[MarketMatch]:
        """Find matching markets with cache, filtering to only those with matching strikes.

        Args:
            kalshi_markets: Kalshi market candidates.
            poly_markets: Polymarket market candidates.
            redis: Redis connection for embedding cache.
            top_n: Number of top matches to return.

        Returns:
            List of top matched market pairs where strikes match exactly.
        """
        return await self.match_with_cache(kalshi_markets, poly_markets, redis, top_n)


__all__ = ["MarketMatcher"]
