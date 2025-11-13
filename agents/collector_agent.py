# agents/collector_agent.py

import json
from pathlib import Path

from core.logging import get_logger
from core.models import NewsItem
from tools.rss_parser import parse_rss_feed

logger = get_logger(__name__)

SOURCES_FILE = Path(__file__).parent.parent / "data" / "sources.json"


def collect_news() -> list[NewsItem]:
    """Collect news from all RSS sources listed in sources.json."""
    all_news = []

    logger.info("Starting news collection from RSS feeds.")

    try:
        with SOURCES_FILE.open("r", encoding="utf-8") as f:
            sources_data = json.load(f)
    except FileNotFoundError:
        logger.exception("Sources file not found at %s", SOURCES_FILE)
        return []
    except json.JSONDecodeError:
        logger.exception("Failed to decode JSON from %s", SOURCES_FILE)
        return []

    for source in sources_data.get("rss_feeds", []):
        name = source.get("name")
        url = source.get("url")

        if not name or not url:
            logger.warning("Skipping source with missing name or url: %s", source)
            continue

        logger.info("Collecting news from: %s", name)
        try:
            news_from_source = parse_rss_feed(feed_url=url, source_name=name)
            all_news.extend(news_from_source)
            logger.info("Found %d news items from %s.", len(news_from_source), name)
        except Exception:
            logger.exception("An unexpected error occurred while processing source: %s", name)

    logger.info("Total news items collected: %d", len(all_news))

    return all_news
