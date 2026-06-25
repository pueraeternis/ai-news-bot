# main.py

import asyncio
import contextlib
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import settings
from core.logging import get_logger, setup_logging
from core.state_storage import StateStorage
from core.workflow_progress import print_node_complete, print_workflow_end, print_workflow_start
from graph.builder import create_graph
from tools.publication_tool import markdown_to_html, publish_post

logger = get_logger(__name__)

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


# --- WORKFLOW EXECUTION FUNCTION ---


def _run_graph(app, initial_state: dict, *, verbose: bool) -> None:
    config = {"recursion_limit": 50}
    if verbose:
        print_workflow_start()
        for event in app.stream(initial_state, config):
            for node_name, update in event.items():
                print_node_complete(node_name, update)
        return

    app.invoke(initial_state, config)


async def run_workflow(*, verbose: bool = False) -> None:
    """
    Execute a single iteration of the news collection and publishing workflow.
    """
    logger.info("--- STARTING WORKFLOW ---")
    try:
        app = create_graph()
        initial_state = {"topic": "AI News"}

        logger.info("RUNNING GRAPH WORKFLOW")

        # Run the synchronous graph in a thread to avoid blocking the bot
        await asyncio.to_thread(_run_graph, app, initial_state, verbose=verbose)

        logger.info("GRAPH WORKFLOW COMPLETED (Result sent for review)")
        if verbose:
            print_workflow_end(success=True)

    except Exception as e:
        logger.exception("Critical error during workflow execution")
        if verbose:
            print_workflow_end(success=False, error=str(e))

    logger.info("--- WORKFLOW FINISHED ---")


# --- TELEGRAM HANDLERS (BUTTON LOGIC) ---


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Welcome message for the admin."""
    hours_str = ",".join(map(str, settings.POSTING_HOURS))
    await message.answer(
        f"👋 Hi! I'm the AI News editor bot.\n"
        f"I will send posts for moderation to this chat (ID: {message.chat.id}).\n"
        f"Schedule: {hours_str} (MSK).",
    )


@dp.callback_query(F.data == "action_publish")
async def on_publish_click(callback: CallbackQuery) -> None:
    """Handle 'Publish' button click."""
    if not isinstance(callback.message, Message):
        return

    message_id = callback.message.message_id
    storage = StateStorage()
    post_data = storage.get_pending_post(message_id)

    if not post_data:
        await callback.answer("⚠️ Error: post data not found.", show_alert=True)
        with contextlib.suppress(Exception):
            await callback.message.edit_reply_markup(reply_markup=None)
        return

    await callback.answer("🚀 Publishing...")

    try:
        success = await publish_post(post_data["text"])

        if success:
            final_html = markdown_to_html(post_data["text"])
            new_text = final_html + "\n\n✅ <b>PUBLISHED</b>"

            await callback.message.edit_text(
                text=new_text,
                parse_mode="HTML",
                reply_markup=None,
                disable_web_page_preview=True,
            )
            storage.delete_pending_post(message_id)
        else:
            await callback.message.reply("❌ Error during publication. Check logs.")

    except Exception as e:
        logger.exception("Error processing publish click: %s", e)
        await callback.message.reply("❌ An error occurred while processing.")


@dp.callback_query(F.data == "action_reject")
async def on_reject_click(callback: CallbackQuery) -> None:
    """Handle 'Reject' button click."""
    if not isinstance(callback.message, Message):
        return

    message_id = callback.message.message_id
    storage = StateStorage()
    post_data = storage.get_pending_post(message_id)
    storage.delete_pending_post(message_id)

    try:
        status_line = "\n\n❌ <b>REJECTED</b>"

        if post_data:
            final_html = markdown_to_html(post_data["text"])
            new_text = final_html + status_line
        else:
            current_text = callback.message.text or "Post"
            new_text = current_text + status_line

        await callback.message.edit_text(
            text=new_text,
            parse_mode="HTML",
            reply_markup=None,
            disable_web_page_preview=True,
        )

    except Exception as e:
        logger.warning("Error updating rejection message: %s", e)
        with contextlib.suppress(Exception):
            await callback.message.edit_reply_markup(reply_markup=None)

    await callback.answer("Post rejected.")


# --- START MODES ---


async def start_scheduler_and_bot() -> None:
    """
    DAEMON MODE: Runs both the scheduler and bot polling.
    """
    scheduler = AsyncIOScheduler(timezone=settings.MOSCOW_TZ)
    hours_str = ",".join(map(str, settings.POSTING_HOURS))
    trigger = CronTrigger(hour=hours_str, minute=0, timezone=settings.MOSCOW_TZ)

    scheduler.add_job(run_workflow, trigger)
    scheduler.start()

    print("🤖 Bot started!")
    print(f"🕒 Timezone: {settings.MOSCOW_TZ}")
    print(f"📅 Schedule (Moscow time): {hours_str}:00")
    print(f"Current time: {datetime.now(tz=settings.MOSCOW_TZ)}")
    print("Press Ctrl+C to exit.")

    await dp.start_polling(bot, drop_pending_updates=True)


def main() -> None:
    is_daemon = len(sys.argv) > 1 and sys.argv[1] == "start"
    setup_logging(console=not is_daemon)

    if is_daemon:
        asyncio.run(start_scheduler_and_bot())
    else:
        print("🚀 Manual run mode — progress below (details also in logs/bot.log)\n")
        asyncio.run(run_workflow(verbose=True))


if __name__ == "__main__":
    main()
