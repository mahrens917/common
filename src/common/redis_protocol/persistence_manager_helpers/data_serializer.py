"""Data serialization and formatting for Redis persistence."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DataSerializer:

    @staticmethod
    def format_persistence_status(status: Dict[str, Any]) -> str:
        if "error" in status:
            return f"❌ Error checking persistence: {status['error']}"

        aof_flag = "✅" if status["aof_enabled"] else "❌"
        rdb_flag = "✅" if status["rdb_enabled"] else "❌"
        overall_flag = "✅ Properly Configured" if status["persistence_properly_configured"] else "❌ Needs Configuration"

        info_lines = [
            "=== Redis Persistence Status ===",
            f"AOF Enabled: {aof_flag} {status['aof_enabled']}",
            f"AOF Filename: {status['aof_filename']}",
            f"AOF Sync Mode: {status['aof_fsync']}",
            f"AOF Size: {status['aof_size']} bytes",
            "",
            f"RDB Enabled: {rdb_flag} {status['rdb_enabled']}",
            f"RDB Filename: {status['rdb_filename']}",
            f"RDB Save Config: {status['rdb_save_config']}",
            f"RDB Last Save: {status['rdb_last_save']}",
            f"RDB Last Status: {status['rdb_last_bgsave_status']}",
            "",
            f"Data Directory: {status['data_directory']}",
            f"Overall Status: {overall_flag}",
        ]
        return "\n".join(info_lines)

    @staticmethod
    def normalize_boolean_config(value: Any) -> bool:
        if not value:
            return False
        return str(value).lower() == "yes"

    @staticmethod
    def build_status_dict(
        config_info: Dict[str, Any],
        persistence_info: Dict[str, Any],
        last_save_time: int,
    ) -> Dict[str, Any]:
        config_values = DataSerializer._extract_config_values(config_info)
        persistence_values = DataSerializer._extract_persistence_values(persistence_info)
        return DataSerializer._assemble_status_dict(config_values, persistence_values, last_save_time)

    @staticmethod
    def _extract_config_values(config_info: Dict[str, Any]) -> Dict[str, Any]:
        field_names = ["appendonly", "appendfilename", "appendfsync", "save", "dbfilename", "dir"]
        return DataSerializer._require_fields(config_info, field_names, "Redis config")

    @staticmethod
    def _extract_persistence_values(persistence_info: Dict[str, Any]) -> Dict[str, Any]:
        field_names = ["aof_current_size", "aof_last_rewrite_time_sec", "rdb_last_bgsave_status"]
        return DataSerializer._require_fields(persistence_info, field_names, "Redis persistence info")

    @staticmethod
    def _assemble_status_dict(config_values: Dict[str, Any], persistence_values: Dict[str, Any], last_save_time: int) -> Dict[str, Any]:
        aof_enabled = DataSerializer.normalize_boolean_config(config_values["appendonly"])
        save_config = config_values["save"]
        return {
            "aof_enabled": aof_enabled,
            "aof_filename": config_values["appendfilename"],
            "aof_fsync": config_values["appendfsync"],
            "aof_size": persistence_values["aof_current_size"],
            "aof_last_rewrite": persistence_values["aof_last_rewrite_time_sec"],
            "rdb_enabled": bool(save_config),
            "rdb_filename": config_values["dbfilename"],
            "rdb_save_config": save_config,
            "rdb_last_save": last_save_time,
            "rdb_last_bgsave_status": persistence_values["rdb_last_bgsave_status"],
            "data_directory": config_values["dir"],
            "persistence_properly_configured": aof_enabled and bool(save_config),
        }

    @staticmethod
    def _require_fields(data: Dict[str, Any], names: list[str], label: str) -> Dict[str, Any]:
        return {name: DataSerializer._require_field(data, name, label) for name in names}

    @staticmethod
    def _require_field(data: Dict[str, Any], name: str, label: str) -> Any:
        if name not in data:
            raise ValueError(f"{label} missing required '{name}' field")
        return data[name]


def format_persistence_status(status: Dict[str, Any]) -> str:

    return DataSerializer.format_persistence_status(status)


def normalize_boolean_config(value: Any) -> bool:

    return DataSerializer.normalize_boolean_config(value)


def build_status_dict(config_info: Dict[str, Any], persistence_info: Dict[str, Any], last_save_time: int) -> Dict[str, Any]:

    return DataSerializer.build_status_dict(config_info, persistence_info, last_save_time)
