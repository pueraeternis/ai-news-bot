# main.py

import click
from rich.console import Console
from rich.markdown import Markdown

from core.logging import setup_logging
from graph.builder import create_graph

console = Console()


@click.group()
def cli() -> None:
    """AI News Bot CLI."""


@cli.command()
def process() -> None:
    """Run the full workflow managed by the LangGraph."""
    setup_logging()

    click.echo("Compiling graph...")
    app = create_graph()
    click.echo("Graph compiled.")

    initial_state = {"topic": "AI News"}

    click.echo("\n--- RUNNING GRAPH WORKFLOW ---")
    final_state = app.invoke(initial_state)

    click.echo("--- GRAPH WORKFLOW COMPLETED ---\n")

    if final_state and "final_post" in final_state:
        final_post = final_state["final_post"]

        click.echo("--- FINAL TELEGRAM POST ---")
        markdown = Markdown(final_post)
        console.print(markdown)
        click.echo("--- END OF POST ---")
    else:
        click.echo("Failed to retrieve final post from graph state. Check the logs.")


if __name__ == "__main__":
    cli()
