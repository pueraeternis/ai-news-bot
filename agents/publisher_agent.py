# agents/publisher_agent.py

import asyncio
import re

from aiogram import Bot

from agents.summarizer_agent import summarize_for_caption
from config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


TELEGRAM_CAPTION_LIMIT = 900
INITIAL_SUMMARY_TOKENS = 800
TOKEN_DECREMENT = 75
MAX_RETRY_ATTEMPTS = 5


def markdown_to_html(text: str) -> str:
    """Convert markdown text to HTML for Telegram."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    return re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)


async def publish_to_telegram(post_text: str | None, image_url: str | None) -> bool:
    if not post_text:
        logger.error("Publisher agent received no text to publish.")
        return False

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    chat_id = settings.TELEGRAM_CHANNEL_ID
    clean_text = post_text.strip().strip("-").strip()

    try:
        if image_url:
            html_caption = markdown_to_html(clean_text)
            if len(html_caption) <= TELEGRAM_CAPTION_LIMIT:
                logger.info("Caption fits the limit. Publishing photo with full text.")
                await bot.send_photo(chat_id=chat_id, photo=image_url, caption=html_caption, parse_mode="HTML")
                return True

            logger.info("Caption is too long. Starting summarization cycle.")
            current_tokens = INITIAL_SUMMARY_TOKENS

            for attempt in range(MAX_RETRY_ATTEMPTS):
                logger.info("Summarization attempt %d with max_tokens=%d", attempt + 1, current_tokens)

                summarized_text = await asyncio.to_thread(summarize_for_caption, clean_text, current_tokens)
                html_caption = markdown_to_html(summarized_text)

                if len(html_caption) <= TELEGRAM_CAPTION_LIMIT:
                    logger.info("Summarization successful. Publishing photo with caption (length: %d)", len(html_caption))
                    await bot.send_photo(chat_id=chat_id, photo=image_url, caption=html_caption, parse_mode="HTML")
                    return True

                current_tokens -= TOKEN_DECREMENT

            logger.warning(
                "All summarization attempts failed. Switching to fallback: publishing text-only post.",
            )
            html_text = markdown_to_html(clean_text)
            await bot.send_message(
                chat_id=chat_id,
                text=html_text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

        else:
            html_text = markdown_to_html(clean_text)
            logger.info("Publishing text-only post.")
            await bot.send_message(
                chat_id=chat_id,
                text=html_text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

        logger.info("Post successfully published.")
        return True

    except Exception:
        logger.exception("A critical error occurred in the publisher agent.")
        return False
    finally:
        await bot.session.close()
