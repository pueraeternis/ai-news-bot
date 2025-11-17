# agents/publisher_agent.py

import re

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


def markdown_to_html(text: str) -> str:
    """Convert markdown text to HTML for Telegram."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    return re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)


async def publish_to_telegram(post_text: str | None, image_url: str | None) -> bool:
    """Attempt to publish a post to Telegram. Returns True on success, False on failure."""
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
            logger.info("Attempting to publish post with image (caption length: %d)", len(html_text))
            await bot.send_photo(
                chat_id=chat_id,
                photo=image_url,
                caption=html_text,
                parse_mode="HTML",
            )
        else:
            logger.info("Attempting to publish text-only post.")
            await bot.send_message(
                chat_id=chat_id,
                text=html_text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

        logger.info("Post successfully published to Telegram.")
        return True

    except TelegramBadRequest as e:
        logger.warning("Publication failed (likely caption too long): %s", e.message)
        return False
    except Exception:
        logger.exception("An unexpected network or aiogram error occurred during publication.")
        return False
    finally:
        await bot.session.close()
