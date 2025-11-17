# agents/publisher_agent.py

import asyncio
import re

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from agents.summarizer_agent import TELEGRAM_CAPTION_MAX_LENGTH, summarize_for_caption
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


async def publish_to_telegram(post_text: str | None, image_url: str | None) -> bool:
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
        if image_url:
            caption_text = clean_text
            if len(clean_text) > TELEGRAM_CAPTION_MAX_LENGTH:
                caption_text = await asyncio.to_thread(summarize_for_caption, clean_text)

            html_caption = markdown_to_html(caption_text)

            logger.info("Publishing post with image to Telegram channel: %s", chat_id)
            await bot.send_photo(
                chat_id=chat_id,
                photo=image_url,
                caption=html_caption,
                parse_mode="HTML",
            )
        else:
            html_text = markdown_to_html(clean_text)
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
        logger.exception("Failed to publish to Telegram due to formatting/API error.")
        return False
    except Exception:
        logger.exception("An unexpected error occurred with aiogram.")
        return False
    finally:
        await bot.session.close()
