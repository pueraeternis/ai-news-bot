import asyncio
from io import BytesIO

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile

from config.settings import settings


async def test_send_file() -> None:
    print(f"🤖 Bot Token: {settings.TELEGRAM_BOT_TOKEN[:5]}...***")
    print(f"📂 Target Chat ID: '{settings.TELEGRAM_WORK_GROUP_ID}'")

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

    dummy_text = "# Test File\n\nThis is a test file for checking the bot's access to the chat."
    file_data = dummy_text.encode("utf-8")
    file_stream = BytesIO(file_data)
    document = BufferedInputFile(file_stream.getvalue(), filename="test_article.md")

    try:
        print("⏳ Attempting to send file...")
        await bot.send_document(
            chat_id=settings.TELEGRAM_WORK_GROUP_ID,
            document=document,
            caption="🧪 Test message. If you are reading this, the ID is correct.",
        )
        print("\n✅ SUCCESS! Message successfully delivered.")
        print("Settings are correct. You can launch the main bot.")

    except TelegramBadRequest as e:
        print(f"\n❌ FAILED: {e}")
        print("-" * 40)
        print("💡 POSSIBLE SOLUTIONS:")
        print("1. The bot is not a member of this group. Add it.")
        print("2. The bot is in the group but does not have permission to send messages.")
        print("3. The group ID is incorrect.")

        current_id = str(settings.TELEGRAM_WORK_GROUP_ID)
        if not current_id.startswith("-100"):
            print("\n👉 TRY ADDING THE -100 PREFIX:")
            print(f'Update in .env: TELEGRAM_WORK_GROUP_ID="-100{current_id}"')

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(test_send_file())
