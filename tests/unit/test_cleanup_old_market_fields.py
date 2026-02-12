"""Tests for scripts/cleanup_old_market_fields.py."""

from unittest.mock import AsyncMock, patch

import pytest
from scripts.cleanup_old_market_fields import OLD_FIELDS, cleanup_old_fields, main


class TestCleanupOldFields:
    """Tests for cleanup_old_fields."""

    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        return redis

    async def test_no_keys_found(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, []))
        with patch("scripts.cleanup_old_market_fields.get_redis_client", return_value=mock_redis):
            with patch("scripts.cleanup_old_market_fields.cleanup_redis_pool", new_callable=AsyncMock):
                scanned, removed = await cleanup_old_fields(dry_run=True)
        assert scanned == 0
        assert removed == 0

    async def test_keys_without_old_fields(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:abc"]))
        mock_redis.hmget = AsyncMock(return_value=[None, None])
        with patch("scripts.cleanup_old_market_fields.get_redis_client", return_value=mock_redis):
            with patch("scripts.cleanup_old_market_fields.cleanup_redis_pool", new_callable=AsyncMock):
                scanned, removed = await cleanup_old_fields(dry_run=True)
        assert scanned == 1
        assert removed == 0

    async def test_dry_run_does_not_delete(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:abc"]))
        mock_redis.hmget = AsyncMock(return_value=[b"0.5", b"0.6"])
        mock_redis.hdel = AsyncMock()
        with patch("scripts.cleanup_old_market_fields.get_redis_client", return_value=mock_redis):
            with patch("scripts.cleanup_old_market_fields.cleanup_redis_pool", new_callable=AsyncMock):
                scanned, removed = await cleanup_old_fields(dry_run=True)
        assert scanned == 1
        assert removed == len(OLD_FIELDS)
        mock_redis.hdel.assert_not_awaited()

    async def test_execute_deletes_fields(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:abc"]))
        mock_redis.hmget = AsyncMock(return_value=[b"0.5", None])
        mock_redis.hdel = AsyncMock()
        with patch("scripts.cleanup_old_market_fields.get_redis_client", return_value=mock_redis):
            with patch("scripts.cleanup_old_market_fields.cleanup_redis_pool", new_callable=AsyncMock):
                scanned, removed = await cleanup_old_fields(dry_run=False)
        assert scanned == 1
        assert removed == 1
        mock_redis.hdel.assert_awaited_once()

    async def test_pagination_via_cursor(self, mock_redis):
        mock_redis.scan = AsyncMock(side_effect=[(42, [b"markets:kalshi:a"]), (0, [b"markets:kalshi:b"])])
        mock_redis.hmget = AsyncMock(return_value=[None, None])
        with patch("scripts.cleanup_old_market_fields.get_redis_client", return_value=mock_redis):
            with patch("scripts.cleanup_old_market_fields.cleanup_redis_pool", new_callable=AsyncMock):
                scanned, removed = await cleanup_old_fields(dry_run=True)
        assert scanned == 2
        assert removed == 0

    async def test_cleanup_pool_called_on_error(self, mock_redis):
        mock_redis.scan = AsyncMock(side_effect=RuntimeError("fail"))
        mock_cleanup = AsyncMock()
        with patch("scripts.cleanup_old_market_fields.get_redis_client", return_value=mock_redis):
            with patch("scripts.cleanup_old_market_fields.cleanup_redis_pool", mock_cleanup):
                with pytest.raises(RuntimeError, match="fail"):
                    await cleanup_old_fields(dry_run=True)
        mock_cleanup.assert_awaited_once()

    async def test_string_key_decoded(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, ["markets:kalshi:abc"]))
        mock_redis.hmget = AsyncMock(return_value=[None, None])
        with patch("scripts.cleanup_old_market_fields.get_redis_client", return_value=mock_redis):
            with patch("scripts.cleanup_old_market_fields.cleanup_redis_pool", new_callable=AsyncMock):
                scanned, removed = await cleanup_old_fields(dry_run=True)
        assert scanned == 1
        assert removed == 0


class TestMain:
    """Tests for the main function."""

    async def test_main_dry_run_by_default(self):
        with patch("scripts.cleanup_old_market_fields.argparse.ArgumentParser.parse_args") as mock_parse:
            mock_parse.return_value.execute = False
            with patch("scripts.cleanup_old_market_fields.cleanup_old_fields", new_callable=AsyncMock, return_value=(0, 0)):
                await main()

    async def test_main_execute_mode(self):
        with patch("scripts.cleanup_old_market_fields.argparse.ArgumentParser.parse_args") as mock_parse:
            mock_parse.return_value.execute = True
            with patch("scripts.cleanup_old_market_fields.cleanup_old_fields", new_callable=AsyncMock, return_value=(5, 2)) as mock_cleanup:
                await main()
                mock_cleanup.assert_awaited_once_with(dry_run=False)
