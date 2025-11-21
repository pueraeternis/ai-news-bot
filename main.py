# main.py

from core.logging import get_logger, setup_logging
from graph.builder import create_graph

logger = get_logger(__name__)


def main() -> None:
    """Run the full workflow managed by the LangGraph."""
    setup_logging()

    logger.info("Compiling graph...")
    app = create_graph()
    logger.info("Graph compiled.")

    initial_state = {"topic": "AI News"}

    logger.info("RUNNING GRAPH WORKFLOW")
    final_state = app.invoke(initial_state)

    logger.info("GRAPH WORKFLOW COMPLETED")

    if final_state and "final_post" in final_state:
        final_post = final_state["final_post"]

        logger.info("FINAL TELEGRAM POST")
        print(final_post)
    else:
        logger.error("Failed to retrieve final post from graph state. Check the logs.")


if __name__ == "__main__":
    main()
