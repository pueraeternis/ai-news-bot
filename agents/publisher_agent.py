# agents/publisher_agent.py

import re

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


def _cleanup_markdown_artifacts(text: str) -> str:
    """
    Remove Markdown artifacts that don't render well in Telegram
    (headers, separators, blockquotes) and fix spacing.
    """
    # 1. Base cleanup
    clean = text.strip().strip("-").strip()

    # 2. Remove headers (### Title)
    clean = re.sub(r"^#+\s*", "", clean, flags=re.MULTILINE)

    # 3. Remove horizontal rules (---) on a separate line
    clean = re.sub(r"^\s*-{3,}\s*$", "", clean, flags=re.MULTILINE)

    # 4. Remove blockquotes (>) at the start of lines
    clean = re.sub(r"^>\s?", "", clean, flags=re.MULTILINE)

    # 5. Collapse excessive newlines (3+ -> 2) to keep paragraphs neat
    clean = re.sub(r"\n{3,}", "\n\n", clean)

    return clean.strip()


def markdown_to_html(text: str) -> str:
    """Convert supported Markdown syntax to HTML for Telegram."""
    # Escape HTML special characters first
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Bold **text** -> <b>text</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # Italic *text* -> <i>text</i>
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)

    # Links [text](url) -> <a href="url">text</a>
    return re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)


async def publish_to_telegram(post_text: str) -> bool:
    """
    Publish the final text post to Telegram.
    """
    if not post_text:
        logger.error("Publisher agent received no text to publish.")
        return False

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    chat_id = settings.TELEGRAM_CHANNEL_ID

    # --- Processing ---
    clean_text = _cleanup_markdown_artifacts(post_text)
    html_text = markdown_to_html(clean_text)

    try:
        logger.info("Publishing text-only post to Telegram channel: %s", chat_id)

        await bot.send_message(
            chat_id=chat_id,
            text=html_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

        logger.info("Post successfully published to Telegram.")
        return True

    except TelegramBadRequest:
        logger.exception("Failed to publish to Telegram due to API error.")
        return False
    except Exception:
        logger.exception("An unexpected error occurred with aiogram.")
        return False
    finally:
        await bot.session.close()
