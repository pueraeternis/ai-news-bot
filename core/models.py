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
    """Defines the state of the LangGraph. This is a dictionary that is passed from one node (agent) to another."""

    topic: str
    all_news_items: list[NewsItem]
    selected_news_item: NewsItem
    post_plan: str
    english_post: str
    russian_post: str
    final_post: str
    image_url: str | None
