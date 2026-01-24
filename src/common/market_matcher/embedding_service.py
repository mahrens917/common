"""Embedding service using Novita AI's Qwen3-Embedding-8B API with Redis caching."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

import aiohttp
import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_NOVITA_API_URL = "https://api.novita.ai/v3/openai/embeddings"
_MODEL_NAME = "qwen/qwen3-embedding-8b"
_EMBEDDING_KEY_PREFIX = "embedding:qwen3-8b"
_OLD_EMBEDDING_KEY_PREFIX = "embedding:qwen3"  # Old 0.6B model prefix
_EMBEDDING_DIM = 4096  # Qwen3-Embedding-8B dimension
_API_BATCH_SIZE = 50  # Max texts per API call (smaller batches for reliability)
_API_TIMEOUT_SECONDS = 300  # 5 minutes per batch
_ENV_FILE_PATH = Path.home() / ".env"


def _load_api_key_from_env_file() -> str | None:
    """Load NOVITA_API_KEY from ~/.env file."""
    if not _ENV_FILE_PATH.exists():
        return None
    for line in _ENV_FILE_PATH.read_text().splitlines():
        line = line.strip()
        if line.startswith("NOVITA_API_KEY="):
            value = line.split("=", 1)[1].strip()
            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            return value
    return None


def _text_to_cache_key(text: str) -> str:
    """Generate a cache key for a text string."""
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{_EMBEDDING_KEY_PREFIX}:{text_hash}"


class EmbeddingService:
    """Service for computing text embeddings using Novita AI's Qwen3-Embedding-8B."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the embedding service.

        Args:
            api_key: Novita API key. If not provided, reads from ~/.env file.
        """
        self._api_key = api_key or _load_api_key_from_env_file()
        if not self._api_key:
            raise ValueError("NOVITA_API_KEY not found in ~/.env")
        logger.info("Initialized EmbeddingService with Novita API (model: %s)", _MODEL_NAME)

    @property
    def device(self) -> str:
        """Return the device being used (API-based)."""
        return "novita-api"

    async def embed(self, texts: Sequence[str]) -> NDArray[np.float32]:
        """Compute embeddings for a batch of texts via Novita API.

        Args:
            texts: Sequence of texts to embed.

        Returns:
            Array of shape (n_texts, embedding_dim) with L2-normalized embeddings.
        """
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, _EMBEDDING_DIM)

        texts_list = list(texts)
        embeddings = np.zeros((len(texts_list), _EMBEDDING_DIM), dtype=np.float32)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        timeout = aiohttp.ClientTimeout(total=_API_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Process in batches to avoid API limits and timeouts
            for batch_start in range(0, len(texts_list), _API_BATCH_SIZE):
                batch_end = min(batch_start + _API_BATCH_SIZE, len(texts_list))
                batch_texts = texts_list[batch_start:batch_end]

                payload = {
                    "model": _MODEL_NAME,
                    "input": batch_texts,
                }

                async with session.post(_NOVITA_API_URL, json=payload, headers=headers) as resp:
                    resp.raise_for_status()
                    result = await resp.json()

                # Extract embeddings in order within this batch
                for item in result["data"]:
                    idx = batch_start + item["index"]
                    embeddings[idx] = np.array(item["embedding"], dtype=np.float32)

                if batch_end < len(texts_list):
                    logger.info("Embedded %d/%d texts...", batch_end, len(texts_list))

        # L2 normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # avoid division by zero
        normalized = embeddings / norms

        return normalized.astype(np.float32)

    async def embed_with_cache(
        self,
        texts: Sequence[str],
        redis: "Redis",
    ) -> NDArray[np.float32]:
        """Compute embeddings with Redis caching.

        Args:
            texts: Sequence of texts to embed.
            redis: Redis connection for caching.

        Returns:
            Array of shape (n_texts, embedding_dim) with L2-normalized embeddings.
        """
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, _EMBEDDING_DIM)

        texts_list = list(texts)
        n_texts = len(texts_list)
        embeddings = np.zeros((n_texts, _EMBEDDING_DIM), dtype=np.float32)
        texts_to_compute: list[tuple[int, str]] = []

        # Check cache for each text
        cache_keys = [_text_to_cache_key(t) for t in texts_list]
        cached_values = await redis.mget(cache_keys)

        for i, (text, cached) in enumerate(zip(texts_list, cached_values)):
            if cached is not None:
                embeddings[i] = np.frombuffer(cached, dtype=np.float32)
            else:
                texts_to_compute.append((i, text))

        cache_hits = n_texts - len(texts_to_compute)
        if cache_hits > 0:
            logger.info("Embedding cache: %d hits, %d misses", cache_hits, len(texts_to_compute))

        # Compute missing embeddings
        if texts_to_compute:
            indices, uncached_texts = zip(*texts_to_compute)
            new_embeddings = await self.embed(uncached_texts)

            # Store in cache and result array
            pipe = redis.pipeline()
            for idx, emb in zip(indices, new_embeddings):
                embeddings[idx] = emb
                cache_key = cache_keys[idx]
                pipe.set(cache_key, emb.tobytes())
            await pipe.execute()
            logger.info("Cached %d new embeddings", len(texts_to_compute))

        return embeddings

    def compute_similarity_matrix(
        self,
        embeddings_a: NDArray[np.float32],
        embeddings_b: NDArray[np.float32],
    ) -> NDArray[np.float32]:
        """Compute cosine similarity matrix between two sets of embeddings.

        Args:
            embeddings_a: First set of embeddings, shape (n, d).
            embeddings_b: Second set of embeddings, shape (m, d).

        Returns:
            Similarity matrix of shape (n, m).
        """
        return np.dot(embeddings_a, embeddings_b.T)


async def clear_old_embedding_cache(redis: "Redis") -> int:
    """Clear old 0.6B model embeddings from Redis.

    Args:
        redis: Redis connection.

    Returns:
        Number of keys deleted.
    """
    pattern = f"{_OLD_EMBEDDING_KEY_PREFIX}:*"
    deleted = 0
    async for key in redis.scan_iter(match=pattern):
        await redis.delete(key)
        deleted += 1
    if deleted > 0:
        logger.info("Cleared %d old embedding cache entries", deleted)
    return deleted


__all__ = ["EmbeddingService", "clear_old_embedding_cache"]
