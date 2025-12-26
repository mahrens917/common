"""Tests for pdf_configuration module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from common.pdf_configuration import (
    NDIM_2D,
    PDFConfigurationCurrencyUnset,
    PDFConfigurationMissing,
    _deep_merge_dict,
    _load_json,
    _normalize_currency,
    _optimized_config_path,
    _resolve_currency,
    currency_context,
    get_active_config_paths,
    load_active_pdf_config,
    load_base_pdf_config,
    reset_current_currency,
    set_current_currency,
    write_optimized_snapshot,
)

# Test constants (data_guard requirement)
TEST_CURRENCY_BTC = "BTC"
TEST_CURRENCY_ETH = "ETH"
TEST_CURRENCY_LOWER = "btc"
TEST_CURRENCY_WITH_SPACE = "  BTC  "
TEST_EMPTY_STRING = ""
TEST_WHITESPACE = "   "
TEST_BASE_CONFIG = {"param1": "value1", "nested": {"key": "val"}}
TEST_OPTIMIZED_PARAMS = {"param2": "value2", "nested": {"key2": "val2"}}
TEST_OPTIMIZED_CONFIG = {"parameters": TEST_OPTIMIZED_PARAMS, "metadata": {"version": "1.0"}}
TEST_INVALID_JSON = "{invalid json content"
TEST_CONFIG_FILENAME = "pdf_parameters.json"
TEST_OPTIMIZED_FILENAME_TEMPLATE = "pdf_parameters.optimized.{}.json"


class TestConstants:
    """Tests for module constants."""

    def test_ndim_2d(self) -> None:
        """Test NDIM_2D constant."""
        assert NDIM_2D == 2


class TestNormalizeCurrency:
    """Tests for _normalize_currency function."""

    def test_uppercase_conversion(self) -> None:
        """Test converts to uppercase."""
        assert _normalize_currency(TEST_CURRENCY_LOWER) == TEST_CURRENCY_BTC
        assert _normalize_currency("eth") == TEST_CURRENCY_ETH

    def test_strips_whitespace(self) -> None:
        """Test strips whitespace."""
        assert _normalize_currency(TEST_CURRENCY_WITH_SPACE) == TEST_CURRENCY_BTC

    def test_empty_raises(self) -> None:
        """Test raises on empty currency."""
        with pytest.raises(ValueError) as exc_info:
            _normalize_currency(TEST_EMPTY_STRING)

        assert "empty" in str(exc_info.value)

    def test_whitespace_only_raises(self) -> None:
        """Test raises on whitespace-only currency."""
        with pytest.raises(ValueError):
            _normalize_currency(TEST_WHITESPACE)


class TestDeepMergeDict:
    """Tests for _deep_merge_dict function."""

    def test_simple_merge(self) -> None:
        """Test simple key merge."""
        base = {"a": 1, "b": 2}
        overlay = {"b": 3, "c": 4}

        result = _deep_merge_dict(base, overlay)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self) -> None:
        """Test nested dict merge."""
        base = {"outer": {"a": 1, "b": 2}}
        overlay = {"outer": {"b": 3, "c": 4}}

        result = _deep_merge_dict(base, overlay)

        assert result == {"outer": {"a": 1, "b": 3, "c": 4}}

    def test_list_replacement(self) -> None:
        """Test lists are replaced not merged."""
        base = {"items": [1, 2, 3]}
        overlay = {"items": [4, 5]}

        result = _deep_merge_dict(base, overlay)

        assert result == {"items": [4, 5]}

    def test_does_not_modify_original(self) -> None:
        """Test original dicts are not modified."""
        base = {"a": 1}
        overlay = {"a": 2}

        _deep_merge_dict(base, overlay)

        assert base == {"a": 1}
        assert overlay == {"a": 2}


class TestResolveCurrency:
    """Tests for _resolve_currency function."""

    def test_uses_provided_currency(self) -> None:
        """Test uses provided currency argument."""
        result = _resolve_currency(TEST_CURRENCY_LOWER)

        assert result == TEST_CURRENCY_BTC

    def test_raises_when_no_currency(self) -> None:
        """Test raises when no currency provided or in context."""
        # Reset context first
        token = set_current_currency(None)
        try:
            with pytest.raises(PDFConfigurationCurrencyUnset):
                _resolve_currency(None)
        finally:
            reset_current_currency(token)

    def test_uses_context_currency(self) -> None:
        """Test uses currency from context when not provided."""
        token = set_current_currency(TEST_CURRENCY_ETH)
        try:
            result = _resolve_currency(None)
            assert result == TEST_CURRENCY_ETH
        finally:
            reset_current_currency(token)


class TestCurrencyContext:
    """Tests for currency context functions."""

    def test_set_and_reset(self) -> None:
        """Test setting and resetting currency."""
        original_token = set_current_currency(None)
        try:
            token = set_current_currency(TEST_CURRENCY_BTC)
            assert _resolve_currency(None) == TEST_CURRENCY_BTC

            reset_current_currency(token)
        finally:
            reset_current_currency(original_token)

    def test_context_manager(self) -> None:
        """Test currency_context context manager."""
        original_token = set_current_currency(None)
        try:
            with currency_context(TEST_CURRENCY_ETH):
                assert _resolve_currency(None) == TEST_CURRENCY_ETH
        finally:
            reset_current_currency(original_token)

    def test_nested_context(self) -> None:
        """Test nested currency contexts."""
        original_token = set_current_currency(None)
        try:
            with currency_context(TEST_CURRENCY_BTC):
                assert _resolve_currency(None) == TEST_CURRENCY_BTC
                with currency_context(TEST_CURRENCY_ETH):
                    assert _resolve_currency(None) == TEST_CURRENCY_ETH
                assert _resolve_currency(None) == TEST_CURRENCY_BTC
        finally:
            reset_current_currency(original_token)


class TestPDFConfigurationExceptions:
    """Tests for exception classes."""

    def test_pdf_configuration_missing(self) -> None:
        """Test PDFConfigurationMissing is FileNotFoundError."""
        error = PDFConfigurationMissing("Config not found")

        assert isinstance(error, FileNotFoundError)
        assert "Config not found" in str(error)

    def test_pdf_configuration_currency_unset(self) -> None:
        """Test PDFConfigurationCurrencyUnset is RuntimeError."""
        error = PDFConfigurationCurrencyUnset("No currency")

        assert isinstance(error, RuntimeError)
        assert "No currency" in str(error)


class TestLoadJson:
    """Tests for _load_json function."""

    def test_loads_valid_json(self) -> None:
        """Test loads valid JSON from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(TEST_BASE_CONFIG, tmp)
            tmp_path = Path(tmp.name)

        try:
            result = _load_json(tmp_path)
            assert result == TEST_BASE_CONFIG
        finally:
            tmp_path.unlink()

    def test_raises_on_missing_file(self) -> None:
        """Test raises FileNotFoundError when file does not exist."""
        nonexistent_path = Path("/nonexistent/path/config.json")

        with pytest.raises(FileNotFoundError) as exc_info:
            _load_json(nonexistent_path)

        assert "not found" in str(exc_info.value)


class TestOptimizedConfigPath:
    """Tests for _optimized_config_path function."""

    def test_generates_correct_path(self) -> None:
        """Test generates correct optimized config path."""
        result = _optimized_config_path(TEST_CURRENCY_BTC)

        assert result.name == TEST_OPTIMIZED_FILENAME_TEMPLATE.format(TEST_CURRENCY_BTC)
        assert "config" in str(result)

    def test_normalizes_currency_in_path(self) -> None:
        """Test normalizes currency when generating path."""
        result = _optimized_config_path(TEST_CURRENCY_LOWER)

        assert result.name == TEST_OPTIMIZED_FILENAME_TEMPLATE.format(TEST_CURRENCY_BTC)


class TestLoadBasePdfConfig:
    """Tests for load_base_pdf_config function."""

    def test_loads_base_config(self) -> None:
        """Test loads base PDF configuration."""
        result = load_base_pdf_config()

        assert isinstance(result, dict)
        assert len(result) > 0


class TestLoadActivePdfConfig:
    """Tests for load_active_pdf_config function."""

    def test_loads_with_currency_argument(self) -> None:
        """Test loads config using currency argument."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / "config"
            config_dir.mkdir()
            base_path = config_dir / TEST_CONFIG_FILENAME
            optimized_path = config_dir / TEST_OPTIMIZED_FILENAME_TEMPLATE.format(TEST_CURRENCY_BTC)

            base_path.write_text(json.dumps(TEST_BASE_CONFIG))
            optimized_path.write_text(json.dumps(TEST_OPTIMIZED_CONFIG))

            with patch("common.pdf_configuration.BASE_CONFIG_PATH", base_path):
                with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                    merged, metadata = load_active_pdf_config(TEST_CURRENCY_BTC)

                    assert "param1" in merged
                    assert "param2" in merged
                    assert metadata.get("currency") == TEST_CURRENCY_BTC

    def test_raises_on_missing_optimized_config(self) -> None:
        """Test raises PDFConfigurationMissing when optimized config absent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / "config"
            config_dir.mkdir()
            base_path = config_dir / TEST_CONFIG_FILENAME
            base_path.write_text(json.dumps(TEST_BASE_CONFIG))

            with patch("common.pdf_configuration.BASE_CONFIG_PATH", base_path):
                with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                    token = set_current_currency(TEST_CURRENCY_BTC)
                    try:
                        with pytest.raises(PDFConfigurationMissing):
                            load_active_pdf_config()
                    finally:
                        reset_current_currency(token)

    def test_allow_missing_returns_empty_params(self) -> None:
        """Test allow_missing returns empty parameters when optimized absent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / "config"
            config_dir.mkdir()
            base_path = config_dir / TEST_CONFIG_FILENAME
            base_path.write_text(json.dumps(TEST_BASE_CONFIG))

            with patch("common.pdf_configuration.BASE_CONFIG_PATH", base_path):
                with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                    merged, metadata = load_active_pdf_config(TEST_CURRENCY_BTC, allow_missing=True)

                    assert merged == TEST_BASE_CONFIG
                    assert metadata.get("currency") == TEST_CURRENCY_BTC

    def test_raises_on_empty_parameters_in_optimized(self) -> None:
        """Test raises ValueError when optimized config has empty parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / "config"
            config_dir.mkdir()
            base_path = config_dir / TEST_CONFIG_FILENAME
            optimized_path = config_dir / TEST_OPTIMIZED_FILENAME_TEMPLATE.format(TEST_CURRENCY_BTC)

            base_path.write_text(json.dumps(TEST_BASE_CONFIG))
            optimized_path.write_text(json.dumps({"parameters": {}, "metadata": {}}))

            with patch("common.pdf_configuration.BASE_CONFIG_PATH", base_path):
                with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                    with pytest.raises(ValueError) as exc_info:
                        load_active_pdf_config(TEST_CURRENCY_BTC)

                    assert "must provide" in str(exc_info.value)

    def test_handles_none_parameters(self) -> None:
        """Test handles None parameters in optimized config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / "config"
            config_dir.mkdir()
            base_path = config_dir / TEST_CONFIG_FILENAME
            optimized_path = config_dir / TEST_OPTIMIZED_FILENAME_TEMPLATE.format(TEST_CURRENCY_BTC)

            base_path.write_text(json.dumps(TEST_BASE_CONFIG))
            optimized_path.write_text(json.dumps({"parameters": None, "metadata": {"currency": TEST_CURRENCY_BTC}}))

            with patch("common.pdf_configuration.BASE_CONFIG_PATH", base_path):
                with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                    with pytest.raises(ValueError):
                        load_active_pdf_config(TEST_CURRENCY_BTC)

    def test_merges_nested_dicts(self) -> None:
        """Test properly merges nested dictionaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / "config"
            config_dir.mkdir()
            base_path = config_dir / TEST_CONFIG_FILENAME
            optimized_path = config_dir / TEST_OPTIMIZED_FILENAME_TEMPLATE.format(TEST_CURRENCY_BTC)

            base_path.write_text(json.dumps(TEST_BASE_CONFIG))
            optimized_path.write_text(json.dumps(TEST_OPTIMIZED_CONFIG))

            with patch("common.pdf_configuration.BASE_CONFIG_PATH", base_path):
                with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                    merged, _ = load_active_pdf_config(TEST_CURRENCY_BTC)

                    assert merged["nested"]["key"] == "val"
                    assert merged["nested"]["key2"] == "val2"

    def test_extracts_metadata_excluding_parameters(self) -> None:
        """Test extracts metadata excluding parameters key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / "config"
            config_dir.mkdir()
            base_path = config_dir / TEST_CONFIG_FILENAME
            optimized_path = config_dir / TEST_OPTIMIZED_FILENAME_TEMPLATE.format(TEST_CURRENCY_BTC)

            base_path.write_text(json.dumps(TEST_BASE_CONFIG))
            optimized_path.write_text(json.dumps(TEST_OPTIMIZED_CONFIG))

            with patch("common.pdf_configuration.BASE_CONFIG_PATH", base_path):
                with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                    _, metadata = load_active_pdf_config(TEST_CURRENCY_BTC)

                    assert "parameters" not in metadata
                    assert metadata.get("metadata") == {"version": "1.0"}
                    assert metadata.get("currency") == TEST_CURRENCY_BTC


class TestGetActiveConfigPaths:
    """Tests for get_active_config_paths function."""

    def test_returns_both_paths(self) -> None:
        """Test returns base and optimized config paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / "config"
            config_dir.mkdir()
            base_path = config_dir / TEST_CONFIG_FILENAME
            optimized_path = config_dir / TEST_OPTIMIZED_FILENAME_TEMPLATE.format(TEST_CURRENCY_BTC)

            base_path.write_text(json.dumps(TEST_BASE_CONFIG))
            optimized_path.write_text(json.dumps(TEST_OPTIMIZED_CONFIG))

            with patch("common.pdf_configuration.BASE_CONFIG_PATH", base_path):
                with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                    token = set_current_currency(TEST_CURRENCY_BTC)
                    try:
                        base_ret, opt_ret = get_active_config_paths()

                        assert base_ret == base_path
                        assert opt_ret == optimized_path
                    finally:
                        reset_current_currency(token)

    def test_raises_on_missing_optimized(self) -> None:
        """Test raises when optimized config does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / "config"
            config_dir.mkdir()
            base_path = config_dir / TEST_CONFIG_FILENAME
            base_path.write_text(json.dumps(TEST_BASE_CONFIG))

            with patch("common.pdf_configuration.BASE_CONFIG_PATH", base_path):
                with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                    token = set_current_currency(TEST_CURRENCY_BTC)
                    try:
                        with pytest.raises(PDFConfigurationMissing):
                            get_active_config_paths()
                    finally:
                        reset_current_currency(token)


class TestWriteOptimizedSnapshot:
    """Tests for write_optimized_snapshot function."""

    def test_writes_snapshot_to_file(self) -> None:
        """Test writes optimized snapshot to correct path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                result_path = write_optimized_snapshot(TEST_OPTIMIZED_CONFIG.copy(), TEST_CURRENCY_BTC)

                assert result_path.exists()
                assert result_path.name == TEST_OPTIMIZED_FILENAME_TEMPLATE.format(TEST_CURRENCY_BTC)

    def test_creates_parent_directory(self) -> None:
        """Test creates parent directory if it does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                result_path = write_optimized_snapshot(TEST_OPTIMIZED_CONFIG.copy(), TEST_CURRENCY_BTC)

                assert result_path.parent.exists()

    def test_sets_default_metadata(self) -> None:
        """Test sets default metadata if not present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            payload = {"parameters": TEST_OPTIMIZED_PARAMS}

            with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                result_path = write_optimized_snapshot(payload, TEST_CURRENCY_BTC)

                written_data = json.loads(result_path.read_text())
                assert "metadata" in written_data
                assert written_data["metadata"]["currency"] == TEST_CURRENCY_BTC

    def test_preserves_existing_metadata_currency(self) -> None:
        """Test preserves existing metadata currency."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            payload = {"parameters": TEST_OPTIMIZED_PARAMS, "metadata": {"currency": "XYZ"}}

            with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                result_path = write_optimized_snapshot(payload, TEST_CURRENCY_BTC)

                written_data = json.loads(result_path.read_text())
                assert written_data["metadata"]["currency"] == "XYZ"

    def test_normalizes_currency(self) -> None:
        """Test normalizes currency in filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                result_path = write_optimized_snapshot(TEST_OPTIMIZED_CONFIG.copy(), TEST_CURRENCY_LOWER)

                assert result_path.name == TEST_OPTIMIZED_FILENAME_TEMPLATE.format(TEST_CURRENCY_BTC)

    def test_writes_formatted_json(self) -> None:
        """Test writes formatted JSON with correct indentation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            with patch("common.pdf_configuration.PROJECT_ROOT", tmpdir_path):
                result_path = write_optimized_snapshot(TEST_OPTIMIZED_CONFIG.copy(), TEST_CURRENCY_BTC)

                content = result_path.read_text()
                assert content.endswith("\n")
                # Verify it's valid JSON
                parsed = json.loads(content)
                assert "parameters" in parsed
