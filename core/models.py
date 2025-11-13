# core/models.py

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class NewsItem(BaseModel):
    """Structure for storing a single news item."""

    title: str
    url: HttpUrl
    summary: str
    source: str
    published_at: datetime | None = None
