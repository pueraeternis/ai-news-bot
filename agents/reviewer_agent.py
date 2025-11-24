# agents/reviewer_agent.py

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.settings import settings
from core.logging import get_logger
from core.state_storage import StateStorage
from tools.publication_tool import markdown_to_html

logger = get_logger(__name__)


def get_review_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard with Publish/Reject buttons."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Publish", callback_data="action_publish")
    builder.button(text="❌ Reject", callback_data="action_reject")
    builder.adjust(2)
    return builder.as_markup()


async def send_for_review(post_text: str, news_title: str, source_url: str) -> bool:
    """
    Send the generated post to the work group for review and save state.
    """
    if not post_text:
        logger.error("Reviewer agent received no text.")
        return False

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    chat_id = settings.TELEGRAM_WORK_GROUP_ID

    try:
        html_text = markdown_to_html(post_text)

        admin_message_text = f"{html_text}\n\n➖➖➖➖➖➖➖\nℹ️ <b>Source:</b> {news_title}\n🔗 {source_url}"

        logger.info("Sending post for review to chat: %s", chat_id)
        message = await bot.send_message(
            chat_id=chat_id,
            text=admin_message_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=get_review_keyboard(),
        )

        storage = StateStorage()
        storage.save_pending_post(
            message_id=message.message_id,
            text=post_text,
            source_url=source_url,
        )

        logger.info("Post saved to pending storage with message_id: %s", message.message_id)
        return True

    except Exception as e:
        logger.exception("Failed to send post for review: %s", e)
        return False
    finally:
        await bot.session.close()
