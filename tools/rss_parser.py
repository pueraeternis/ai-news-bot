# tools/rss_parser.py

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from time import mktime, struct_time
from typing import TYPE_CHECKING, cast

import feedparser

from core.logging import get_logger
from core.models import NewsItem

if TYPE_CHECKING:
    from pydantic import HttpUrl

NEWS_TIME_WINDOW_HOURS = 24

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

        if not published_time:
            logger.debug("Skipping entry without a date from %s: '%s'", feed_url, entry.get("title", "N/A"))
            return None

        try:
            published_dt = datetime.fromtimestamp(mktime(published_time), tz=timezone.utc)
        except (ValueError, OverflowError) as e:
            logger.warning("Skipping entry with invalid date from %s: %s", feed_url, e)
            return None

        now = datetime.now(timezone.utc)
        time_difference = now - published_dt

        if time_difference > timedelta(hours=NEWS_TIME_WINDOW_HOURS):
            logger.debug("Skipping old entry from %s (published %s ago)", feed_url, time_difference)
            return None

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
