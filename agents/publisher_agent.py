# agents/publisher_agent.py

import re

import requests

from config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram's MarkdownV2 parse mode."""
    escape_chars = r"[_*\[\]()~`>#+\-=|{}.!]"
    return re.sub(f"({escape_chars})", r"\\\1", text)


def publish_to_telegram(post_text: str | None) -> bool:
    """Send the final post text to the specified Telegram channel."""
    if not post_text:
        logger.error("Publisher agent received no text to publish.")
        return False

    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHANNEL_ID

    escaped_text = escape_markdown_v2(post_text)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": escaped_text,
        "parse_mode": "MarkdownV2",
    }

    try:
        logger.info("Publishing post to Telegram channel: %s", chat_id)
        response = requests.post(url, data=payload, timeout=30)

        if response.status_code == 200:
            logger.info("Post successfully published to Telegram.")
            return True
        logger.error(
            "Failed to publish post to Telegram. Status: %s, Response: %s",
            response.status_code,
            response.json(),
        )
        return False

    except requests.exceptions.RequestException as e:
        logger.exception("A network error occurred while trying to publish to Telegram: %s", e)
        return False
