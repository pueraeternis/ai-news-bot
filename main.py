# main.py

from core.logging import setup_logging
from graph.builder import create_graph


def main() -> None:
    """Run the full workflow managed by the LangGraph."""
    setup_logging()

    print("Compiling graph...")
    app = create_graph()
    print("Graph compiled.")

    initial_state = {"topic": "AI News"}

    print("\n--- RUNNING GRAPH WORKFLOW ---")
    final_state = app.invoke(initial_state)

    print("--- GRAPH WORKFLOW COMPLETED ---\n")

    if final_state and "final_post" in final_state:
        final_post = final_state["final_post"]

        print("--- FINAL TELEGRAM POST ---")
        print(final_post)
        print("---------------------------")
    else:
        print("Failed to retrieve final post from graph state. Check the logs.")


if __name__ == "__main__":
    main()
