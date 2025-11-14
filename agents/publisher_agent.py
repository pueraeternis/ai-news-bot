# agents/publisher_agent.py

import re

import requests

from config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


def markdown_to_html(text: str) -> str:
    """
    Convert markdown text to HTML for Telegram.
    Supports: **bold**, *italic*, [links](url), `inline code`, ```code blocks```,
    __underline__, _underline_, ~~strikethrough~~.
    """
    # Escape HTML special characters first
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    # Code blocks ```code```
    text = re.sub(r"```(.+?)```", r"<pre>\1</pre>", text, flags=re.DOTALL)

    # Inline code `code`
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # Bold **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # Italic *text* (not part of **bold**)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)

    # Links [text](url)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)

    # Underline __text__ or _text_
    text = re.sub(r"__(.+?)__", r"<u>\1</u>", text)
    text = re.sub(r"(?<!_)_([^_]+?)_(?!_)", r"<u>\1</u>", text)

    # Strikethrough ~~text~~
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)

    return text


def publish_to_telegram(post_text: str | None) -> bool:
    """
    Send the final post text to the specified Telegram channel using HTML parse mode.
    """
    if not post_text:
        logger.error("Publisher agent received no text to publish.")
        return False

    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHANNEL_ID

    # Clean up text
    clean_text = post_text.strip().strip("-").strip()

    # Convert markdown to HTML
    html_text = markdown_to_html(clean_text)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": html_text,
        "parse_mode": "HTML",
    }

    try:
        logger.info("Publishing post to Telegram channel: %s", chat_id)
        logger.debug("HTML preview: %s...", html_text[:200])

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            logger.info("Post successfully published to Telegram.")
            return True

        error_data = response.json()
        logger.error(
            "Failed to publish post to Telegram. Status: %s, Response: %s",
            response.status_code,
            error_data,
        )

        if "parse" in str(error_data).lower():
            logger.error("Problematic HTML snippet: %s", html_text[:300])

        return False

    except requests.exceptions.RequestException as e:
        logger.exception("Network error occurred while publishing to Telegram: %s", e)
        return False
