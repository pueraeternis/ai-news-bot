# scripts/delete_article.py

from pathlib import Path
from typing import Any

import chromadb

DB_PATH = Path("db/chroma")
COLLECTION_NAME = "published_articles"
TARGET_TITLE = "Early experiments in accelerating science with GPT-5"


def delete_specific_article() -> None:
    if not DB_PATH.exists():
        print(f"❌ Database folder '{DB_PATH}' not found. Run the script from the project root.")
        return

    print(f"🔌 Connecting to ChromaDB at '{DB_PATH}'...")
    try:
        client = chromadb.PersistentClient(path=str(DB_PATH))
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        print(f"❌ Failed to access collection: {e}")
        return

    print(f"🔍 Searching for article with title: '{TARGET_TITLE}'...")

    # Chromadb returns a GetResult object, not a dict → use Any
    results: Any = collection.get(where={"title": TARGET_TITLE})
    ids_to_delete: list[str] = results.get("ids", [])

    if ids_to_delete:
        print(f"✅ Records found: {len(ids_to_delete)}")
        print(f"🆔 IDs to delete: {ids_to_delete}")

        collection.delete(ids=ids_to_delete)
        print("🗑️ Successfully deleted.")
        return

    print("⚠️ Article not found.")
    print("The title may differ by a character or space.")

    print("\n📋 Last 5 articles in the database:")
    peek: Any = collection.peek(limit=5)
    metadatas = peek.get("metadatas") or []

    for meta in metadatas:
        title = meta.get("title") if isinstance(meta, dict) else None
        print(f"- {title or 'No title'}")


if __name__ == "__main__":
    delete_specific_article()
