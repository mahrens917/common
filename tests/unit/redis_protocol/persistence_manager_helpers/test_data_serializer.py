import pytest

from common.redis_protocol.persistence_manager_helpers.data_serializer import (
    DataSerializer,
    build_status_dict,
    format_persistence_status,
    normalize_boolean_config,
)


class TestDataSerializer:
    def test_normalize_boolean_config(self):
        assert normalize_boolean_config("yes") is True
        assert normalize_boolean_config("Yes") is True
        assert normalize_boolean_config("no") is False
        assert normalize_boolean_config("") is False
        assert normalize_boolean_config(None) is False

        # Test static method access
        assert DataSerializer.normalize_boolean_config("yes") is True

    def test_format_persistence_status_error(self):
        status = {"error": "Something went wrong"}
        formatted = format_persistence_status(status)
        assert "❌ Error checking persistence: Something went wrong" in formatted

    def test_format_persistence_status_success(self):
        status = {
            "aof_enabled": True,
            "aof_filename": "appendonly.aof",
            "aof_fsync": "everysec",
            "aof_size": 1024,
            "rdb_enabled": True,
            "rdb_filename": "dump.rdb",
            "rdb_save_config": "900 1",
            "rdb_last_save": 1234567890,
            "rdb_last_bgsave_status": "ok",
            "data_directory": "/data",
            "persistence_properly_configured": True,
        }
        formatted = format_persistence_status(status)
        assert "✅ Properly Configured" in formatted
        assert "AOF Enabled: ✅ True" in formatted
        assert "RDB Enabled: ✅ True" in formatted

    def test_format_persistence_status_needs_config(self):
        status = {
            "aof_enabled": False,
            "aof_filename": "appendonly.aof",
            "aof_fsync": "everysec",
            "aof_size": 0,
            "rdb_enabled": False,
            "rdb_filename": "dump.rdb",
            "rdb_save_config": "",
            "rdb_last_save": 0,
            "rdb_last_bgsave_status": "unknown",
            "data_directory": "/data",
            "persistence_properly_configured": False,
        }
        formatted = format_persistence_status(status)
        assert "❌ Needs Configuration" in formatted
        assert "AOF Enabled: ❌ False" in formatted

    def test_build_status_dict(self):
        config_info = {
            "appendonly": "yes",
            "appendfilename": "test.aof",
            "appendfsync": "always",
            "save": "3600 1",
            "dbfilename": "test.rdb",
            "dir": "/tmp",
        }
        persistence_info = {
            "aof_current_size": 500,
            "aof_last_rewrite_time_sec": 100,
            "rdb_last_bgsave_status": "ok",
        }
        last_save = 1000

        result = build_status_dict(config_info, persistence_info, last_save)

        assert result["aof_enabled"] is True
        assert result["aof_filename"] == "test.aof"
        assert result["aof_fsync"] == "always"
        assert result["aof_size"] == 500
        assert result["aof_last_rewrite"] == 100
        assert result["rdb_enabled"] is True
        assert result["rdb_filename"] == "test.rdb"
        assert result["rdb_save_config"] == "3600 1"
        assert result["rdb_last_save"] == 1000
        assert result["rdb_last_bgsave_status"] == "ok"
        assert result["data_directory"] == "/tmp"
        assert result["persistence_properly_configured"] is True
