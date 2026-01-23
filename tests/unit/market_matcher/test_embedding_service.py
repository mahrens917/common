"""Tests for market_matcher embedding_service module."""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from common.market_matcher.embedding_service import (
    _EMBEDDING_DIM,
    EmbeddingService,
    _load_api_key_from_env_file,
    _text_to_cache_key,
)


class TestLoadApiKeyFromEnvFile:
    """Tests for _load_api_key_from_env_file function."""

    def test_returns_none_when_file_missing(self, tmp_path) -> None:
        """Test returns None when ~/.env doesn't exist."""
        with patch("common.market_matcher.embedding_service._ENV_FILE_PATH", tmp_path / "nonexistent"):
            assert _load_api_key_from_env_file() is None

    def test_returns_none_when_key_not_present(self, tmp_path) -> None:
        """Test returns None when key not in file."""
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_KEY=value\n")
        with patch("common.market_matcher.embedding_service._ENV_FILE_PATH", env_file):
            assert _load_api_key_from_env_file() is None

    def test_loads_unquoted_key(self, tmp_path) -> None:
        """Test loads unquoted API key."""
        env_file = tmp_path / ".env"
        env_file.write_text("NOVITA_API_KEY=test-key-123\n")
        with patch("common.market_matcher.embedding_service._ENV_FILE_PATH", env_file):
            assert _load_api_key_from_env_file() == "test-key-123"

    def test_loads_double_quoted_key(self, tmp_path) -> None:
        """Test loads double-quoted API key."""
        env_file = tmp_path / ".env"
        env_file.write_text('NOVITA_API_KEY="test-key-123"\n')
        with patch("common.market_matcher.embedding_service._ENV_FILE_PATH", env_file):
            assert _load_api_key_from_env_file() == "test-key-123"

    def test_loads_single_quoted_key(self, tmp_path) -> None:
        """Test loads single-quoted API key."""
        env_file = tmp_path / ".env"
        env_file.write_text("NOVITA_API_KEY='test-key-123'\n")
        with patch("common.market_matcher.embedding_service._ENV_FILE_PATH", env_file):
            assert _load_api_key_from_env_file() == "test-key-123"


class TestTextToCacheKey:
    """Tests for _text_to_cache_key function."""

    def test_generates_consistent_key(self) -> None:
        """Test generates same key for same text."""
        key1 = _text_to_cache_key("hello world")
        key2 = _text_to_cache_key("hello world")
        assert key1 == key2

    def test_generates_different_keys_for_different_text(self) -> None:
        """Test generates different keys for different text."""
        key1 = _text_to_cache_key("hello")
        key2 = _text_to_cache_key("world")
        assert key1 != key2

    def test_key_has_prefix(self) -> None:
        """Test key has the expected prefix."""
        key = _text_to_cache_key("test")
        assert key.startswith("embedding:qwen3-8b:")


class TestEmbeddingServiceInit:
    """Tests for EmbeddingService initialization."""

    def test_init_with_explicit_api_key(self) -> None:
        """Test initialization with explicit API key."""
        service = EmbeddingService(api_key="test-key")
        assert service._api_key == "test-key"

    def test_init_raises_without_api_key(self, tmp_path) -> None:
        """Test initialization raises when no API key available."""
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_KEY=value\n")
        with patch("common.market_matcher.embedding_service._ENV_FILE_PATH", env_file):
            with pytest.raises(ValueError, match="NOVITA_API_KEY not found"):
                EmbeddingService()

    def test_device_property_returns_api(self) -> None:
        """Test device property returns 'novita-api'."""
        service = EmbeddingService(api_key="test-key")
        assert service.device == "novita-api"


class TestEmbeddingServiceEmbed:
    """Tests for EmbeddingService.embed method."""

    @pytest.mark.asyncio
    async def test_embed_empty_returns_empty_array(self) -> None:
        """Test embed returns empty array for empty input."""
        service = EmbeddingService(api_key="test-key")
        result = await service.embed([])
        assert result.shape == (0, _EMBEDDING_DIM)

    @pytest.mark.asyncio
    async def test_embed_calls_api(self) -> None:
        """Test embed calls Novita API."""
        service = EmbeddingService(api_key="test-key")

        mock_response = {
            "data": [
                {"index": 0, "embedding": [1.0] * _EMBEDDING_DIM},
                {"index": 1, "embedding": [0.5] * _EMBEDDING_DIM},
            ]
        }

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_response_obj = AsyncMock()
            mock_response_obj.raise_for_status = MagicMock()
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_post = AsyncMock(return_value=mock_response_obj)
            mock_post.__aenter__ = AsyncMock(return_value=mock_response_obj)
            mock_post.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post.return_value = mock_post
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_cls.return_value = mock_session

            result = await service.embed(["text1", "text2"])

            assert result.shape == (2, _EMBEDDING_DIM)
            # Check L2 normalization
            norms = np.linalg.norm(result, axis=1)
            assert np.allclose(norms, 1.0, atol=1e-5)


class TestEmbeddingServiceComputeSimilarityMatrix:
    """Tests for EmbeddingService.compute_similarity_matrix method."""

    def test_compute_similarity_matrix(self) -> None:
        """Test computing similarity matrix."""
        service = EmbeddingService(api_key="test-key")

        embeddings_a = np.eye(2, dtype=np.float32)
        embeddings_b = np.eye(2, dtype=np.float32)

        result = service.compute_similarity_matrix(embeddings_a, embeddings_b)

        assert result.shape == (2, 2)
        assert result[0, 0] == pytest.approx(1.0)
        assert result[1, 1] == pytest.approx(1.0)
        assert result[0, 1] == pytest.approx(0.0)


class TestEmbeddingServiceEmbedWithCache:
    """Tests for EmbeddingService.embed_with_cache method."""

    @pytest.mark.asyncio
    async def test_embed_with_cache_empty_returns_empty(self) -> None:
        """Test embed_with_cache returns empty array for empty input."""
        service = EmbeddingService(api_key="test-key")
        redis = AsyncMock()

        result = await service.embed_with_cache([], redis)
        assert result.shape == (0, _EMBEDDING_DIM)

    @pytest.mark.asyncio
    async def test_embed_with_cache_uses_cached_values(self) -> None:
        """Test embed_with_cache uses cached values when available."""
        service = EmbeddingService(api_key="test-key")

        # Create cached embedding
        cached_embedding = np.zeros(_EMBEDDING_DIM, dtype=np.float32)
        cached_embedding[0] = 1.0

        redis = AsyncMock()
        redis.mget.return_value = [cached_embedding.tobytes()]

        result = await service.embed_with_cache(["test text"], redis)

        assert result.shape == (1, _EMBEDDING_DIM)
        assert result[0, 0] == 1.0

    @pytest.mark.asyncio
    async def test_embed_with_cache_computes_missing_embeddings(self) -> None:
        """Test embed_with_cache computes and caches embeddings not in cache."""
        service = EmbeddingService(api_key="test-key")

        mock_response = {"data": [{"index": 0, "embedding": [1.0] * _EMBEDDING_DIM}]}

        pipe_mock = MagicMock()
        pipe_mock.execute = AsyncMock()

        redis = MagicMock()
        redis.mget = AsyncMock(return_value=[None])
        redis.pipeline.return_value = pipe_mock

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_response_obj = AsyncMock()
            mock_response_obj.raise_for_status = MagicMock()
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response_obj)
            mock_post.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post.return_value = mock_post
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_cls.return_value = mock_session

            result = await service.embed_with_cache(["uncached text"], redis)

            assert result.shape == (1, _EMBEDDING_DIM)
            pipe_mock.set.assert_called_once()
            pipe_mock.execute.assert_called_once()
