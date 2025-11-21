# main.py

import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import settings
from core.logging import get_logger, setup_logging
from graph.builder import create_graph

logger = get_logger(__name__)


def run_workflow() -> None:
    """
    Execute a single iteration of the news gathering and publishing workflow.
    """
    logger.info("--- STARTING WORKFLOW ---")

    try:
        logger.info("Compiling graph...")
        app = create_graph()

        initial_state = {"topic": "AI News"}

        logger.info("RUNNING GRAPH WORKFLOW")
        final_state = app.invoke(initial_state)

        logger.info("GRAPH WORKFLOW COMPLETED")

        if final_state and "final_post" in final_state:
            final_post = final_state["final_post"]

            print("\n--- FINAL TELEGRAM POST ---")
            print(final_post)
            print("---------------------------\n")
        else:
            logger.error("Failed to retrieve final post from graph state.")

    except Exception:
        logger.exception("Critical error during workflow execution")

    logger.info("--- WORKFLOW FINISHED ---")


def start_scheduler() -> None:
    """
    Start the scheduler to run the workflow at specific Moscow times.
    """
    scheduler = BlockingScheduler(timezone=settings.MOSCOW_TZ)

    # Create a Cron trigger.
    # hour='8,11,...' means "run at these hours"
    # minute=0 means "at exactly 00 minutes"
    hours_str = ",".join(map(str, settings.POSTING_HOURS))
    trigger = CronTrigger(hour=hours_str, minute=0, timezone=settings.MOSCOW_TZ)

    scheduler.add_job(run_workflow, trigger)

    print("🤖 Bot started!")
    print(f"🕒 Timezone: {settings.MOSCOW_TZ}")
    print(f"📅 Schedule (Moscow time): {hours_str}:00")
    print(f"Server time: {datetime.now(tz=settings.MOSCOW_TZ)}")
    print("Press Ctrl+C to exit.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Bot stopped.")


def main() -> None:
    setup_logging()

    # Simple argument parsing.
    # If 'start' is passed, launch the scheduler.
    # Otherwise, run the workflow once (for testing).
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        start_scheduler()
    else:
        print("🚀 Manual run mode...")
        run_workflow()


if __name__ == "__main__":
    main()
