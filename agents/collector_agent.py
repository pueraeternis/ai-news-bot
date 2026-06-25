# agents/collector_agent.py

import json
import random
from pathlib import Path

from core.logging import get_logger
from core.models import NewsItem
from tools.rss_parser import parse_rss_feed

logger = get_logger(__name__)

SOURCES_FILE = Path(__file__).parent.parent / "data" / "ai_rss_sources_master.json"


def _load_rubrics() -> list[dict]:
    """Load the rubricator from the JSON file."""
    try:
        with SOURCES_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.exception("Failed to load sources from %s", SOURCES_FILE)
        return []


def _select_rubric(rubrics: list[dict]) -> dict | None:
    """Select a rubric based on weights."""
    if not rubrics:
        return None

    weights = [r.get("weight", 1.0) for r in rubrics]
    selected_rubric = random.choices(rubrics, weights=weights, k=1)[0]

    logger.info(
        "🎯 Selected Rubric: '%s' (Weight: %.2f)",
        selected_rubric["rubric"],
        selected_rubric.get("weight", 1.0),
    )
    return selected_rubric


def collect_news() -> list[NewsItem]:
    """
    Select a rubric and collects news from its sources.
    """
    rubrics = _load_rubrics()
    if not rubrics:
        return []

    # Select a rubric
    rubric = _select_rubric(rubrics)
    if not rubric:
        return []

    all_news = []
    sources = rubric.get("sources", [])

    logger.info("Starting news collection for rubric: '%s' (%d sources)", rubric["rubric"], len(sources))

    # Collect news only from this rubric
    for source in sources:
        name = source.get("title")
        url = source.get("feed")

        if not name or not url:
            continue

        try:
            news_from_source = parse_rss_feed(feed_url=url, source_name=name)
            all_news.extend(news_from_source)
            if news_from_source:
                logger.info("Found %d news items from %s.", len(news_from_source), name)
        except Exception:
            logger.exception("An unexpected error occurred while processing source: %s", name)

    logger.info("Total news items collected for rubric '%s': %d", rubric["rubric"], len(all_news))

    return all_news
