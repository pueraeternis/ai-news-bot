# core/models.py

from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, HttpUrl


class NewsItem(BaseModel):
    """Structure for storing a single news item."""

    title: str
    url: HttpUrl
    summary: str
    source: str
    published_at: datetime | None = None


class AgentState(TypedDict):
    """Defines the state of the LangGraph."""

    topic: str
    all_news_items: list[NewsItem]
    selected_news_item: NewsItem
    text_to_embed: str

    post_plan: str
    english_post: str
    russian_post: str
    final_post: str

    excluded_urls: list[str]
    is_duplicate: bool
