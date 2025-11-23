# agents/internal_publisher_agent.py

from io import BytesIO

from aiogram import Bot
from aiogram.types import BufferedInputFile

from config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


async def send_article_file(article_text: str | None, topic: str) -> bool:
    """
    Create an in-memory .md file from the text and sends it to the private work group.
    """
    if not article_text:
        logger.warning("Internal publisher received empty text.")
        return False

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    chat_id = settings.TELEGRAM_WORK_GROUP_ID

    try:
        # Create an in-memory file
        file_data = article_text.encode("utf-8")
        file_stream = BytesIO(file_data)

        # Generate a safe filename from the topic title
        safe_filename = "".join([c for c in topic if c.isalnum() or c in (" ", "-", "_")]).strip()
        safe_filename = safe_filename.replace(" ", "_")[:50]  # Limit the length
        filename = f"{safe_filename}.md"

        # Prepare the object for sending
        document = BufferedInputFile(file_stream.getvalue(), filename=filename)

        logger.info("Sending long-read article to work group: %s", chat_id)

        await bot.send_document(
            chat_id=chat_id,
            document=document,
            caption=f"📝 **New Long Read Generated**\nTopic: {topic}",
            parse_mode="Markdown",
        )

        logger.info("Article file sent successfully.")
        return True

    except Exception:
        logger.exception("Failed to send article file to work group.")
        return False
    finally:
        await bot.session.close()
