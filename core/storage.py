# core/storage.py

from __future__ import annotations

from typing import Any, cast

import chromadb

from core.logging import get_logger
from tools.embedding_tool import get_embedding

logger = get_logger(__name__)

DB_PATH = "db/chroma"
COLLECTION_NAME = "published_articles"


class VectorStorage:
    """Persistent vector storage for articles using ChromaDB."""

    def __init__(self) -> None:
        client = chromadb.PersistentClient(path=DB_PATH)
        self.collection = client.get_or_create_collection(name=COLLECTION_NAME)

    def add_article(self, article_id: str, text_to_embed: str, metadata: dict[str, Any]) -> None:
        """Generate embedding and add article to storage."""
        embedding = get_embedding(text_to_embed)

        existing = cast("dict[str, Any]", self.collection.get(ids=[article_id]) or {})
        if existing.get("ids"):
            logger.warning("Article with ID %s already exists. Skipping.", article_id)
            return

        self.collection.add(
            ids=[article_id],
            embeddings=[embedding],
            metadatas=[metadata],
        )
        logger.info("Article '%s' added to vector storage.", metadata.get("title", "N/A"))

    def is_duplicate(self, text_to_embed: str, threshold: float = 0.70) -> bool:
        """Check if a semantically similar article already exists."""
        if self.collection.count() == 0:
            return False

        embedding = get_embedding(text_to_embed)
        results = cast("dict[str, Any]", self.collection.query(query_embeddings=[embedding], n_results=1) or {})

        if not results.get("distances") or not results["distances"][0]:
            return False

        distances = cast("list[list[float]]", results.get("distances"))
        distance = distances[0][0]
        similarity = 1 - distance

        metadatas = cast("list[list[dict[str, Any]]]", results.get("metadatas", [[{}]]))
        metadata = metadatas[0][0] or {}
        similar_title = metadata.get("title", "Unknown")

        logger.info("Similarity check: %.4f with '%s'", similarity, similar_title)

        if similarity > threshold:
            logger.warning(
                "DUPLICATE DETECTED (Similarity: %.2f > %.2f). This news is too similar to '%s'.",
                similarity,
                threshold,
                similar_title,
            )
            return True

        return False
