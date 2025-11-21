# tools/embedding_tool.py

import logging
from functools import lru_cache

import torch
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"


@lru_cache(maxsize=1)
def _get_cached_embedding_client() -> HuggingFaceEmbeddings:
    """Create the embeddings client once and cache it for reuse."""
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():  # For Mac M1/M2/M3
        device = "mps"
    else:
        device = "cpu"

    logger.info("Initializing embedding model '%s' on device: %s", EMBEDDING_MODEL_NAME, device)

    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_embedding_client() -> HuggingFaceEmbeddings:
    """Initialize and return a Hugging Face embeddings client."""
    return _get_cached_embedding_client()


def get_embedding(text: str) -> list[float]:
    """Generate embedding for a single text."""
    client = get_embedding_client()
    return client.embed_query(text)


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts (more efficient than one by one)."""
    client = get_embedding_client()
    return client.embed_documents(texts)
