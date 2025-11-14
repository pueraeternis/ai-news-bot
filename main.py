# main.py

import click
from rich import print as rich_print

from agents.collector_agent import collect_news
from agents.filtering_agent import select_best_news_item
from core.logging import setup_logging


@click.group()
def cli() -> None:
    """AI News Bot CLI."""


@cli.command()
def process() -> None:
    """Run the complete process: collects news and selects the best one."""
    # 1. Set up logging. All logs will be written to a file.
    setup_logging()

    # 2. Launch the main function of our agent
    click.echo("Starting news collection...")
    news_items = collect_news()

    # 3. Filtering stage
    click.echo("\nStep 2: Selecting the best news item using LLM...")
    best_item = select_best_news_item(news_items)

    # 3. Output the result to the console
    if news_items:
        click.echo("\nThe best news item selected:")
        rich_print(best_item)
    else:
        click.echo("No news items were collected. Check logs for details.")


if __name__ == "__main__":
    cli()
