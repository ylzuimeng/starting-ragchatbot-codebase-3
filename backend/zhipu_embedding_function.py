"""ZhipuAI embedding function for ChromaDB.

This module provides a custom embedding function that uses ZhipuAI's online
embedding API instead of local models. It implements exponential backoff retry
logic for handling network failures and rate limits.
"""

import time
import numpy as np
from typing import List, Union, Optional
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from zhipuai import ZhipuAI


class ZhipuEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    ChromaDB embedding function using ZhipuAI's embedding API.

    This class implements the EmbeddingFunction interface required by ChromaDB,
    using ZhipuAI's embedding-3 model which produces 2048-dimensional vectors.
    """

    def __init__(self, api_key: str, model_name: str = "embedding-3"):
        """
        Initialize the ZhipuAI embedding function.

        Args:
            api_key: ZhipuAI API key for authentication
            model_name: Model to use for embeddings (default: embedding-3)

        Raises:
            ValueError: If api_key is None or empty
        """
        if not api_key:
            raise ValueError(
                "ZHIPUAI_API_KEY is required. Set it in .env file or pass it directly. "
                "Get your API key at: https://open.bigmodel.cn/"
            )

        self.api_key = api_key
        self.model_name = model_name
        self.client = ZhipuAI(api_key=api_key)
        print(f"✓ Using ZhipuAI embedding: {model_name}")

    def __call__(self, input: Documents) -> Embeddings:
        """
        Generate embeddings for the given documents.

        This method implements:
        - Automatic batching (max 64 items per batch per ZhipuAI API limit)
        - Exponential backoff retry logic for network failures and rate limits

        Args:
            input: Documents to embed (string or list of strings)

        Returns:
            List of embedding vectors as numpy arrays (float32)

        Raises:
            Exception: If API calls fail after all retries
        """
        # Convert single string to list for uniform processing
        texts = [input] if isinstance(input, str) else list(input)

        # ZhipuAI API limit: max 64 items per batch
        BATCH_SIZE = 64
        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            batch_embeddings = self._embed_batch_with_retry(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def _embed_batch_with_retry(self, texts: List[str]) -> List[np.ndarray]:
        """
        Embed a batch of texts with retry logic.

        Args:
            texts: Batch of texts to embed

        Returns:
            List of embedding vectors as numpy arrays (float32)

        Raises:
            Exception: If API calls fail after all retries
        """
        max_retries = 3
        base_delay = 1.0  # seconds

        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=texts
                )

                # Extract embeddings and convert to numpy arrays with float32 dtype
                embeddings = [
                    np.array(item.embedding, dtype=np.float32)
                    for item in response.data
                ]

                return embeddings

            except Exception as e:
                error_str = str(e)

                # Check for authentication errors - these should fail immediately
                if "401" in error_str or "authentication" in error_str.lower():
                    raise Exception(
                        f"ZhipuAI authentication failed. Please check your API key. "
                        f"Error: {error_str}"
                    )

                # For other errors, retry with exponential backoff
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(
                        f"⚠ ZhipuAI API error (attempt {attempt + 1}/{max_retries}): "
                        f"{error_str}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    # Final attempt failed
                    raise Exception(
                        f"ZhipuAI API failed after {max_retries} attempts. "
                        f"Last error: {error_str}"
                    )

        # This should never be reached, but kept for completeness
        raise Exception("Unexpected error in embedding generation")
