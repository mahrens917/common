"""Tests for llm_extractor _api_key module."""

from unittest.mock import patch

from common.llm_extractor._api_key import load_api_key_from_env_file


class TestLoadApiKeyFromEnvFile:
    """Tests for load_api_key_from_env_file."""

    def test_returns_none_when_file_missing(self, tmp_path) -> None:
        """Test returns None when .env file does not exist."""
        with patch("common.llm_extractor._api_key._ENV_FILE_PATH", tmp_path / "nonexistent"):
            result = load_api_key_from_env_file("ANTHROPIC_API_KEY")
        assert result is None

    def test_returns_none_when_key_not_found(self, tmp_path) -> None:
        """Test returns None when key is not in the file."""
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_KEY=some_value\n")
        with patch("common.llm_extractor._api_key._ENV_FILE_PATH", env_file):
            result = load_api_key_from_env_file("ANTHROPIC_API_KEY")
        assert result is None

    def test_loads_unquoted_value(self, tmp_path) -> None:
        """Test loading an unquoted API key value."""
        env_file = tmp_path / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=sk-ant-test123\n")
        with patch("common.llm_extractor._api_key._ENV_FILE_PATH", env_file):
            result = load_api_key_from_env_file("ANTHROPIC_API_KEY")
        assert result == "sk-ant-test123"

    def test_loads_double_quoted_value(self, tmp_path) -> None:
        """Test loading a double-quoted API key value."""
        env_file = tmp_path / ".env"
        env_file.write_text('ANTHROPIC_API_KEY="sk-ant-quoted"\n')
        with patch("common.llm_extractor._api_key._ENV_FILE_PATH", env_file):
            result = load_api_key_from_env_file("ANTHROPIC_API_KEY")
        assert result == "sk-ant-quoted"

    def test_loads_single_quoted_value(self, tmp_path) -> None:
        """Test loading a single-quoted API key value."""
        env_file = tmp_path / ".env"
        env_file.write_text("ANTHROPIC_API_KEY='sk-ant-single'\n")
        with patch("common.llm_extractor._api_key._ENV_FILE_PATH", env_file):
            result = load_api_key_from_env_file("ANTHROPIC_API_KEY")
        assert result == "sk-ant-single"

    def test_handles_multiple_keys(self, tmp_path) -> None:
        """Test loading correct key when multiple keys exist."""
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_KEY=abc\nANTHROPIC_API_KEY=sk-ant-multi\nTHIRD=xyz\n")
        with patch("common.llm_extractor._api_key._ENV_FILE_PATH", env_file):
            result = load_api_key_from_env_file("ANTHROPIC_API_KEY")
        assert result == "sk-ant-multi"

    def test_handles_value_with_equals_sign(self, tmp_path) -> None:
        """Test loading a value that contains an equals sign."""
        env_file = tmp_path / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=test-key=with=equals\n")
        with patch("common.llm_extractor._api_key._ENV_FILE_PATH", env_file):
            result = load_api_key_from_env_file("ANTHROPIC_API_KEY")
        assert result == "test-key=with=equals"
