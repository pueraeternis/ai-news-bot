# main.py

import click
from rich.console import Console
from rich.markdown import Markdown

from core.logging import setup_logging
from graph_builder import create_graph

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
    final_state = None
    for event in app.stream(initial_state):
        final_state = event

    click.echo("--- GRAPH WORKFLOW COMPLETED ---\n")

    if final_state:
        last_node_output = next(iter(final_state.values()))
        russian_post = last_node_output.get("russian_post")

        if russian_post:
            click.echo("--- FINAL TELEGRAM POST (RUSSIAN) ---")
            markdown = Markdown(russian_post)
            console.print(markdown)
            click.echo("--- END OF POST ---")
        else:
            click.echo("Failed to retrieve final post from graph state.")
    else:
        click.echo("Graph did not return a final state.")


if __name__ == "__main__":
    cli()
