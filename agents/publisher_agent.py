# agents/publisher_agent.py

import asyncio
import re

import vk_api
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


def clean_markdown_for_vk(text: str) -> str:
    """
    Remove Markdown formatting for VK, converting links to text representation.
    """
    # Bold (**text**) -> text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    # Italic (*text*) -> text
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"\1", text)
    # Links [text](url) -> text (url)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", text)
    return text


async def _send_to_telegram(clean_text: str) -> bool:
    """Send to Telegram."""
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    chat_id = settings.TELEGRAM_CHANNEL_ID
    html_text = markdown_to_html(clean_text)

    try:
        logger.info("Publishing to Telegram channel: %s", chat_id)
        await bot.send_message(
            chat_id=chat_id,
            text=html_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        logger.info("Successfully published to Telegram.")
        return True
    except TelegramBadRequest:
        logger.exception("Failed to publish to Telegram due to API error.")
        return False
    except Exception:
        logger.exception("Unexpected error sending to Telegram.")
        return False
    finally:
        await bot.session.close()


def _send_to_vk(clean_text: str) -> bool:
    """Send to VK."""
    try:
        vk_text = clean_markdown_for_vk(clean_text)

        # Authorization
        vk_session = vk_api.VkApi(token=settings.VK_ACCESS_TOKEN)
        vk = vk_session.get_api()

        # The group ID must be negative in order to post as the group
        owner_id = -abs(int(settings.VK_GROUP_ID))

        logger.info("Publishing to VK community: %s", owner_id)
        vk.wall.post(
            owner_id=owner_id,
            message=vk_text,
            from_group=1,
        )
        logger.info("Successfully published to VK.")
        return True
    except Exception:
        logger.exception("Failed to publish to VK.")
        return False


async def publish_post(post_text: str) -> bool:
    """
    Publish the post to ALL configured social networks.
    """
    if not post_text:
        logger.error("Publisher agent received no text to publish.")
        return False

    # General cleanup of unwanted artifacts
    clean_text = _cleanup_markdown_artifacts(post_text)

    # Start publishing
    # Telegram (asynchronously)
    tg_success = await _send_to_telegram(clean_text)

    # VK (synchronously, run in thread to avoid blocking async loop)
    vk_success = await asyncio.to_thread(_send_to_vk, clean_text)

    # Consider it a success if at least one social network accepted the post
    return tg_success or vk_success
