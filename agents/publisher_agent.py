# agents/publisher_agent.py

import re

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


def markdown_to_html(text: str) -> str:
    """Convert markdown text to HTML for Telegram."""
    # Escape HTML special characters first
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Italic *text*
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    # Convert markdown links to HTML anchor tags
    return re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)


async def publish_to_telegram(post_text: str | None) -> bool:
    """Send the final post text to the specified Telegram channel using aiogram and HTML."""
    if not post_text:
        logger.error("Publisher agent received no text to publish.")
        return False

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    chat_id = settings.TELEGRAM_CHANNEL_ID

    # Clean up and convert text
    clean_text = post_text.strip().strip("-").strip()
    clean_text = re.sub(r"### > ---", "", clean_text)
    html_text = markdown_to_html(clean_text)

    try:
        logger.info("Publishing post to Telegram channel: %s", chat_id)

        await bot.send_message(
            chat_id=chat_id,
            text=html_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

        logger.info("Post successfully published to Telegram.")
        return True

    except TelegramBadRequest as e:
        logger.exception("Failed to publish to Telegram due to formatting error: %s", e)
        return False
    except Exception as e:
        logger.exception("An unexpected error occurred with aiogram: %s", e)
        return False
    finally:
        await bot.session.close()
