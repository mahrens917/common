"""Embedding service using Qwen3-Embedding-0.6B model with Redis caching."""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Sequence

import numpy as np
import torch
from numpy.typing import NDArray
from transformers import AutoModel, AutoTokenizer

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
_EMBEDDING_KEY_PREFIX = "embedding:qwen3"
_EMBEDDING_DIM = 1024  # Qwen3-Embedding-0.6B dimension


def _resolve_device() -> str:
    """Resolve the best available device for inference."""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _text_to_cache_key(text: str) -> str:
    """Generate a cache key for a text string."""
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{_EMBEDDING_KEY_PREFIX}:{text_hash}"


class EmbeddingService:
    """Service for computing text embeddings using Qwen3-Embedding-0.6B."""

    def __init__(self, device: str = "auto") -> None:
        """Initialize the embedding service.

        Args:
            device: Device to use for inference. "auto" selects the best available.
        """
        self._device = _resolve_device() if device == "auto" else device
        logger.info("Initializing EmbeddingService on device: %s", self._device)
        logger.info("Loading model: %s", _MODEL_NAME)

        self._tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, trust_remote_code=True)
        self._model = AutoModel.from_pretrained(_MODEL_NAME, trust_remote_code=True)
        self._model.to(self._device)
        self._model.eval()

        # Log model info to confirm it loaded
        num_params = sum(p.numel() for p in self._model.parameters())
        logger.info("Model loaded: %s (%.1fM parameters)", _MODEL_NAME, num_params / 1e6)

    @property
    def device(self) -> str:
        """Return the device being used."""
        return self._device

    def embed(self, texts: Sequence[str]) -> NDArray[np.float32]:
        """Compute embeddings for a batch of texts.

        Args:
            texts: Sequence of texts to embed.

        Returns:
            Array of shape (n_texts, embedding_dim) with L2-normalized embeddings.
        """
        if not texts:
            return np.array([], dtype=np.float32)

        inputs = self._tokenizer(
            list(texts),
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)
            embeddings = outputs.last_hidden_state[:, 0, :]
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu().numpy().astype(np.float32)

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
            return np.array([], dtype=np.float32)

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
            new_embeddings = self.embed(uncached_texts)

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


__all__ = ["EmbeddingService"]
