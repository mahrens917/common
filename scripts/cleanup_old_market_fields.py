#!/usr/bin/env python3
"""Clean up old non-namespaced t_yes_bid/t_yes_ask fields from Redis.

This is a one-time migration script for the transition to namespaced fields.
Old fields: t_yes_bid, t_yes_ask (non-namespaced)
New fields: {algo}:t_bid, {algo}:t_ask (namespaced by algo)

Usage:
    python -m scripts.cleanup_old_market_fields [--dry-run]
"""

import argparse
import asyncio
import logging
from typing import List

from common.redis_protocol.connection_pool_core import cleanup_redis_pool, get_redis_client
from common.redis_protocol.typing import ensure_awaitable

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

OLD_FIELDS = ("t_yes_bid", "t_yes_ask")


async def cleanup_old_fields(dry_run: bool = True) -> tuple[int, int]:
    """Remove old non-namespaced t_yes_bid/t_yes_ask fields from all markets.

    Args:
        dry_run: If True, only report what would be cleaned without making changes.

    Returns:
        Tuple of (markets_scanned, fields_removed)
    """
    redis = await get_redis_client()

    try:
        markets_scanned = 0
        fields_removed = 0
        cursor = 0

        logger.info("Scanning markets:kalshi:* for old non-namespaced fields...")
        if dry_run:
            logger.info("DRY RUN - no changes will be made")

        while True:
            cursor, keys = await ensure_awaitable(redis.scan(cursor, match="markets:kalshi:*", count=1000))

            for key in keys:
                key_str = key.decode("utf-8") if isinstance(key, bytes) else str(key)
                markets_scanned += 1

                # Check which old fields exist
                existing: List[bytes | None] = await ensure_awaitable(redis.hmget(key_str, list(OLD_FIELDS)))
                fields_to_remove = [field for field, value in zip(OLD_FIELDS, existing) if value is not None]

                if fields_to_remove:
                    if dry_run:
                        logger.info("Would remove %s from %s", fields_to_remove, key_str)
                    else:
                        await ensure_awaitable(redis.hdel(key_str, *fields_to_remove))
                        logger.debug("Removed %s from %s", fields_to_remove, key_str)
                    fields_removed += len(fields_to_remove)

            if cursor == 0:
                break

        return markets_scanned, fields_removed

    finally:
        await cleanup_redis_pool()


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Clean up old non-namespaced t_yes_bid/t_yes_ask fields")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Only report what would be cleaned (default: True)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the cleanup (disables dry-run)",
    )
    args = parser.parse_args()

    dry_run = not args.execute

    markets_scanned, fields_removed = await cleanup_old_fields(dry_run=dry_run)

    logger.info("")
    logger.info("Summary:")
    logger.info("  Markets scanned: %d", markets_scanned)
    logger.info("  Fields %s: %d", "would be removed" if dry_run else "removed", fields_removed)

    if dry_run and fields_removed > 0:
        logger.info("")
        logger.info("To execute cleanup, run with --execute flag")


if __name__ == "__main__":
    asyncio.run(main())
