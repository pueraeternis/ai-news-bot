# tools/rss_parser.py

from collections.abc import Sequence
from datetime import datetime, timezone
from time import mktime, struct_time
from typing import TYPE_CHECKING, cast

import feedparser

from core.logging import get_logger
from core.models import NewsItem

if TYPE_CHECKING:
    from pydantic import HttpUrl

logger = get_logger(__name__)


def _coerce_to_str(value: object) -> str | None:
    """Convert a value to a string, handling sequences by returning the first string item."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, Sequence):
        for item in value:
            if isinstance(item, str):
                return item
        return None
    return str(value)


def _build_news_item(
    entry: feedparser.FeedParserDict,
    source_name: str,
    feed_url: str,
) -> NewsItem | None:
    """Build a NewsItem from an RSS feed entry."""
    try:
        raw_published = entry.get("published_parsed")
        published_time = raw_published if isinstance(raw_published, struct_time) else None
        published_dt = None
        if published_time:
            published_dt = datetime.fromtimestamp(mktime(published_time), tz=timezone.utc)

        title = _coerce_to_str(entry.get("title"))
        link = _coerce_to_str(entry.get("link"))
        summary = _coerce_to_str(entry.get("summary"))

        if not link:
            logger.warning("Skipping RSS entry without link from %s", feed_url)
            return None

        return NewsItem(
            title=title or "",
            url=cast("HttpUrl", link),
            summary=summary or "",
            source=source_name,
            published_at=published_dt,
        )
    except Exception:
        logger.exception("Failed to parse RSS entry from %s", feed_url)
        return None


def parse_rss_feed(feed_url: str, source_name: str) -> list[NewsItem]:
    """Parse an RSS feed and return the news items in the NewsItem format."""
    items = []
    feed = feedparser.parse(feed_url)

    for entry in feed.entries:
        news_item = _build_news_item(entry, source_name, feed_url)
        if news_item:
            items.append(news_item)

    return items
